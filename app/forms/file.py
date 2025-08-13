from django import forms
from django.core.exceptions import ValidationError

from app import models
from app.forms.bootstrap import BootStrapForm


class FolderModelForm(BootStrapForm, forms.ModelForm):
    """用于新建文件夹"""

    class Meta:
        model = models.FileRepository
        fields = ['name']

    def __init__(self, request, parent_object, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.parent_object = parent_object

    def clean_name(self):
        """文件在同一个项目及同一个父目录下，文件夹名称不能重复。"""
        name = self.cleaned_data.get('name')
        queryset = models.FileRepository.objects.filter(
            file_type=2,
            name=name,
            project=self.request.tracer.project,
        )
        if self.parent_object:
            exists = queryset.filter(parent=self.parent_object).exists()
        else:
            exists = queryset.filter(parent__isnull=True).exists()
        if exists:
            raise ValidationError("该目录下文件夹已存在")
        return name