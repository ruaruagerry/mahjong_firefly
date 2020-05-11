# -*- coding: utf-8 -*-

import sys
import urllib
import urllib2
import cookielib
import hashlib
from time import time


class SendMsgTest(object):
    """网易云信 短信模板：
    • 短信由三部分构成：签名+内容+变量
    • 短信模板示例：尊敬的%s ，您的余额不足%s元，请及时缴费。"""

    def __init__(self):
        super(SendMsgTest, self).__init__()
        sys.stdout.flush()
        self.cookie = cookielib.CookieJar()
        self.handler = urllib2.HTTPCookieProcessor(self.cookie)
        self.opener = urllib2.build_opener(self.handler)
        urllib2.install_opener(self.opener)

    def addHeaders(self, name, value):
        self.opener.addheaders.append((name, value))

    def doPost(self, url, payload=None):
        req = urllib2.Request(url, data=payload)
        req = self.opener.open(req)
        return req

    def checkSum(self, appSecret, nonce, curTime):
        # SHA1(AppSecret + Nonce + CurTime),三个参数拼接的字符串，
        # 进行SHA1哈希计算，转化成16进制字符(String，小写)
        return hashlib.sha1(appSecret + nonce + curTime).hexdigest()

    def send(self):
        appSecret = '4cfbe2df93c7'
        nonce = 'gerryluo'  # 随机数（最大长度128个字符）
        curTime = str(int(time()))

        self.addHeaders("AppKey", "788e904f55c6cede9f86a056d531aa9a")
        self.addHeaders("CheckSum", self.checkSum(appSecret, nonce, curTime))
        self.addHeaders("Content-Type", "application/x-www-form-urlencoded;charset=utf-8")
        self.addHeaders("CurTime", curTime)
        self.addHeaders("Nonce", nonce)

        accid = 'gerryluo'  # 模板ID
        name = "gerryluo"
        token = 'd0cd2d4f66584843cc9a5ba72b33279a'

        values = {'accid': accid, 'name': name, 'token': token}
        postData = urllib.urlencode(values)
        print postData
        postUrl = 'https://api.netease.im/nimserver/user/create.action'
        try:
            req = self.doPost(postUrl, postData)
            if 200 == req.getcode():
                res = req.read()
                print res
                # 成功返回{"code":200,"msg":"sendid","obj":8}
                # 主要的返回码200、315、403、413、414、500
                # 详情：http://dev.netease.im/docs?doc=server&#code状态表
            else:
                print req.getcode()

        except Exception, e:
            print e


if __name__ == '__main__':
    sendTest = SendMsgTest()
    sendTest.send()

