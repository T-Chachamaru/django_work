import json
import requests
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from app import models
from app.forms.file import FolderModelForm, FileModelForm
from utils.tencent.cos import CosManager

def file(request, project_id):
    """
    文件库主视图。
    - GET: 显示文件和文件夹列表，支持进入子文件夹。
    - POST: (AJAX) 处理新建或编辑文件夹。
    """
    folder_id = request.GET.get('folder', "")
    parent_object = None
    if folder_id.isdecimal():
        parent_object = get_object_or_404(models.FileRepository, id=int(folder_id), file_type=2, project_id=project_id)

    if request.method == 'POST':
        fid = request.POST.get('fid', '')
        edit_object = None
        if fid.isdecimal():
            edit_object = get_object_or_404(models.FileRepository, id=int(fid), file_type=2, project_id=project_id)

        form_class = FolderModelForm
        form = form_class(request, parent_object=parent_object, data=request.POST,
                          instance=edit_object) if edit_object else form_class(request, parent_object=parent_object,
                                                                               data=request.POST)
        if form.is_valid():
            form.instance.project = request.tracer.project
            form.instance.file_type = 2
            form.instance.update_user = request.tracer.user
            form.instance.parent = parent_object
            form.save()
            return JsonResponse({'status': True})
        return JsonResponse({'status': False, 'error': form.errors})

    breadcrumb_list = []
    parent = parent_object
    while parent:
        breadcrumb_list.insert(0, {'id': parent.id, 'name': parent.name})
        parent = parent.parent

    queryset = models.FileRepository.objects.filter(project_id=project_id)
    file_object_list = queryset.filter(parent=parent_object).order_by('-file_type',
                                                                      'name') if parent_object else queryset.filter(
        parent__isnull=True).order_by('-file_type', 'name')

    form = FolderModelForm(request, parent_object=parent_object)
    context = {
        'form': form,
        'file_object_list': file_object_list,
        'breadcrumb_list': breadcrumb_list,
        'folder_object': parent_object,
    }
    return render(request, 'app/file.html', context)

@csrf_exempt
def file_delete(request, project_id):
    """ (AJAX) 删除文件或文件夹（及其所有内容） """
    fid = request.GET.get('fid')
    delete_object = get_object_or_404(models.FileRepository, id=fid, project_id=project_id)
    cos_client = CosManager(region=request.tracer.project.region)

    try:
        # 使用数据库事务确保数据一致性
        with transaction.atomic():
            # 情况一：删除的是文件
            if delete_object.file_type == 1:
                request.tracer.project.use_space -= delete_object.file_size
                request.tracer.project.save()
                cos_client.delete_file(request.tracer.project.bucket, delete_object.key)
                delete_object.delete()
            # 情况二：删除的是文件夹
            else:
                total_size = 0
                key_list = []
                folder_list = [delete_object]
                for folder in folder_list:
                    children = models.FileRepository.objects.filter(project_id=project_id, parent=folder)
                    for child in children:
                        if child.file_type == 2:
                            folder_list.append(child)
                        else:
                            total_size += child.file_size
                            key_list.append({"Key": child.key})

                if key_list:
                    cos_client.delete_file_list(request.tracer.project.bucket, key_list)
                if total_size:
                    request.tracer.project.use_space -= total_size
                    request.tracer.project.save()
                delete_object.delete()
    except Exception as e:
        return JsonResponse({'status': False, 'error': "删除失败，请稍后重试。"})

    return JsonResponse({'status': True})

@csrf_exempt
def cos_credential(request, project_id):
    """ (AJAX) 获取腾讯云COS上传临时凭证，并在获取前进行容量校验 """
    file_list = json.loads(request.body.decode('utf-8'))
    per_file_limit = request.tracer.price_policy.per_file_size * 1024 * 1024
    total_project_space = request.tracer.price_policy.project_space * 1024 * 1024 * 1024
    total_upload_size = 0
    for item in file_list:
        if item['size'] > per_file_limit:
            msg = f"单文件超出限制（最大{request.tracer.price_policy.per_file_size}M），文件：{item['name']}"
            return JsonResponse({'status': False, 'error': msg})
        total_upload_size += item['size']

    if request.tracer.project.use_space + total_upload_size > total_project_space:
        return JsonResponse({'status': False, 'error': '项目容量超过限制，请升级套餐。'})

    cos_client = CosManager(region=request.tracer.project.region)
    data_dict = cos_client.get_credential(request.tracer.project.bucket)
    return JsonResponse({'status': True, 'data': data_dict})


@csrf_exempt
def file_post(request, project_id):
    """ (AJAX) 在文件成功上传到COS后，将文件元数据写入数据库 """
    form = FileModelForm(request, data=request.POST)
    if form.is_valid():
        try:
            with transaction.atomic():
                cleaned_data = form.cleaned_data
                cleaned_data.pop('etag')
                cleaned_data.update({
                    'project': request.tracer.project,
                    'file_type': 1,
                    'update_user': request.tracer.user
                })
                instance = models.FileRepository.objects.create(**cleaned_data)
                request.tracer.project.use_space += cleaned_data['file_size']
                request.tracer.project.save()

        except Exception as e:
            return JsonResponse({'status': False, 'error': "文件信息写入失败。"})

        result = {
            'id': instance.id,
            'name': instance.name,
            'file_size': instance.file_size,
            'username': instance.update_user.username,
            'datetime': instance.update_datetime.strftime('%Y-%m-%d %H:%M'),
            'download_url': reverse('file_download', kwargs={'project_id': project_id, 'file_id': instance.id}),
        }
        return JsonResponse({'status': True, 'data': result})

    return JsonResponse({'status': False, 'error': form.errors})


def file_download(request, project_id, file_id):
    """ 文件下载视图，通过后端代理从COS下载 """
    file_object = get_object_or_404(models.FileRepository, id=file_id, project_id=project_id)
    res = requests.get(file_object.file_path, stream=True)

    if res.status_code != 200:
        return HttpResponse("文件获取失败", status=404)

    response = HttpResponse(res.iter_content(chunk_size=8192), content_type=res.headers['Content-Type'])
    response['Content-Disposition'] = f'attachment; filename="{file_object.name}"'
    return response