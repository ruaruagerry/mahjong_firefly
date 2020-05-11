# coding: utf8

"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : Firefly_net模块，主要负责牌桌逻辑
           内部function统一格式 "play_function_"+cmd
"""

from firefly.server.globalobject import GlobalObject, remoteserviceHandle
from twisted.python import log
from common.log import logger
from common.desk_mgr_controller import MjDeskMgrController
import config
import functools
import time
from common import proto
from common.mahjong_pb2 import GameOptionHuReq, GameOptionChiReq, GameOptionPengReq, GameOptionGangReq, \
    GameSendCardReq, GameOptionPassReq, GamePlayerReadyReq, GamePlayerReadyEvt, GameOptionGangNotFirstReq, \
    ApplyDeleteReq, ApplyDeleteEvt, GameEnterDeskReq, GameEnterDeskRsp, GameExitDeskRsp, ClientNotifyStartGameRsp, \
    GameSendCardRsp, GameOptionChiRsp, GameOptionPengRsp, GameOptionGangRsp, GameOptionHuRsp, GameOptionPassRsp, \
    GameOptionGangNotFirstRsp
from common import error_contrast
from common.bus_func import load_desk, desk_required, pre_game_function, pre_game_function_with_desk
from common.firefly_utils import write_to_users
import json


def doWhenStop():
    """
    服务器关闭前的处理
    :return:
    """
    log.msg("****    The [game] server is shut down ...    ****")


GlobalObject().stophandler = doWhenStop


@remoteserviceHandle('_transfer_')
# CMD_TIME_OUT_CHECK = 10000
def play_function_10000(request):
    # logger.debug('request:%s', request)
    # return
    try:
        body = json.loads(request['body'])
        prefix, tid = str(body['timer_id']).split(":")
        op_type = str(body['op_type'])
        expire_time = int(body['expire_time'])
    except:
        logger.error("invalid body: %s", request)
        return

    # logger.debug('timer_id: %s, op_type: %s, expire_time: %s', body['timer_id'], body['op_type'], body['expire_time'])

    if prefix in ('mj_desk', ):
        desk = load_desk(tid, with_lock=True)
        if not desk:
            logger.error("Desk %s is not exist. op_type: %s", tid, op_type)
            return

        real_time = desk.timeout_info.get(op_type, None)
        if real_time is None or real_time != expire_time:
            desk.unlock()
            logger.error("invalid expire_time: %s, real_time is %s, op_type is %s, desk id %s, desk.timeout_info %s", \
                         expire_time, real_time, op_type, desk.id, desk.timeout_info)
            return

        # 每触发一次定时器都会检测一次桌子状态，如果可以清除就干掉
        desk.restore_later = True
        desk.handle_timeout(op_type)
        desk.unlock()


def exit_prev_desk(request, prev_desk):
    # 手动lock
    try:
        prev_desk.user_exit(request['user'].uin, ntf_me=False)
    except:
        logger.error('user_exit fail')


def get_reconnect_desk(user, lock_desk=True):
    """
    获取断线重连的桌子
    :param user:
    :param lock_desk:
    :return:
    """
    if user.desk_id > 0:
        desk = load_desk(user.desk_id, with_lock=lock_desk)
        if desk:
            if desk.type not in [config.DESK_TYPE_MJ_WZ, config.DESK_TYPE_MJ_ZZ]:
                desk.unlock()
                logger.error('invalid params')
                return error_contrast.ERROR_INVALID_PARAMS, None
            return 0, desk
        else:
            logger.error('desk not exist')
            return error_contrast.ERROR_DESK_NOT_EXIST, None
    logger.error('user.desk is 0')
    return error_contrast.ERROR_NOT_IN_DESK, None


def check_to_exit_prev_desk(request):
    """
    换桌前的退桌
    :param request:
    :param req:
    :return:
    """
    prev_desk = load_desk(request['user'].desk_id, with_lock=True) if request['user'].desk_id else None
    # 我得先把他原来的房间给退了
    if prev_desk:
        if prev_desk.type not in [config.DESK_TYPE_MJ_WZ, config.DESK_TYPE_MJ_ZZ]:
            prev_desk.unlock()
            logger.error('invalid params')
            return error_contrast.ERROR_INVALID_PARAMS, 0

        prev_desk.restore_later = True
        exit_prev_desk(request, prev_desk)
        prev_desk.unlock()
        return 0, prev_desk.id
    else:
        logger.error('desk not exist')
        return error_contrast.ERROR_DESK_NOT_EXIST, 0


def try_allocate_desk(user, desk_id, req):
    # 如果是开新桌就开，不是就取桌子
    if req.new_desk:
        desk = MjDeskMgrController().create_desk(desk_id, lock_desk=True, seat_limit=req.seat_limit,
                                                 win_type=req.win_type, laizi=req.extra_type.hongzhong,
                                                 qidui=req.extra_type.qidui, zhuaniao=req.extra_type.zhuaniao,
                                                 piaofen=req.extra_type.piaofen, shanghuo=req.extra_type.shanghuo,
                                                 type=req.desk_type,
                                                 user_id=user.uin,
                                                 card_num=req.card_num)
        if desk:
            return 0, desk
        else:
            logger.error('desk not exist')
            return error_contrast.ERROR_DESK_NOT_EXIST, None
    else:
        desk = MjDeskMgrController().get_desk(desk_id, lock_desk=True)
        if desk:
            return 0, desk
        else:
            return error_contrast.ERROR_DESK_NOT_EXIST, None


@remoteserviceHandle('_transfer_')
# CMD_REDIRECT_ENTER_DESK
@pre_game_function
def play_function_7001(request):
    """
    只处理进桌
    """
    req = GameEnterDeskReq()
    req.ParseFromString(request['body'])
    rsp = GameEnterDeskRsp()

    user = request['user']
    # 先保存下来，后面要做判断
    dst_desk_id = req.dst_desk_id or 0

    # 正常从hall里面走进来的dst_desk_id是肯定有值的
    if not dst_desk_id:
        # 获取断线重连桌子
        err, desk = get_reconnect_desk(user)
        if err:
            rsp.ret = err
            write_to_users(user.id, proto.CMD_USER_ENTER_DESK, rsp.SerializeToString())
            return

        if desk.status == config.GAME_STATE_WAIT_DELETE:
            desk.user_exit(user.uin)
            return
    else:
        # 为了支持服务器重启清除所有数据的时候，如果这时
        # 用户在游戏大厅，那这时应该可以让他进指定桌。
        request['user'].update(dict(
            status=1,
            desk_id=0,
        ))

        err, desk = try_allocate_desk(user, dst_desk_id, req)

        if err:
            if desk:
                desk.unlock()
            rsp.ret = err
            write_to_users(user.id, proto.CMD_USER_ENTER_DESK, rsp.SerializeToString())
            return

        # 先判断桌子的状态
        if desk.status == config.GAME_STATE_WAIT_DELETE:
            desk.user_exit(user.uin)
            rsp.ret = error_contrast.ERROR_DESK_NOT_EXIST
            write_to_users(user.id, proto.CMD_USER_ENTER_DESK, rsp.SerializeToString())
            return

    # 把用户加入进去
    enter_ok = desk.user_enter(request)
    # player = desk.player_group.get_player_or_viewer_by_uin(request.user.uin)

    # 坐下失败了
    if enter_ok >= config.RET_SIT_DOWN_FAILED:
        logger.debug('sit_down failed')
        rsp.ret = error_contrast.ERROR_SIT_DOWN_FAIL
        write_to_users(user.id, proto.CMD_USER_ENTER_DESK, rsp.SerializeToString())

    # 如果是中途退桌再回来，那才在这里发
    if enter_ok == config.RET_SIT_DOWN_RECONNECT:
        logger.debug('reconnect, player_group:%s', desk.player_group)
        desk.broadcast_user_enter(request)

    # 手动解锁
    desk.unlock()


@remoteserviceHandle('_transfer_')
# CMD_REDIRECT_EXIT_DESK
@pre_game_function
def play_function_7002(request):
    """
    内部使用
    换桌前的退桌, 然后重定向到分配桌子ID
    :param request:
    :return:
    """
    req = GameEnterDeskReq()
    req.ParseFromString(request['body'])
    user = request['user']
    rsp = GameEnterDeskRsp()

    # 是否是换桌, 检查退桌
    err, prev_desk_id = check_to_exit_prev_desk(request)
    if err:
        rsp.ret = err
        write_to_users(user.id, proto.CMD_USER_ENTER_DESK, rsp.SerializeToString())
        return


@remoteserviceHandle('_transfer_')
# CMD_GAME_EXIT_DESK
@pre_game_function
def play_function_7003(request):
    """
    离开桌子
    """
    rsp = GameExitDeskRsp()

    desk = load_desk(request['user'].desk_id, with_lock=True)
    if not desk:
        return

    ret = desk.user_exit(request['user'].uin, reason=config.USER_EXIT_REASON_USER_REQUEST)

    if desk:
        desk.unlock()

    rsp.ret = ret
    return rsp.SerializeToString()


@remoteserviceHandle('_transfer_')
# CMD_CLIENT_NTF_START_GAME
@pre_game_function
@desk_required(lock_desk=True, restore_later=True)
def play_function_7004(request):
    """
    客户端通知服务器立即开始游戏
    :param request:
    :return:
    """
    rsp = ClientNotifyStartGameRsp()
    request['desk'].check_to_start_play()

    rsp.ret = 0
    return rsp.SerializeToString()


@remoteserviceHandle('_transfer_')
# CMD_GAME_SEND_CARD
@pre_game_function
@desk_required(lock_desk=True, restore_later=True)
def play_function_7005(request):
    """
    出牌
    """
    req = GameSendCardReq()
    req.ParseFromString(request['body'])
    rsp = GameSendCardRsp()
    rsp.ret = request['desk'].send_card(request['user'].uin, req.card)
    return rsp.SerializeToString()


@remoteserviceHandle('_transfer_')
# CMD_GAME_CHI
@pre_game_function
@desk_required(lock_desk=True, restore_later=True)
def play_function_7006(request):
    """
    吃牌
    """
    req = GameOptionChiReq()
    req.ParseFromString(request['body'])
    rsp = GameOptionChiRsp()
    rsp.ret = request['desk'].option_chi(request['user'].uin, req.index)
    return rsp.SerializeToString()


@remoteserviceHandle('_transfer_')
# CMD_GAME_PENG
@pre_game_function
@desk_required(lock_desk=True, restore_later=True)
def play_function_7007(request):
    """
    碰牌
    """
    req = GameOptionPengReq()
    req.ParseFromString(request['body'])
    rsp = GameOptionPengRsp()
    rsp.ret = request['desk'].option_peng(request['user'].uin)
    return rsp.SerializeToString()


@remoteserviceHandle('_transfer_')
# CMD_GAME_GANG
@pre_game_function
@desk_required(lock_desk=True, restore_later=True)
def play_function_7008(request):
    """
    杠牌
    """
    req = GameOptionGangReq()
    req.ParseFromString(request['body'])
    rsp = GameOptionGangRsp()
    rsp.ret = request['desk'].option_gang(request['user'].uin)
    return rsp.SerializeToString()


@remoteserviceHandle('_transfer_')
# CMD_GAME_HU
@pre_game_function
@desk_required(lock_desk=True, restore_later=True)
def play_function_7009(request):
    """
    胡牌
    """
    req = GameOptionHuReq()
    req.ParseFromString(request['body'])
    rsp = GameOptionHuRsp()
    rsp.ret = request['desk'].option_hu(request['user'].uin)
    return rsp.SerializeToString()


@remoteserviceHandle('_transfer_')
# CMD_GAME_PASS
@pre_game_function
@desk_required(lock_desk=True, restore_later=True)
def play_function_7010(request):
    """
    过牌
    """
    req = GameOptionPassReq()
    req.ParseFromString(request['body'])
    rsp = GameOptionPassRsp()
    rsp.ret = request['desk'].option_pass(request['user'].uin)
    return rsp.SerializeToString()


@remoteserviceHandle('_transfer_')
# CMD_PLAYER_STATUS_CHANGE
@pre_game_function
@desk_required(lock_desk=True, restore_later=True)
def play_function_7012(request):
    """
    改变用户状态
    """
    req = GamePlayerReadyReq()
    req.ParseFromString(request['body'])

    logger.debug('req:%s\n, desk:%s\n', req, request['desk'])
    request['desk'].player_status_change(request['user'].uin, req)

    evt = GamePlayerReadyEvt()
    evt.deskid = request['desk'].id
    if 'game_start' in request['desk'].timeout_info and request['desk'].type == config.DESK_TYPE_MJ_WZ:
        evt.pre_remain_time = request['desk'].timeout_info['game_start'] - int(time.time())
    else:
        evt.pre_remain_time = -1

    for player in request['desk'].player_group.valid_players:
        evt_info_list = evt.users.add()
        if req.status == 2 or req.status == 3:
            evt_info_list.status = player.delete_status
        else:
            evt_info_list.status = player.status
        evt_info_list.piaofen = player.piaofen
        evt_info_list.shanghuo = player.shanghuo
        evt_info_list.uin = player.uin

    logger.debug('status evt:\n%s', evt)
    evt = evt.SerializeToString()
    for player in request['desk'].player_group.valid_players:
        write_to_users(player.uin, proto.CMD_PLAYER_STATUS_CHANGE, evt)


@remoteserviceHandle('_transfer_')
# CMD_GAME_GANG_NOT_FIRST
@pre_game_function
@desk_required(lock_desk=True, restore_later=True)
def play_function_7013(request):
    """
    非即时杠牌
    """
    req = GameOptionGangNotFirstReq()
    req.ParseFromString(request['body'])
    rsp = GameOptionGangNotFirstRsp()
    rsp.ret = request['desk'].option_gang_not_first(request['user'].uin, req.gang_card)
    return rsp.SerializeToString()


@remoteserviceHandle('_transfer_')
# CMD_APPLY_DELETE_DESK
@pre_game_function
@desk_required(lock_desk=True, restore_later=True)
def play_function_7014(request):
    """
    申请解散牌桌
    """
    req = ApplyDeleteReq()
    req.ParseFromString(request['body'])

    state = request['desk'].apply_delete_desk(request['user'].uin)

    if config.GAME_START_PASS == state:
        return

    evt = ApplyDeleteEvt()
    evt.apply_uin = request['user'].uin
    evt.game_status = state
    if 'count_down' in request['desk'].timeout_info:
        evt.remain_time = request['desk'].timeout_info['count_down'] - int(time.time())
    evt.status = request['desk'].status
    evt.deskid = request['desk'].id

    evt = evt.SerializeToString()
    for player in request['desk'].player_group.valid_players:
        write_to_users(player.uin, proto.CMD_APPLY_DELETE_DESK, evt)




