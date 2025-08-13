import hashlib
import uuid

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from app import models
from app.forms.wiki import WikiModelForm
from utils.tencent.cos import upload_file

def wiki(request, project_id):
    """Wiki 页面主视图。"""
    wiki_id = request.GET.get('wiki_id')
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if wiki_id:
            try:
                wiki_object = models.Wiki.objects.get(id=wiki_id, project_id=project_id)
                data = {
                    'id': wiki_object.id,
                    'title': wiki_object.title,
                    'content': wiki_object.content,
                }
                return JsonResponse({'status': True, 'data': data})
            except models.Wiki.DoesNotExist:
                return JsonResponse({'status': False, 'error': '文章不存在'})
        return JsonResponse({'status': False, 'error': '缺少wiki_id参数'})
    wiki_object = None
    if wiki_id:
        wiki_object = models.Wiki.objects.filter(id=wiki_id, project_id=project_id).first()
    return render(request, 'app/wiki.html', {'wiki_object': wiki_object})

def wiki_add(request, project_id):
    """处理新建 Wiki 文章的视图"""
    if request.method == 'GET':
        form = WikiModelForm(request)
        return render(request, 'app/wiki_form.html', {'form': form})
    form = WikiModelForm(request, data=request.POST)
    if form.is_valid():
        form.instance.project = request.tracer.project
        form.save()
        url = reverse('wiki', kwargs={'project_id': project_id})
        return redirect(f"{url}?wiki_id={form.instance.id}")
    return render(request, 'app/wiki_form.html', {'form': form})

def wiki_catalog(request, project_id):
    """获取 Wiki 目录树的 API 视图"""
    data = models.Wiki.objects.filter(project=request.tracer.project).values('id', 'title', 'parent_id')
    return JsonResponse({'status': True, 'data': list(data)})

def wiki_delete(request, project_id, wiki_id):
    """删除wiki文章及其所有子孙文章。"""
    ids_to_delete = [wiki_id]
    queue = [wiki_id]
    while queue:
        parent_id = queue.pop(0)
        children = models.Wiki.objects.filter(project_id=project_id, parent_id=parent_id).values_list('id', flat=True)
        if children:
            ids_to_delete.extend(children)
            queue.extend(children)
    models.Wiki.objects.filter(project_id=project_id, id__in=ids_to_delete).delete()
    url = reverse('wiki', kwargs={'project_id': project_id})
    return redirect(url)

def wiki_edit(request, project_id, wiki_id):
    """修改wiki文章的视图"""
    wiki_object = models.Wiki.objects.filter(project_id=project_id, id=wiki_id).first()
    if not wiki_object:
        url = reverse('wiki', kwargs={'project_id': project_id})
        return redirect(url)
    if request.method == 'GET':
        form = WikiModelForm(request, instance=wiki_object)
        return render(request, 'app/wiki_form.html', {'form': form, 'wiki_id': wiki_id})
    form = WikiModelForm(request, data=request.POST, instance=wiki_object)
    if form.is_valid():
        form.save()
        url = reverse('wiki', kwargs={'project_id': project_id})
        return redirect(f"{url}?wiki_id={wiki_id}")
    return render(request, 'app/wiki_form.html', {'form': form, 'wiki_id': wiki_id})

@csrf_exempt
def wiki_upload(request, project_id):
    """处理 Editor.md 编辑器中的图片上传。"""
    result = {
        'success': 0,
        'message': None,
        'url': None,
    }
    image_object = request.FILES.get('editormd-image-file')
    if not image_object:
        result['message'] = "文件不存在"
        return JsonResponse(result)
    ext = image_object.name.split('.')[-1]
    random_key = f"{uuid.uuid4()}.{ext}"

    image_url = upload_file(
        bucket=request.tracer.project.bucket,
        file_object=image_object,
        key=random_key,
        region=request.tracer.project.region
    )

    result['success'] = 1
    result['url'] = image_url
    return JsonResponse(result)
