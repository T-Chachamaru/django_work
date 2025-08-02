from django.db import models


class UserInfo(models.Model):
    """用户表"""
    username = models.CharField(verbose_name='用户名', max_length=32, db_index=True)
    password = models.CharField(verbose_name='密码', max_length=128)
    email = models.EmailField(verbose_name='邮箱', max_length=32)
    mobile_phone = models.CharField(verbose_name='手机号', max_length=32)

    def __str__(self):
        return self.username


class PricePolicy(models.Model):
    """价格策略（套餐）表"""
    CATEGORY_CHOICES = (
        (1, '免费版'),
        (2, '收费版'),
        (3, '其他'),
    )
    category = models.SmallIntegerField(verbose_name='收费类型', default=1, choices=CATEGORY_CHOICES)
    title = models.CharField(verbose_name='标题', max_length=32)
    price = models.PositiveIntegerField(verbose_name='价格')

    project_num = models.PositiveIntegerField(verbose_name='项目数')
    project_members = models.PositiveIntegerField(verbose_name='项目成员数')
    project_space = models.PositiveIntegerField(verbose_name='单项目空间(GB)')
    per_file_size = models.PositiveIntegerField(verbose_name='单文件大小(MB)')

    create_datetime = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)

    def __str__(self):
        return self.title


class Transaction(models.Model):
    """交易记录表"""
    STATUS_CHOICES = (
        (1, '未支付'),
        (2, '已支付'),
    )
    status = models.SmallIntegerField(verbose_name='状态', default=1, choices=STATUS_CHOICES)
    order = models.CharField(verbose_name='订单号', max_length=64, unique=True)

    user = models.ForeignKey(verbose_name='用户', to='UserInfo', on_delete=models.CASCADE)
    price_policy = models.ForeignKey(verbose_name='价格策略', to='PricePolicy', on_delete=models.CASCADE)

    count = models.IntegerField(verbose_name='数量（年）', help_text='0表示无限期')
    price = models.IntegerField(verbose_name='实际支付价格')

    start_datetime = models.DateTimeField(verbose_name='开始时间', null=True, blank=True)
    end_datetime = models.DateTimeField(verbose_name='结束时间', null=True, blank=True)

    create_datetime = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)


class Project(models.Model):
    """项目表"""
    COLOR_CHOICES = (
        (1, '#56b8eb'), (2, '#f28033'), (3, '#ebc656'),
        (4, '#a2d148'), (5, '#20BFA4'), (6, '#7461c2'),
        (7, '#20bfa3'),
    )
    name = models.CharField(verbose_name='项目名', max_length=32)
    color = models.SmallIntegerField(verbose_name='颜色', choices=COLOR_CHOICES, default=1)
    desc = models.CharField(verbose_name='项目描述', max_length=255, null=True, blank=True)

    use_space = models.BigIntegerField(verbose_name='项目已使用空间(字节)', default=0)
    star = models.BooleanField(verbose_name='星标', default=False)

    join_count = models.SmallIntegerField(verbose_name='参与人数', default=1)
    creator = models.ForeignKey(verbose_name='创建者', to='UserInfo', on_delete=models.CASCADE)
    create_datetime = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)

    def __str__(self):
        return self.name


class ProjectUser(models.Model):
    """项目参与者关系表"""
    user = models.ForeignKey(verbose_name='用户', to='UserInfo', on_delete=models.CASCADE)
    project = models.ForeignKey(verbose_name='项目', to='Project', on_delete=models.CASCADE)
    star = models.BooleanField(verbose_name='星标', default=False)
    create_datetime = models.DateTimeField(verbose_name='加入时间', auto_now_add=True)

    class Meta:
        # 同一个用户只能参与同一个项目一次
        unique_together = ['user', 'project']

    def __str__(self):
        return f"{self.user.username} - {self.project.name}"
