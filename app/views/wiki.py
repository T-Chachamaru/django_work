import uuid
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from app import models
from app.forms.wiki import WikiModelForm
from utils.tencent.cos import CosManager

def wiki(request, project_id):
    """
    Wiki 页面主视图。
    - 普通GET请求：返回Wiki主页面。
    - AJAX GET请求：根据wiki_id返回指定文章的JSON数据。
    """
    wiki_id = request.GET.get('wiki_id')
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        if not wiki_id:
            return JsonResponse({'status': False, 'error': '缺少wiki_id参数'})
        wiki_object = get_object_or_404(models.Wiki, id=wiki_id, project_id=project_id)
        data = {
            'id': wiki_object.id,
            'title': wiki_object.title,
            'content': wiki_object.content,
        }
        return JsonResponse({'status': True, 'data': data})

    wiki_object = None
    if wiki_id:
        wiki_object = models.Wiki.objects.filter(id=wiki_id, project_id=project_id).first()

    return render(request, 'app/wiki.html', {'wiki_object': wiki_object})


def wiki_catalog(request, project_id):
    """
    获取项目下所有Wiki文章的目录结构（API）。
    使用.values()可以优化数据库查询，只获取需要的字段。
    """
    data = models.Wiki.objects.filter(project=request.tracer.project).values('id', 'title', 'parent_id')
    return JsonResponse({'status': True, 'data': list(data)})

def wiki_add(request, project_id):
    """
    处理新建 Wiki 文章的视图。
    - GET: 显示一个空的表单。
    - POST: 验证并保存新文章，然后重定向到该文章的展示页。
    """
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


def wiki_edit(request, project_id, wiki_id):
    """
    修改指定Wiki文章的视图。
    - GET: 显示填充了现有数据的表单。
    - POST: 验证并更新文章。
    """
    # 使用get_object_or_404获取文章，如果不存在则自动返回404页面
    wiki_object = get_object_or_404(models.Wiki, project_id=project_id, id=wiki_id)

    if request.method == 'GET':
        form = WikiModelForm(request, instance=wiki_object)
        return render(request, 'app/wiki_form.html', {'form': form})

    form = WikiModelForm(request, data=request.POST, instance=wiki_object)
    if form.is_valid():
        form.save()
        url = reverse('wiki', kwargs={'project_id': project_id})
        return redirect(f"{url}?wiki_id={wiki_id}")

    return render(request, 'app/wiki_form.html', {'form': form})


def wiki_delete(request, project_id, wiki_id):
    """
    删除Wiki文章及其所有子孙文章。
    """
    # 使用队列实现广度优先搜索（BFS）来查找所有子孙节点ID
    ids_to_delete = [wiki_id]
    queue = [wiki_id]

    while queue:
        parent_id = queue.pop(0)
        children_ids = models.Wiki.objects.filter(
            project_id=project_id, parent_id=parent_id
        ).values_list('id', flat=True)
        if children_ids:
            ids_to_delete.extend(children_ids)
            queue.extend(children_ids)

    models.Wiki.objects.filter(project_id=project_id, id__in=ids_to_delete).delete()
    url = reverse('wiki', kwargs={'project_id': project_id})
    return redirect(url)

@csrf_exempt
def wiki_upload(request, project_id):
    """
    处理 Editor.md 编辑器中的图片上传。
    @csrf_exempt: 标记此视图函数不需要CSRF令牌，因为一些编辑器上传时不携带。
    """
    result = {'success': 0, 'message': None, 'url': None}

    image_object = request.FILES.get('editormd-image-file')
    if not image_object:
        result['message'] = "未找到上传的文件"
        return JsonResponse(result)

    project_info = request.tracer.project
    ext = image_object.name.split('.')[-1]
    random_key = f"wiki/{uuid.uuid4()}.{ext}"

    try:
        cos_client = CosManager(region=project_info.region)
        image_url = cos_client.upload_file(
            bucket=project_info.bucket,
            file_object=image_object,
            key=random_key
        )
        result['success'] = 1
        result['url'] = image_url
    except Exception as e:
        result['message'] = "上传失败，请检查COS配置或联系管理员"

    return JsonResponse(result)