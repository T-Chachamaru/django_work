import datetime
import uuid

from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect

from app.forms.account import RegisterForm, SendSmsForm, LoginSmsForm, LoginForm
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
        instance = form.save()
        # 创建交易记录
        policy_object = models.PricePolicy.objects.filter(category=1, title='个人免费版').first()
        models.Transaction.objects.create(
            status=2,
            order=str(uuid.uuid4()),
            user=instance,
            price_policy=policy_object,
            count=0,
            price=0,
            start_datetime=datetime.datetime.now(),
        )
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
        form = LoginSmsForm()
        return render(request, 'app/login_sms.html', {'form': form})

    form = LoginSmsForm(data=request.POST)
    if form.is_valid():
        # 表单验证成功后，cleaned_data中已包含查询到的用户对象
        user_object = form.cleaned_data['mobile_phone']

        request.session['user_id'] = user_object.id
        request.session.set_expiry(60 * 60 * 24 * 14)

        return JsonResponse({'status': True, 'data': '/index/'})

    return JsonResponse({'status': False, 'error': form.errors})

def login(request):
    """处理邮箱和密码登录"""
    if request.method == 'GET':
        form = LoginForm(request=request)
        return render(request, 'app/login.html', {'form': form})

    form = LoginForm(request=request, data=request.POST)
    if form.is_valid():
        # 表单验证已在 LoginForm 的 clean 方法中完成
        # 现在可以直接从 cleaned_data 中获取用户对象
        user_object = form.cleaned_data['user_object']

        request.session['user_id'] = user_object.id
        request.session.set_expiry(60 * 60 * 24 * 14)  # 设置 session 两周内有效

        return redirect('index')

    return render(request, 'app/login.html', {'form': form})


def image_code(request):
    """
    生成图片验证码并返回。

    调用工具函数生成图片和验证码字符串，
    将验证码字符串存入 session，然后将图片以二进制流的形式返回。
    """
    from io import BytesIO
    from utils.image_code import generate_verification_code

    # 1. 调用工具函数生成图片对象和验证码字符串
    image_object, code = generate_verification_code()

    # 2. 将验证码字符串写入到当前用户的 session 中（以便后续验证）
    request.session['image_code'] = code
    request.session.set_expiry(60)  # 可选：设置验证码60秒后过期

    # 3. 将图片对象写入内存流
    stream = BytesIO()
    image_object.save(stream, 'png')

    # 4. 将内存中的图片数据作为 HTTP 响应返回
    return HttpResponse(stream.getvalue(), content_type='image/png')


def logout(request):
    """处理用户登出请求"""
    # 清空 session，移除所有已登录状态
    request.session.flush()
    return redirect('index')