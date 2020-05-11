# -*- coding:utf-8 -*-
"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : 联通django和firefly的模块
"""
import socket
from common.log import logger
from app.datapack import sendData
import config
import json
import time


count = 0
def connect_send_logger(*args, **kw):
    global count
    if count < 15:
        count += 1
        logger.debug(*args, **kw)
    else:
        count = 0
        logger.error(*args, **kw)


def singleton(cls, *args, **kw):
    instances = {}
    def _singleton(*args, **kw):
        if cls not in instances:
            instances[cls] = cls(*args, **kw)
        return instances[cls]
    return _singleton


@singleton
class Bridge(object):

    client = None
    host = None
    port = None
    process_name = None

    def __init__(self, pro_name=None):
        self.host = config.GATEWAY_TCP_HOST
        self.port = config.GATEWAY_TCP_PORT
        self.process_name = pro_name

    def get_connect(self):
        result = False
        # 要写到这里，每次链接的时候新建一个socket
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 设置成非阻塞
        self.client.setblocking(False)
        while not result:
            time.sleep(config.BRIDGE_CONNECT_INTERVAL)
            try:
                self.client.connect((self.host, self.port))
                result = True
            except socket.error, arg:
                (errno, err_msg) = arg
                # Operation now in progress
                # 非阻塞connect会直接返回这个错误，不用理它
                if errno == 115:
                    pass
                else:
                    connect_send_logger('process:%s connect failed, errno:%s, err_msg:%s', self.process_name, errno, err_msg, exc_info=True)
                    result = False

    def close_connect(self):
        try:
            self.client.close()
        except:
            connect_send_logger('process:%s close connect, exc occur.', self.process_name, exc_info=True)

    def get_status(self):
        # 有链接就来判断
        if self.client:
            try:
                # 设置为非阻塞后读到None就证明对端断了
                data = self.client.recv(1024)
                # 没有数据就返回断掉了
                if not data:
                    return False
            except socket.error, arg:
                (errno, err_msg) = arg
                # 11是EAGAIN
                if errno in [11, ]:
                    return True
                else:
                    connect_send_logger('process:%s listening recv error, errno:%s, err_msg:%s', self.process_name, errno, err_msg, exc_info=True)
                    return False
        else:
            return False

    # 这里0写死
    def send_data(self, cmd, data):
        # 能不用json.dumps就不用json.dumps，完全就是个坑嘛(2017.1.18)
        data = repr(dict(cmd=cmd, data=data))
        self.client.sendall(sendData(data, 0))
