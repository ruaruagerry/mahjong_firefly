# coding: utf8

"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : Firefly_game模块，主要负责游戏大厅功能
           内部function统一格式 "hall_function_"+cmd
"""

from firefly.server.globalobject import GlobalObject, remoteserviceHandle
from twisted.python import log
from common.log import logger
from common.mahjong_pb2 import GameEnterDeskReq, GameEnterDeskRsp
from common.bus_func import alloc_desk_id, pre_game_function
from common import error_contrast, proto
from common.firefly_utils import write_to_other_game
import config


def doWhenStop():
    """
    服务器关闭前的处理
    :return:
    """
    log.msg("****    The [game] server is shut down ...    ****")


GlobalObject().stophandler = doWhenStop


# @remoteserviceHandle('_transfer_')
# def hall_function_4002(request):
#     logger.debug('recv request:%s', request)


@remoteserviceHandle('_transfer_')
# CMD_USER_ENTER_DESK = 4001
@pre_game_function
def hall_function_4001(request):
    req = GameEnterDeskReq()
    req.ParseFromString(request['body'])
    rsp = GameEnterDeskRsp()

    logger.debug('req:%s', req)
    # 先判断是否是换桌
    # 因为换桌前用户还没退桌, 所以 user.desk_id > 0
    if request['user'].desk_id > 0 and not req.reconnect:
        if request['user'].desk_id != req.dst_desk_id:
            write_to_other_game(proto.CMD_REDIRECT_EXIT_DESK, request)

    # 进别人的桌子或是断线重连
    if (req.dst_desk_id > 0 and not req.new_desk) or req.reconnect:
        # logger.debug('enter desk req:\n%s', req)
        # request.gw_box.ret = req.dst_desk_id
        write_to_other_game(proto.CMD_REDIRECT_ENTER_DESK, request)
    # 新开桌子
    elif req.dst_desk_id == 0 and req.new_desk and not req.reconnect:
        if config.OPEN_ROOM_CARD_USED:
            # 没足够的房卡
            if request['user'].card - req.card_num < 0:
                logger.debug('not enough card')
                rsp.ret = error_contrast.ERROR_NOT_ENOUGH_CARD
                return rsp.SerializeToString()

        # 先分配桌子ID，有desk_id就保存着
        desk_id = alloc_desk_id()
        req.dst_desk_id = desk_id
        # 设置路由分组
        # request.gw_box.ret = desk_id
        # logger.debug('new desk req:\n%s', req)
        request['body'] = req.SerializeToString()
        write_to_other_game(proto.CMD_REDIRECT_ENTER_DESK, request)
    else:
        logger.error('invalid params')
        rsp.ret = error_contrast.ERROR_INVALID_PARAMS
        return rsp.SerializeToString()
