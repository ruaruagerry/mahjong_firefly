# coding: utf8

"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : Firefly_game模块，主要负责鉴权功能(Login)
           内部function统一格式 "auth_function_"+cmd
"""

from firefly.server.globalobject import GlobalObject, remoteserviceHandle
from common.log import logger
from common.mahjong_pb2 import LoginReq, WsProtoTest, EvtDeskUserEnter, LoginRsp
from common import error_contrast
from common.bus_func import is_app_crime, common_user_reg_or_login, get_password
from common.models import User
import config
import hashlib
from common.redis_user_manager import RedisUserMgr
from common.bus_func import celery_delay
from common.tasks import wx_login
from common.firefly_utils import write_to_users
from common import proto
# from common.tasks import my_test


def doWhenStop():
    """
    服务器关闭前的处理
    :return:
    """
    logger.debug("****    The [auth] server is shut down ...    ****")
    # my_test()


GlobalObject().stophandler = doWhenStop


def tell_transfer_to_bind(uin, conn_id):
    GlobalObject().remote['_transfer_'].callRemote('bind_id_and_conn', uin, conn_id)


@remoteserviceHandle('_transfer_')
def auth_function_1002(request): # unicode
    """
    微信登录
    """
    from common.mahjong_pb2 import WeChatLoginReq
    from common.models import WXUser

    req = WeChatLoginReq()
    req.ParseFromString(request['body'])
    rsp = LoginRsp()

    # logger.debug('1002 req:%s', req)

    src = "%s&%s&%s" % (config.ONLY_PAY_SECRET, req.openid, req.token)
    sign = hashlib.md5(src).hexdigest()

    if req.sign != sign:
        logger.error('invalid sign! req: %s', req)
        rsp.ret = error_contrast.ERROR_INVALID_PARAMS
        return rsp.SerializeToString()

    appid = str(config.WX_LOGIN_CHANNEL_TO_APPID.get(req.channel, config.WX_LOGIN_APPID))

    wx_user = WXUser.objects.filter(
        userid=req.openid,
        appid=appid,
    ).first()

    if not wx_user or wx_user.access_token != req.token:
        celery_delay(
            wx_login,
            request,
        )
        return

    if request['uin'] and request['uin'] != wx_user.native_id:
        rsp.ret = error_contrast.ERROR_USER_BIND_NOT_MATCH
        return rsp.SerializeToString()

    user = RedisUserMgr().get_user(wx_user.native_id)
    user.update(dict(
        channel=req.channel or None,
        version=req.version,
        os=req.os or 'android',
    ))

    rsp = common_user_reg_or_login(request, user)

    tell_transfer_to_bind(user.uin, request['connid'])

    write_to_users(user.uin, proto.CMD_REG, rsp)


@remoteserviceHandle('_transfer_')
# CMD_REG = 1001
def auth_function_1001(request):
    """
    注册或登录
    :param request:
    :return:
    """
    req = LoginReq()
    req.ParseFromString(request['body'])
    rsp = LoginRsp()

    logger.debug('req:%s', req)

    if not req.uuid:
        rsp.ret = error_contrast.ERROR_INVALID_PARAMS
        return rsp.SerializeToString()

    if not req.sign:
        rsp.ret = error_contrast.ERROR_INVALID_PARAMS
        return rsp.SerializeToString()

    src = "%s&%s&%s" % (config.ONLY_PAY_SECRET, req.uuid, req.version)

    if req.sign != hashlib.md5(src).hexdigest():
        logger.error('invalid sign! req: %s', req)
        rsp.ret = error_contrast.ERROR_INVALID_PARAMS
        return rsp.SerializeToString()

    if is_app_crime(req.channel, req.version):
        if not req.extra_username or not req.extra_password:
            # 请输入用户名和密码
            rsp.ret = error_contrast.ERROR_ENTER_USERNAME_AND_PASSWORD
            return rsp.SerializeToString()

        db_user = User.objects.filter(extra_username=req.extra_username).first()
        if req.is_register and db_user:
            # 用户名已注册
            rsp.ret = error_contrast.ERROR_USERNAME_HAS_EXIST
            return rsp.SerializeToString()

        if not req.is_register:
            if not db_user:
                # 用户名不存在
                rsp.ret = error_contrast.ERROR_USERNAME_NOT_EXIST
                return rsp.SerializeToString()

            if db_user and db_user.extra_password != req.extra_password:
                # 密码错误
                rsp.ret = error_contrast.ERROR_PASSWORD_IS_ERROR
                return rsp.SerializeToString()
    else:
        db_user = User.objects.filter(uuid=req.uuid).first()

    if not db_user:
        db_user = User()
        db_user.password = get_password()
        if is_app_crime(req.channel, req.version):
            db_user.uuid = req.uuid + req.extra_username
            db_user.nick = req.extra_username
            db_user.extra_username = req.extra_username
            db_user.extra_password = req.extra_password
        else:
            db_user.uuid = req.uuid
            db_user.nick = req.nick[:6]
            db_user.card = 100

        if req.os:
            db_user.os = req.os

        db_user.save()

    # 转成Redis对象
    user = RedisUserMgr().get_user(db_user.uin)
    user.attach_db_user(db_user)
    user.update(dict(
        channel=req.channel,
        version=req.version,
        os=req.os,
    ))

    tell_transfer_to_bind(user.uin, request['connid'])

    return common_user_reg_or_login(request, user)
