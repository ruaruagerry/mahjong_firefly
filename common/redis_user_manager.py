# -*- coding: utf-8 -*-

from redis_user import RedisUser, FlashUser, FreqUser
from common.models import User


def singleton(cls, *args, **kw):
    instances = {}
    def _singleton():
        if cls not in instances:
            instances[cls] = cls(*args, **kw)
        return instances[cls]
    return _singleton


# 那就单例模式咯，总可以吧
@singleton
class RedisUserMgr(object):
    redis_users = None
    cached = None

    def __init__(self, cached=False):
        self.redis_users = dict()
        self.cached = cached

    def get_user(self, user_id):
        user = self.redis_users.get(user_id, None)
        if user is None:
            user = RedisUser(user_id)
            if self.cached:
                self.redis_users[user_id] = user

        return user

    def get_users(self, user_list, load_db_user=False, load_flash_user=False, load_freq_user=False):
        result = dict()
        from_db_user_id_list = []
        from_flash_user_id_list = []
        from_freq_user_id_list = []

        for user_id in user_list:
            user = self.get_user(user_id)
            result[user_id] = user

            # 先从已有的读取
            if load_db_user and user.get_db_user() is None:
                from_db_user_id_list.append(user.id)

            if load_flash_user and user.get_flash_user().values is None:
                from_flash_user_id_list.append(user.id)

            if load_freq_user and user.get_freq_user().values is None:
                from_freq_user_id_list.append(user.id)

        if from_db_user_id_list:
            db_users = User.objects.filter(id__in=from_db_user_id_list)

            for db_user in db_users:
                redis_users = self.get_user(db_user.id)
                redis_users.attach_db_user(db_user)

        if from_flash_user_id_list:
            flash_users = FlashUser.batch_load_values(from_flash_user_id_list)

            for id, values in flash_users.items():
                redis_users = self.get_user(id)
                redis_users.get_flash_user().attach_values(values)

        if from_freq_user_id_list:
            freq_users = FreqUser.batch_load_values(from_freq_user_id_list)

            for id, values in freq_users.items():
                redis_users = self.get_user(id)
                redis_users.get_freq_user().attach_values(values)

        return result

    def clear(self):
        self.redis_users = dict()
