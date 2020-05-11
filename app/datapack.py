# coding: utf8
"""
pack/unpack的具体实现
"""
from firefly.netconnect.datapack import DataPackError
from twisted.python import log
import struct

# inner tcp packet
import time

from socket import AF_INET,SOCK_STREAM,socket
import struct


def sendData(sendstr,commandId):
    HEAD_0 = chr(0)
    HEAD_1 = chr(0)
    HEAD_2 = chr(0)
    HEAD_3 = chr(0)
    ProtoVersion = chr(0)
    ServerVersion = 0
    sendstr = sendstr
    data = struct.pack('!sssss3I',HEAD_0,HEAD_1,HEAD_2,\
                       HEAD_3,ProtoVersion,ServerVersion,\
                       len(sendstr)+4,commandId)
    senddata = data+sendstr
    return senddata


def resolveRecvdata(data):
    head = struct.unpack('!sssss3I',data[:17])
    length = head[6]
    data = data[17:17+length]
    return data


class DataPackProtoc:
    """数据包协议
    """
    def __init__(self):
        self.header = 8

    def getHeadlength(self):
        """获取数据包的长度
        """
        return self.header

    def unpack(self, dpack):
        '''解包
        '''
        try:
            length, command = struct.unpack('!2I', dpack)
        except DataPackError, de:
            log.err(de)
            return {'result': False, 'command': 0, 'length': 0}
        return {'result': True, 'command': command, 'length': length}

    def pack(self, response, command):
        '''打包数据包
        '''
        length = response.__len__()
        data = struct.pack('!2I', length, command)
        print len(data + response)
        return data + response


