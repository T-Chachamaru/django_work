from typing import List, Dict, Any, IO
from django.conf import settings
from qcloud_cos import CosConfig, CosS3Client, CosServiceError
from sts.sts import Sts

class CosManager:
    """
    腾讯云对象存储COS操作的管理器。

    通过实例化此类来获取一个COS客户端，然后调用其方法来执行
    创建存储桶、上传/删除文件、获取临时密钥等操作。

    使用示例:
        cos_client = CosManager(region='ap-chengdu')

        # 上传文件
        url = cos_client.upload_file('my-bucket', file_object, 'path/to/file.jpg')

        # 删除文件
        cos_client.delete_file('my-bucket', 'path/to/file.jpg')

        # 获取临时密钥
        credentials = cos_client.get_credential('my-bucket')
    """

    def __init__(self, region: str = 'ap-chengdu'):
        """
        初始化COS管理器，创建客户端。
        :param region: 存储桶所在的地域。
        """
        # 从Django settings中获取密钥
        secret_id = settings.TENCENT_COS_ID
        secret_key = settings.TENCENT_COS_KEY

        # 创建CosConfig和CosS3Client，后续所有方法共享此客户端
        config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
        self.client = CosS3Client(config)
        self.region = region

    def create_bucket(self, bucket: str, acl: str = 'public-read'):
        """
        创建一个新的存储桶，并配置公共读权限和跨域规则。
        :param bucket: 存储桶名称，全局唯一。
        :param acl: 存储桶的访问控制列表，默认为'public-read'。
        """
        self.client.create_bucket(Bucket=bucket, ACL=acl)
        cors_config = {
            'CORSRule': [{
                'AllowedOrigin': '*',
                'AllowedMethod': ['GET', 'POST', 'PUT', 'DELETE', 'HEAD'],
                'AllowedHeader': "*",
                'ExposeHeader': "*",
                'MaxAgeSeconds': 500
            }]
        }
        self.client.put_bucket_cors(Bucket=bucket, CORSConfiguration=cors_config)

    def upload_file(self, bucket: str, file_object: IO, key: str) -> str:
        """
        从文件流（内存）上传文件到指定的存储桶。
        :param bucket: 存储桶名称。
        :param file_object: 文件对象（例如 request.FILES.get('file')）。
        :param key: 文件在存储桶中的唯一路径名 (e.g., 'images/avatar.jpg')。
        :return: 上传成功后文件的完整访问URL。
        """
        self.client.upload_file_from_buffer(
            Bucket=bucket,
            Body=file_object,
            Key=key
        )
        return f"https://{bucket}.cos.{self.region}.myqcloud.com/{key}"

    def delete_file(self, bucket: str, key: str):
        """
        从存储桶中删除单个文件。
        :param bucket: 存储桶名称。
        :param key: 要删除的文件在存储桶中的路径。
        """
        self.client.delete_object(Bucket=bucket, Key=key)

    def delete_file_list(self, bucket: str, key_list: List[Dict[str, str]]):
        """
        从存储桶中批量删除文件。
        :param bucket: 存储桶名称。
        :param key_list: 包含文件Key的字典列表，格式如: [{'Key': 'file1.jpg'}, {'Key': 'file2.txt'}]。
        """
        objects = {
            "Quiet": "true",
            "Object": key_list
        }
        self.client.delete_objects(Bucket=bucket, Delete=objects)

    def get_credential(self, bucket: str) -> Dict[str, Any]:
        """
        生成用于前端直传的临时密钥（凭证）。
        使用STS服务生成限时、限权的临时凭证，保障后端永久密钥的安全。
        :param bucket: 存储桶名称。
        :return: 包含临时密钥、会话令牌和过期时间的字典。
        """
        config = {
            'duration_seconds': 1800,
            'secret_id': settings.TENCENT_COS_ID,
            'secret_key': settings.TENCENT_COS_KEY,
            'bucket': bucket,
            'region': self.region,
            'allow_prefix': '*',
            'allow_actions': [
                'name/cos:PutObject',
                'name/cos:PostObject',
            ],
        }
        sts = Sts(config)
        return sts.get_credential()

    def check_file(self, bucket: str, key: str) -> Dict[str, Any]:
        """
        检查文件是否存在并获取其元数据。
        使用HEAD请求，比GET请求更高效，因为它只获取头部信息而不传输文件内容。
        :param bucket: 存储桶名称。
        :param key: 文件的路径。
        :return: 文件的元数据字典。如果文件不存在，会抛出CosServiceError异常。
        """
        return self.client.head_object(Bucket=bucket, Key=key)

    def delete_bucket(self, bucket: str):
        """
        删除一个存储桶。注意：删除前必须清空存储桶内的所有文件和未完成的分块上传。
        这是一个危险操作，请谨慎使用！
        :param bucket: 要删除的存储桶名称。
        """
        try:
            while True:
                part_objects = self.client.list_objects(bucket)
                contents = part_objects.get('Contents')
                if not contents:
                    break
                objects_to_delete = {"Object": [{'Key': item["Key"]} for item in contents]}
                self.client.delete_objects(bucket, Delete=objects_to_delete)
                if part_objects.get('IsTruncated') == 'false':
                    break

            while True:
                part_uploads = self.client.list_multipart_uploads(bucket)
                uploads = part_uploads.get('Upload')
                if not uploads:
                    break
                for item in uploads:
                    self.client.abort_multipart_upload(
                        Bucket=bucket, Key=item['Key'], UploadId=item['UploadId']
                    )
                if part_uploads.get('IsTruncated') == 'false':
                    break

            self.client.delete_bucket(Bucket=bucket)

        except CosServiceError as e:
            print(f"删除存储桶 {bucket} 失败: {e}")