from django import forms
from app import models
from app.forms.bootstrap import BootStrapForm

class WikiModelForm(BootStrapForm,forms.ModelForm):
    class Meta:
        model = models.Wiki
        exclude = ('project',)

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        total_data_list = [("", "请选择"),]
        data_list = models.Wiki.objects.filter(project=request.tracer.project).values_list('id', 'title')
        total_data_list.extend(data_list)
        self.fields['parent'].choices = total_data_list