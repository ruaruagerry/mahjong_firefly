# -*- coding: utf-8 -*-
import functools
from collections import defaultdict
from operator import itemgetter
from celery import shared_task
import config
import proto
from common.redis_fd import rds_tmp
from common.models import DeskRecord
from common.log import logger
from common.redis_user_manager import RedisUserMgr
from common.mahjong_pb2 import LoginRsp, WeChatLoginReq
from common import error_contrast
from common.bus_func import common_user_reg_or_login, get_password
import json
from firefly_utils import celery_to_users


def release_db_conns(func):
    from common.bus_func import release_django_invalid_db_conns

    @functools.wraps(func)
    def func_wrapper(*args, **kwargs):
        release_django_invalid_db_conns()
        return func(*args, **kwargs)
    return func_wrapper


@shared_task
@release_db_conns
def parse_desk_record_to_db(round_id):
    records = rds_tmp.lrange(config.REDIS_KEY_DESK_RECORD_PREFIX + round_id, 0, -1)
    if not records:
        return

    # 解序列化并按时间排序
    records = sorted([json.loads(r) for r in records], key=itemgetter('optime'))

    if len(records) > 1:
        first, mid_records, last = records[0], records[1:-1], records[-1]

        if first['source'] != config.STATISTIC_MAHJONG_DESK_GAME_START:
            logger.error('first record is not game start, desk uuid: %s', round_id)
            return

        # 不是牌桌结束，那就是半路把桌子解散掉了
        if last['source'] != config.STATISTIC_MAHJONG_DESK_GAME_OVER:
            while True:
                # 会有多条
                if last['source'] == config.STATISTIC_MAHJONG_DESK_GAME_START:
                    # 最后一条如果是用户退桌,删除掉
                    last = mid_records.pop()
                else:
                    break

            if last['source'] != config.STATISTIC_MAHJONG_DESK_GAME_OVER:
                logger.error('last record is not game over, desk uuid: %s', round_id)
                return

        user_records = defaultdict(list)

        round_id = first['uuid']
        desk_id = first['desk_id']
        desk_model = dict(
            desk_round=first['desk_round'],
            desk_type=first['desk_type'],
            desk_seat_limit=first['desk_seat_limit'],
            desk_win_type=first['desk_win_type'],
            desk_has_laizi=first['desk_has_laizi'],
            desk_can_win_by_qidui=first['desk_can_win_by_qidui'],
            desk_bird_num=first['desk_bird_num'],
            desk_piaofen_max_num=first['desk_piaofen_max_num'],
            desk_has_shanghuo=first['desk_has_shanghuo'],
            desk_master_uin=first['desk_master_uin'],
        )

        user_data = first['user_info']
        for uin in user_data:
            user_records[int(uin)].append(round_id)

        for item in records:
            if item['source'] == config.STATISTIC_MAHJONG_DESK_GAME_OVER:
                game_round = item['game_round']
                desk_model['desk_bird_card'] = item['desk_bird_card']
                desk_model['desk_over_time'] = item['desk_over_time']
                desk_model['desk_winners'] = item['desk_winners']
                user_info = item['user_info']

                DeskRecord(
                    uuid=round_id,
                    desk_id=desk_id,
                    game_round=game_round,
                    desk_model=desk_model,
                    user_data=user_info,
                ).save()

        # 存储最多近期100条记录
        users = RedisUserMgr().get_users(user_records.keys(), load_db_user=True)
        for uin, user in users.items():
            records = list(user.desk_records or [])
            if round_id not in records:
                records.insert(0, round_id)
                if len(records) > 100:
                    records.pop()
                user.update(dict(
                    desk_records=records
                ))
    else:
        # 开局就退了的选手，到时候统计起来
        logger.debug('only one round and not over, round id: %s', round_id)

    rds_tmp.delete(config.REDIS_KEY_DESK_RECORD_PREFIX + round_id)


@shared_task
@release_db_conns
def wx_login(request):
    from common.models import WXUser, User
    from django.db.utils import IntegrityError
    from common.bus_func import replace_forbidden_content, get_user_info

    req = WeChatLoginReq()
    req.ParseFromString(request['body'])
    uin = request['uin']
    rsp = LoginRsp()

    appid = str(config.WX_LOGIN_CHANNEL_TO_APPID.get(req.channel, config.WX_LOGIN_APPID))

    wx_user = WXUser.objects.filter(
        userid=req.openid,
        appid=appid,
    ).first()
    # logger.debug('wx_user find')
    wx_info = dict()
    if not wx_user:
        wx_info = get_user_info(req.openid, req.token)
        # logger.debug('wx_info:%s', wx_info)
        if not wx_info:
            rsp.ret = error_contrast.ERROR_WX_LOGIN_FAILED
            return rsp.SerializeToString()

        # logger.debug('wx_user create')
        wx_user = WXUser(
            userid=req.openid,
            access_token=req.token,
            expire_date=req.expire_date,
            appid=appid,
        )
        # logger.debug('wx_user create success')

        if not uin:
            # logger.debug('native_user create, head:%s', wx_info.get('headimgurl'))
            native_user = User(
                password=get_password(),
                nick=replace_forbidden_content(wx_info.get('nickname')[:6]),
                sex=config.SEX_MALE if wx_info.get('sex') == 1 else config.SEX_FEMALE,
                channel=req.channel or None,
                version=req.version,
                os=req.os or 'android',
                portrait_path=wx_info.get('headimgurl'),
            )
            # logger.debug('native_user create success')
            native_user.save()
            # logger.debug('native_user save success')
            wx_user.native_id = native_user.id

        else:
            if WXUser.objects.filter(native_id=uin):
                # id如果已经和其他绑定过，就返回报错了，否则加金币会重复，只要不停的换账号就行了
                rsp.ret = error_contrast.ERROR_WX_BIND_ALREADY
                return rsp.SerializeToString()

        try:
            wx_user.save()
        except IntegrityError, e:
            logger.error(e.message, exc_info=True)
            rsp.ret = error_contrast.ERROR_WX_LOGIN_FAILED
            return rsp.SerializeToString()

        # logger.debug('wx_user save success')
        user = RedisUserMgr().get_user(wx_user.native_id)

    else:
        if wx_user.access_token != req.token:
            # logger.debug('access_token not the same')
            wx_info = get_user_info(req.openid, req.token)
            # logger.debug('not wx_info:%s', wx_info)
            if not wx_info:
                rsp.ret = error_contrast.ERROR_WX_LOGIN_FAILED
                return rsp.SerializeToString()
            else:
                # 更新token
                wx_user.access_token = req.token
                wx_user.save()

        if uin and uin != wx_user.native_id:
            rsp.ret = error_contrast.ERROR_USER_BIND_NOT_MATCH
            return rsp.SerializeToString()

        user = RedisUserMgr().get_user(wx_user.native_id)
        if wx_info.has_key('headimgurl') and user.portrait_path != wx_info.get('headimgurl'):
            user.update(dict(
                channel=req.channel or None,
                version=req.version,
                os=req.os or 'android',
                portrait_path=wx_info.get('headimgurl'),
            ))
        else:
            user.update(dict(
                channel=req.channel or None,
                version=req.version,
                os=req.os or 'android',
            ))
        # logger.debug('start common_user_reg_or_login')

    rsp = common_user_reg_or_login(request, user)
    wx_login_rsp = dict(connid=request['connid'], data=rsp)
    celery_to_users(user.uin, proto.CMD_REG, wx_login_rsp)


@shared_task
def celery_test(name):
    for i in range(1, 10):
        logger.debug('hello:%s, %s', i, name)


# def my_test():
#     from common.bus_func import celery_delay
#
#     celery_delay(celery_test, 'my_test')
