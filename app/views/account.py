from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View

from app.forms.account import RegisterForm, SendSmsForm, LoginForm
from app import models


def register(request):
    """处理用户注册"""
    if request.method == 'GET':
        form = RegisterForm()
        return render(request, 'app/register.html', {'form': form})

    # 接收并校验POST数据
    form = RegisterForm(data=request.POST)
    if form.is_valid():
        # ModelForm验证通过，直接保存即可自动创建用户（密码已在Form中加密）
        form.save()
        return JsonResponse({'status': True, 'data': '/login/sms/'})

    return JsonResponse({'status': False, 'error': form.errors})


def send_sms(request):
    """发送短信验证码的视图"""

    # 视图层先处理业务逻辑：根据场景判断手机号状态
    tpl = request.GET.get('tpl')
    mobile_phone = request.GET.get('mobile_phone')
    exists = models.UserInfo.objects.filter(mobile_phone=mobile_phone).exists()

    if tpl == 'login' and not exists:
        return JsonResponse({'status': False, 'error': {'mobile_phone': ['手机号未注册']}})
    if tpl == 'register' and exists:
        return JsonResponse({'status': False, 'error': {'mobile_phone': ['手机号已被注册']}})

    # 业务逻辑通过后，再交由Form验证格式、发送短信、写入Redis
    form = SendSmsForm(request, data=request.GET)
    if form.is_valid():
        # is_valid()会触发clean_mobile_phone，成功则代表短信已发送
        return JsonResponse({'status': True})

    return JsonResponse({'status': False, 'error': form.errors})


def login_sms(request):
    """短信验证码登录"""
    if request.method == 'GET':
        form = LoginForm()
        return render(request, 'app/login_sms.html', {'form': form})

    form = LoginForm(data=request.POST)
    if form.is_valid():
        # 表单验证成功后，cleaned_data中已包含查询到的用户对象
        user_object = form.cleaned_data['mobile_phone']

        # 在Session中记录用户登录状态
        request.session['user_id'] = user_object.id
        request.session.set_expiry(60 * 60 * 24 * 14)  # 设置session两周内有效

        return JsonResponse({'status': True, 'data': '/index/'})

    return JsonResponse({'status': False, 'error': form.errors})
