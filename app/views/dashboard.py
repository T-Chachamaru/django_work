import datetime
import time

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import render
from app import models


def dashboard(request, project_id):
    """
    项目概览视图。

    负责展示：
    1. 各状态问题的数量统计。
    2. 项目成员列表。
    3. 最新被指派的10个问题。
    """

    status_dict = {
        key: {"text": text, "count": 0}
        for key, text in models.Issues.status_choices
    }
    issues_by_status = models.Issues.objects.filter(project_id=project_id).values('status').annotate(ct=Count('id'))
    for item in issues_by_status:
        status_dict[item['status']]["count"] = item['ct']

    user_list = models.ProjectUser.objects.filter(project_id=project_id).values_list('user_id', 'user__username')

    top_ten_issues = models.Issues.objects.filter(
        project_id=project_id,
        assign__isnull=False
    ).select_related('assign', 'creator').order_by('-create_datetime')[0:10]

    context = {
        'status_dict': status_dict,
        'user_list': user_list,
        'top_ten': top_ten_issues
    }
    return render(request, 'app/dashboard.html', context)


def issues_chart(request, project_id):
    """
    为前端 highcharts 图表提供最近30天内每日创建问题数量的数据。

    返回的数据格式为: [[timestamp1, count1], [timestamp2, count2], ...]
    """

    today = datetime.datetime.now().date()
    date_dict = {}
    for i in range(30):
        date = today - datetime.timedelta(days=i)
        timestamp_ms = int(time.mktime(date.timetuple())) * 1000
        date_dict[date.strftime('%Y-%m-%d')] = [timestamp_ms, 0]

    result = models.Issues.objects.filter(
        project_id=project_id,
        create_datetime__gte=today - datetime.timedelta(days=30)
    ).annotate(
        ctime=TruncDate('create_datetime')
    ).values(
        'ctime'
    ).annotate(
        ct=Count('id')
    ).values('ctime', 'ct')

    for item in result:
        date_str = item['ctime'].strftime('%Y-%m-%d')
        if date_str in date_dict:
            date_dict[date_str][1] = item['ct']

    return JsonResponse({'status': True, 'data': list(date_dict.values())})
