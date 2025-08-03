from django import forms
from app import models
from app.forms.bootstrap import BootStrapForm
from app.forms.widgets import ColorRadioSelect


class ProjectModelForm(BootStrapForm, forms.ModelForm):
    """
    用于创建和编辑 `Project` 模型的表单。

    该表单继承自 BootStrapForm 以自动应用样式，并包含针对项目名称
    唯一性和用户项目数量限制的自定义验证逻辑。
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
        super().__init__(*args, **kwargs)
        self.request = request

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            return name

        queryset = models.Project.objects.filter(
            name=name,
            creator=self.request.tracer.user
        )
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError("项目名称已存在，请更换一个。")

        if not self.instance.pk:
            project_count = models.Project.objects.filter(
                creator=self.request.tracer.user
            ).count()

            max_project_num = self.request.tracer.price_policy.project_num
            if project_count >= max_project_num:
                raise forms.ValidationError(f"项目数量已达上限（最多{max_project_num}个），请升级您的套餐。")

        return name