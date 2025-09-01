import datetime
import json
from urllib.parse import parse_qs

from django.http import HttpResponse
from django.shortcuts import render, redirect
from django_redis import get_redis_connection

from app import models
from app.views.issues import _uid
from django_work import settings
from utils.alipay import AliPaySDK


def index(request):
    """
    渲染首页。
    """
    return render(request, 'app/index.html')

def price(request):
    """
    渲染价格套餐页面。
    """
    policy_list = models.PricePolicy.objects.filter(category=2)
    return render(request, 'app/price.html', {'policy_list': policy_list})

def payment(request, policy_id):
    """
    渲染支付确认页面。

    - 验证套餐和购买数量。
    - 计算新订单价格。
    - 如果用户有正在生效的付费套餐，计算可抵扣的余额。
    - 将订单信息临时存入 Redis，有效期30分钟。
    """
    policy_object = models.PricePolicy.objects.filter(id=policy_id, category=2).first()
    if not policy_object:
        return redirect('price')

    number = request.GET.get('number', '')
    if not number or not number.isdecimal() or int(number) < 1:
        return redirect('price')
    number = int(number)

    origin_price = number * policy_object.price
    balance = 0
    current_order = None
    if request.tracer.price_policy.category == 2:
        current_order = models.Transaction.objects.filter(user=request.tracer.user, status=2).order_by('-id').first()
        if current_order:
            total_timedelta = current_order.end_datetime - current_order.start_datetime
            balance_timedelta = current_order.end_datetime - datetime.datetime.now()
            if total_timedelta.days > 0 and balance_timedelta.days > 0:
                daily_price = current_order.price / total_timedelta.days
                balance = daily_price * balance_timedelta.days

    if balance >= origin_price:
        return redirect('price')

    total_price = origin_price - round(balance, 2)
    payment_context = {
        'policy_id': policy_object.id,
        'number': number,
        'origin_price': origin_price,
        'balance': round(balance, 2),
        'total_price': total_price,
    }

    conn = get_redis_connection()
    redis_key = f'payment_{request.tracer.user.id}'
    conn.set(redis_key, json.dumps(payment_context), ex=60 * 30)

    context = {
        'policy_object': policy_object,
        'transaction': current_order,
        **payment_context
    }
    return render(request, 'app/payment.html', context)

def pay(request):
    """
    创建本地订单并发起支付宝支付。

    - 从 Redis 中获取待支付信息。
    - 创建一个状态为“未支付”的本地交易记录。
    - 调用 AliPaySDK 生成支付页面的完整 URL。
    - 重定向用户到支付宝支付页面。
    """
    conn = get_redis_connection()
    redis_key = f'payment_{request.tracer.user.id}'
    context_string = conn.get(redis_key)
    if not context_string:
        return redirect('price')
    context = json.loads(context_string.decode('utf-8'))

    order_id = _uid(str(request.tracer.user.id))
    models.Transaction.objects.create(
        status=1,
        order=order_id,
        user=request.tracer.user,
        price_policy_id=context['policy_id'],
        count=context['number'],
        price=context['total_price']
    )

    alipay = AliPaySDK(
        appid=settings.ALI_APPID,
        app_notify_url=settings.ALI_NOTIFY_URL,
        return_url=settings.ALI_RETURN_URL,
        app_private_key_path=settings.ALI_PRI_KEY_PATH,
        alipay_public_key_path=settings.ALI_PUB_KEY_PATH,
        debug=True
    )

    pay_url = alipay.direct_pay(
        subject="Tracer系统会员",
        out_trade_no=order_id,
        total_amount=context['total_price'],
    )
    return redirect(pay_url)

def pay_notify(request):
    """
    处理支付宝的异步通知 (POST) 和同步跳转 (GET)。
    """
    ali_pay = AliPaySDK(
        appid=settings.ALI_APPID,
        app_notify_url=settings.ALI_NOTIFY_URL,
        return_url=settings.ALI_RETURN_URL,
        app_private_key_path=settings.ALI_PRI_KEY_PATH,
        alipay_public_key_path=settings.ALI_PUB_KEY_PATH,
        debug=True
    )

    if request.method == 'GET':
        params = request.GET.dict()
        sign = params.pop('sign', None)
        status = ali_pay.verify(params, sign)
        if status:
            order_id = params.get('out_trade_no')
            # 也可以在这里更新订单状态，但异步通知更可靠
            # _update_order_status(order_id)
            return redirect('payment_success')
        return HttpResponse('支付失败（同步）')

    elif request.method == 'POST':
        body_str = request.body.decode('utf-8')
        post_data = parse_qs(body_str)
        post_dict = {k: v[0] for k, v in post_data.items()}
        sign = post_dict.pop('sign', None)
        status = ali_pay.verify(post_dict, sign)
        if status:
            order_id = post_dict.get('out_trade_no')
            _update_order_status(order_id)
            return HttpResponse('success')
        return HttpResponse('error')
    else:
        return HttpResponse('error')

def payment_success(request):
    """
    渲染支付成功页面。
    通过GET参数获取订单号，并从数据库中检索订单信息以供显示。
    """
    order_id = request.GET.get('order_id')
    transaction_object = models.Transaction.objects.filter(
        order=order_id,
        user=request.tracer.user,
        status=2
    ).first()
    return render(request, 'app/payment_success.html', {'transaction': transaction_object})

def _update_order_status(order_id):
    """
    辅助函数：更新订单状态，确保幂等性。

    :param order_id: 商户订单号
    """
    order_object = models.Transaction.objects.filter(order=order_id).first()
    if order_object and order_object.status == 1:
        order_object.status = 2
        order_object.start_datetime = datetime.datetime.now()
        order_object.end_datetime = order_object.start_datetime + datetime.timedelta(days=365 * order_object.count)
        order_object.save()
