from django import forms
from django.db.models import Q

from app.forms.bootstrap import BootStrapForm
from app import models


class IssuesModelForm(BootStrapForm, forms.ModelForm):
    """
    用于新建和编辑 Issues（问题）的 ModelForm。
    - 自动应用Bootstrap样式。
    - 高效地动态生成所有下拉选项的查询集。
    - 自动排除不合逻辑的选项（如将问题自身设为父问题）。
    """

    class Meta:
        model = models.Issues
        exclude = ['project', 'creator', 'create_datetime', 'latest_update_datetime']
        widgets = {
            "assign": forms.Select(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
            "attention": forms.SelectMultiple(
                attrs={'class': 'selectpicker', 'data-live-search': 'true', 'data-actions-box': 'true'}
            ),
            "parent": forms.Select(attrs={'class': 'selectpicker', 'data-live-search': 'true'}),
        }

    def __init__(self, request, *args, **kwargs):
        """
        重写构造方法，以 Django 推荐的方式动态设置外键字段的 queryset。
        """
        super().__init__(*args, **kwargs)
        project = request.tracer.project
        self.fields['issues_type'].queryset = models.IssuesType.objects.filter(project=project)
        self.fields['module'].queryset = models.Module.objects.filter(project=project)
        self.fields['module'].empty_label = "--- 未选择 ---"

        project_users_queryset = models.UserInfo.objects.filter(
            Q(id=project.creator_id) | Q(projectuser__project=project)
        ).distinct()

        self.fields['assign'].queryset = project_users_queryset
        self.fields['assign'].empty_label = "--- 未指派 ---"
        self.fields['attention'].queryset = project_users_queryset

        parent_queryset = models.Issues.objects.filter(project=project)
        if self.instance.pk:
            parent_queryset = parent_queryset.exclude(pk=self.instance.pk)

        self.fields['parent'].queryset = parent_queryset
        self.fields['parent'].empty_label = "--- 无父问题 ---"


class IssuesReplyModelForm(BootStrapForm, forms.ModelForm):
    """
    用于问题回复的 ModelForm。
    - 继承 BootStrapForm 以自动应用样式。
    """

    class Meta:
        model = models.IssuesReply
        fields = ['content', 'reply']


class InviteModelForm(BootStrapForm, forms.ModelForm):
    """
    用于创建项目邀请码的ModelForm。

    此表单允许项目创建者或管理员生成一个邀请链接，并可以设置链接的
    有效期（period）和最大使用次数（count）。
    """

    class Meta:
        # 指定该表单关联的模型
        model = models.ProjectInvite

        # 指定在表单中需要显示的字段
        fields = ['period', 'count']