# coding: utf8

"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : 牌局逻辑定时器模块启动
"""

from django.core.management.base import BaseCommand
from mjango.timer_awake import run
from common.bridge import Bridge


class Command(BaseCommand):
    def handle(self, *args, **options):
        Bridge(pro_name='timer_server')
        run()

