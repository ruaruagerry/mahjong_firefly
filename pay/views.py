# -*- coding: utf-8 -*-
import json
import config
import datetime
import time
import hashlib
from django.http import HttpResponse
from django.shortcuts import render, redirect
from common import proto
from common.redis_fd import rds_tmp
from common.models import WXUser
from common.mahjong_pb2 import UserCreatePreBill, CreateFormalBill
from common.firefly_utils import bridge_to_other_game
from common.log import pay_logger
from common.user_pay import UserPayAction
from wzhifuSDK import UnifiedOrder_pub, JsApi_pub, Wxpay_server_pub


# MARK 到时候需要整理下保存哪些数据，现在是全部存起来
def pre_record(data, uin):
    record = json.loads(rds_tmp.hget(config.WX_BUY_RETURN_USER_REDIS_KEY, str(uin)) or 'null')
    if not record:
        record = list()

    if data in record:
        return False
    else:
        # 历史支付保存起来
        record.append(data)
        rds_tmp.hset(config.WX_BUY_RETURN_USER_REDIS_KEY, str(uin), json.dumps(record))

        # 只保存一天的数据
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        rds_tmp.expireat(config.WX_BUY_RETURN_USER_REDIS_KEY, int(time.mktime(tomorrow.timetuple())))
        return True


# 发起支付接口
def wx_pay_test(request):
    pay_logger.debug('request:%s', request.GET.get('code', None))

    get_a = JsApi_pub()
    get_a.setCode(request.GET.get('code', None))

    name = 'card_150_50'
    item_id = str(int(time.time() * 1000)) + str(int(time.clock() * 10000000))
    body = u'得闲娱乐健康产品'
    notify_url = 'mahjong.wzdexian.com/pay/only_pay/cb'
    trade_type = 'JSAPI'
    # money = store.NEW_PAY_ITEM_DIAMOND_DICT[name].get('amt')
    money = '1'
    try:
        open_id = get_a.getOpenid()
        pay_logger.debug('openid:%s', open_id)
    except:
        return

    wx_user = WXUser.objects.filter(userid=open_id).first()
    if wx_user:
        uin = wx_user.native_id
    else:
        return HttpResponse(u'未找到对应微信用户，请先绑定')

    # 生成预付单
    a = UnifiedOrder_pub()
    a.parameters['out_trade_no'] = item_id
    a.parameters['body'] = body
    a.parameters['total_fee'] = money
    a.parameters['notify_url'] = notify_url
    a.parameters['trade_type'] = trade_type
    a.parameters['openid'] = open_id

    prepay_id = a.getPrepayId()

    # 正常场景不会有这种情况
    # not_exist = pre_record(prepay_id, uin)
    if prepay_id:
        b = JsApi_pub()
        b.setPrepayId(prepay_id)

        pre_bill = json.loads(b.getParameters())

        # 获取用户信息，修改订单状态
        ntf = UserCreatePreBill()
        ntf.uin = uin
        ntf.name = name
        ntf.item_id = item_id

        bridge_to_other_game(proto.CMD_QUERY_CREATE_PRE_BILL, ntf.SerializeToString())

        return render(request, 'mj_pay.html', dict(
            appId=pre_bill['appId'],
            timeStamp=pre_bill['timeStamp'],
            nonceStr=pre_bill['nonceStr'],
            package=pre_bill['package'],
            signType=pre_bill['signType'],
            paySign=pre_bill['paySign'],
        ))
    else:
        return HttpResponse(u'下单失败，请重试')


# 回调发货
# 微信会响应多次，但是我们只需要处理一次
def wx_pay_test_cb(request):
    c = Wxpay_server_pub()
    c.saveData(request.body)

    data = c.getData()
    open_id = data['openid']
    wx_user = WXUser.objects.filter(userid=open_id).first()
    uin = None
    if wx_user:
        uin = wx_user.native_id

    if uin is None:
        return HttpResponse(u'FAILED')

    # 保存一份微信对账单
    not_exist = pre_record(data, uin)
    if not not_exist:
        return HttpResponse(u'SUCCESS')

    # 证明支付成功
    if c.checkSign() and data['result_code'] == 'SUCCESS':
        pay_logger.debug('pay success!\n data:%s', data)
        item_id = data['out_trade_no']

        user_pay = UserPayAction(data, uin)
        # 发货逻辑
        ret, error = user_pay.deliver_commodity()

        if ret == 0:
            ntf = CreateFormalBill()
            ntf.uin = user_pay.user.uin
            ntf.item_id = item_id

            bridge_to_other_game(proto.CMD_QUERY_CREATE_BILL, ntf.SerializeToString())
    else:
        pay_logger.error('pay error, data:%s', data)

    return HttpResponse(u'SUCCESS')


def wx_gzh_receive(request):
    pay_logger.debug('request:%s', request)

    signature = request.GET.get('signature', None)
    nonce = request.GET.get('nonce', None)
    timestamp = request.GET.get('timestamp', None)
    echostr = request.GET.get('echostr', None)

    sortlist = [config.WX_GZH_TOKEN, timestamp, nonce]
    sortlist.sort()
    desk_sha = hashlib.sha1("".join(map(str, sortlist))).hexdigest()

    # 直接用sha把我坑了一下午，气死了
    if signature == desk_sha:
        return HttpResponse(echostr)
    else:
        return HttpResponse(u'error')


def wx_code(request):
    from urllib import quote_plus
    pay_logger.debug('request:%s', request)
    a = JsApi_pub()
    redirect_url = quote_plus('http://mahjong.wzdexian.com/pay/only_pay')
    result_url = a.createOauthUrlForCode(redirect_url)
    pay_logger.debug('redirect_url:%s', result_url)
    return redirect(result_url)





