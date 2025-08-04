import datetime

from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

from app import models


class Tracer(object):
    """
    一个用于追踪和存储当前请求相关信息的对象。

    它会作为一个方便的容器，被附加到每个请求上，
    用于存放当前登录的用户及其有效的价格策略。
    """

    def __init__(self):
        self.user = None
        self.price_policy = None
        self.project = None


class AuthMiddleware(MiddlewareMixin):
    """
    认证与价格策略处理中间件。

    1.  为每个请求初始化一个 Tracer 对象。
    2.  检查用户登录状态。
    3.  对于已登录用户，动态获取其当前有效的价格策略。
    4.  实现访问控制，对未登录用户强制重定向到登录页面（白名单URL除外）。
    """

    def process_request(self, request):
        """在每个请求到达视图前执行。"""

        # 1. 初始化 Tracer 对象并附加到 request
        request.tracer = Tracer()
        user_id = request.session.get('user_id', 0)
        user_object = models.UserInfo.objects.filter(id=user_id).first()
        request.tracer.user = user_object

        # 2. 访问白名单中的URL，无需登录即可访问
        if request.path_info in settings.WHITE_REGEX_URL_LIST:
            return None

        # 3. 对非白名单URL，检查用户是否已登录
        if not user_object:
            return redirect('login')

        # 4. 获取用户当前有效的价格策略
        # 查找用户最近一个已付款的订单
        latest_transaction = models.Transaction.objects.filter(user=user_object, status=2).order_by('-id').first()

        # 检查付费套餐是否已过期
        current_datetime = datetime.datetime.now()
        if latest_transaction and latest_transaction.end_datetime and latest_transaction.end_datetime < current_datetime:
            # 如果已过期，则为其分配免费版套餐
            free_policy = models.PricePolicy.objects.filter(category=1).first()
            request.tracer.price_policy = free_policy
        elif latest_transaction:
            # 如果未过期，则使用该订单对应的套餐
            request.tracer.price_policy = latest_transaction.price_policy
        else:
            # 如果从未付过费，同样分配免费版套餐
            free_policy = models.PricePolicy.objects.filter(category=1).first()
            request.tracer.price_policy = free_policy

        return None

    def process_view(self, request, view, args, kwargs):

        if not request.path_info.startswith('/manage/'):
            return None
        project_id = kwargs.get('project_id')
        project_object = models.Project.objects.filter(id=project_id, creator=request.tracer.user).first()
        if project_object:
            request.tracer.project = project_object
            return None
        project_user_object = models.ProjectUser.objects.filter(user=request.tracer.user, project_id=project_id).first()
        if project_user_object:
            request.tracer.project = project_user_object.project
            return None
        return redirect('project_list')