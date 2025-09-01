from django.template import Library

register = Library()

@register.simple_tag
def user_space(size):
    """
    将字节大小格式化为人类可读的字符串（如 B, KB, MB, GB）。

    这是一个简单的模板标签，用于在前端模板中方便地显示文件或存储空间大小。
    它会根据传入的字节数自动选择最合适的单位。

    用法 (在Django模板中):
        {% load filters %}  <!-- 假设文件名是 filters.py -->
        ...
        <span>已用空间: {% user_space project.use_space %}</span>

    :param size: 整数或浮点数，表示字节（Bytes）大小。
    :return: 格式化后的字符串，例如 "1.25 MB" 或 "2.00 GB"。
    """
    # 检查大小是否达到GB级别
    if size >= 1024 * 1024 * 1024:
        return f"{size / (1024 ** 3):.2f} GB"

    # 检查大小是否达到MB级别
    elif size >= 1024 * 1024:
        return f"{size / (1024 ** 2):.2f} MB"

    # 检查大小是否达到KB级别
    elif size >= 1024:
        return f"{size / 1024:.2f} KB"

    # 如果小于KB，则直接显示字节
    else:
        return f"{size} B"
