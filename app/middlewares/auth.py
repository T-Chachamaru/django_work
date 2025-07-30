from django.utils.deprecation import MiddlewareMixin

from app import models


class AuthMiddleware(MiddlewareMixin):
    """
    用户认证中间件

    处理每个到达服务器的请求，检查 session 中是否存在 user_id。
    如果存在，则从数据库中获取对应的用户对象，并将其附加到 request 对象上，
    以便在项目的任何视图和模板中都能轻松访问当前登录的用户信息。
    """

    def process_request(self, request):
        """
        在请求到达视图前执行。

        将查询到的用户对象（或 None）赋值给 request.tracer。
        """
        # 1. 从 session 中获取 user_id，如果不存在则默认为 0
        user_id = request.session.get('user_id', 0)

        # 2. 根据 user_id 查询用户对象。
        #    .first() 在找不到对象时会返回 None，避免了抛出异常。
        user_object = models.UserInfo.objects.filter(id=user_id).first()

        # 3. 将用户对象（或 None）赋值给 request.tracer，供后续使用。
        #    这是一种自定义约定，使得在视图函数中可以通过 request.tracer
        #    来获取当前登录的用户，如果未登录则为 None。
        request.tracer = user_object
