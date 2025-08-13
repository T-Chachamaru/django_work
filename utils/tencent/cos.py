from django.conf import settings
from qcloud_cos import CosConfig, CosS3Client
from sts.sts import Sts

from django_work.settings import TENCENT_COS_ID, TENCENT_COS_KEY

def create_bucket(bucket, region='ap-chengdu'):
    """
    创建一个新的腾讯云COS存储桶，并设置公共读权限和跨域规则。

    :param bucket: 存储桶名称，全局唯一。
    :param region: 存储桶所在的地域，默认为'ap-chengdu'。
    """
    config = CosConfig(Region=region, SecretId=TENCENT_COS_ID, SecretKey=TENCENT_COS_KEY)
    client = CosS3Client(config)
    client.create_bucket(
        Bucket=bucket,
        ACL='public-read'
    )
    cors_config = {
        'CORSRule': [
            {
                'AllowedOrigin': '*',
                'AllowedMethod': ['GET', 'POST', 'PUT', 'DELETE', 'HEAD'],
                'AllowedHeader': "*",
                'ExposeHeader': "*",
                'MaxAgeSeconds': 500
            }
        ]
    }
    client.put_bucket_cors(
        Bucket=bucket,
        CORSConfiguration=cors_config
    )

def upload_file(bucket, file_object, key, region='ap-chengdu'):
    """
    将文件对象上传到指定的存储桶。

    :param bucket: 存储桶名称。
    :param file_object: 文件对象（例如，通过request.FILES获取的对象）。
    :param key: 文件在存储桶中的唯一路径和名称（例如 'images/avatar.jpg'）。
    :param region: 存储桶所在的地域。
    :return: 上传成功后文件的完整访问URL。
    """
    config = CosConfig(Region=region, SecretId=TENCENT_COS_ID, SecretKey=TENCENT_COS_KEY)
    client = CosS3Client(config)
    client.upload_file_from_buffer(
        Bucket=bucket,
        Body=file_object,
        Key=key,
    )
    return f"https://{bucket}.cos.{region}.myqcloud.com/{key}"

def delete_file(bucket, key, region='ap-chengdu'):
    """
    从存储桶中删除单个文件。

    :param bucket: 存储桶名称。
    :param key: 要删除的文件在存储桶中的路径。
    :param region: 存储桶所在的地域。
    """
    config = CosConfig(Region=region, SecretId=TENCENT_COS_ID, SecretKey=TENCENT_COS_KEY)
    client = CosS3Client(config)
    client.delete_object(
        Bucket=bucket,
        Key=key,
    )

def delete_file_list(bucket, key_list, region='ap-chengdu'):
    """
    从存储桶中批量删除文件。

    :param bucket: 存储桶名称。
    :param key_list: 包含要删除文件信息的字典列表，格式如: [{'Key': 'file1.jpg'}, {'Key': 'file2.txt'}]。
    :param region: 存储桶所在的地域。
    """
    config = CosConfig(Region=region, SecretId=TENCENT_COS_ID, SecretKey=TENCENT_COS_KEY)
    client = CosS3Client(config)
    objects = {
        "Quiet": "true",
        "Object": key_list
    }
    client.delete_objects(
        Bucket=bucket,
        Delete=objects,
    )

def credential(bucket, region='ap-chengdu'):
    """
    生成用于前端直传的腾讯云COS临时密钥。

    使用STS（Security Token Service）服务生成一个有时间限制、有权限范围的临时凭证，
    让前端可以直接与COS交互，而无需将永久密钥暴露在客户端，更加安全。

    :param bucket: 存储桶名称。
    :param region: 存储桶所在的地域。
    :return: 一个包含临时密钥、会话令牌和过期时间的字典。
    """
    config = {
        'duration_seconds': 1800,
        'secret_id': settings.TENCENT_COS_ID,
        'secret_key': settings.TENCENT_COS_KEY,
        'bucket': bucket,
        'region': region,
        'allow_prefix': '*',
        'allow_actions': [
            'name/cos:PutObject',
            'name/cos:PostObject',
        ],
    }
    sts = Sts(config)
    result_dict = sts.get_credential()
    return result_dict
