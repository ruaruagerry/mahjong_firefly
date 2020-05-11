# -*- coding: utf-8 -*-

"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : 每一张牌型的定义
"""


class Card(object):

    num = 0

    def __init__(self, num=0):
        # [-7, 26]
        # 先进行必要的初始化
        super(Card, self).__init__()
        self.num = 0

        # 然后再赋值
        self.num = num

    def __cmp__(self, other):
        if self.num == other:
            return 0
        elif self.num > other:
            return 1
        else:
            return -1

    @property
    def point(self):
        # [1, 9]
        if self.num >= 0:
            return self.num % 9 + 1
        else:
            return 0

    @property
    def type(self):
        # -7东 -6南 -5西 -4北 -3中 -2发 -1白 0万 1筒 2条
        if self.num >= 0:
            return self.num / 9
        else:
            return self.num

    # 一个对象的打印字符串
    def __repr__(self):
        return '%s:%s' % (self.point, self.type)

    @property
    def human_str(self):
        if self.type == -7:
            return u'东风'
        elif self.type == -6:
            return u'南风'
        elif self.type == -5:
            return u'西风'
        elif self.type == -4:
            return u'北风'
        elif self.type == -3:
            return u'红中'
        elif self.type == -2:
            return u'发财'
        elif self.type == -1:
            return u'白板'
        elif self.type == 0:
            return u'%s万' % self.point
        elif self.type == 1:
            return u'%s筒' % self.point
        elif self.type == 2:
            return u'%s条' % self.point