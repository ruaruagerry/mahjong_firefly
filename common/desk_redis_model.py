# -*- coding: utf-8 -*-
from common.redis_fd import rds_tmp
from mj_json_encode import json_encoder, json_decoder
from common.log import logger


def _constructor(cls, lock, *args, **kwargs):
    obj = cls(*args, **kwargs)
    obj.lock_obj = lock
    return obj


class RdsDeskModel(object):

    id = None
    r_obj = None
    lock_obj = None

    @classmethod
    def create_lock(cls, id, r_obj=None):
        import config
        from redis.lock import LuaLock as Lock

        redis_key = 'lock_%s_%s' % (cls.__name__, id)
        return Lock(r_obj or rds_tmp, redis_key,
                    sleep=config.REDIS_LOCK_SLEEP,
                    timeout=config.REDIS_LOCK_TIMEOUT)

    @classmethod
    def get_redis_key(cls, id):
        # return '%s' % id
        raise NotImplementedError

    @classmethod
    def create(cls, id, r_obj, with_lock=False):
        from functools import partial

        lock_obj = cls.create_lock(id) if with_lock else None
        if lock_obj:
            lock_obj.acquire(blocking=True)
        return partial(
            _constructor,
            partial(cls, id=id, r_obj=r_obj),
            lock=lock_obj
        )

    @classmethod
    def load(cls, r_obj, id, with_lock=False):
        lock_obj = cls.create_lock(id) if with_lock else None
        if lock_obj:
            lock_obj.acquire(blocking=True)
            # logger.error('acquire lock for %s, id:%s', cls.__name__, id)

        ret_obj = json_decoder(r_obj.get(cls.get_redis_key(id)) or 'null')
        # logger.debug('ret_obj:%s', ret_obj)
        if ret_obj:
            ret_obj.r_obj, ret_obj.lock_obj = r_obj, lock_obj
        else:
            # logger.error("Couldn't load a %s that the id is %s", cls.__name__, id)
            lock_obj and lock_obj.release()
        return ret_obj

    def lock(self):
        self.lock_obj = self.create_lock(self.id)
        self.lock_obj.acquire(blocking=True)

    def unlock(self):
        # logger.error('release lock for %s, id:%s', self.__class__.__name__, self.id)
        self.lock_obj and self.lock_obj.release()
        self.lock_obj = None

    def save(self, r_obj=None):
        # return (r_obj or self.r_obj).set(self.get_redis_key(self.id), json.dumps(convert_to_dict(self)))
        return (r_obj or self.r_obj).set(self.get_redis_key(self.id), json_encoder(self))
