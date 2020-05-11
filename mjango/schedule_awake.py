#!/usr/bin/env python
# coding: utf8

"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : 自定义定时器
"""

import time
from common.broadcast import ScheduleBroadcast
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED
from common.bus_func import module_register
from common.bridge import Bridge
from common.log import sche_logger


job = BackgroundScheduler()


def err_listener(ev):
    if ev.exception:
        sche_logger.exception('%s error.', str(ev.job))
    else:
        sche_logger.info('%s miss', str(ev.job))


@job.scheduled_job('interval', seconds=1)
def schedule_broadcast_info():
    ScheduleBroadcast.broadcast_all()
    # OK测试通过
    # logger.debug('hello')


def run():
    # 注册module
    module_register()

    job.add_listener(err_listener, EVENT_JOB_ERROR | EVENT_JOB_MISSED)
    job.start()

    while 1:
        # 应该会有性能问题，先写着，到时候看看
        if Bridge().get_status():
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                Bridge().close_connect()
                break
            except:
                sche_logger.error('error\n', exc_info=True)
                Bridge().close_connect()
                break
        else:
            Bridge().get_connect()


