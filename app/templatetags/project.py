from django.template import Library
from django.urls import reverse
from app import models
from django import template

register = Library()

@register.inclusion_tag('app/inclusion/all_project_list.html')
def all_project_list(request):
    """
    Inclusion Tag: 获取并返回用户所有相关的项目列表。

    这个标签专门用于渲染导航栏中的项目下拉菜单。
    """
    my_project_list = models.Project.objects.filter(creator=request.tracer.user)
    join_project_list = models.ProjectUser.objects.filter(user=request.tracer.user)
    return {'my': my_project_list, 'join': join_project_list, 'request': request}


@register.inclusion_tag('app/inclusion/manage_menu_list.html')
def manage_menu_list(request):
    """
    Inclusion Tag: 生成项目管理页面的侧边栏菜单。
    """
    data_list = [
        {'title': '概览', 'url_name': 'dashboard'},
        {'title': '问题', 'url_name': 'issues'},
        {'title': '统计', 'url_name': 'statistics'},
        {'title': '文件', 'url_name': 'file'},
        {'title': 'wiki', 'url_name': 'wiki'},
        {'title': '配置', 'url_name': 'setting'},
    ]
    for item in data_list:
        item['url'] = reverse(item['url_name'], kwargs={'project_id': request.tracer.project.id})
        if request.path_info.startswith(item['url']):
            item['class'] = 'active'
    return {'data_list': data_list}

@register.inclusion_tag('app/inclusion/_project_card.html')
def render_project_card(project_item, project_type):
    """
    渲染一个项目卡片的 inclusion tag。
    :param project_item: 项目对象 (Project model instance)
    :param project_type: 项目类型 ('my' or 'join')
    """
    return {'project': project_item, 'project_type': project_type}