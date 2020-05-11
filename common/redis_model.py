# -*- coding: utf-8 -*-
import json


class RedisModel(object):

    ATTR_DICT = None
    KEY_PRE = None
    TTL = None

    id = None
    rds = None
    values = None

    def __init__(self, id, rds):
        self.id = id
        self.rds = rds

    def attach_values(self, values):
        self.values = values

    def update(self, params):
        if not params:
            return 0

        delta_params = dict(filter(lambda x: "__" in x[0], params.items()))
        normal_params = dict(filter(lambda x: "__" not in x[0] and x[1] is not None, params.items()))
        remove_params = dict(filter(lambda x: "__" not in x[0] and x[1] is None, params.items()))

        for p_k, p_v in delta_params.items():
            real_k = p_k.replace("__", "")

            val_type = self.ATTR_DICT[real_k].get("type") or (lambda x: x)
            real_v = val_type(p_v)

            if isinstance(real_v, int):
                self.rds.hincrby(self.redis_key, real_k, real_v)
            elif isinstance(real_v, float):
                self.rds.hincrbyfloat(self.redis_key, real_k, real_v)
            else:
                raise TypeError("type(v) should be float/int. not %s" % str(val_type))

        if normal_params:
            self.rds.hmset(self.redis_key, normal_params)

        if remove_params:
            self.rds.hdel(self.redis_key, *remove_params.keys())

        if self.TTL is not None:
            self.rds.expire(self.redis_key, self.TTL)

        self._reload_from_redis()

        return len(params)

    def __getattr__(self, item):
        if item in self.ATTR_DICT.keys():
            if self.values is None:
                # 说明是redis的数据
                self._reload_from_redis()

            # 万一取不到，配置默认值
            default_val = self.ATTR_DICT[item].get('default', None)
            return self.values.get(item, default_val)
        else:
            raise AttributeError('has not attr: %s' % item)

    def __repr__(self):
        tmp_dict = dict(
            id=self.id,
        )
        if self.values is not None:
            tmp_dict.update(self.values)
        return repr(tmp_dict)

    def __unicode__(self):
        return repr(self).decode('utf8')

    def _reload_from_redis(self):
        org_values = self.rds.hgetall(self.redis_key)

        self.values = dict()

        for k, v in org_values.items():
            if k not in self.ATTR_DICT:
                continue

            val_type = self.ATTR_DICT[k].get("type") or (lambda x: x)

            # if issubclass(val_type, CustomType):
            #     self.values[k] = val_type.decode(v)
            # else:
            self.values[k] = val_type(v)

    @property
    def redis_key(self):
        return "%s%s" % (self.KEY_PRE, self.id)


class RedisJsonModel(object):

    ATTR_DICT = None
    KEY_PRE = None
    TTL = None

    id = None
    rds = None
    values = None

    def __init__(self, id, rds):
        self.id = id
        self.rds = rds

    def attach_values(self, values):
        self.values = values

    def update(self, params):

        if not params:
            return 0

        for p_k in params:
            assert "__" not in p_k, "not support update with delta, k: %s" % p_k

        if self.values is None:
            self._reload_from_redis()

        self.values.update(params)

        self.rds.set(self.redis_key, json.dumps(self.values))

        if self.TTL is not None:
            self.rds.expire(self.redis_key, self.TTL)

        return len(params)

    def has_data(self, item):
        if item in self.ATTR_DICT.keys():
            if self.values is None:
                # 说明是redis的数据
                self._reload_from_redis()

            return item in self.values
        else:
            return False

    def __getattr__(self, item):
        if item in self.ATTR_DICT.keys():
            if self.values is None:
                # 说明是redis的数据
                self._reload_from_redis()

            # 万一取不到，配置默认值
            default_val = self.ATTR_DICT[item].get('default', None)
            return self.values.get(item, default_val)
        else:
            raise AttributeError('has not attr: %s' % item)

    def __repr__(self):
        tmp_dict = dict(
            id=self.id,
        )
        if self.values is not None:
            tmp_dict.update(self.values)
        return repr(tmp_dict)

    def __unicode__(self):
        return repr(self).decode('utf8')

    def _reload_from_redis(self):
        str_data = self.rds.get(self.redis_key)
        self.values = self.parse_data(str_data)

    @classmethod
    def parse_data(cls, str_data):
        if not str_data:
            return dict()

        org_values = json.loads(str_data)

        return dict(filter(lambda x: x[0] in cls.ATTR_DICT, org_values.items()))

    @property
    def redis_key(self):
        return "%s%s" % (self.KEY_PRE, self.id)
