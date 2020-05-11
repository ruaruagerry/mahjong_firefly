# -*- coding: utf-8 -*-

"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : 统计相关的信号，注意：每个进程内的信号都是独立的，每个进程拥有自己的一份信号拷贝
           信号可用connect方法和receiver装饰器加入到监听集，可在receivers属性里面打印出当前信号监听的方法
"""

from django.dispatch import Signal

# 游戏开始
mahjong_desk_start_play = Signal(providing_args=["desk", "delta_card"], use_caching=True)

# 牌桌游戏结束
mahjong_desk_game_over = Signal(providing_args=["desk"], use_caching=True)
