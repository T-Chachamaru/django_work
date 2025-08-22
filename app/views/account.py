import uuid
import datetime
from io import BytesIO

from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse

from app.forms.account import RegisterForm, SendSmsForm, LoginSmsForm, LoginForm
from app import models
from utils.image_code import generate_verification_code

def _perform_login(request, user_object):
    """
    一个私有的辅助函数，用于处理用户登录后的session设置。
    避免在多个登录视图中重复代码。
    """
    request.session['user_id'] = user_object.id
    request.session.set_expiry(60 * 60 * 24 * 14)

def register(request):
    """
    处理用户注册。
    - GET: 显示注册表单。
    - POST (AJAX): 验证数据并创建用户和初始套餐。
    """
    if request.method == 'GET':
        form = RegisterForm()
        return render(request, 'app/register.html', {'form': form})

    form = RegisterForm(data=request.POST)
    if form.is_valid():
        try:
            with transaction.atomic():
                user_instance = form.save()
                policy_object = models.PricePolicy.objects.get(category=1, title='个人免费版')
                models.Transaction.objects.create(
                    status=2,
                    order=str(uuid.uuid4()),
                    user=user_instance,
                    price_policy=policy_object,
                    count=0,
                    price=0,
                    start_datetime=datetime.datetime.now(),
                )
        except models.PricePolicy.DoesNotExist:
            return JsonResponse({'status': False, 'error': {'__all__': ['注册失败：初始套餐未找到，请联系管理员。']}})
        except Exception as e:
            return JsonResponse({'status': False, 'error': {'__all__': ['注册失败，请稍后重试。']}})

        return JsonResponse({'status': True, 'data': reverse('login_sms')})

    return JsonResponse({'status': False, 'error': form.errors})

def send_sms(request):
    """
    (AJAX) 根据模板类型（注册/登录）发送短信验证码。
    在发送前会校验手机号是否已注册。
    """
    form = SendSmsForm(request, data=request.GET)
    if form.is_valid():
        tpl = form.cleaned_data['tpl']
        mobile_phone = form.cleaned_data['mobile_phone']

        if tpl == 'register' and models.UserInfo.objects.filter(mobile_phone=mobile_phone).exists():
            return JsonResponse({'status': False, 'error': {'mobile_phone': ['该手机号已被注册。']}})

        if tpl == 'login' and not models.UserInfo.objects.filter(mobile_phone=mobile_phone).exists():
            return JsonResponse({'status': False, 'error': {'mobile_phone': ['该手机号未注册。']}})

        # 验证通过，发送短信（此处为模拟）
        # result = send_tencent_sms(mobile_phone, code)
        # if not result:
        #     return JsonResponse({'status': False, 'error': "短信发送失败"})

        return JsonResponse({'status': True})

    return JsonResponse({'status': False, 'error': form.errors})

def login_sms(request):
    """
    处理短信验证码登录。
    - GET: 显示登录表单。
    - POST (AJAX): 验证验证码并登录。
    """
    if request.method == 'GET':
        form = LoginSmsForm()
        return render(request, 'app/login_sms.html', {'form': form})

    form = LoginSmsForm(data=request.POST)
    if form.is_valid():
        user_object = form.cleaned_data['mobile_phone']
        _perform_login(request, user_object)
        return JsonResponse({'status': True, 'data': reverse('index')})

    return JsonResponse({'status': False, 'error': form.errors})

def login(request):
    """
    处理用户名/密码登录。
    - GET: 显示登录表单。
    - POST (标准表单提交): 验证凭据并登录。
    """
    if request.method == 'GET':
        form = LoginForm(request=request)
        return render(request, 'app/login.html', {'form': form})

    form = LoginForm(request=request, data=request.POST)
    if form.is_valid():
        user_object = form.cleaned_data['user_object']
        _perform_login(request, user_object)
        return redirect('index')

    return render(request, 'app/login.html', {'form': form})

def image_code(request):
    """
    生成图片验证码，将图片作为HTTP响应返回，并将验证码文本存入session。
    """
    image_object, code = generate_verification_code()
    request.session['image_code'] = code
    request.session.set_expiry(60)
    stream = BytesIO()
    image_object.save(stream, 'png')

    return HttpResponse(stream.getvalue(), content_type='image/png')

def logout(request):
    """
    处理用户登出请求，清空当前会话。
    """
    request.session.flush()
    return redirect('index')