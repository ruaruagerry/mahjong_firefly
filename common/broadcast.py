# -*- coding: utf-8 -*-
import datetime, time
from common import proto
from common.log import sche_logger
from common.mahjong_pb2 import EvtBroadCast
from common.firefly_utils import bridge_to_users
from common.redis_fd import rds
from common.mj_json_encode import json_encoder, json_decoder


class BroadcastInfo(object):
    b_id = None
    content = None
    start_time = None
    end_time = None
    frequency = None
    # 可用与否
    active = None

    def __init__(self, b_id=None, start_time=None, end_time=None, frequency=None, content=None, active=None):
        super(BroadcastInfo, self).__init__()
        self.b_id = b_id
        self.start_time = start_time
        self.end_time = end_time
        self.frequency = frequency
        self.content = content
        self.active = active

    @property
    def is_online(self):
        if not self.active or not self.start_time or not self.end_time :
            return False

        return self.start_time <= datetime.datetime.now() <= self.end_time

    @property
    def is_offline(self):
        return datetime.datetime.now() > self.end_time


class RedisBroadcastInfo(object):

    REDIS_CONTENT_KEY = 'broadcast_info_hash'

    @classmethod
    def load(cls, b_id):
        broad_info = rds.hget(cls.REDIS_CONTENT_KEY, b_id)
        if broad_info:
            return json_decoder(broad_info)
        else:
            return None

    @classmethod
    def save(cls, broad_info):
        rds.hset(cls.REDIS_CONTENT_KEY, broad_info.b_id, json_encoder(broad_info))

    @classmethod
    def is_exist(cls, b_id):
        return rds.hexists(cls.REDIS_CONTENT_KEY, b_id)

    @classmethod
    def save_broadcast_info(cls, start_time, end_time, frequency, content, b_id, active=True):
        b_id = int(time.time()) if not b_id else b_id

        broad_info = BroadcastInfo(
            b_id=b_id,
            start_time=start_time,
            end_time=end_time,
            frequency=frequency,
            content=content,
            active=active,
        )

        cls.save(broad_info)

        return broad_info

    @classmethod
    def broadcast(cls, uin, nick, content):
        evt = EvtBroadCast()
        evt.uin = uin
        evt.nick = nick
        evt.content = content

        evt = evt.SerializeToString()
        bridge_to_users(None, proto.CMD_EVENT_USER_BROADCAST, evt, broadcast=True)

    @classmethod
    def admin_broadcast(cls, content):
        admin_nick = u'系统广播'
        admin_uin = 1

        cls.broadcast(admin_uin, admin_nick, content)


class ScheduleBroadcast(RedisBroadcastInfo):
    """
    定时广播器
    """
    REDIS_SCHEDULE_KEY = 'broadcast_info_zset'
    FREQUENCY_UNIT = 60

    @classmethod
    def insert_broadcast(cls, broad_info):
        timestamp = int(time.time()) + (broad_info.frequency * cls.FREQUENCY_UNIT)
        rds.zadd(cls.REDIS_SCHEDULE_KEY, timestamp, broad_info.cid)

    @classmethod
    def get_broadcast_info_by_id(cls):
        for cid, _ in rds.zrangebyscore(cls.REDIS_SCHEDULE_KEY, 0, int(time.time()), withscores=True):
            yield cid

    @classmethod
    def remove_broadcast_by_id(cls, cid):
        rds.zrem(cls.REDIS_SCHEDULE_KEY, cid)

    @classmethod
    def broadcast_all(cls):
        for cid in cls.get_broadcast_info_by_id():
            broad_info = cls.load(cid)
            broad_info.begin_time = datetime.datetime.strptime(broad_info.begin_time, '%Y-%m-%d %H:%M:%S')
            broad_info.end_time = datetime.datetime.strptime(broad_info.end_time, '%Y-%m-%d %H:%M:%S')
            if broad_info:
                # 有效期就拿出来广播出去
                if broad_info.is_online:
                    cls.remove_broadcast_by_id(cid)
                    RedisBroadcastInfo.admin_broadcast(broad_info.content)
                    cls.insert_broadcast(broad_info)
                # 过期了就删掉
                if broad_info.is_exceed:
                    sche_logger.debug('delete broadcast')
                    cls.remove_broadcast_by_id(cid)
            else:
                sche_logger.critical('no broadcast but get it')