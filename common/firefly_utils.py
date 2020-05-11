# -*- coding: utf-8 -*-

"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : 对firefly模块的封装都放这里
"""

from firefly.server.globalobject import GlobalObject
from common.bridge import Bridge
from common.log import logger


# 发送消息给客户端
def write_to_users(uins, cmd, data):
    if not isinstance(uins, list):
        uin_list = [uins]
    else:
        uin_list = uins

    # 返回给客户端的一定要是这种格式的repr(dict())的body
    GlobalObject().remote['_transfer_'].callRemote('write_to_gateway', cmd, data, uin_list)


# 在一个game_server内发送消息给其它的game_server
def write_to_other_game(cmd, request):
    request['inner'] = True
    # conn传个空字典过去
    GlobalObject().remote['_transfer_'].callRemote('transfer_to_game', cmd, request, {})


# django内转发消息给firefly，切记只在django app内使用
# MARK 这里引入了一个问题：当从自己写的run命令发的消息都是OK的 但是从webserver发的消息是经过编码的
def bridge_to_other_game(cmd, request):
    Bridge().send_data(cmd, request)


# django直接发消息给客户端
# 如果是广播uins就带None
def bridge_to_users(uins, cmd, request, broadcast=False):
    if broadcast:
        uin_list = None
        cmd = dict(op_cmd=1000, send_cmd=cmd, uin_list=uin_list)
    else:
        if not isinstance(uins, list):
            uin_list = [uins]
        else:
            uin_list = uins
        cmd = dict(op_cmd=999, send_cmd=cmd, uin_list=uin_list)

    Bridge().send_data(cmd, request)


# celery里面发消息就用短连接好了
def celery_to_users(uins, cmd, request):
    Bridge().get_connect()
    bridge_to_users(uins, cmd, request)
    Bridge().close_connect()





