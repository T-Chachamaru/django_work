from django import forms
from django.core.exceptions import ValidationError

from app import models
from app.forms.bootstrap import BootStrapForm
from app.forms.widgets import ColorRadioSelect


class ProjectModelForm(BootStrapForm, forms.ModelForm):
    """
    用于创建和编辑 `Project` 模型的表单。
    - 自动应用Bootstrap样式。
    - 校验项目名称对当前用户是否唯一。
    - 在创建新项目时，校验用户是否已达到其套餐允许的项目数量上限。
    """
    bootstrap_class_exclude = ['color']

    class Meta:
        model = models.Project
        fields = ['name', 'color', 'desc']
        widgets = {
            'desc': forms.Textarea,
            'color': ColorRadioSelect(attrs={'class': 'color-radio'}),
        }

    def __init__(self, request, *args, **kwargs):
        """
        重写构造方法，接收并存储request对象。
        这使得我们可以在表单的验证方法中访问到当前用户及其权限信息(tracer)。
        """
        super().__init__(*args, **kwargs)
        self.request = request

    def clean_name(self):
        """
        字段级别验证：只负责验证 'name' 字段本身的合法性。
        主要检查项目名称对于当前用户是否唯一。
        """
        name = self.cleaned_data.get('name')
        queryset = models.Project.objects.filter(
            name=name,
            creator=self.request.tracer.user
        )

        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise ValidationError("项目名称已存在，请更换一个。")

        return name

    def clean(self):
        """
        表单级别验证：当所有字段自身的验证都通过后执行。
        适合进行需要依赖多个字段或进行全局业务逻辑的验证。
        这里我们用它来校验项目数量限制。
        """
        cleaned_data = super().clean()
        if not self.instance.pk:
            price_policy = self.request.tracer.price_policy

            if not price_policy:
                raise ValidationError("无法获取您的套餐信息，请联系管理员。")

            project_count = models.Project.objects.filter(
                creator=self.request.tracer.user
            ).count()
            max_project_num = price_policy.project_num
            if project_count >= max_project_num:
                raise ValidationError(f"项目数量已达上限（最多{max_project_num}个），请升级您的套餐。")

        return cleaned_data