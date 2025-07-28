import random

from django import forms
from django.conf import settings
from django.core.validators import RegexValidator
from django.contrib.auth.hashers import make_password
from django_redis import get_redis_connection

from app import models
from app.forms.bootstrap import BootStrapForm
from utils.tencent.sms import send_sms_single


class RegisterForm(BootStrapForm, forms.ModelForm):
    """用户注册表单"""
    mobile_phone = forms.CharField(
        label='手机号',
        validators=[RegexValidator(r'^1[3-9]\d{9}$', '手机号格式错误')]
    )
    password = forms.CharField(
        label='密码',
        min_length=8,
        max_length=64,
        error_messages={
            'min_length': '密码长度不能小于8个字符',
            'max_length': '密码长度不能大于64个字符'
        },
        widget=forms.PasswordInput()
    )
    confirm_password = forms.CharField(
        label='重复密码',
        min_length=8,
        max_length=64,
        error_messages={
            'min_length': '重复密码长度不能小于8个字符',
            'max_length': '重复密码长度不能大于64个字符'
        },
        widget=forms.PasswordInput()
    )
    code = forms.CharField(
        label='验证码',
        widget=forms.TextInput()
    )

    class Meta:
        model = models.UserInfo
        # 定义表单需要渲染的字段
        fields = ['username', 'email', 'password', 'confirm_password', 'mobile_phone', 'code']

    def clean_username(self):
        """校验用户名是否存在"""
        username = self.cleaned_data.get('username')
        if models.UserInfo.objects.filter(username=username).exists():
            raise forms.ValidationError("用户名已存在")
        return username

    def clean_email(self):
        """校验邮箱是否存在"""
        email = self.cleaned_data.get('email')
        if models.UserInfo.objects.filter(email=email).exists():
            raise forms.ValidationError("邮箱已存在")
        return email

    def clean_mobile_phone(self):
        """校验手机号是否存在"""
        mobile_phone = self.cleaned_data['mobile_phone']
        if models.UserInfo.objects.filter(mobile_phone=mobile_phone).exists():
            raise forms.ValidationError("手机号已注册")
        return mobile_phone

    def clean_code(self):
        """校验手机验证码是否正确"""
        code = self.cleaned_data['code']
        mobile_phone = self.cleaned_data.get('mobile_phone')

        # 确保手机号字段已通过验证
        if not mobile_phone:
            return code

        try:
            conn = get_redis_connection('default')
            stored_code = conn.get(mobile_phone)

            if not stored_code:
                raise forms.ValidationError("验证码失效或未发送")

            if code.strip() != stored_code.decode('utf-8'):
                raise forms.ValidationError("验证码错误")
        except Exception:
            # 捕获Redis连接等潜在异常
            raise forms.ValidationError("验证码校验失败，请稍后重试")

        return code

    def clean(self):
        """全局校验：密码一致性检查 & 密码加密"""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        # 校验两次密码是否一致
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', '两次输入的密码不一致')

        # 使用Django内置方法对密码进行安全加密
        if password:
            cleaned_data['password'] = make_password(password)

        return cleaned_data


class SendSmsForm(forms.Form):
    """发送短信验证码表单"""
    mobile_phone = forms.CharField(
        label='手机号',
        validators=[RegexValidator(r'^1[3-9]\d{9}$', '手机号格式错误')]
    )

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request

    def clean_mobile_phone(self):
        """校验手机号并发送验证码"""
        mobile_phone = self.cleaned_data['mobile_phone']

        # 从请求中获取短信模板类型（如：注册/登录）
        tpl = self.request.GET.get('tpl')
        template_id = settings.TENCENT_SMS_APP_TEMPLATE.get(tpl)
        if not template_id:
            raise forms.ValidationError("短信模板不存在")

        # 生成随机验证码
        code = random.randrange(1000, 9999)
        print(f"生成的验证码: {code}")  # 方便调试

        # 发送短信
        # res = send_sms_single(mobile_phone, template_id, [code, ])
        # if res.get('result') != 0:
        #     raise forms.ValidationError(f'短信发送失败，{res["errmsg"]}')

        # 将验证码存入Redis，有效期60秒
        conn = get_redis_connection('default')
        conn.set(mobile_phone, code, ex=60)

        return mobile_phone


class LoginForm(BootStrapForm, forms.Form):
    """短信登录表单"""
    mobile_phone = forms.CharField(
        label='手机号',
        validators=[RegexValidator(r'^1[3-9]\d{9}$', '手机号格式错误')]
    )
    code = forms.CharField(
        label='验证码',
        widget=forms.TextInput()
    )

    def clean_mobile_phone(self):
        """校验手机号是否存在，并返回用户对象"""
        mobile_phone = self.cleaned_data['mobile_phone']
        user_object = models.UserInfo.objects.filter(mobile_phone=mobile_phone).first()
        if not user_object:
            raise forms.ValidationError('手机号未注册')

        # 将查询到的用户对象直接返回，供后续方法使用，避免二次查询
        return user_object

    def clean_code(self):
        """校验验证码，此时mobile_phone字段已是user_object"""
        user_object = self.cleaned_data.get('mobile_phone')
        code = self.cleaned_data.get('code')

        # 如果手机号验证未通过，则直接返回，无需校验验证码
        if not user_object:
            return code

        conn = get_redis_connection('default')
        stored_code = conn.get(user_object.mobile_phone)

        if not stored_code:
            raise forms.ValidationError("验证码已失效，请重新发送")

        if code.strip() != stored_code.decode('utf-8'):
            raise forms.ValidationError("验证码错误")

        return code
