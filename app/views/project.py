import time
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from app.forms.project import ProjectModelForm
from app import models
from utils.tencent.cos import CosManager

def project_list(request):
    """
    项目列表视图，同时处理GET（显示列表）和POST（创建项目）请求。
    """
    if request.method == 'POST':
        form = ProjectModelForm(request=request, data=request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    bucket_name = f"{request.tracer.user.mobile_phone}-{int(time.time())}"
                    region = "ap-chengdu"

                    cos_client = CosManager(region=region)
                    cos_client.create_bucket(bucket=bucket_name)

                    form.instance.creator = request.tracer.user
                    form.instance.bucket = bucket_name
                    form.instance.region = region
                    project_instance = form.save()

                    issue_types_to_create = [
                        models.IssuesType(project=project_instance, title=item)
                        for item in models.IssuesType.PROJECT_INIT_LIST
                    ]
                    models.IssuesType.objects.bulk_create(issue_types_to_create)
            except Exception as e:
                return JsonResponse({'status': False, 'error': "项目创建失败，请稍后重试。"})

            return JsonResponse({'status': True})

        return JsonResponse({'status': False, 'error': form.errors})

    projects_dict = {
        'star': [],
        'my': [],
        'join': []
    }

    my_projects = models.Project.objects.filter(creator=request.tracer.user)
    for proj in my_projects:
        if proj.star:
            projects_dict['star'].append({'value': proj, 'type': 'my'})
        else:
            projects_dict['my'].append(proj)

    join_relations = models.ProjectUser.objects.filter(user=request.tracer.user).select_related('project')
    for relation in join_relations:
        if relation.star:
            projects_dict['star'].append({'value': relation.project, 'type': 'join'})
        else:
            projects_dict['join'].append(relation.project)

    form = ProjectModelForm(request)
    context = {
        'form': form,
        'projects_dict': projects_dict,
    }
    return render(request, 'app/project_list.html', context)

@require_POST  # 使用装饰器强制此视图只接受POST请求
def project_star(request, project_type, project_id):
    """
    处理项目加星/取消星标的 AJAX 请求。
    """
    user = request.tracer.user
    if project_type == 'my':
        project_obj = models.Project.objects.filter(id=project_id, creator=user).first()
        if not project_obj:
            return JsonResponse({'status': False, 'error': '项目不存在或无权限操作'})

        project_obj.star = not project_obj.star
        project_obj.save()
        return JsonResponse({'status': True, 'starred': project_obj.star})

    elif project_type == 'join':
        relation_obj = models.ProjectUser.objects.filter(project_id=project_id, user=user).first()
        if not relation_obj:
            return JsonResponse({'status': False, 'error': '未参与该项目，无法设置星标'})

        relation_obj.star = not relation_obj.star
        relation_obj.save()
        return JsonResponse({'status': True, 'starred': relation_obj.star})

    else:
        return JsonResponse({'status': False, 'error': '无效的项目类型'})