# -*- coding: utf-8 -*-
from common.redis_fd import rds_tmp
import time
import json
from common import proto
import config
from common.firefly_utils import bridge_to_other_game
from common.bridge import Bridge
from common.log import timer_logger


def process():
    # timer_logger.debug('start process')
    now = int(time.time())
    # 超时的条目都在这里
    item_list = rds_tmp.zrangebyscore('mj_timer', 0, now, withscores=True)
    if not item_list:
        # bridge_to_other_game(proto.CMD_TIME_OUT_CHECK, "timer test")
        return

    for member, expire_time in item_list:
        # timer_logger.debug('member: %s, expire_time: %s', member, expire_time)
        try:
            timer_id, op_type = member.split('-')
        except:
            timer_id, op_type = member, 0

        # 把超时的定时器消息发过去
        request = json.dumps(dict(
            timer_id=timer_id,
            op_type=op_type,
            expire_time=expire_time,
        ))
        bridge_to_other_game(proto.CMD_TIME_OUT_CHECK, request)

    # *相当于就是unpack了
    rds_tmp.zrem('mj_timer', *(zip(*item_list)[0]))


def run():
    while 1:
        if Bridge().get_status():
            time.sleep(config.TIMER_CHECKER_INTERVAL)
            try:
                process()
            except KeyboardInterrupt:
                Bridge().close_connect()
                break
            except:
                timer_logger.error('exc occur.', exc_info=True)
                Bridge().close_connect()
                break
        else:
            Bridge().get_connect()
