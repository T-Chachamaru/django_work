from django.db.models import F
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from app import models
from app.forms.issues import IssuesModelForm, IssuesReplyModelForm
from utils.pagination import Pagination
from utils.issues_filter import CheckFilter

def issues(request, project_id):
    """
    处理问题列表的展示（GET）和新问题的创建（POST AJAX）。
    """
    if request.method == 'POST':
        form = IssuesModelForm(request=request, data=request.POST)
        if form.is_valid():
            form.instance.project = request.tracer.project
            form.instance.creator = request.tracer.user
            form.save()
            return JsonResponse({'status': True})
        return JsonResponse({'status': False, 'error': form.errors})
    allowed_filters = ['status', 'priority', 'assign', 'attention']
    filter_handler = CheckFilter(allowed_filters, request)
    query_conditions = filter_handler.get_query_conditions()

    queryset = models.Issues.objects.filter(project_id=project_id, **query_conditions)
    page_object = Pagination(
        current_page=request.GET.get('page'),
        all_count=queryset.count(),
        base_url=request.path_info,
        query_params=request.GET
    )

    issues_object_list = queryset[page_object.start:page_object.end]
    form = IssuesModelForm(request=request)
    context = {
        'form': form,
        'issues_object_list': issues_object_list,
        'page_html': page_object.page_html(),
        'filter_choices': filter_handler.get_filter_choices(),
    }
    return render(request, 'app/issues.html', context)

def issues_detail(request, project_id, issues_id):
    """
    显示单个问题的详细信息。
    """
    issues_object = get_object_or_404(models.Issues, id=issues_id, project_id=project_id)
    form = IssuesModelForm(request=request, instance=issues_object)
    context = {
        'form': form,
        'issues_object': issues_object
    }
    return render(request, 'app/issues_detail.html', context)

@csrf_exempt
def issues_record(request, project_id, issues_id):
    """
    处理问题记录的获取（GET）和新回复的创建（POST）。
    这是一个纯AJAX接口。
    """
    if request.method == 'GET':
        reply_list = models.IssuesReply.objects.filter(
            issues_id=issues_id, issues__project_id=project_id
        ).select_related('creator').values(
            'id',
            'reply_type',
            'content',
            'create_datetime',
            'reply_id',
            creator_name=F('creator__username'),
        )
        data_list = list(reply_list)
        return JsonResponse({'status': True, 'data': data_list})

    form = IssuesReplyModelForm(data=request.POST)
    if form.is_valid():
        form.instance.issues_id = issues_id
        form.instance.reply_type = 2
        form.instance.creator = request.tracer.user
        instance = form.save()

        new_reply_info = {
            'id': instance.id,
            'reply_type_text': instance.get_reply_type_display(),
            'content': instance.content,
            'creator': instance.creator.username,
            'datetime': instance.create_datetime.strftime('%Y-%m-%d %H:%M'),
            'parent_id': instance.reply_id
        }
        return JsonResponse({'status': True, 'data': new_reply_info})

    return JsonResponse({'status': False, 'error': form.errors})