# coding: utf8

"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : 牌桌内的所有玩家对象
"""

import config
import itertools
from common.log import logger


class PlayerGroup(object):
    players = None

    def __init__(self, fixed_size=0):
        super(PlayerGroup, self).__init__()

        self.players = [it for it in itertools.repeat(None, fixed_size)]

    def __repr__(self):
        return repr(self.players)

    def add_player(self, player, seat_id=None):
        if seat_id is None:
            for k, v in enumerate(self.players):
                if v is None:
                    # 说明这个位置可以
                    self.players[k] = player
                    player.seatid = k
                    return k
        else:
            # 指定坐在哪个位置
            seat_id %= len(self.players)
            if self.players[seat_id] is None:
                self.players[seat_id] = player
                player.seatid = seat_id
                return seat_id

        return -1

    def remove_player(self, player):
        if not player or player not in self.players:
            return

        index = self.players.index(player)
        if index < 0:
            return

        player.seatid = None
        self.players[index] = None

    def get_player_by_uin(self, uin):
        # logger.debug('players:%s', self.players)
        if not uin:
            return None

        for one in self.players:
            if one and one.uin == uin:
                return one

        return None

    def clear_players(self):
        for k, v in enumerate(self.players):
            if v:
                v.seatid = None
            self.players[k] = None

    @property
    def valid_players(self):
        """
        只要是非None，就可以
        """
        return filter(lambda x: x, self.players)

    # 已经都准备好了的人
    @property
    def sit_players(self):
        return filter(lambda x: x and x.status >= config.USER_STATE_READY, self.players)

    # 游戏状态下的人
    @property
    def active_players(self):
        return filter(lambda x: x and x.status in (config.USER_STATE_INGAME, config.USER_STATE_AFTER_GANG),
                      self.players)

    # 同意解散房间的人
    @property
    def agree_players(self):
        return filter(lambda x: x and x.delete_status == config.USER_STATE_AGREE_DELETE, self.players)

    # 拒绝解散房间的人
    @property
    def disagree_players(self):
        return filter(lambda x: x and x.delete_status == config.USER_STATE_DISAGREE_DELETE, self.players)




