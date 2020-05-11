# -*- coding: utf-8 -*-
from redis_fd import rds_tmp
import time
import config
from common.bus_func import count_costs
from log import logger


class Timer(object):

    def __init__(self, t, i, op):
        self.type = t
        self.id = i
        self.op_type = op

    @classmethod
    def redis_set(cls, t, m):
        logger.debug('member: %s, expire_time: %s', m, t)
        rds_tmp.zadd('mj_timer', t, m)

    @classmethod
    def get_member(cls, t, i, op):
        return '%s:%s-%s' % (t, i, op)

    def set_time(self, t):
        self.redis_set(t, self.member)

    @property
    def member(self):
        return self.get_member(self.type, self.id, self.op_type)

    @count_costs(config.COUNT_COSTS_TIME)
    def start_timer(self, delay, caller=None):
        if caller:
            logger.debug("caller: %s", caller)
        score = int(time.time()) + delay
        self.set_time(score)
        return score

    @count_costs(config.COUNT_COSTS_TIME)
    def stop_timer(self):
        rds_tmp.zrem('mj_timer', self.member)
        logger.debug('member: %s', self.member)
