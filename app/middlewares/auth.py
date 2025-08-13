import datetime

from django.conf import settings
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

from app import models


class Tracer(object):
    """
    一个用于追踪和存储当前请求相关信息的对象。

    它会作为一个方便的容器，被附加到每个请求(request)上，
    用于在整个请求生命周期中携带当前登录的用户、其价格策略以及正在访问的项目信息。
    """

    def __init__(self):
        self.user = None
        self.price_policy = None
        self.project = None


class AuthMiddleware(MiddlewareMixin):
    """
    用户认证与核心信息处理中间件。

    主要职责:
    1.  在每个请求开始时，为 request 对象附加一个 tracer 实例。
    2.  检查用户的登录状态，未登录用户将被重定向到登录页面（白名单URL除外）。
    3.  对于已登录用户，动态获取并设置其当前有效的价格策略。
    4.  对于项目管理相关的URL，校验用户是否有权访问该项目。
    """

    def process_request(self, request):
        """
        在每个请求到达视图(View)之前被调用。
        主要处理用户身份认证和价格策略的初始化。
        """
        request.tracer = Tracer()
        user_id = request.session.get('user_id', 0)
        user_object = models.UserInfo.objects.filter(id=user_id).first()
        request.tracer.user = user_object
        if request.path_info in settings.WHITE_REGEX_URL_LIST:
            return None
        if not user_object:
            return redirect('login')
        latest_transaction = models.Transaction.objects.filter(
            user=user_object, status=2
        ).order_by('-id').first()
        current_datetime = datetime.datetime.now()
        if latest_transaction and latest_transaction.end_datetime and latest_transaction.end_datetime < current_datetime:
            policy_object = models.PricePolicy.objects.filter(category=1).first()
        elif latest_transaction:
            policy_object = latest_transaction.price_policy
        else:
            policy_object = models.PricePolicy.objects.filter(category=1).first()
        request.tracer.price_policy = policy_object
        return None

    def process_view(self, request, view, args, kwargs):
        """
        在路由匹配成功，即将执行视图(View)之前被调用。
        主要用于校验用户对特定项目的访问权限。
        """
        if not request.path_info.startswith('/manage/'):
            return None
        project_id = kwargs.get('project_id')
        project_object = models.Project.objects.filter(
            id=project_id, creator=request.tracer.user
        ).first()
        if project_object:
            request.tracer.project = project_object
            return None
        project_user_object = models.ProjectUser.objects.filter(
            user=request.tracer.user, project_id=project_id
        ).first()
        if project_user_object:
            request.tracer.project = project_user_object.project
            return None
        return redirect('project_list')
