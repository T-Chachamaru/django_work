from django.http import JsonResponse
from django.shortcuts import render, redirect
from app.forms.account import RegisterForm,SendSmsForm

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
    # 后端校验
    form = SendSmsForm(request, data=request.GET)
    if form.is_valid():
        return JsonResponse({'status': True})
    return JsonResponse({'status': False, 'error': form.errors})

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
        return render(request, 'app/register.html', {'form': form})

    form = RegisterForm(request.POST)
    if form.is_valid():
        form.save()
        return redirect('/login/')
    return render(request, 'app/register.html', {'form': form})