import json
from datetime import datetime
from urllib.parse import quote_plus

from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
from base64 import b64encode, b64decode


class AliPaySDK(object):
    """
    支付宝支付 SDK 工具类。
    封装了电脑网站支付的请求生成和支付宝异步通知的验签功能。
    """

    def __init__(self, appid, app_notify_url, app_private_key_path, alipay_public_key_path, return_url, debug=False):
        """
        初始化支付宝配置。

        :param appid: 支付宝分配的应用ID
        :param app_notify_url: 支付宝服务器主动通知商户服务器里指定的页面http/https路径(异步通知)
        :param app_private_key_path: 商户应用私钥文件路径
        :param alipay_public_key_path: 支付宝公钥文件路径
        :param return_url: 支付成功后同步跳转的页面http/https路径
        :param debug: 是否是沙箱模式，默认为False (生产环境)
        """
        self.appid = appid
        self.app_notify_url = app_notify_url
        self.return_url = return_url

        try:
            with open(app_private_key_path, 'rb') as f:
                self.app_private_key = RSA.import_key(f.read())
        except Exception as e:
            raise IOError(f"商户私钥文件加载失败，请检查路径：{app_private_key_path}。错误: {e}")

        try:
            with open(alipay_public_key_path, 'rb') as f:
                self.alipay_public_key = RSA.import_key(f.read())
        except Exception as e:
            raise IOError(f"支付宝公钥文件加载失败，请检查路径：{alipay_public_key_path}。错误: {e}")

        if debug:
            self.gateway_url = "https://openapi-sandbox.alipay.com/gateway.do"
        else:
            self.gateway_url = "https://openapi.alipay.com/gateway.do"

    def direct_pay(self, subject, out_trade_no, total_amount):
        """
        生成电脑网站支付(Page Pay)的请求URL。

        :param subject: 订单标题
        :param out_trade_no: 商户订单号，必须唯一
        :param total_amount: 订单总金额，单位为元
        :return: 拼接了所有参数和签名的完整支付宝网关URL
        """
        biz_content = {
            "subject": subject,
            "out_trade_no": out_trade_no,
            "total_amount": total_amount,
            "product_code": "FAST_INSTANT_TRADE_PAY",
        }

        public_params = {
            "app_id": self.appid,
            "method": "alipay.trade.page.pay",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "notify_url": self.app_notify_url,
            "return_url": self.return_url,
            "biz_content": json.dumps(biz_content, separators=(',', ':'))
        }

        signed_url = self._sign_and_build_url(public_params)
        return signed_url

    def _ordered_data(self, data):
        """
        对字典数据进行排序，并处理复杂类型的值。
        这是生成待签名字符串前的必要步骤。
        """
        complex_keys = [key for key, value in data.items() if isinstance(value, dict)]
        for key in complex_keys:
            data[key] = json.dumps(data[key], separators=(',', ':'))

        return sorted(data.items())

    def _sign_and_build_url(self, data):
        """
        内部方法：对参数进行签名，并拼接成最终的URL。
        """
        ordered_items = self._ordered_data(data)
        pre_sign_string = "&".join(f"{k}={v}" for k, v in ordered_items)
        signer = PKCS1_v1_5.new(self.app_private_key)
        signature = signer.sign(SHA256.new(pre_sign_string.encode("utf-8")))
        sign = b64encode(signature).decode("utf-8")
        quoted_items = [f"{k}={quote_plus(str(v))}" for k, v in ordered_items]
        signed_query_string = "&".join(quoted_items) + f"&sign={quote_plus(sign)}"

        return f"{self.gateway_url}?{signed_query_string}"

    def verify(self, data, signature):
        """
        验证支付宝异步通知的签名是否正确。

        :param data: 从支付宝POST请求中获取的、除`sign`和`sign_type`外的所有参数的字典
        :param signature: 从支付宝POST请求中获取的`sign`参数的值
        :return: 布尔值，True表示验签成功，False表示失败
        """
        if "sign" in data:
            data.pop("sign")

        ordered_items = self._ordered_data(data)
        pre_verify_string = "&".join(f"{k}={v}" for k, v in ordered_items)

        try:
            verifier = PKCS1_v1_5.new(self.alipay_public_key)
            digest = SHA256.new(pre_verify_string.encode("utf-8"))
            return verifier.verify(digest, b64decode(signature))
        except (ValueError, TypeError, IndexError):
            return False

