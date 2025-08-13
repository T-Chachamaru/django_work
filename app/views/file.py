import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from app import models
from app.forms.file import FolderModelForm
from utils.tencent.cos import delete_file, delete_file_list, credential

def file(request, project_id):
    """文件库视图，处理文件和文件夹的展示、新建与编辑。"""
    parent_object = None
    folder_id = request.GET.get('folder', "")
    if folder_id.isdecimal():
        parent_object = models.FileRepository.objects.filter(
            id=int(folder_id), file_type=2, project=request.tracer.project
        ).first()

    if request.method == 'GET':
        breadcrumb_list = []
        parent = parent_object
        while parent:
            breadcrumb_list.insert(0, {'id': parent.id, 'name': parent.name})
            parent = parent.parent
        queryset = models.FileRepository.objects.filter(project=request.tracer.project)
        if parent_object:
            file_object_list = queryset.filter(parent=parent_object).order_by('-file_type', 'name')
        else:
            file_object_list = queryset.filter(parent__isnull=True).order_by('-file_type', 'name')
        form = FolderModelForm(request=request, parent_object=parent_object)
        context = {
            'form': form,
            'file_object_list': file_object_list,
            'breadcrumb_list': breadcrumb_list,
            'folder_object': parent_object,
        }
        return render(request, 'app/file.html', context)

    fid = request.POST.get('fid', '')
    edit_object = None
    if fid.isdecimal():
        edit_object = models.FileRepository.objects.filter(
            id=int(fid), file_type=2, project=request.tracer.project
        ).first()
    if edit_object:
        form = FolderModelForm(request=request, parent_object=parent_object, data=request.POST, instance=edit_object)
    else:
        form = FolderModelForm(request=request, parent_object=parent_object, data=request.POST)
    if form.is_valid():
        form.instance.project = request.tracer.project
        form.instance.file_type = 2
        form.instance.update_user = request.tracer.user
        form.instance.parent = parent_object
        form.save()
        return JsonResponse({'status': True})
    return JsonResponse({'status': False, 'error': form.errors})

def file_delete(request, project_id):
    """删除文件或文件夹。"""
    fid = request.GET.get('fid', '')
    delete_object = models.FileRepository.objects.filter(id=int(fid), project=request.tracer.project).first()
    if not delete_object:
        return JsonResponse({'status': False, 'error': "文件或文件夹不存在"})
    if delete_object.file_type == 1:
        request.tracer.project.use_space -= delete_object.file_size
        request.tracer.project.save()
        delete_file(request.tracer.project.bucket, delete_object.key)
        delete_object.delete()
        return JsonResponse({'status': True})
    total_size = 0
    key_list = []
    folder_list = [delete_object, ]
    for folder in folder_list:
        child_list = models.FileRepository.objects.filter(project=request.tracer.project, parent=folder)
        for child in child_list:
            if child.file_type == 2:
                folder_list.append(child)
            else:
                total_size += child.file_size
                key_list.append({"Key": child.key})
    if key_list:
        delete_file_list(request.tracer.project.bucket, key_list)
    if total_size:
        request.tracer.project.use_space -= total_size
        request.tracer.project.save()
    delete_object.delete()
    return JsonResponse({'status': True})

@csrf_exempt
def cos_credential(request, project_id):
    """获取腾讯云COS上传临时凭证。"""
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
    data_dict = credential(request.tracer.project.bucket, request.tracer.project.region)
    return JsonResponse({'status': True, 'data': data_dict})