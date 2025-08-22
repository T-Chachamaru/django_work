import random

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Q
from django_redis import get_redis_connection

from app import models
from app.forms.bootstrap import BootStrapForm
from utils.tencent.sms import send_sms_single


class RegisterForm(BootStrapForm, forms.ModelForm):
    """
    用户注册表单。
    - 负责接收和校验用户注册信息。
    - 将密码加密后存入数据库。
    - 校验唯一性字段（用户名、邮箱、手机号）是否已被占用。
    """
    mobile_phone = forms.CharField(label='手机号', validators=[RegexValidator(r'^1[3-9]\d{9}$', '手机号格式错误')])
    password = forms.CharField(label='密码', min_length=8, max_length=64,
                               error_messages={'min_length': '密码长度不能小于8个字符',
                                               'max_length': '密码长度不能大于64个字符'}, widget=forms.PasswordInput())
    confirm_password = forms.CharField(label='重复密码', min_length=8, max_length=64,
                                       error_messages={'min_length': '重复密码长度不能小于8个字符',
                                                       'max_length': '重复密码长度不能大于64个字符'},
                                       widget=forms.PasswordInput())
    code = forms.CharField(label='验证码', widget=forms.TextInput())

    class Meta:
        model = models.UserInfo
        fields = ['username', 'email', 'password', 'confirm_password', 'mobile_phone', 'code']

    def clean(self):
        """
        表单级别验证。
        - 校验密码一致性。
        - 将多个唯一性字段（用户名、邮箱、手机号）的检查合并为一次数据库查询。
        - 对密码进行加密。
        """
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        username = cleaned_data.get('username')
        email = cleaned_data.get('email')
        mobile_phone = cleaned_data.get('mobile_phone')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', '两次输入的密码不一致')

        if all([username, email, mobile_phone]):
            existing_user = models.UserInfo.objects.filter(
                Q(username=username) | Q(email=email) | Q(mobile_phone=mobile_phone)
            ).first()
            if existing_user:
                if existing_user.username == username:
                    self.add_error('username', '用户名已存在')
                if existing_user.email == email:
                    self.add_error('email', '邮箱已存在')
                if existing_user.mobile_phone == mobile_phone:
                    self.add_error('mobile_phone', '手机号已存在')

        if password and not self.errors:
            cleaned_data['password'] = make_password(password)

        return cleaned_data

    def clean_code(self):
        """字段级别验证：校验手机验证码的正确性。"""
        code = self.cleaned_data.get('code')
        mobile_phone = self.cleaned_data.get('mobile_phone')

        if not mobile_phone:
            return code

        try:
            conn = get_redis_connection('default')
            stored_code = conn.get(f"sms_{mobile_phone}")
            if not stored_code:
                raise ValidationError("验证码失效或未发送，请重新获取")
            if code.strip().lower() != stored_code.decode('utf-8').lower():
                raise ValidationError("验证码错误")
        except Exception:
            raise ValidationError("验证码校验失败，请稍后重试")

        return code

class SendSmsForm(forms.Form):
    """
    发送短信验证码的表单。
    - 仅负责校验手机号格式和模板有效性。
    - 业务逻辑（如手机号是否已注册）应移至视图(View)中处理。
    """
    mobile_phone = forms.CharField(
        label='手机号',
        validators=[RegexValidator(r'^1[3-9]\d{9}$', '手机号格式错误')]
    )
    tpl = forms.ChoiceField(label='短信模板', choices=[('login', '登录'), ('register', '注册')])

    def clean(self):
        """
        表单级别验证。
        - 发送短信验证码并存入Redis。
        """
        cleaned_data = super().clean()
        mobile_phone = cleaned_data.get('mobile_phone')
        tpl = cleaned_data.get('tpl')

        if not all([mobile_phone, tpl]):
            return cleaned_data

        template_id = settings.TENCENT_SMS_APP_TEMPLATE.get(tpl)
        if not template_id:
            raise ValidationError("短信模板配置错误")

        code = str(random.randint(1000, 9999))
        print(f"生成的验证码: {code}，手机号: {mobile_phone}")

        # 发送短信（生产环境中应取消注释）
        # res = send_sms_single(mobile_phone, template_id, [code])
        # if res.get('result') != 0:
        #     raise ValidationError(f'短信发送失败: {res["errmsg"]}')

        try:
            conn = get_redis_connection('default')
            conn.set(f"sms_{mobile_phone}", code, ex=60)
        except Exception:
            raise ValidationError("验证码存储失败，请稍后重试")

        return cleaned_data


class LoginSmsForm(BootStrapForm, forms.Form):
    """短信登录表单，校验手机号和验证码。"""
    mobile_phone = forms.CharField(label='手机号', validators=[RegexValidator(r'^1[3-9]\d{9}$', '手机号格式错误')])
    code = forms.CharField(label='验证码', widget=forms.TextInput())

    def clean(self):
        """
        表单级别验证，校验手机号是否存在和验证码是否正确。
        """
        cleaned_data = super().clean()
        mobile_phone = cleaned_data.get('mobile_phone')
        code = cleaned_data.get('code')

        if not all([mobile_phone, code]):
            return cleaned_data

        user_object = models.UserInfo.objects.filter(mobile_phone=mobile_phone).first()
        if not user_object:
            self.add_error('mobile_phone', '该手机号未注册')
            return cleaned_data

        try:
            conn = get_redis_connection('default')
            stored_code = conn.get(f"sms_{mobile_phone}")
            if not stored_code:
                raise ValidationError("验证码已失效，请重新发送")
            if code.strip().lower() != stored_code.decode('utf-8').lower():
                raise ValidationError("验证码错误")
        except ValidationError as e:
            self.add_error('code', e)
        except Exception:
            self.add_error('code', "验证码校验失败，请稍后重试")

        cleaned_data['user_object'] = user_object
        return cleaned_data

class LoginForm(BootStrapForm, forms.Form):
    """邮箱或手机号密码登录表单，校验凭据和图片验证码。"""
    user_input = forms.CharField(label='邮箱或手机号')
    password = forms.CharField(label='密码', widget=forms.PasswordInput(render_value=True))
    code = forms.CharField(label='图片验证码')

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request

    def clean_code(self):
        code = self.cleaned_data.get('code')
        session_code = self.request.session.get('image_code')
        if not session_code:
            raise ValidationError("验证码已过期，请刷新页面")
        if code.strip().upper() != session_code.upper():
            raise ValidationError("验证码输入错误")
        return code

    def clean(self):
        """全局校验，处理用户身份和密码验证。"""
        cleaned_data = super().clean()
        user_input = cleaned_data.get('user_input')
        password = cleaned_data.get('password')

        if not all([user_input, password]):
            return cleaned_data

        user_object = models.UserInfo.objects.filter(
            Q(email=user_input) | Q(mobile_phone=user_input)
        ).first()

        if not user_object or not check_password(password, user_object.password):
            raise ValidationError("用户名或密码错误")

        cleaned_data['user_object'] = user_object
        return cleaned_data
