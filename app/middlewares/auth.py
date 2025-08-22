import datetime
from django.conf import settings
from django.db.models import Q
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

from app import models

class Tracer(object):
    """
    一个用于追踪和存储当前请求上下文信息的对象。

    它作为request的一个属性，充当一个轻量级的容器，方便在整个请求-响应周期中
    传递和访问当前用户、其价格策略以及正在操作的项目等核心数据。
    """

    def __init__(self):
        self.user = None
        self.price_policy = None
        self.project = None

class AuthMiddleware(MiddlewareMixin):
    """
    用户认证与核心信息处理中间件。

    主要职责:
    1.  初始化Tracer对象，并从session中获取当前用户。
    2.  校验用户登录状态，对受保护的URL进行访问控制。
    3.  高效地计算并设置用户当前生效的价格策略（处理付费、免费、过期等情况）。
    4.  对于项目相关的URL，用单次数据库查询高效校验用户权限（创建者或参与者）。
    """

    def process_request(self, request):
        """
        在每个请求到达视图前执行，主要处理用户身份和全局权限（如价格策略）。
        """
        request.tracer = Tracer()
        user_id = request.session.get('user_id', 0)
        current_user = models.UserInfo.objects.filter(id=user_id).first()
        request.tracer.user = current_user

        if request.path_info in settings.WHITE_REGEX_URL_LIST:
            return None

        if not current_user:
            return redirect('login')

        latest_transaction = models.Transaction.objects.filter(
            user=current_user, status=2
        ).select_related('price_policy').order_by('-id').first()
        effective_policy = None
        current_datetime = datetime.datetime.now()

        if latest_transaction and (
                not latest_transaction.end_datetime or latest_transaction.end_datetime > current_datetime):
            effective_policy = latest_transaction.price_policy

        if not effective_policy:
            try:
                effective_policy = models.PricePolicy.objects.get(category=1)
            except models.PricePolicy.DoesNotExist:
                pass

        request.tracer.price_policy = effective_policy
        return None

    def process_view(self, request, view, args, kwargs):
        """
        在路由匹配成功、视图执行前调用，主要处理与具体视图相关的权限，如项目访问。
        """
        if not request.path_info.startswith('/manage/'):
            return None

        project_id = kwargs.get('project_id')
        current_user = request.tracer.user
        project_object = models.Project.objects.filter(
            Q(creator=current_user) | Q(projectuser__user=current_user),
            id=project_id
        ).distinct().first()

        if project_object:
            request.tracer.project = project_object
            return None

        return redirect('project_list')