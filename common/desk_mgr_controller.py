# -*- coding: utf-8 -*-
import random
from common.mj_desk import MjDesk
from common.desk_mgr import DeskMgr
from common.redis_fd import rds_tmp
import config


class DeskMgrController(object):

    rds = None

    desk_mgr = None

    desk_class = None

    @classmethod
    def _alloc_desk_id(cls):
        # 修改房间号区间 100000-999999，随机生成
        plan_desk_id = random.randint(config.MIN_MAHJONG_DESK_ID, config.MAX_MAHJONG_DESK_ID)
        random_add = random.randint(config.MIN_MAHJONG_DESK_ID, config.MAX_MAHJONG_DESK_ID) / 100

        now_id = plan_desk_id + random_add
        if now_id > config.MAX_MAHJONG_DESK_ID:
            now_id /= 10

        return now_id

    def alloc_desk(self, **kwargs):
        desk_id = self._alloc_desk_id()
        desk = self.desk_class(desk_id, **kwargs)
        self.add_desk(desk.id, desk.exist_players_num)
        return desk

    def add_desk(self, desk_id, players_num):
        return self.desk_mgr.add_desk(desk_id, players_num)

    def remove_desk(self, *desk_id_list):
        return self.desk_mgr.remove_desks(*desk_id_list)


class MjDeskMgrController(DeskMgrController):

    desk_class = MjDesk

    rds = rds_tmp

    _desk_managers = {
        config.DESK_MANAGE_MJ: DeskMgr(rds, config.REDIS_KEY_DESK_MGR_MAHJONG),
    }

    desk_mgr = None

    desk_type = config.DESK_MANAGE_MJ

    def __init__(self):
        if self.desk_type not in self._desk_managers:
            raise ValueError('invalid desk type: %s', self.desk_type)
        # 获得桌子管理对象
        self.desk_mgr = self._desk_managers.get(self.desk_type)

    @classmethod
    def get_all_desks(cls):
        for desk_type, desk_mgr in cls._desk_managers.iteritems():
            for desk_list in desk_mgr.get_all_desks():
                yield desk_mgr, desk_type, desk_list

    def alloc_desk_id(self):
        desk_id = self._alloc_desk_id()
        # 如果id存在就再分配一个
        # 检查牌桌存在的待会看看
        while self.is_desk_exist(desk_id):
            desk_id = self._alloc_desk_id()

        if not self.is_desk_exist(desk_id):
            self.add_desk(desk_id, 0)

        return desk_id

    @classmethod
    def is_desk_exist(cls, desk_id):
        return cls.rds.exists(cls.desk_class.get_redis_key(desk_id))

    @classmethod
    def load_desk(cls, desk_id, lock_desk=True):
        desk = None

        if cls.is_desk_exist(desk_id):
            desk = cls.desk_class.load(desk_id, with_lock=lock_desk)

        return desk

    def get_desk_data(self, desk_id):
        return self.desk_mgr.get_desk(desk_id)

    def create_desk(self, desk_id, password=None, lock_desk=True, seat_limit=None, \
                    win_type=None, laizi=None, qidui=None, zhuaniao=None, piaofen=None,
                    shanghuo=None, type=None, user_id=None, card_num=0):
        desk = self.desk_class(desk_id, type, password, self.rds, seat_limit, \
                               win_type, laizi, qidui, zhuaniao, piaofen, shanghuo, user_id, card_num)
        if lock_desk:
            desk.lock()
        return desk

    def get_desk(self, desk_id, lock_desk=True):
        data = self.get_desk_data(desk_id)
        if not data:
            return None

        return self.load_desk(desk_id, lock_desk)

