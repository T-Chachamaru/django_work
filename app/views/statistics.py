from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import render

from app import models

def statistics(request, project_id):
    """
    渲染统计页面主视图。
    """
    return render(request, 'app/statistics.html')


def statistics_priority(request, project_id):
    """
    为前端 highcharts 提供按「优先级」分类的饼图数据。
    这是一个纯AJAX接口。
    """
    start = request.GET.get('start')
    end = request.GET.get('end')
    data_dict = {
        key: {'name': text, 'y': 0}
        for key, text in models.Issues.priority_choices
    }

    result = models.Issues.objects.filter(
        project_id=project_id,
        create_datetime__gte=start,
        create_datetime__lt=end
    ).values('priority').annotate(ct=Count('id'))

    for item in result:
        data_dict[item['priority']]['y'] = item['ct']

    return JsonResponse({'status': True, 'data': list(data_dict.values())})


def statistics_project_user(request, project_id):
    """
    为前端 highcharts 提供按「项目成员」和「问题状态」分类的柱状图数据。
    这是一个纯AJAX接口。
    """
    start = request.GET.get('start')
    end = request.GET.get('end')

    all_user_dict = {
        request.tracer.project.creator.id: {
            'name': request.tracer.project.creator.username,
            'status': {key: 0 for key, text in models.Issues.status_choices}
        },
        None: {
            'name': '未指派',
            'status': {key: 0 for key, text in models.Issues.status_choices}
        }
    }
    user_list = models.ProjectUser.objects.filter(project_id=project_id)
    for item in user_list:
        all_user_dict[item.user_id] = {
            'name': item.user.username,
            'status': {key: 0 for key, text in models.Issues.status_choices}
        }

    issues_data = models.Issues.objects.filter(
        project_id=project_id,
        create_datetime__gte=start,
        create_datetime__lt=end
    ).values('assign_id', 'status').annotate(ct=Count('id'))

    for item in issues_data:
        assign_id = item['assign_id']
        status_id = item['status']
        count = item['ct']
        if assign_id in all_user_dict:
            all_user_dict[assign_id]['status'][status_id] = count

    categories = [data['name'] for data in all_user_dict.values()]

    series_data_map = {
        key: {'name': text, 'data': []}
        for key, text in models.Issues.status_choices
    }
    for user_info in all_user_dict.values():
        for status_id, count in user_info['status'].items():
            series_data_map[status_id]['data'].append(count)

    context = {
        'status': True,
        'data': {
            'categories': categories,
            'series': list(series_data_map.values())
        }
    }

    return JsonResponse(context)
