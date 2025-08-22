from django import template
import math

register = template.Library()

@register.filter(name='filesizeformat')
def filesizeformat(value):
    """
    一个自定义的模板过滤器，用于将字节数格式化为人类可读的格式 (KB, MB, GB 等)。
    这是 django.contrib.humanize.filesizeformat 的一个简化版实现。

    :param value: 文件大小，单位为字节 (bytes)。
    :return: 格式化后的字符串。
    """
    try:
        value = int(value)
    except (TypeError, ValueError, AttributeError):
        return "0 Bytes"

    if value <= 0:
        return "0 Bytes"

    units = ("Bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    power = int(math.floor(math.log(value, 1024)))

    if power >= len(units):
        power = len(units) - 1

    formatted_size = round(value / (1024 ** power), 2)

    return f"{formatted_size} {units[power]}"