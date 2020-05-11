#coding:utf8
'''
Created on 2013-8-12

@author: lan (www.9miao.com)
'''
from globalobject import GlobalObject,masterserviceHandle
from twisted.internet import reactor
from twisted.python import log
from common.log import logger

reactor = reactor


@masterserviceHandle
def serverStop():
    """
    停止服务
    :return:
    """
    reactor.callLater(0.5, reactor.stop)
    return True


@masterserviceHandle
def sreload():
    """
    重载模块
    :return:
    """
    log.msg('reload')
    if GlobalObject().reloadmodule:
        reload(GlobalObject().reloadmodule)
    return True


@masterserviceHandle
def remote_connect(rname, rhost):
    """
    连接远程节点
    :param rname:
    :param rhost:
    :return:
    """
    # logger.debug("rname:%s, rhost:%s", rname, rhost)
    GlobalObject().remote_connect(rname, rhost)

