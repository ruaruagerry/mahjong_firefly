# coding: utf8

"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : 定时器任务模块启动
"""

from django.core.management.base import BaseCommand
from mjango.schedule_awake import run
from common.bridge import Bridge


class Command(BaseCommand):
    def handle(self, *args, **options):
        Bridge(pro_name='schedule_server')
        run()

