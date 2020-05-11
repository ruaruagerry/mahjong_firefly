# coding: utf8
"""
配置管理器
@name: config.py 
@author: cbwfree
@create: 15/12/21 21:31
"""
from firefly.utils.singleton import Singleton
from MySQLdb import converters


# 转换MySQL查询的特定字符, 例如 Datetime('2015-12-21'), Decimal('2') 等数据
conv = converters.conversions.copy()
# conv[10] = str                          # convert dates to strings
# conv[246] = float                       # convert decimals to floats


class Config(object):

    __metaclass__ = Singleton

    def __init__(self):
        self._master = {
            'roothost': '127.0.0.1',
            'rootport': 9999,
            'webport': 9998
        }
        self._db = {
            'host': '127.0.0.1',
            'port': 3306,
            'charset': 'utf8',
            'user': '',
            'passwd': '',
            'db': '',
            'conv': conv
        }
        self._cache = {}
        self._servers = {}
        self._other = {}

    @property
    def master(self):
        return self._master

    @property
    def db(self):
        return self._db

    @property
    def cache(self):
        return self._cache

    @property
    def other(self):
        return self._other

    @property
    def servers(self):
        """
        获取服务器节点配置
        :return:
        """
        servers = {}
        for server in self._servers.values():
            servers[server.node] = server.config
        return servers

    @property
    def config(self):
        """
        获取完整配置
        :return:
        """
        return {
            'master': self.master,
            'servers': self.servers,
            'db': self.db,
            'cache': self.cache,
            'other': self.other
        }

    def setMaster(self, **kwargs):
        """
        设置Master进程配置
        :param kwargs:
        :return:
        """
        if kwargs.get("roothost"):
            self._master["roothost"] = kwargs.get("roothost")
        if kwargs.get("rootport"):
            self._master["rootport"] = kwargs.get("rootport")
        if kwargs.get("webport"):
            self._master["webport"] = kwargs.get("webport")

    def setDb(self, **kwargs):
        """
        设置数据库配置
        :param kwargs:
        :return:
        """
        if kwargs.get("host"):
            self._db['host'] = kwargs.get("host")
        if kwargs.get("port"):
            self._db['port'] = kwargs.get("port")
        if kwargs.get("charset"):
            self._db['charset'] = kwargs.get("charset")
        if kwargs.get("user"):
            self._db['user'] = kwargs.get("user")
        if kwargs.get("passwd"):
            self._db['passwd'] = kwargs.get("passwd")
        if kwargs.get("db"):
            self._db['db'] = kwargs.get("db")
        if kwargs.get("conv"):
            # conv 数据格式是一个字典, key为要转换的数据类型索引, value是转换函数
            convDict = kwargs.get("conv", {})
            for index, val in convDict.items():
                conv[index] = val
            self._db['conv'] = conv

    def setCache(self, cache):
        """
        设置缓存配置
        :param cache:
        :return:
        """
        self._cache = cache

    def set(self, key, value, db=False):
        """
        属性设置
        :param key:
        :param value:
        :param db:
        :return:
        """
        if db:
            convDict = value.get("conv", {})
            for index, val in convDict.items():
                conv[index] = val
            value['conv'] = conv
        self._other[key] = value

    def get(self, key):
        """
        属性获取
        :param key:
        :return:
        """
        return self._other.get(key, {})

    def addServer(self, server):
        """
        增加Server配置
        :param server:
        :return:
        """
        if server.node in self._servers:
            raise "Server node [%s] already exists" % server.node
        self._servers[server.node] = server

    def getServer(self, name):
        """
        获取Server配置对象
        :param name:
        :return:
        """
        return self._servers.get(name)



class ServerConfig:
    """
    服务器节点配置
    """
    def __init__(self, name, node=None):
        self.name = name
        self.node = node if node else name
        self.app = "app.%sserver" % name
        self.log = None
        self.cpu = None
        self.db = False
        self.mem = False
        self.reload = None
        self.netport = 0
        self.rootport = 0
        self.webport = 0
        self.wsport = 0
        self.remote = []

    @property
    def remoteList(self):
        """
        远程连接列表
        :return:
        """
        remote = []
        for name in self.remote:
            server = Config().getServer(name)
            if server and server.rootport:
                remote.append({"rootname": name, "rootport": server.rootport})
        return remote

    @property
    def config(self):
        """
        获取属性
        :return:
        """
        attr = {'name': self.node}
        for key, val in self.__dict__.items():
            if val and key not in ['name', 'remote', 'node']:
                attr[key] = val
        if self.remote:
            attr['remoteport'] = self.remoteList
        return attr

    def set_log(self):
        """
        开启日志
        :return:
        """
        self.log = "logs/%s.log" % self.node

    def set_cpu(self, cpuId):
        """
        绑定CPU
        :param cpuId:
        :return:
        """
        self.cpu = cpuId

    def set_db(self):
        """
        启用数据库
        :return:
        """
        self.db = True

    def set_mem(self):
        """
        启用缓存
        :return:
        """
        self.mem = True

    def set_reload(self):
        """
        启用重载
        :return:
        """
        self.reload = "app.%s.doreload" % self.name

    def set_net(self, port):
        """
        启用Net服务
        :param port:
        :return:
        """
        self.netport = port

    def set_root(self, port):
        """
        作为Root节点
        :param port:
        :return:
        """
        self.rootport = port

    def set_web(self, port):
        """
        启用Web服务
        :param port:
        :return:
        """
        self.webport = port

    def set_ws(self, port):
        """
        启用WebSocket
        :param port:
        :return:
        """
        self.wsport = port

    def set_remote(self, *remote):
        """
        设置远程连接节点
        :param remote: 需要连接的节点名称
        :return:
        """
        self.remote = remote
