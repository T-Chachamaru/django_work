from django import forms


class BootStrapForm:
    """
    一个为Django表单字段自动应用Bootstrap样式的Mixin。

    特性:
    - 自动为所有字段添加 'form-control' CSS类。
    - 智能地追加class，而不是粗暴地覆盖，保留字段原有的class。
    - 仅在字段未设置placeholder时，根据其类型自动生成友好的提示文本。
    - 可通过 `bootstrap_class_exclude` 列表排除特定字段。
    """
    bootstrap_class_exclude = []  # 定义要排除自动样式的字段名

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            if name in self.bootstrap_class_exclude:
                continue

            existing_classes = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f'{existing_classes} form-control'.strip()

            if 'placeholder' not in field.widget.attrs:
                if isinstance(field.widget, forms.Select):
                    placeholder = f"请选择{field.label}"
                else:
                    placeholder = f"请输入{field.label}"

                field.widget.attrs['placeholder'] = placeholder