from django import forms

from app.forms.bootstrap import BootStrapForm
from app import models


class ProjectModelForm(BootStrapForm, forms.ModelForm):
    """
    用于创建和编辑项目的 ModelForm。
    """

    class Meta:
        model = models.Project
        fields = ['name', 'color', 'desc']
        widgets = {
            'desc': forms.Textarea,
        }

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request

    def clean_name(self):
        name = self.cleaned_data.get('name')
        current_user = self.request.tracer.user
        exists = models.Project.objects.filter(name=name, creator=current_user).exists()
        if exists:
            raise forms.ValidationError("项目名称已存在")

        project_count = models.Project.objects.filter(creator=current_user).count()
        max_project_num = self.request.tracer.price_policy.project_num

        if project_count >= max_project_num:
            raise forms.ValidationError("项目数量已达上限，请升级您的套餐")

        return name
