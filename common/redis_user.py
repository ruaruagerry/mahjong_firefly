# -*- coding: utf-8 -*-
from django.db.models import F
from django.forms.models import model_to_dict

import config
from common.models import User
from common.redis_model import RedisJsonModel, RedisModel
from common.redis_fd import rds, rds_tmp


# Mem和Flash只取其一，这两者是互不共存的，也就是说一个key值不可能同时在mem和falsh中一起出现
# Freq只是方便使用，放到rds中去io的

class MemUser(RedisModel):
    """
    永不会过期用户的数据
    """
    ATTR_DICT = dict(
        play_times=dict(type=int, default=0,),
        # desk_id放在这里来，不让它过期，不然就断线重连回不来了
        desk_id=dict(type=int, default=0,),
        user_inviter=dict(type=int, default=0,),
        status=dict(type=int, default=0,),
    )

    KEY_PRE = "mem_user:"
    TTL = None


class FlashUser(RedisJsonModel):
    """
    闪存数据，过期时间5分钟
    """
    ATTR_DICT = dict(
        # status=dict(default=0,),
    )

    KEY_PRE = "flash_user:"
    TTL = 5 * 60

    @classmethod
    def batch_load_values(cls, id_list):
        """
        批量获取values
        :param id_list:
        :return:
        """
        key_list = ['%s%s' % (cls.KEY_PRE, id) for id in id_list]
        result = rds_tmp.mget(key_list)

        values_list = [cls.parse_data(str_data) for str_data in result]

        return dict(zip(id_list, values_list))


class FreqUser(RedisJsonModel):
    """
    频繁使用的数据，过期时间一周
    """
    ATTR_DICT = dict(
        portrait_path=dict(),
        nick=dict(),
        sex=dict(),
        channel=dict(),
        version=dict(),
        os=dict(),
        card=dict(),
        client_ip=dict(),
    )

    KEY_PRE = "freq_user:"
    TTL = 60 * 60 * 24 * 7

    @classmethod
    def batch_load_values(cls, id_list):
        key_list = ['%s%s' % (cls.KEY_PRE, id) for id in id_list]
        result = rds_tmp.mget(key_list)

        values_list = [cls.parse_data(str_data) for str_data in result]

        return dict(zip(id_list, values_list))


class RedisUser(object):

    id = None
    _mem_user = None
    _flash_user = None
    _freq_user = None
    _db_user = None

    def __init__(self, id):
        self.id = id
        self._mem_user = MemUser(self.id, rds)
        self._flash_user = FlashUser(self.id, rds_tmp)
        self._freq_user = FreqUser(self.id, rds_tmp)

    def get_db_user(self):
        return self._db_user

    def get_mem_user(self):
        return self._mem_user

    def get_flash_user(self):
        return self._flash_user

    def get_freq_user(self):
        return self._freq_user

    def validate(self):
        if self._db_user is None:
            self._reload_from_db()

        return self._db_user is not None

    def attach_mem_user(self, mem_user):
        assert self.id == mem_user.id, 'mem <<< %s and %s >>> not equal' % (self.id, mem_user.id)
        self._mem_user = mem_user

    def attach_flash_user(self, flash_user):
        assert self.id == flash_user.id, 'flash <<< %s and %s >>> not equal' % (self.id, flash_user.id)
        self._flash_user = flash_user

    def attach_freq_user(self, freq_user):
        assert self.id == freq_user.id, 'frequency <<< %s and %s >>> not equal' % (self.id, freq_user.id)
        self._freq_user = freq_user

    def attach_db_user(self, db_user):
        if db_user is not None:
            assert self.id == db_user.id, 'db <<< %s and %s >>> not equal' % (self.id, db_user.id)
        self._db_user = db_user

    def update(self, params):
        mem_params = dict()
        flash_params = dict()
        freq_params = dict()
        db_params = dict()

        for p_k, p_v in params.items():
            real_k = p_k.replace("__", "")

            if real_k in self._mem_user.ATTR_DICT:
                mem_params[p_k] = p_v
            elif real_k in self._flash_user.ATTR_DICT:
                flash_params[p_k] = p_v
            else:
                db_params[p_k] = p_v

            if real_k in self._freq_user.ATTR_DICT:
                freq_params[p_k] = p_v

        affect_rows = 0
        affect_rows += self._update_db(db_params)

        if freq_params:
            affect_rows += self._sync_db_to_freq_user()

        affect_rows += self._mem_user.update(mem_params)
        affect_rows += self._flash_user.update(flash_params)

        return affect_rows

    def _update_db(self, params):
        if not params:
            return 0

        update_kwargs = dict()

        card_delta = 0

        for p_k, p_v in params.items():
            if "__" in p_k:
                is_delta = True
            else:
                is_delta = False

            real_k = p_k.replace("__", "")
            if real_k == 'card':
                card_delta = p_v

            if is_delta:
                update_kwargs[real_k] = F(real_k) + p_v
            else:
                update_kwargs[real_k] = p_v

        filter_kwargs = dict(pk=self.id)
        if card_delta < 0:
            filter_kwargs['card__gte'] = abs(card_delta)

        affect_rows = User.objects.filter(**filter_kwargs).update(**update_kwargs)

        self._reload_from_db()

        return affect_rows

    def __getattr__(self, item):
        if item in self._mem_user.ATTR_DICT:
            return getattr(self._mem_user, item)
        elif item in self._flash_user.ATTR_DICT:
            return getattr(self._flash_user, item)
        elif item in self._freq_user.ATTR_DICT:
            if not self._freq_user.has_data(item):
                self._sync_db_to_freq_user()
            return getattr(self._freq_user, item)
        else:
            if self._db_user is None:
                self._reload_from_db()

            return getattr(self._db_user, item, None)

    def __repr__(self):
        tmp_dict = dict(
            id=self.id,
        )
        if self._mem_user.values is not None:
            tmp_dict.update(self._mem_user.values)
        if self._flash_user.values is not None:
            tmp_dict.update(self._flash_user.values)
        if self._db_user is not None:
            tmp_dict.update(model_to_dict(self._db_user))
        return repr(tmp_dict)

    def __unicode__(self):
        return repr(self).decode('utf8')

    def _reload_from_db(self):
        self._db_user = User.objects.filter(pk=self.id).first()

    @property
    def uin(self):
        return int(self.id)

    def _sync_db_to_freq_user(self):
        if not self._db_user:
            self._reload_from_db()

        if not self._db_user:
            raise Exception('not find db_user: %s in mysql', self.id)

        params = dict()
        for attr_name in self._freq_user.ATTR_DICT:
            attr_value = getattr(self._db_user, attr_name)
            params[attr_name] = attr_value

        return self._freq_user.update(params)

