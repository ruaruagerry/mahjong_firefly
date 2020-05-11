# -*- coding: utf-8 -*-
import config
from common.desk_redis_model import RdsDeskModel
from common.redis_fd import rds_tmp


class BaseDesk(RdsDeskModel):

    def __init__(self, id=None):
        super(BaseDesk, self).__init__()

    @classmethod
    def create_lock(cls, id, r_obj=None):
        """
        创建一个假锁，这样desk的锁的代码不用改，但是其实已经没有锁了
        :param id:
        :param r_obj:
        :return:
        """
        class FakeLock(object):
            """
            模拟一个假锁
            """

            def acquire(self, *args, **kwargs):
                # logger.error('fake acquire')
                pass

            def release(self, *args, **kwargs):
                # logger.error('fake release')
                pass

        return FakeLock()

    @classmethod
    def get_redis_key(cls, id):
        return 'r_desk:%s' % id

    @classmethod
    def get_desk_redis_key(cls, desk_id):
        return cls.get_redis_key(desk_id)

    @classmethod
    def update_expire(cls, desk_id, timeout=config.HEARTBEAT_MAX_INTERVAL, r_obj=None):
        (r_obj or rds_tmp).expire(cls.get_desk_redis_key(desk_id), timeout)

    def save(self, *args, **kwargs):
        """
        重写保存
        :return:
        """
        # 锁还是先放在这里
        return super(BaseDesk, self).save(*args, **kwargs)

