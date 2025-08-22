from django import forms
from app import models
from app.forms.bootstrap import BootStrapForm


class WikiModelForm(BootStrapForm, forms.ModelForm):
    """
    用于新建和编辑Wiki文章的ModelForm。
    - 继承BootStrapForm以应用样式。
    - 动态生成父文章的下拉选项。
    - 在编辑模式下，自动排除文章自身及其所有子孙文章，防止循环引用。
    """

    class Meta:
        model = models.Wiki
        exclude = ('project',)

    def __init__(self, request, *args, **kwargs):
        """
        重写构造方法，以动态处理 'parent' 字段的下拉选项。
        """
        super().__init__(*args, **kwargs)
        current_wiki_instance = self.instance
        queryset = models.Wiki.objects.filter(project=request.tracer.project)

        if current_wiki_instance and current_wiki_instance.pk:
            descendant_ids = self._get_descendant_ids(current_wiki_instance)
            exclude_ids = descendant_ids + [current_wiki_instance.pk]
            queryset = queryset.exclude(id__in=exclude_ids)

        self.fields['parent'].queryset = queryset

    def _get_descendant_ids(self, wiki_instance):
        """
        一个私有的辅助方法，用于递归地获取一个Wiki实例的所有子孙ID。

        :param wiki_instance: 当前的Wiki文章实例。
        :return: 一个包含所有子孙ID的列表。
        """
        descendant_ids = []
        children = wiki_instance.children.all()

        for child in children:
            descendant_ids.append(child.pk)
            descendant_ids.extend(self._get_descendant_ids(child))

        return descendant_ids