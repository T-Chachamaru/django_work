import uuid
import hashlib

from qcloud_cos import CosConfig, CosS3Client
from django_work.settings import TENCENT_COS_ID, TENCENT_COS_KEY

def create_bucket(bucket, region='ap-chengdu'):
    secret_id = TENCENT_COS_ID
    secret_key = TENCENT_COS_KEY

    config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
    client = CosS3Client(config)

    response = client.create_bucket(
        Bucket=bucket,
        ACL='public-read'
    )

def upload_image(bucket, image_object, key, region='ap-chengdu'):
    secret_id = TENCENT_COS_ID
    secret_key = TENCENT_COS_KEY

    config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
    client = CosS3Client(config)

    response = client.upload_file_from_buffer(
        Bucket=bucket,
        Body=image_object,
        Key=key,
    )

    return f"https://{bucket}.cos.{region}.myqcloud.com/{key}"