from django import forms

from app import models
from app.forms.bootstrap import BootStrapForm


class WikiModelForm(BootStrapForm, forms.ModelForm):
    """ 用于新建和编辑Wiki文章的ModelForm """

    class Meta:
        model = models.Wiki
        exclude = ('project',)

    def __init__(self, request, *args, **kwargs):
        """重写构造方法，以便动态处理 'parent' 字段的下拉选项。"""
        super().__init__(*args, **kwargs)
        wiki_options = models.Wiki.objects.filter(
            project=request.tracer.project
        ).values_list('id', 'title')
        total_choices = [("", "请选择"),]
        total_choices.extend(wiki_options)
        self.fields['parent'].choices = total_choices