# coding:utf8

"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : Firefly_net模块，主要负责对外en/de packet
"""
from firefly.utils.services import CommandService
from twisted.internet import defer
from twisted.python import log
from app.datapack import DataPackProtoc
from firefly.server.globalobject import GlobalObject, remoteserviceHandle, netserviceHandle
from common.log import logger
from common import proto
from common.bus_func import safe_str
from common.mahjong_pb2 import HeartBeatRsp


def doWhenStop():
    """
    服务器关闭前的处理
    :return:
    """
    log.msg("****    The [net] server is shut down ...    ****")


def callWhenConnLost(conn):
    """
    客户端连接断开时处理
    :param conn:
    :return:
    """
    # logger.debug("client %s login out", conn.transport.sessionno)
    GlobalObject().remote['_transfer_'].callRemote('unbind_id_and_conn', conn.transport.sessionno)


GlobalObject().stophandler = doWhenStop

# WebSocket设置
GlobalObject().server.ws.setDataProtocl(DataPackProtoc())
GlobalObject().server.ws.doConnectionLost = callWhenConnLost


class CurrentService(CommandService):

    def callTargetSingle(self, targetKey, *args, **kw):
        self._lock.acquire()
        try:
            target = self.getTarget(0)
            if not target:
                log.err('the command '+str(targetKey)+' not Found on net service')
                return None
            if targetKey not in self.unDisplay:
                log.msg("call method %s on service[single]"%target.__name__)
            defer_data = target(targetKey, *args, **kw)
            if not defer_data:
                return None
            if isinstance(defer_data, defer.Deferred):
                return defer_data
            d = defer.Deferred()
            d.callback(defer_data)
        finally:
            self._lock.release()
        return d


wsservice = CurrentService("wsservice")
GlobalObject().server.ws.addServiceChannel(wsservice)


def wsserviceHandle(target):
    """
    net节点服务
    :param target:
    :return:
    """
    wsservice.mapTarget(target)


# 从django app过来的消息
@netserviceHandle
def inner_recvall_0(conn, request):
    # logger.debug('django request:%s', request)
    conn_details = dict(
        id=conn.transport.sessionno,
        ip=conn.transport.client[0],
        port=conn.transport.client[1],
    )
    request = eval(request)
    cmd = request.get('cmd', None)
    if isinstance(cmd, dict):
        if cmd['send_cmd'] == proto.CMD_REG:
            connid = request['data']['connid']
            data = safe_str(request['data']['data'])
            for uin in cmd['uin_list']:
                # 绑定UIN和CONN关系
                GlobalObject().remote['_transfer_'].callRemote('bind_id_and_conn', uin, connid)
            # 发给用户登录
            # logger.debug('send_cmd:%d, data:%s, connid:%d', cmd['send_cmd'], data, connid)
            GlobalObject().server.ws.pushObject(cmd['send_cmd'], data, [connid])
        else:
            request = safe_str(request.get('data', None))
            if request:
                if cmd['op_cmd'] == proto.CMD_EVENT_USER_BROADCAST:
                    GlobalObject().remote['_transfer_'].callRemote('write_to_gateway', cmd['send_cmd'], request, 'broadcast_to_all')
                elif cmd['op_cmd'] == proto.CMD_WEB_SEND_MSG_TO_USER:
                    GlobalObject().remote['_transfer_'].callRemote('write_to_gateway', cmd['send_cmd'], request, cmd['uin_list'])
    else:
        request = dict(body=safe_str(request.get('data', None)), inner=True)
        GlobalObject().remote['_transfer_'].callRemote('transfer_to_game', cmd, request, conn_details)


# 从外到里传递
@wsserviceHandle
# 参数的顺序不能换
def recvall_0(cmd, conn, request):
    if cmd == proto.CMD_WEBSOCKET_HEARTHEAT:
        # logger.debug("recv heartbeat, conn:%d", conn.transport.sessionno)
        rsp = HeartBeatRsp()
        return rsp.SerializeToString()
    else:
        conn_details = dict(
            id=conn.transport.sessionno,
            ip=conn.transport.client[0],
            port=conn.transport.client[1],
        )
        return GlobalObject().remote['_transfer_'].callRemote('transfer_to_game', cmd, request, conn_details)


# 从里到外传递
# 调试到凌晨四点，记录一下，永远记住net仍然是gateway的一个child
@remoteserviceHandle('_transfer_')
def write_to_clients(cmd, data, conn_id):
    return GlobalObject().server.ws.pushObject(cmd, data, conn_id)


@remoteserviceHandle('_transfer_')
def close_clients_conn(conn_id):
    GlobalObject().server.ws.loseConnection(conn_id)
