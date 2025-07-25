from django.conf import settings
from django.core.validators import RegexValidator
from django.http import HttpResponse, JsonResponse
from django import forms
from django.shortcuts import render, redirect
from app import models
import random
from utils.tencent.sms import send_sms_single
import redis

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
                r = redis.Redis(host='localhost', port=6379, password='foobared', encoding='utf-8')
                stored_code = r.get(mobile_phone)
                if stored_code is None or stored_code != code:
                    raise forms.ValidationError({'code':'验证码错误或已过期'})
            except redis.RedisError:
                raise forms.ValidationError({'code':'无法验证验证码，请稍后重试'})

        return cleaned_data

    def save(self, commit=True):
        # 仅保存模型字典，排除 confirm_password 和 code
        instance = super().save(commit=False)
        instance.set_password(self.cleaned_data['password'])
        if commit:
            instance.save()
        return instance


def send_sms(request):
    """
    发送短信验证码。

    接收 GET 参数：
    - tpl: 模板类型（login 或 register）。
    - phone: 手机号码。
    生成随机验证码，发送短信，并存储到 Redis（有效期60秒）。
    返回 JSON 响应，包含 success 状态和错误信息（如果有）。
    注意：测试环境中，无论短信发送是否成功，验证码都会存储并返回成功。
    """
    tpl = request.GET.get('tpl')
    phone = request.GET.get('phone')
    template_id = settings.TENCENT_SMS_APP_TEMPLATE.get(tpl)
    if not template_id:
        return JsonResponse({'success': False, 'errmsg': '模板不存在'})

    code = random.randrange(1000, 9999)
    # 注意修改 qcloudsms 包内的 httpclient.py 文件的 HTTPResponse 类，将 json 方法使用到的 encoding 删除
    res = send_sms_single(phone, template_id, [code,])

    # 存储验证码到 Redis（无论发送是否成功）
    try:
        r = redis.Redis(host='localhost', port=6379, password='foobared', encoding='utf-8')
        r.set(phone, code, ex=60)
    except redis.RedisError as e:
        return JsonResponse({'success': False, 'errmsg': '数据库错误'})

    # 检查短信发送结果
    if res.get('result') == 0:
        return JsonResponse({'success': True, 'errmsg': '验证码发送成功'})
    else:
        return JsonResponse({'success': True, 'errmsg': '验证码发送成功'})
        # 生产环境中应返回：{'success': False, 'errmsg': res.get('errmsg', '短信发送失败')}

def register(request):
    """
    处理用户注册请求。

    - GET 请求：渲染注册页面，显示空的注册表单。
    - POST 请求：验证表单数据，包括手机号码、密码、确认密码和验证码。
      - 验证手机号码格式（通过表单的 RegexValidator）。
      - 验证密码一致性（通过 clean 方法）。
      - 验证验证码是否匹配 Redis 存储的值（通过 clean 方法）。
      - 如果验证通过，保存用户信息（加密密码）并重定向到登录页面。
      - 如果验证失败，重新渲染注册页面并显示错误信息。
    """
    if request.method == 'GET':
        form = RegisterForm()
        return render(request, 'register.html', {'form': form})

    form = RegisterForm(request.POST)
    if form.is_valid():
        form.save()
        return redirect('/login/')
    return render(request, 'register.html', {'form': form})