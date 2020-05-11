#coding:utf8
'''
Created on 2013-8-7

@author: lan (www.9miao.com)
'''
from twisted.web import resource
from twisted.internet import reactor
from firefly.server.globalobject import GlobalObject
from firefly.utils.common import Jsonify, ToUtf8
from status import getServerInfo, buildConsoleResult

root = GlobalObject().webroot
reactor = reactor


def ErrorBack(reason):
    pass


def masterwebHandle(cls):
    """
    Master Web 服务注册
    :param cls:
    :return:
    """
    root.putChild(cls.__name__, cls())


@masterwebHandle
class stop(resource.Resource):
    
    def render(self, request):
        """
        停止服务器
        :param request:
        :return:
        """
        for child in GlobalObject().root.childsmanager._childs.values():
            d = child.callbackChild('serverStop')
            d.addCallback(ErrorBack)
        reactor.callLater(0.5, reactor.stop)
        return "stop\n"


@masterwebHandle
class reloadmodule(resource.Resource):

    def render(self, request):
        """
        重载模块(热更新)
        :param request:
        :return:
        """
        for child in GlobalObject().root.childsmanager._childs.values():
            d = child.callbackChild('sreload')
            d.addCallback(ErrorBack)
        return "reload\n"


@masterwebHandle
class status(resource.Resource):

    def getChild(self, path, request):
        return ServerStatus()

    def render(self, request):
        """
        控制台显示结果
        :param request:
        :return:
        """
        serverInfo = getServerInfo()
        result = buildConsoleResult(serverInfo)
        return result


class ServerStatus(resource.Resource):

    isLeaf = True

    def render(self, request):
        """
        服务器状态
        :param request:
        :return:
        """
        serverInfo = getServerInfo()
        dataType = request.path.split('/')[2]
        if dataType == "json":
            result = Jsonify(serverInfo)
        else:
            result = buildConsoleResult(serverInfo)
        return result

