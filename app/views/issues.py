import datetime
import json
import uuid
import hashlib

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from app import models
from app.forms.issues import IssuesModelForm, InviteModelForm
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

    invite_form = InviteModelForm()
    issues_object_list = queryset[page_object.start:page_object.end]
    form = IssuesModelForm(request=request)
    context = {
        'form': form,
        'issues_object_list': issues_object_list,
        'page_html': page_object.page_html(),
        'filter_choices': filter_handler.get_filter_choices(),
        'invite_form': invite_form,
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
def issues_change(request, project_id, issues_id):
    """
    通过AJAX更新问题字段的通用接口。
    """
    post_data = json.loads(request.body.decode('utf-8'))
    name = post_data.get('name')
    value = post_data.get('value')

    issue = get_object_or_404(models.Issues, id=issues_id, project_id=project_id)
    field_object = models.Issues._meta.get_field(name)

    # 1. 文本或日期类型
    if field_object.get_internal_type() in ['CharField', 'TextField', 'DateField']:
        return _update_text_or_date_field(request, issue, field_object, value)

    # 2. 外键类型
    if field_object.get_internal_type() == 'ForeignKey':
        return _update_fk_field(request, issue, field_object, value, project_id)

    # 3. Choices类型
    if field_object.choices:
        return _update_choice_field(request, issue, field_object, value)

    # 4. 多对多类型
    if field_object.get_internal_type() == 'ManyToManyField':
        return _update_m2m_field(request, issue, field_object, value, project_id)

    return JsonResponse({'status': False, 'error': '不支持的字段类型'})

# ========== issues_change 的辅助函数 ==========

def _create_change_record(request, issue, content):
    """创建一条变更记录并返回JsonResponse。"""
    new_record = models.IssuesReply.objects.create(
        reply_type=1, issues=issue, content=content, creator=request.tracer.user
    )
    response_data = {
        'id': new_record.id,
        'reply_type': new_record.reply_type,
        'content': new_record.content,
        'creator_name': new_record.creator.username,
        'create_datetime': new_record.create_datetime.strftime('%Y-%m-%d %H:%M'),
        'reply_id': new_record.reply_id
    }
    return JsonResponse({'status': True, 'data': response_data})


def _update_text_or_date_field(request, issue, field_object, value):
    """处理文本和日期字段的更新。"""
    if not value:
        if not field_object.null:
            return JsonResponse({'status': False, 'error': '该字段不能为空'})
        setattr(issue, field_object.name, None)
        issue.save()
        change_record = f"{field_object.verbose_name} 更新为空"
    else:
        setattr(issue, field_object.name, value)
        issue.save()
        change_record = f"{field_object.verbose_name} 更新为 {value}"

    return _create_change_record(request, issue, change_record)


def _update_fk_field(request, issue, field_object, value, project_id):
    """处理外键字段的更新。"""
    if not value:
        if not field_object.null:
            return JsonResponse({'status': False, 'error': '该字段不能为空'})
        setattr(issue, field_object.name, None)
        issue.save()
        change_record = f"{field_object.verbose_name} 更新为空"
    else:
        if field_object.name == 'assign':
            # 特殊处理 'assign' 字段
            if int(value) == request.tracer.project.creator_id:
                instance = request.tracer.project.creator
            else:
                project_user = models.ProjectUser.objects.filter(project_id=project_id, user_id=value).first()
                instance = project_user.user if project_user else None
        else:
            # 通用外键处理
            instance = field_object.remote_field.model.objects.filter(id=value, project_id=project_id).first()

        if not instance:
            return JsonResponse({'status': False, 'error': '选择的值不存在'})

        setattr(issue, field_object.name, instance)
        issue.save()
        change_record = f"{field_object.verbose_name} 更新为 {str(instance)}"

    return _create_change_record(request, issue, change_record)


def _update_choice_field(request, issue, field_object, value):
    """处理带choices的字段更新。"""
    choice_text = dict(field_object.choices).get(int(value))
    if not choice_text:
        return JsonResponse({'status': False, 'error': '选择的值无效'})

    setattr(issue, field_object.name, value)
    issue.save()
    change_record = f"{field_object.verbose_name} 更新为 {choice_text}"
    return _create_change_record(request, issue, change_record)


def _update_m2m_field(request, issue, field_object, value, project_id):
    """处理多对多字段（关注者）的更新。"""
    if not isinstance(value, list):
        return JsonResponse({'status': False, 'error': '数据格式错误'})

    if not value:
        issue.attention.set([])
        change_record = f"{field_object.verbose_name} 更新为空"
    else:
        # 验证所有用户ID是否合法
        project_users = models.ProjectUser.objects.filter(project_id=project_id)
        allowed_user_ids = {str(u.user_id) for u in project_users}
        allowed_user_ids.add(str(request.tracer.project.creator_id))

        if not all(str(v) in allowed_user_ids for v in value):
            return JsonResponse({'status': False, 'error': '选择的用户无效'})

        issue.attention.set(value)
        # 获取用户名以生成变更记录
        usernames = list(models.UserInfo.objects.filter(id__in=value).values_list('username', flat=True))
        change_record = f"{field_object.verbose_name} 更新为 {', '.join(usernames)}"

    return _create_change_record(request, issue, change_record)


@csrf_exempt
def invite_url(request, project_id):
    """
    生成项目邀请链接的API视图。
    仅限项目创建者可以调用。
    """
    form = InviteModelForm(data=request.POST)

    if request.tracer.user != request.tracer.project.creator:
        form.add_error('period', '只有项目创建者才能生成邀请链接')
        return JsonResponse({'status': False, 'error': form.errors})

    if form.is_valid():
        random_invite_code = _uid(request.tracer.user.mobile_phone)
        form.instance.project = request.tracer.project
        form.instance.code = random_invite_code
        form.instance.creator = request.tracer.user
        form.save()
        url_path = request.build_absolute_uri(
            reverse('invite_join', kwargs={'code': random_invite_code})
        )

        return JsonResponse({'status': True, 'data': url_path})

    return JsonResponse({'status': False, 'error': form.errors})


def invite_join(request, code):
    """
    处理用户通过邀请链接加入项目的视图。
    """
    invite_object = models.ProjectInvite.objects.filter(code=code).first()

    if not invite_object:
        return render(request, 'app/invite_join.html', {'error': '邀请码不存在，请重新确认。'})

    project = invite_object.project
    user = request.tracer.user
    is_valid, error_msg = _check_invite_validity(user, project, invite_object)
    if not is_valid:
        return render(request, 'app/invite_join.html', {'error': error_msg})

    if _is_project_at_member_limit(project):
        return render(request, 'app/invite_join.html', {'error': '项目成员已达上限，请联系创建者升级套餐。'})

    if invite_object.count:
        invite_object.use_count += 1
        invite_object.save()

    models.ProjectUser.objects.create(user=user, project=project)
    project.join_count += 1
    project.save()

    return render(request, 'app/invite_join.html', {'project': project})


def _check_invite_validity(user, project, invite):
    """
    辅助函数：检查邀请的有效性（用户身份、是否已加入、是否过期、是否用尽）。

    :return: (bool, str) -> (是否有效, 错误信息)
    """
    if project.creator == user:
        return False, '您是项目创建者，无需再次加入。'

    if models.ProjectUser.objects.filter(project=project, user=user).exists():
        return False, '您已加入该项目，请勿重复加入。'

    current_datetime = datetime.datetime.now()
    limit_datetime = invite.create_datetime + datetime.timedelta(minutes=invite.period)
    if current_datetime > limit_datetime:
        return False, '邀请码已过期。'

    if invite.count and invite.use_count >= invite.count:
        return False, '邀请码使用次数已达上限。'

    return True, ""


def _is_project_at_member_limit(project):
    """
    辅助函数：检查项目成员数量是否已达到其创建者套餐的上限。

    :return: bool -> 是否已达上限
    """
    creator = project.creator
    transaction = models.Transaction.objects.filter(user=creator, status=2).order_by('-id').first()

    if not transaction:
        policy = models.PricePolicy.objects.filter(category=1).first()
        max_members = policy.project_members
    else:
        current_datetime = datetime.datetime.now()
        if transaction.end_datetime and transaction.end_datetime < current_datetime:
            policy = models.PricePolicy.objects.filter(category=1).first()
            max_members = policy.project_members
        else:
            max_members = transaction.price_policy.project_members

    current_members = models.ProjectUser.objects.filter(project=project).count()

    return (current_members + 1) >= max_members

def _uid(string):
    """
    生成一个基于字符串和Django SECRET_KEY的唯一MD5哈希值。
    用于创建不可预测的邀请码。

    :param string: 通常是用户的手机号或其他唯一标识。
    :return: 32位的十六进制哈希字符串。
    """
    data = f"{str(uuid.uuid4())}-{string}"
    hash_object = hashlib.md5(settings.SECRET_KEY.encode('utf-8'))
    hash_object.update(data.encode('utf-8'))

    return hash_object.hexdigest()



















