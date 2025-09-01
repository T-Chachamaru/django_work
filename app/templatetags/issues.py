from django.template import Library

register = Library()

@register.inclusion_tag('app/inclusion/_check_filter.html', takes_context=True)
def check_filter(context, title, param_name):
    """
    渲染一个标准的链接式筛选器模块。

    :param context: 模板上下文，自动传入。
    :param title: 筛选器的显示标题 (例如: "状态")。
    :param param_name: 该筛选器在URL中的参数名 (例如: "status")。
    """
    filter_choices_data = context['filter_choices']
    choices = filter_choices_data.get(param_name)
    return {'title': title, 'choices': choices}

@register.inclusion_tag('app/inclusion/_select_filter.html', takes_context=True)
def select_filter(context, title, param_name):
    """
    渲染一个下拉选择式筛选器模块。
    """
    filter_choices_data = context['filter_choices']
    options = filter_choices_data.get(param_name)
    return {'title': title, 'param_name': param_name, 'options': options}

@register.simple_tag
def format_with_pad(num, width=3):
    """
    将数字格式化为指定宽度的字符串，不足部分用 '0' 填充，并添加 '#' 前缀。

    :param num: 需要格式化的数字
    :param width: 格式化后的总宽度，默认为3
    """
    return f"#{num:0{width}d}"