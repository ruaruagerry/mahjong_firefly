# coding: utf8
"""
扩展函数库
@name: common.py
@author: cbwfree
@create: 15/12/22 21:23
"""
import json
import hashlib
import random


def Jsonify(data):
    """
    构建web输出的JSON数据
    :param data:
    :return:
    """
    return str(ToUtf8(JsonStringify(data)))


def ToUtf8(data):
    """
    转换编码为utf8
    :param data:
    :return:
    """
    if isinstance(data, unicode):
        return data.decode("utf-8")
    return data


def JsonStringify(data):
    """
    序列化数据为JSON字符串
    :param data:
    :return:
    """
    return json.dumps(data, ensure_ascii=False, separators=(',',':'))


def JsonParse(b):
    """
    解析JSON字符串数据
    :param b:
    :return:
    """
    return json.loads(b)


def GetRandom(minNum, maxNum, step=1):
    """
    获取随机数
    :param minNum:
    :param maxNum:
    :return:
    """
    if minNum > maxNum:
        minNum, maxNum = maxNum, minNum
    if step > 1:
        return random.randrange(minNum, maxNum, step)
    return random.randint(minNum, maxNum)


def GetProbResult(limit, ratio=100):
    """
    获取概率结果
    :param limit:
    :param ratio:
    :return:
    """
    return GetRandom(0, ratio) < limit


def ChoiceRandom(sequence, size=1):
    """
    从list或tuple中随机取出一个或多个
    :param sequence:
    :param size:
    :return:
    """
    if size > 1:
        return random.sample(sequence, size)
    return random.choice(sequence)


def md5(s):
    """
    创建MD5值
    :param s:
    :return:
    """
    return hashlib.md5(s).hexdigest()