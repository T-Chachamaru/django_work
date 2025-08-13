import ssl
from django.conf import settings
from qcloudsms_py import SmsSingleSender
from qcloudsms_py.httpclient import HTTPError

# 以下这行代码是为了绕过SSL证书验证，在某些开发环境中可能需要。
# 但在生产环境中，这会带来安全风险。正确的做法是确保服务器环境信任相关的SSL证书。
# 如果非生产环境，可以保留；生产环境强烈建议移除，并配置好证书。
ssl._create_default_https_context = ssl._create_unverified_context

def send_sms_single(phone_num: str, template_id: int, template_param_list: list):
    """
    发送单条腾讯云短信。

    Args:
        phone_num (str): 需要发送短信的手机号码。
        template_id (int): 腾讯云后台配置的短信模板ID。
        template_param_list (list): 模板中的参数列表，如 [验证码, 有效时间]。

    Returns:
        dict: 腾讯云API返回的原始响应。如果发生网络错误，则返回一个自定义的错误字典。
    """
    appid = settings.TENCENT_SMS_APP_ID
    appkey = settings.TENCENT_SMS_APP_KEY
    sms_sign = settings.TENCENT_SMS_APP_SIGN
    sender = SmsSingleSender(appid, appkey)
    try:
        response = sender.send_with_param(
            86, phone_num, template_id, template_param_list, sign=sms_sign
        )
    except HTTPError as e:
        response = {'result': -1, 'errmsg': "网络异常，短信发送失败"}
    return response

