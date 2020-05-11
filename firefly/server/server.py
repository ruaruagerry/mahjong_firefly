# coding:utf8
from twisted.python import log
from twisted.internet import reactor
from twisted.web import vhost
from firefly.netconnect.protoc import LiberateFactory
from firefly.web.delayrequest import DelaySite
from firefly.distributed.root import PBRoot, BilateralFactory
from firefly.distributed.node import RemoteObject
from firefly.dbentrust.dbpool import dbpool
from firefly.dbentrust.memclient import mclient
from firefly.utils import services
from websocket import WsFactory
from config import Config
from logobj import loogoo
from globalobject import GlobalObject
import os, sys, affinity, signal
from common.log import logger


class FFServer:
    
    def __init__(self):
        self.netfactory = None              # net前端
        self.root = None                    # 分布式root节点
        self.webroot = None                 # http服务
        self.ws = None
        self.remote = {}                    # remote节点
        self.master_remote = None
        self.db = None
        self.mem = None
        self.servername = None
        self.remoteportlist = []

    def set_name(self, name):
        """
        设置当前节点服务器名称
        :param name:
        :return:
        """
        self.servername = name
        
    def set_config(self):
        """
        初始化节点服务配置
        :return:
        """
        config = Config().config
        ser_cfg = config.get("servers", {}).get(self.servername)
        if not ser_cfg:
            raise ValueError
        mem_cfg = config.get("cache")
        master_cfg = config.get("master")
        db_cfg = config.get("db")

        GlobalObject().json_config = ser_cfg
        netport = ser_cfg.get('netport')                     # 客户端连接
        webport = ser_cfg.get('webport')                     # http连接
        rootport = ser_cfg.get('rootport')                   # root节点配置
        wsport = ser_cfg.get("wsport")                       # WebSocket端口
        self.remoteportlist = ser_cfg.get('remoteport',[])   # remote节点配置列表
        logpath = ser_cfg.get('log')                         # 日志
        hasdb = ser_cfg.get('db')                            # 数据库连接
        hasmem = ser_cfg.get('mem')                          # memcached连接
        app = ser_cfg.get('app')                             # 入口模块名称
        cpuid = ser_cfg.get('cpu')                           # 绑定cpu
        mreload = ser_cfg.get('reload')                      # 重新加载模块名称

        if master_cfg:
            masterport = master_cfg.get('rootport')
            masterhost = master_cfg.get('roothost')
            self.master_remote = RemoteObject(self.servername)
            addr = ('localhost',masterport) if not masterhost else (masterhost,masterport)
            self.master_remote.connect(addr)
            GlobalObject().masterremote = self.master_remote

        if netport:
            self.netfactory = LiberateFactory()
            netservice = services.CommandService("netservice")
            self.netfactory.addServiceChannel(netservice)
            reactor.listenTCP(netport, self.netfactory)
            
        if webport:
            self.webroot = vhost.NameVirtualHost()
            GlobalObject().webroot = self.webroot
            reactor.listenTCP(webport, DelaySite(self.webroot))
            
        if rootport:
            self.root = PBRoot()
            rootservice = services.Service("rootservice")
            self.root.addServiceChannel(rootservice)
            reactor.listenTCP(rootport, BilateralFactory(self.root))

        if wsport:
            self.ws = WsFactory(wsport)
            wsservice = services.CommandService("wsservice")
            self.ws.addServiceChannel(wsservice)
            reactor.listenTCP(wsport, self.ws)
            
        for cnf in self.remoteportlist:
            rname = cnf.get('rootname')
            self.remote[rname] = RemoteObject(self.servername)
            
        if hasdb and db_cfg:
            log.msg(str(db_cfg))
            dbpool.initPool(**db_cfg)
            
        if hasmem and mem_cfg:
            urls = mem_cfg.get('urls')
            hostname = str(mem_cfg.get('hostname'))
            mclient.connect(urls, hostname)
            
        # if logpath:
        #     log.addObserver(loogoo(logpath))#日志处理
        log.addObserver(loogoo())
        log.startLogging(sys.stdout)
        
        if cpuid:
            affinity.set_process_affinity_mask(os.getpid(), cpuid)

        GlobalObject().config(netfactory=self.netfactory, root=self.root, remote=self.remote)
        GlobalObject().server = self

        if app:
            __import__(app)
        if mreload:
            _path_list = mreload.split(".")
            GlobalObject().reloadmodule = __import__(mreload, fromlist=_path_list[:1])

        GlobalObject().remote_connect = self.remote_connect
        # logger.debug('servername:%s', self.servername)
        # import admin
        if self.servername not in ['_transfer_', ]:
            for cnf in self.remoteportlist:
                _rname = cnf.get('rootname')
                self.remote_connect(_rname, "")

    def remote_connect(self, rname, rhost):
        """
        连接远程RRoot节点
        :param rname:
        :param rhost:
        :return:
        """
        for cnf in self.remoteportlist:
            logger.debug('enter remote_connect')
            _rname = cnf.get('rootname')
            if rname == _rname:
                rport = cnf.get('rootport')
                if not rhost:
                    addr = ('localhost', rport)
                else:
                    addr = (rhost, rport)
                self.remote[rname].connect(addr)
                break

    def startAfter(self):
        """
        启动之后
        :return:
        """
        log.msg('%s has started, the pid is %s ...' % (self.servername, os.getpid()))

    def stopBefore(self):
        """
        停止之前
        :return:
        """
        log.msg('[%s] server is stopped ...' % self.servername)
        if GlobalObject().stophandler:
            GlobalObject().stophandler()
        signal.alarm(1)
        
    def start(self):
        """
        启动服务器
        :return:
        """
        reactor.addSystemEventTrigger('after', 'startup', self.startAfter)
        reactor.addSystemEventTrigger('before', 'shutdown', self.stopBefore)
        reactor.run()

