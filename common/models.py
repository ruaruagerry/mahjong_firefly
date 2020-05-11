# -*- coding: utf-8 -*-
import datetime
from django.db import models
import jsonfield
import config


# Create your models here.
class User(models.Model):
    # key是保留字
    password = models.CharField(max_length=255, null=True, blank=True)
    uuid = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    nick = models.CharField(max_length=255, null=True)
    login_time = models.DateTimeField(default=datetime.datetime.now())
    login_days = models.IntegerField(default=1)
    create_time = models.DateTimeField(default=datetime.datetime.now(), verbose_name=u'创建时间')
    sex = models.IntegerField(default=config.SEX_MALE)
    channel = models.CharField(max_length=64, null=True, blank=True)
    version = models.IntegerField(null=True, default=0)
    os = models.CharField(max_length=16, default=config.CLIENT_OS_ANDROID, choices=config.CLIENT_OS)
    # 客户端IP
    client_ip = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    # 牌局纪录ID
    desk_records = jsonfield.JSONField(null=True, blank=True, default=list)
    # 头像url
    portrait_path = models.CharField(max_length=256, null=True, blank=True)
    # 房卡数,被它搞残了，原来是和下面取字段的方法重名了，所以不行，但你也不给个报错，别这样好吗
    card = models.IntegerField(default=0, null=True, blank=True)
    # 是否充值过
    recharged = models.BooleanField(default=False)
    # 购买礼包的记录
    buy_info = jsonfield.JSONField(default=dict)
    # 额外添加的密码字段
    extra_username = models.CharField(max_length=255, null=True, blank=True)
    extra_password = models.CharField(max_length=255, null=True, blank=True)

    # 是否已经填过邀请人的标识，这里还是保存着吧，毕竟是房卡数据
    has_invited = models.BooleanField(default=False)

    @property
    def uin(self):
        return int(self.id)

    def calculate_login_days(self):
        if not self.login_time:

            self.login_time = datetime.datetime.now()

        if datetime.datetime.now().date() - self.login_time.date() > datetime.timedelta(days=1):
            # 没有连续登录，重新开始算
            # self.login_days = 1
            return 1
        else:
            if datetime.datetime.now().date() != self.login_time.date():
                return self.login_days + 1
            else:
                # 同一天重复登录
                return self.login_days

    def __unicode__(self):
        return u'%s-%s' % (self.id, self.nick)

    class Meta:
        verbose_name = verbose_name_plural = u'用户'


class DeskRecord(models.Model):
    uuid = models.CharField(u"牌局ID ", max_length=32)
    desk_id = models.IntegerField(u"桌子ID", db_index=True)
    game_round = models.IntegerField(u"牌局轮数")
    desk_model = jsonfield.JSONField(u"桌子属性", default=dict)
    user_data = jsonfield.JSONField(u"玩家牌局详情", default=dict)


BILL_STATE_LIST = [
        (0, u'订单生成'),
        (1, u'已发货'),
    ]


class Commodity(models.Model):
    uin = models.IntegerField(u"用户")
    channel = models.CharField(u"渠道", max_length=128)
    name = models.CharField(u'商品名称', max_length=128)
    item_type = models.IntegerField(u'商品类型', choices=config.PAY_TYPE_CHOICE)
    currency = models.CharField(u'币种', max_length=64, choices=config.CURRENCY_TYPE_CHOICES)
    amount = models.FloatField(u"价格")
    create_time = models.DateTimeField(u"充值时间", default=datetime.datetime.now())
    item_id = models.CharField(u'订单号', max_length=128)
    bill_state = models.IntegerField(u'商品类型', choices=BILL_STATE_LIST)

    def __unicode__(self):
        return u"%s" % self.name

    class Meta:
        # unique_together = (("amount", "for_bill_type"), )
        verbose_name = verbose_name_plural = u'订单'
        ordering = ['create_time']


class WXUser(models.Model):
    userid = models.CharField(max_length=32)
    native_id = models.IntegerField(default=0, db_index=True)
    access_token = models.CharField(max_length=255)
    expire_date = models.CharField(max_length=255, null=True, blank=True)
    create_time = models.DateTimeField(default=datetime.datetime.now())
    appid = models.CharField(max_length=32, null=True)

    def __unicode__(self):
        return '%s:%s' % (self.userid, self.native_id)

    class Meta:
        verbose_name = verbose_name_plural = u'微信用户'
        unique_together = (("userid", "appid"), )