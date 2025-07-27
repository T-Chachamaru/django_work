from django.core.validators import RegexValidator
from django import forms
from django.http import JsonResponse
from django_redis import get_redis_connection
from app import models
from utils.tencent.sms import send_sms_single
from django.conf import settings
import random

class RegisterForm(forms.ModelForm):
    """
    注册表单类，用于处理用户注册时的输入验证和表单渲染。

    该表单基于 `UserInfo` 模型，包含用户名、邮箱、密码、确认密码、手机号码和验证码字段。
    - 手机号码：验证是否为中国大陆11位手机号（以1开头，第二位为3-9）。
    - 密码：使用密码输入框，隐藏输入内容。
    - 确认密码：用于验证密码一致性。
    - 验证码：用于输入短信验证码。
    - 所有字段：自动添加 Bootstrap的`form-control`类和占位符。
    """
    mobile_phone = forms.CharField(label='手机号', validators=[RegexValidator(r'^1[3-9]\d{9}$','手机号格式错误'),])
    password = forms.CharField(label='密码', widget=forms.PasswordInput())
    confirm_password = forms.CharField(label='重复密码', widget=forms.PasswordInput())
    code = forms.CharField(label='验证码', widget=forms.TextInput())

    class Meta:
        model = models.UserInfo
        fields = ['username', 'email', 'password', 'confirm_password', 'mobile_phone', 'code']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name,field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['placeholder'] = "请输入{}".format(field.label)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        mobile_phone = cleaned_data.get('mobile_phone')
        code = cleaned_data.get('code')

        # 验证密码一致性
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError({'confirm_password':'两次输入的密码不一致'})

        # 验证验证码
        if mobile_phone and code:
            try:
                conn = get_redis_connection('default')
                stored_code = conn.get(mobile_phone)
                if stored_code is None or stored_code != code:
                    raise forms.ValidationError({'code':'验证码错误或已过期'})
            except Exception as e:
                raise forms.ValidationError({'code':'无法验证验证码，请稍后重试'})

        return cleaned_data

    def save(self, commit=True):
        # 仅保存模型字典，排除 confirm_password 和 code
        instance = super().save(commit=False)
        instance.set_password(self.cleaned_data['password'])
        if commit:
            instance.save()
        return instance

class SendSmsForm(forms.Form):
    mobile_phone = forms.CharField(label='手机号', validators=[RegexValidator(r'^1[3-9]\d{9}$','手机号格式错误'),])

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request

    def clean_mobile_phone(self):
        # 钩子函数验证手机号是否已存在
        mobile_phone = self.cleaned_data.get('mobile_phone')
        exists = models.UserInfo.objects.filter(mobile_phone=mobile_phone).exists()
        if exists:
            raise forms.ValidationError('手机号已存在')
        tpl = self.request.GET.get('tpl')

        # 钩子函数验证短信模板是否正确
        template_id = settings.TENCENT_SMS_APP_TEMPLATE.get(tpl)
        if not template_id:
            raise forms.ValidationError('模板不存在')

        # 发送短信
        code = random.randrange(1000, 9999)
        # 注意修改 qcloudsms 包内的 httpclient.py 文件的 HTTPResponse 类，将 json 方法使用到的 encoding 删除
        res = send_sms_single(mobile_phone, template_id, [code, ])
        # 测试环境注释，生产环境去掉下面的注释
        # if res.get('result') != 0:
        #     raise forms.ValidationError('短信发送失败，{}'.format(res['errmsg']))

        # 存储验证码到 Redis
        conn = get_redis_connection('default')
        conn.set(mobile_phone, code, ex=60)

        return mobile_phone