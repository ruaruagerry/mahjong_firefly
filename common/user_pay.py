# -*- coding: utf-8 -*-
"""
商城内用货币购买商品的发货逻辑
"""

import config
import datetime
import time
import json
from redis_user_manager import RedisUserMgr
from common.redis_fd import rds
from common.log import pay_logger
from common.bus_func import user_room_card_notify


# 具体谁他妈的要买什么，之前谁写的，封装那么多层，像你妈一样，真是鸡巴恶心，显得自己很吊？
# 忍不住素质三连，放在这里，以儆效尤，也提醒自己时刻自勉
class UserPayAction(object):
    uin = None
    user = None
    commodity = None
    data = None
    name = None

    def __init__(self, data, uin):
        # data、uin有必要保存一份
        self.data = data
        self.uin = int(uin)
        # self.name = data[]
        # self.commodity = config.COMMODITY_ITEM_DICT.get(name, None)
        self.commodity = config.COMMODITY_ITEM_DICT['card_150_50']
        self.user = RedisUserMgr().get_user(self.uin)

    def check_valid(self):
        # 加上一个redis的判断
        # record = json.loads(rds.hget(config.SUCCESS_BUY_USER_REDIS_KEY, str(self.user.uin)) or 'null')
        # for it in record:
        #     if self.bill_id == it['bill_id']:
        #         return -2, u'bill has exist'

        # if self.data['cash_fee'] != self.data['total_fee'] != self.bill_amt:
        #     return -4, u'money difference, bill_amt:%s, data:%s' % (self.data, self.bill_amt)

        if not self.user or not self.user.validate():
            pay_logger.error('user %s not exist. data: \n%s', self.uin, self.data)
            return -3, u'user %s not exists!' % self.uin

        if not self.commodity:
            # 没有找到跟这个item_id匹配的发货动作
            pay_logger.error('name %s not exist. data: \n%s', self.name, self.data)
            return -1, u'item_id is not given!'

        return 0, ""

    def redis_record(self):
        """
        保存购买记录
        :return:
        """
        record = json.loads(rds.hget(config.SUCCESS_BUY_USER_REDIS_KEY, str(self.user.uin)) or 'null')
        if not record:
            record = list()

        # 历史支付保存起来
        record.append(dict(
            bill_id=self.data['out_trade_no'],
            when=int(time.time()),
            bill_type=self.commodity['type']
        ))
        rds.hset(config.SUCCESS_BUY_USER_REDIS_KEY, str(self.user.uin), json.dumps(record))

        # 只保存一天的数据
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        rds.expireat(config.SUCCESS_BUY_USER_REDIS_KEY, int(time.mktime(tomorrow.timetuple())))

    def update_user_buy_info(self):
        """
        更新存在user的buy_info信息
        :return:
        """
        buy_info = {}

        buy_info.setdefault("buy_card_total_times", 0)
        buy_info["buy_card_total_times"] += 1

        buy_info.setdefault("buy_card_total_cost", 0)
        buy_info["buy_card_total_cost"] += self.commodity['amt']

        return buy_info

    def deliver(self):
        buy_info = self.update_user_buy_info()
        add_card = self.commodity['count']
        self.user.update(dict(
            recharged=True,
            card__=add_card,
            buy_info=buy_info
        ))

        # user_room_card_notify(self.user)

        return add_card

    def deliver_commodity(self):
        ret, error = 0, ""

        try:
            # 先检查是否需要发货,参数是否正确
            ret, error = self.check_valid()
            if ret != 0:
                return

            # 发货
            self.deliver()
            self.redis_record()
        except Exception as e:
            pay_logger.error(e, exc_info=True)
        finally:
            return ret, error