class BootStrapForm(object):
    """
    Bootstrap 风格表单的基类。

    这个 Mixin 会自动为继承它的表单中所有字段的 widget 添加
    'form-control' class 和 '请输入[字段标签]' 格式的 placeholder，
    从而简化表单在前端的渲染。
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 循环所有字段，为其添加通用的 class 和 placeholder 属性
        for name, field in self.fields.items():
            # 为字段的 widget 添加 CSS class
            field.widget.attrs['class'] = 'form-control'

            # 为字段的 widget 设置 placeholder
            field.widget.attrs['placeholder'] = f"请输入{field.label}"
