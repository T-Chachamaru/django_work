from django.http import JsonResponse
from django.shortcuts import render

from app.forms.project import ProjectModelForm
from app import models


def project_list(request):
    """项目列表视图"""
    if request.method == 'GET':
        form = ProjectModelForm(request)
        context = {
            'form': form,
        }
        return render(request, 'app/project_list.html', context)

    form = ProjectModelForm(request=request, data=request.POST)
    if form.is_valid():
        form.instance.creator = request.tracer.user
        form.save()
        return JsonResponse({'status': True})
    return JsonResponse({'status': False, 'error': form.errors})
