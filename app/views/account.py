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

    form = RegisterForm(data=request.POST)
    if form.is_valid():
        instance = form.save()
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
    tpl = request.GET.get('tpl')
    mobile_phone = request.GET.get('mobile_phone')
    exists = models.UserInfo.objects.filter(mobile_phone=mobile_phone).exists()

    if tpl == 'login' and not exists:
        return JsonResponse({'status': False, 'error': {'mobile_phone': ['手机号未注册']}})
    if tpl == 'register' and exists:
        return JsonResponse({'status': False, 'error': {'mobile_phone': ['手机号已被注册']}})

    form = SendSmsForm(request, data=request.GET)
    if form.is_valid():
        return JsonResponse({'status': True})
    return JsonResponse({'status': False, 'error': form.errors})

def login_sms(request):
    """短信验证码登录"""
    if request.method == 'GET':
        form = LoginSmsForm()
        return render(request, 'app/login_sms.html', {'form': form})

    form = LoginSmsForm(data=request.POST)
    if form.is_valid():
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
        user_object = form.cleaned_data['user_object']
        request.session['user_id'] = user_object.id
        request.session.set_expiry(60 * 60 * 24 * 14)
        return redirect('index')
    return render(request, 'app/login.html', {'form': form})

def image_code(request):
    """生成图片验证码并返回。"""
    from io import BytesIO
    from utils.image_code import generate_verification_code

    image_object, code = generate_verification_code()
    request.session['image_code'] = code
    request.session.set_expiry(60)
    stream = BytesIO()
    image_object.save(stream, 'png')
    return HttpResponse(stream.getvalue(), content_type='image/png')

def logout(request):
    """处理用户登出请求"""
    request.session.flush()
    return redirect('index')