# coding: utf8
"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : Firefly_gateway模块，主要负责内部通讯，转发由内而外和由外而内的消息
           由外而内 req/rsp模式
           由内而外 push模式，broadcast模式
"""

from firefly.server.globalobject import GlobalObject, rootserviceHandle
from twisted.python import log
from common.log import logger
from common.firefly_map import FireflyMap
from common.redis_user_manager import RedisUserMgr
from common import proto
import config


def doWhenStop():
    """
    服务器关闭前的处理
    :return:
    """
    log.msg("****    The [gate] server is shut down ...    ****")


GlobalObject().stophandler = doWhenStop

# MARK 后续加进flask blueprint
# transfer根据cmd来判断如何转发
# game: auth,hall,play
# cmd分配 auth:1001-4000 hall:4001-7000 play:7001-10000
@rootserviceHandle
def transfer_to_game(cmd, request, conn):
    conn_id = conn.get('id', None)
    conn_ip = conn.get('ip', None)
    conn_port = conn.get('port', None)

    # logger.debug('cmd:%s', cmd)
    # 登录消息绑定这些
    if cmd == 1001:
        # 组装传到内部的消息
        request = dict(
            body=request,
            connid=conn_id,
            ip=conn_ip,
        )
    # 为了适配微信登录和绑定
    elif cmd == 1002:
        uin = FireflyMap().get_user_by_conn(conn_id)
        request = dict(
            body=request,
            connid=conn_id,
            ip=conn_ip,
            uin=uin,
        )
    elif cmd >= 4001:
        # 内部消息不做任何处理
        if cmd == proto.CMD_TIME_OUT_CHECK:
            pass
        else:
            # 没有inner说明是外部消息
            if not isinstance(request, dict) or 'inner' not in request:
                uin = FireflyMap().get_user_by_conn(conn_id)
                if not uin:
                    logger.critical('not found user, cmd:%s, conn_id:%s, ip:%s, port:%s', cmd, conn_id, conn_ip, conn_port)
                    return
                request = dict(
                    body=request,
                    uin=uin,
                )
    # 到时候调试好了记得把desk加进来
    # if 9999 >= cmd >= 7001:
    #     request['desk'] =

    # 分发消息到game server
    if cmd in range(1001, 4001):
        return GlobalObject().root.callChild("_auth_", "auth_function_" + str(cmd), request)
    elif cmd in range(4001, 7001):
        return GlobalObject().root.callChild("_hall_", "hall_function_" + str(cmd), request)
    elif cmd in range(7001, 10001):
        return GlobalObject().root.callChild("_play_", "play_function_" + str(cmd), request)
    elif cmd in range(10001, 13001):
        return GlobalObject().root.callChild("_common_", "common_function_" + str(cmd), request)


@rootserviceHandle
def write_to_gateway(cmd, data, uin_list):
    conn_list = []
    if uin_list == 'broadcast_to_all':
        for _, conn_id in FireflyMap().user_conn_map.items():
            conn_list.append(conn_id)
    else:
        for uin in uin_list:
            conn_list.append(FireflyMap().get_conn_by_user(uin))

    return GlobalObject().root.callChild("_gateway_", "write_to_clients", cmd, data, conn_list)


@rootserviceHandle
def bind_id_and_conn(uin, conn_id):
    result, old_conn_id = FireflyMap().attach_user_conn(uin, conn_id)
    # logger.debug('current bind:%s, old_conn:%s', FireflyMap().user_conn_map, old_conn_id)
    # 绑定失败了，说明之前已经有了，把之前的链接断掉
    # 2017-3-28 加上socket复用，之前的链接跟新链接是同一个就不变
    if not result and old_conn_id != conn_id:
        GlobalObject().root.callChild("_gateway_", "close_clients_conn", old_conn_id)


@rootserviceHandle
# 用户如果离线了就把它置为离线状态
def unbind_id_and_conn(conn_id):
    user_id = FireflyMap().get_user_by_conn(conn_id)
    if user_id:
        # 先更改用户状态，直接换成不在线就OK了
        user = RedisUserMgr().get_user(user_id)
        user.update(dict(
            status=config.LOGIN_USER_STATUS_OFFLINE,
        ))
        FireflyMap().detach_user_conn(user_id)
    else:
        logger.debug('conn:%s not find user_id', conn_id)

