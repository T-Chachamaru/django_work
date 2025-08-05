from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from markdown import markdown

from app import models
from app.forms.wiki import WikiModelForm


def wiki(request, project_id):
    """
    Wiki 页面主视图 (已优化)。

    - 如果是普通 GET 请求，则渲染完整的 HTML 页面骨架。
    - 如果是 AJAX GET 请求，则仅返回指定 wiki 文章的 JSON 数据。
    """
    wiki_id = request.GET.get('wiki_id')

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if is_ajax and wiki_id:
        try:
            wiki_object = models.Wiki.objects.get(id=wiki_id, project_id=project_id)
            data = {
                'title': wiki_object.title,
                'content': markdown(wiki_object.content, extensions=['fenced_code', 'tables']),
            }
            return JsonResponse({'status': True, 'data': data})
        except models.Wiki.DoesNotExist:
            return JsonResponse({'status': False, 'error': '文章不存在'})

    wiki_object = None
    if wiki_id:
        wiki_object = models.Wiki.objects.filter(id=wiki_id, project_id=project_id).first()
        if wiki_object:
            wiki_object.content = markdown(wiki_object.content, extensions=['fenced_code', 'tables'])

    return render(request, 'app/wiki.html', {'wiki_object': wiki_object})


def wiki_add(request, project_id):
    """处理新建 Wiki 文章"""
    if request.method == 'GET':
        form = WikiModelForm(request)
        return render(request, 'app/wiki_add.html', {'form': form})

    form = WikiModelForm(request, data=request.POST)
    if form.is_valid():
        form.instance.project = request.tracer.project
        form.save()
        url = reverse('wiki', kwargs={'project_id': project_id})
        return redirect(f"{url}?wiki_id={form.instance.id}")

    return render(request, 'app/wiki_add.html', {'form': form})


def wiki_catalog(request, project_id):
    """获取 Wiki 目录树的 API 视图"""
    data = models.Wiki.objects.filter(project=request.tracer.project).values('id', 'title', 'parent_id')
    return JsonResponse({'status': True, 'data': list(data)})