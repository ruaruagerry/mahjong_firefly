# coding: utf8
"""
Master 管理进程
@name: master.py
@author: cbwfree
@create: 15/12/29 20:02
"""
import os, time, sys, signal
from twisted.application import service, internet
from twisted.internet import reactor
from twisted.runner.procmon import ProcessMonitor
from twisted.web import vhost
from twisted.python import log
from twisted.python.logfile import DailyLogFile
from firefly.utils import  services
from firefly.distributed.root import PBRoot,BilateralFactory
from firefly.server.globalobject import GlobalObject
from firefly.web.delayrequest import DelaySite
from firefly.server.config import Config
from firefly.utils.common import Jsonify


if os.name != 'nt' and os.name != 'posix':
    from twisted.internet import epollreactor
    epollreactor.install()


MULTI_SERVER_MODE = 1
SINGLE_SERVER_MODE = 2
MASTER_SERVER_MODE = 3


class Master:
    
    def __init__(self):
        self.root = None
        self.web = None
        self.mode = MULTI_SERVER_MODE
        self.node = None
        self.script = "appmain.py"
        self.process = ProcessMonitor()
        self.service = service.MultiService()
        self.start_time = 0

    def set_mode(self, mode):
        self.mode = mode

    def set_node(self, node):
        self.node = node

    def set_script(self, script):
        self.script = script
        
    def create_master(self):
        """
        创建Master服务
        :return:
        """
        config = Config().config
        GlobalObject().json_config = config
        mastercnf = config.get('master')
        rootport = mastercnf.get('rootport')
        webport = mastercnf.get('webport')
        masterlog = mastercnf.get('log')
        self.root = PBRoot()
        rootservice = services.Service("rootservice")
        self.root.addServiceChannel(rootservice)
        self.web = vhost.NameVirtualHost()
        self.web.addHost('0.0.0.0', './')
        GlobalObject().root = self.root
        GlobalObject().webroot = self.web
        import webapp
        import rootapp
        internet.TCPServer(webport, DelaySite(self.web)).setServiceParent(self.service)
        internet.TCPServer(rootport, BilateralFactory(self.root)).setServiceParent(self.service)
        self.process.setServiceParent(self.service)

    def create_node(self, name):
        """
        创建节点服务
        :param name:
        :return:
        """
        args = ["python", self.script, name]
        self.process.addProcess(name, args, env=os.environ)

    def start(self, app):
        """
        启动APP
        :param app:
        :return:
        """
        self.start_time = reactor.seconds()
        if self.mode == MULTI_SERVER_MODE:
            self.create_master()
            servers = Config().servers
            for name in servers.keys():
                self.create_node(name)
        elif self.mode == SINGLE_SERVER_MODE:
            self.create_node(self.node)
        else:
            self.create_master()
        reactor.addSystemEventTrigger('after', 'startup', self.startAfter)
        reactor.addSystemEventTrigger('before', 'shutdown', self.stopBefore)
        if "-y" in sys.argv and "-n" not in sys.argv:
            app.setComponent(log.ILogObserver, log.FileLogObserver(DailyLogFile("logs/master.log", "")).emit)
        self.service.setServiceParent(app)
        GlobalObject().server = self
            
    def startAfter(self):
        """
        启动之后
        :return:
        """
        log.msg("*** The master in the %s launch ***" % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time)))
        # 在根目录写入启动进程信息
        process = [(os.getpid(), 'master')]
        for name, proc in self.process.protocols.items():
            process.append((proc.transport.pid, name))
        with open("status.json", "w+") as f:
            f.write(Jsonify(process))
            f.close()

    def stopBefore(self):
        """
        关闭之前
        :return:
        """
        log.msg("*** Wait for the child process to exit ***")
        wait = dict([(proc.transport.pid, name) for name, proc in self.process.protocols.items()])
        while True:
            try:
                pid = os.wait()[0]
                log.msg("[%s] child node has quit, pid: %s" % (wait.get(pid), pid))
            except:
                break
        signal.alarm(1)