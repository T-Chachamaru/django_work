import time

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect

from app.forms.project import ProjectModelForm
from app import models
from utils.tencent.cos import create_bucket


def project_list(request):
    """项目列表视图"""
    if request.method == 'GET':
        projects_dict = {'star':[],'my':[],'join':[]}
        projects_list = models.Project.objects.filter(creator=request.tracer.user)
        for row in projects_list:
            if row.star:
                projects_dict['star'].append({'value':row, 'type':'my'})
            else:
                projects_dict['my'].append(row)
        join_projects_list = models.ProjectUser.objects.filter(user=request.tracer.user)
        for item in join_projects_list:
            if item.star:
                projects_dict['star'].append({'value':item.project,'type':'join'})
            else:
                projects_dict['join'].append(item.project)
        form = ProjectModelForm(request)
        context = {
            'form': form,
            'projects_dict': projects_dict,
        }
        return render(request, 'app/project_list.html', context)

    form = ProjectModelForm(request=request, data=request.POST)
    if form.is_valid():
        bucket = f"{request.tracer.user.mobile_phone}-{str(int(time.time()))}"
        region = "ap-chengdu"
        create_bucket(bucket, region)
        form.instance.creator = request.tracer.user
        form.instance.region = region
        form.instance.bucket = bucket
        form.save()
        return JsonResponse({'status': True})
    return JsonResponse({'status': False, 'error': form.errors})


def project_star(request, project_type, project_id):
    """
    处理项目加星/取消星标的 AJAX 请求。

    根据项目当前状态自动切换，并返回 JSON 响应。
    """
    if request.method != 'POST':
        return JsonResponse({'status': False, 'error': '请求方法错误'})

    user = request.tracer.user
    new_star_status = None

    if project_type == 'my':
        # 查找并切换“我创建的”项目的星标状态
        project_obj = models.Project.objects.filter(id=project_id, creator=user).first()
        if not project_obj:
            return JsonResponse({'status': False, 'error': '项目不存在或无权限'})

        project_obj.star = not project_obj.star
        project_obj.save()
        new_star_status = project_obj.star

    elif project_type == 'join':
        # 查找并切换“我参与的”项目的星标状态
        relation_obj = models.ProjectUser.objects.filter(project_id=project_id, user=user).first()
        if not relation_obj:
            return JsonResponse({'status': False, 'error': '未参与该项目'})

        relation_obj.star = not relation_obj.star
        relation_obj.save()
        new_star_status = relation_obj.star

    else:
        return JsonResponse({'status': False, 'error': '无效的项目类型'})

    return JsonResponse({'status': True, 'starred': new_star_status})