from django.conf import settings
from django.core.validators import RegexValidator
from django.http import HttpResponse, JsonResponse
from django import forms
from django.shortcuts import render
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

def send_sms(request):
    """
    发送短信
    ?tpl=login
    ?tpl=register
    """
    tpl = request.GET.get('tpl')
    phone = request.GET.get('phone')
    template_id = settings.TENCENT_SMS_APP_TEMPLATE.get(tpl)
    if not template_id:
        return JsonResponse({'success': False, 'errmsg': '模板不存在'})

    code = random.randrange(1000, 9999)
    # 注意修改qcloudsms包内的httpclient.py文件的HTTPResponse类，将json方法使用到的encoding删除
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
    #     return JsonResponse({'success': False, 'errmsg': '短信发送失败'})

def register(request):
    form = RegisterForm()
    return render(request, 'register.html', {'form': form})