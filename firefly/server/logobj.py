#coding:utf8

"""
Created on 2017-1-22
Author: GerryLuo
Blog: blog.gerryluo.cn
function: 在firefly中重载game server log
"""

from twisted.python import log
from zope.interface import implements
from common.log import firefly_logger


class loogoo:
    """
    日志处理
    """
    implements(log.ILogObserver)

    def __call__(self, eventDict):
        """
        日志处理
        """
        if 'logLevel' in eventDict:
            level = eventDict['logLevel']
        elif eventDict['isError']:
            level = 'ERROR'
        else:
            level = 'INFO'
        text = log.textFromEventDict(eventDict)
        if text is None or level != 'ERROR':
            return

        # 使用exception抛异常，这样email邮件体可以收到详细信息，避免了标题长度有限的问题
        if eventDict['log_format'] == '{log_text}' and not eventDict['message']:
            firefly_logger.exception(text)



