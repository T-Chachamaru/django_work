from django import forms
from django.core.exceptions import ValidationError

from app import models
from app.forms.bootstrap import BootStrapForm
from utils.tencent.cos import CosManager
from qcloud_cos.cos_exception import CosServiceError


class FolderModelForm(BootStrapForm, forms.ModelForm):
    """ 用于新建和编辑文件夹的 ModelForm。"""

    class Meta:
        model = models.FileRepository
        fields = ['name']

    def __init__(self, request, parent_object, *args, **kwargs):
        """
        重写构造方法，接收并存储 request 和 parent_object。
        这使得我们可以在验证方法中获取当前项目、用户以及父文件夹的信息。
        """
        super().__init__(*args, **kwargs)
        self.request = request
        self.parent_object = parent_object

    def clean_name(self):
        """
        字段级别验证：确保在同一个父目录下，文件夹名称不重复。
        """
        name = self.cleaned_data.get('name')
        query_filters = {
            'file_type': 2,
            'name': name,
            'project': self.request.tracer.project,
            'parent': self.parent_object
        }
        queryset = models.FileRepository.objects.filter(**query_filters)

        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise ValidationError("该目录下已存在同名文件夹")

        return name


class FileModelForm(forms.ModelForm):
    """
    文件上传后，用于在后端进行安全校验并将元数据写入数据库的表单。
    这是文件上传安全体系的关键一环。
    """
    # 从前端接收POST过来的etag，用于和COS上的真实etag进行比对
    etag = forms.CharField(label='ETag')

    class Meta:
        model = models.FileRepository
        # 排除这些字段，它们将由后端逻辑自动填充，而不是由用户提交
        exclude = ['project', 'file_type', 'update_user', 'update_datetime', 'file_path']

    def __init__(self, request, *args, **kwargs):
        """
        重写构造方法，接收并存储request对象。
        """
        super().__init__(*args, **kwargs)
        self.request = request

    def clean(self):
        """
        表单级别验证：在所有字段都通过基础验证后执行。
        核心职责：调用COS API，核对前端提交的文件元数据（key, etag, size）是否真实存在于云端。
        """
        key = self.cleaned_data.get('key')
        etag = self.cleaned_data.get('etag')
        size = self.cleaned_data.get('size')

        if not key or not etag:
            return super().clean()

        project = self.request.tracer.project
        cos_client = CosManager(region=project.region)

        try:
            cos_metadata = cos_client.check_file(bucket=project.bucket, key=key)
        except CosServiceError:
            self.add_error('key', '文件不存在或上传凭证无效。')
            return super().clean()

        cos_etag = cos_metadata.get('ETag', "")
        if f'"{etag}"' != cos_etag:
            self.add_error('etag', '文件内容校验失败，请重新上传。')

        cos_length = int(cos_metadata.get('Content-Length', 0))
        if cos_length != size:
            self.add_error('size', '文件大小校验失败，请重新上传。')

        full_url = f"https://{project.bucket}.cos.{project.region}.myqcloud.com/{key}"
        self.cleaned_data['file_path'] = full_url

        return self.cleaned_data