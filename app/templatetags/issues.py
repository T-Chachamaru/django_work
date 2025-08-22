from django.template import Library

register = Library()

@register.inclusion_tag('app/inclusion/_check_filter.html', takes_context=True)
def check_filter(context, title):
    """
    渲染一个筛选器模块的 inclusion tag。
    """
    filter_choices_data = context['filter_choices']
    choices = filter_choices_data.get(title)

    return {'title': title, 'choices': choices}

@register.simple_tag
def format_with_pad(num, width=3):
    """
    将数字格式化为指定宽度的字符串，不足部分用 '0' 填充，并添加 '#' 前缀。

    :param num: 需要格式化的数字
    :param width: 格式化后的总宽度，默认为3
    """
    return f"#{num:0{width}d}"