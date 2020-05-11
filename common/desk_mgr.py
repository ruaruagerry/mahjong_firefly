# -*- coding: utf-8 -*-


class DeskMgr(object):

    rds = None
    key = None

    def __init__(self, rds, key):
        self.rds = rds
        self.key = key

    def incr_players(self, desk_id, delta=1):
        member = str(desk_id)
        # 先member，再score
        return self.rds.zincrby(self.key, member, delta)

    def get_player_num(self, score):
        player_num = score
        return player_num

    def add_desk(self, desk_id, players=0):
        member = str(desk_id)
        score = players
        return self.rds.zadd(self.key, score, member)

    def get_desk(self, desk_id):
        member = str(desk_id)
        score = self.rds.zscore(self.key, member)
        if score is None:
            return None

        return int(score)

    def remove_desks(self, *desk_id_list):
        member_list = [str(desk_id) for desk_id in desk_id_list]
        return self.rds.zrem(self.key, *member_list)

    def get_all_desks(self, order='asc'):
        fetch_func = self.rds.zrange if order == 'asc' else self.rds.zrevrange
        value_list = fetch_func(self.key, 0, -1,
                                withscores=True,
                                score_cast_func=int
                                )

        desk_list = []
        for member, score in value_list:
            players = score
            desk_id = int(member)
            desk_list.append((desk_id, players))

        return desk_list

    def remove_all_desks(self):
        return self.rds.delete(self.key)
