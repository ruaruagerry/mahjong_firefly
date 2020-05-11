# -*- coding: utf-8 -*-

"""
author: GerryLuo
bus_func.py: 公共功能模块（谁都可以用，所以就叫bus了）
"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mjango.settings")
# 日志模块这里初始化，方便别的地方引用，这里一定要写上，不然gateway打不出日志
from django.conf import settings
settings.BASE_DIR

import config
import requests
import json
from django.http import HttpResponse
import hashlib
import time
import datetime
from common import proto
import functools
from log import logger
import error_contrast
from common.mahjong_pb2 import UserRoomCardChange
from common.firefly_utils import write_to_users, bridge_to_users
from common.firefly_map import JsonRegisterObj
import uuid
from common.redis_user_manager import RedisUserMgr
from common.firefly_utils import bridge_to_users
from common.forbidden_words_mgr import ForbiddenWordsMgr


def get_password():
    password = "passwd_%s" % uuid.uuid4()
    return password


# 判断是否是审核的状态
def is_app_crime(channel, version):
    if version in config.CRIME_APP_DICT.get(channel, {}):
        return True
    else:
        return False


def safe_str(src):
    """
    转成str
    """
    if isinstance(src, unicode):
        return src.encode('utf8')
    else:
        return str(src)


def make_sign(*args):
    """
    消息校验签名
    :param args:
    :return:
    """
    src = ''.join([safe_str(it) for it in args])
    sign = hashlib.md5(src).hexdigest()
    return sign


def rest_rsp_json(*args, **kwargs):
    ret_dict = json.dumps(
        dict(*args, **kwargs),
        ensure_ascii=False,
    )

    return HttpResponse(
        ret_dict,
        content_type='application/json'
    )


def common_user_reg_or_login(request, user):
    """
    共同的登录处理
    """
    from common.mahjong_pb2 import LoginRsp
    from common.redis_fd import rds

    update_info = dict()
    # 保存用户上线状态
    update_info['status'] = config.LOGIN_USER_STATUS_ONLINE
    update_info['client_ip'] = request['ip']
    update_info['login_time'] = datetime.datetime.now()
    update_info['login_days'] = user.calculate_login_days()

    old_desk = 0
    if user.desk_id > 0:
        old_desk = load_desk(user.desk_id)

    if old_desk:
        old_deskid = old_desk.id
    else:
        update_info['desk_id'] = 0
        old_deskid = 0

    user.update(update_info)

    rsp = LoginRsp()
    rsp.uin = user.uin
    rsp.password = user.password
    rsp.nick = user.nick
    rsp.sex = user.sex
    rsp.old_deskid = old_deskid
    rsp.portrait = user.portrait_path if user.portrait_path else ''
    rsp.wx_public_id = config.WX_PUBLIC_ID
    rsp.wx_agent_id = config.WX_AGENT_ID
    rsp.ip = user.client_ip
    rsp.room_card = user.card
    rsp.wy_yunxin_token = config.SDK_YUNXIN_TOKEN

    # 获取系统公告
    content_all = rds.get(config.BILLBOARD_REDIS_KEY) or ''
    content = ''
    if content_all:
        content_id, content = content_all.split('|')

    rsp.hall_billband = content.decode('utf8')

    rsp.ret = 0

    # 直接return就可以
    # logger.debug('rsp:%s', rsp)
    return rsp.SerializeToString()


def alloc_desk_id():
    """
    内部使用
    分配桌子ID, 分配完后进桌
    :param user
    :param reg
    :return:
    """
    from common.desk_mgr_controller import MjDeskMgrController

    desk_id = MjDeskMgrController().alloc_desk_id()

    return desk_id


def desk_required(lock_desk=False, restore_later=False, d_cls=None):
    """
    指定了d_cls 就会忽略 accepted_room_type
    :param lock_desk:
    :param restore_later:
    :param d_cls:
    :return:
    """

    def outer_wrapper(func):
        @functools.wraps(func)
        def inner_wrapper(request, *args, **kwargs):
            # 这里又取了一次
            if d_cls is None:
                desk = load_desk(request['user'].desk_id,
                                 with_lock=lock_desk)
            else:
                desk = d_cls.load(request['user'].desk_id, lock_desk)

            if not desk:
                logger.error('not has desk, request:%s', request)
                return

            request['desk'] = desk
            # 是否需要手动restore group TODO 废除掉restore later
            request['desk'].restore_later = restore_later

            try:
                return func(request, *args, **kwargs)
            finally:
                # 这里unlock的桌子信息是之前的
                request['desk'].unlock()

        return inner_wrapper

    return outer_wrapper


def right_turn_required(func):
    @functools.wraps(func)
    def func_wrapper(desk, uin, *args, **kwargs):
        if desk.current_uin != uin:
            # logger.error('not right turn. current_uin:%s, request uin:%s', desk.current_uin, uin)
            return error_contrast.ERROR_NOT_RIGHT_TURN

        return func(desk, uin, *args, **kwargs)

    return func_wrapper


def one_round_over_checker(func):
    @functools.wraps(func)
    def func_wrapper(desk, *args, **kwargs):
        result = func(desk, *args, **kwargs)
        desk.check_one_round_over()
        return result

    return func_wrapper


def load_desk(desk_id, r_obj=None, with_lock=False):
    """
    加载desk
    :param desk_id:
    :param r_obj:
    :param with_lock:
    :return:
    """
    from common.base_desk import BaseDesk
    from common.redis_fd import rds_tmp
    desk = BaseDesk.load(r_obj or rds_tmp, desk_id, with_lock=with_lock)
    return desk


def count_costs(threshold=None):
    """
    计算函数执行时间
    :param threshold: 单位毫秒,超过这个设定时间才打印Log，不设定时间始终打印log
    :return:
    """

    def function(func):
        @functools.wraps(func)
        def func_wrapper(self, *args, **kwargs):
            try:
                begin = time.time()
                return func(self, *args, **kwargs)
            finally:
                delta = (time.time() - begin) * 1000
                if threshold is None or delta > threshold:
                    if hasattr(self, func.__name__):
                        logger.error("***Process %s.%s costs %s, threshold value is %s",
                                     self.__class__.__name__, func.__name__, delta, threshold)
                    else:
                        logger.error("***Process %s costs %s, threshold value is %s",
                                     func.__name__, delta, threshold)

        return func_wrapper

    return function


def fill_user_enter_desk_info(desk, player, to_player):
    """
    填充玩家进桌消息
    :param desk:
    :param player: 进桌的玩家
    :param to_player: 消息要发给哪个玩家
    :return:
    """
    from common.mahjong_pb2 import EvtDeskUserEnter

    event = EvtDeskUserEnter()
    # 进桌人
    event.op_uin = player.user.uin
    event.deskid = desk.id
    event.max_round = desk.desk_round
    event.dealer_seatid = desk.dealer_seatid
    event.status = desk.status
    # event.player_op_past_time = desk.player_op_past_time
    event.next_uin = desk.current_uin
    event.desk_remain_round = desk.desk_remain_round
    event.seat_num = desk.seat_limit
    if 'count_down' in desk.timeout_info:
        event.remain_time = desk.timeout_info['count_down'] - int(time.time())
    event.apply_uin = desk.apply_uin
    event.win_type = desk.win_type
    event.extra_type.hongzhong = desk.has_laizi
    event.extra_type.qidui = desk.can_win_by_qidui
    event.extra_type.zhuaniao = desk.bird_num
    event.extra_type.piaofen = desk.piaofen_max_num
    event.extra_type.shanghuo = desk.has_shanghuo
    event.type = desk.type
    if 'game_start' in desk.timeout_info and desk.type == config.DESK_TYPE_MJ_WZ:
        event.pre_remain_time = desk.time_info['game_start'] - int(time.time())
    else:
        event.pre_remain_time = -1

    # 填充play_info,发给谁就是谁的的play_info
    # desk.adapt_play_info(event, to_player)

    # 坐着的玩家信息列表
    sit_players_info_dict = desk.get_sit_players_info_dict()
    desk.adapt_game_user_info_list(event, sit_players_info_dict.values())
    # 这些是战斗信息
    for in_player in desk.player_group.active_players:
        if in_player.uin == to_player.uin:
            event.cards.extend(in_player.card_group.num_list)
            event.share_cards_len = desk.share_cards_len
            event.game_round = desk.one_game_round_index
            event.my_option.op_chi = in_player.op_chi
            event.my_option.op_peng = in_player.op_peng
            event.my_option.op_gang = in_player.op_gang
            event.my_option.op_hu = in_player.op_hu
            event.my_option.need_wait = in_player.need_wait
            if in_player.op_type:
                event.my_option.chi_cards.extend(in_player.op_type[0])
            if not desk.send_card_uin:
                event.recv_card_uin = desk.recv_card_uin

        evt_user_info = event.in_users.add()
        evt_user_info.uin = in_player.uin
        evt_user_info.card_len = in_player.card_len
        evt_user_info.out_cards.extend(in_player.card_group.num_out_card_list)
        evt_user_info.discard.extend(in_player.card_group.num_discard_list)
        evt_user_info.seatid = in_player.seatid
        evt_user_info.status = in_player.status
        evt_user_info.op_list.extend(in_player.op_list)
        evt_user_info.chips = in_player.chips

    return event


def celery_delay(func, *args, **kwargs):
    try:
        return func.delay(*args, **kwargs)
    except Exception as e:
        logger.critical('error, e:%s, func:%s', e, func, exc_info=True)
        return e


def user_room_card_notify(user, user_in_web=False, reason=0):
    rsp = UserRoomCardChange()
    rsp.room_card = user.card
    rsp.change_reason = reason

    logger.debug('card change rsp:%s', rsp)
    rsp = rsp.SerializeToString()
    if user_in_web:
        bridge_to_users(user.uin, proto.CMD_EVENT_USER_CARD_CHANGE, rsp)
    else:
        write_to_users(user.uin, proto.CMD_EVENT_USER_CARD_CHANGE, rsp)


def module_register():
    from common.card import Card
    from common.card_group import CardGroup
    from common.player import Player
    from common.player_group import PlayerGroup
    from common.mj_desk import MjDesk
    from common.broadcast import BroadcastInfo
    JsonRegisterObj().register_module([MjDesk, PlayerGroup, Player, Card, CardGroup, BroadcastInfo])


def signal_register():
    from common import signals_desk_records
    logger.debug('signal handler register')
    signals_desk_records.register_signal_handlers()


def release_django_invalid_db_conns():
    from django.db import connections
    for conn in connections.all():
        conn.close_if_unusable_or_obsolete()


def pre_game_function(func):
    @functools.wraps(func)
    def func_wrapper(request, *args, **kwargs):
        user = RedisUserMgr().get_user(request.get('uin', None))
        request = dict(
            uin=user.uin,
            body=request.get('body', None),
            user=user,
        )
        return func(request, *args, **kwargs)
    return func_wrapper


def pre_game_function_with_desk(func):
    @functools.wraps(func)
    def func_wrapper(request, *args, **kwargs):
        user = RedisUserMgr().get_user(request.get('uin', None))
        request = dict(
            uin=user.uin,
            body=request.get('body', None),
            user=user,
            desk=load_desk(user.desk_id),
        )
        return func(request, *args, **kwargs)
    return func_wrapper


def load_desks(desk_ids='*'):
    """
    默认load所有桌子，部分桌子提供一个桌子id列表
    :param desk_ids:
    :return:
    """
    from common.mj_desk import MjDesk
    from common.redis_fd import rds_tmp
    from common.mj_json_encode import json_decoder

    if desk_ids == '*':
        desk_keys = rds_tmp.keys(MjDesk.get_desk_redis_key(desk_ids))
    else:
        desk_keys = [MjDesk.get_desk_redis_key(did) for did in desk_ids]

    if desk_keys:
        for raw_data in rds_tmp.mget(desk_keys):
            if not raw_data:
                continue

            desk = json_decoder(raw_data)
            if not desk:
                continue

            yield desk


def modify_card(user, add_room_card, result_limit=None, add_remark=None, user_in_web=False):
    if result_limit is not None:
        assert (user.card + add_room_card) <= result_limit, u'result out of limit'

    if user.card + add_room_card < 0:
        return

    user.update(dict(card__=add_room_card))
    user_room_card_notify(user, user_in_web=user_in_web)


def get_user_info(openid, access_token):
    url = 'https://api.weixin.qq.com/sns/userinfo'

    params = dict(
        openid=openid,
        access_token=access_token,
    )

    rsp = requests.get(url, params=params, timeout=config.SDK_HTTP_TIMEOUT, verify=False)
    if not rsp.ok:
        logger.error('fail. request: %s, status_code: %s', rsp.request.url, rsp.status_code)
        return False

    rjson = json.loads(rsp.content)

    if 'errcode' in rjson:
        logger.error('fail. request: %s, rjson: %s', rsp.request.url, rjson)
        return False

    return rjson


def replace_forbidden_content(content):
    return ForbiddenWordsMgr.replace_word(content)



