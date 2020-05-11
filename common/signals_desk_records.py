# -*- coding: utf-8 -*-
from django.dispatch import receiver
from common import mj_signals
import config
import time
from common.redis_fd import rds_tmp
from common.log import logger
import json


def push_desk_record_to_redis(key, model):
    if 'optime' not in model:
        model['optime'] = int(time.time())

    data = json.dumps(model)

    rds_tmp.rpush(key, data)
    # 一些不完整到数据将自动过期
    rds_tmp.expire(key, config.REDIS_KEY_DESK_RECORD_EXPIRE_TIME)


def register_signal_handlers():

    @receiver(mj_signals.mahjong_desk_start_play, weak=False)
    def stat_desk_active_start(sender, **kwargs):
        logger.debug('recv signal')
        desk = kwargs['desk']
        delta_card = kwargs['delta_card']

        user_info = dict()
        for player in desk.player_group.active_players:
            user = player.user
            user_info[str(player.uin)] = dict(
                nick=user.nick,
                portrait=user.portrait_path,
                cards=player.card_group.num_list,
                is_dealer=player.seatid == desk.dealer_seatid,
                is_master=desk.is_master(player.uin),
                client_ip=user.client_ip,
                seatid=player.seatid,
            )

        model = dict(
            source=config.STATISTIC_MAHJONG_DESK_GAME_START,
            uuid=desk.uuid,
            desk_id=desk.id,
            desk_round=desk.desk_round,
            desk_type=desk.type,
            desk_seat_limit=desk.seat_limit,
            desk_win_type=desk.win_type,
            desk_has_laizi=desk.has_laizi,
            desk_can_win_by_qidui=desk.can_win_by_qidui,
            desk_bird_num=desk.bird_num,
            desk_piaofen_max_num=desk.piaofen_max_num,
            desk_has_shanghuo=desk.has_shanghuo,
            desk_master_uin=desk.master_uin,
            user_info=user_info,
        )

        # push_stat(
        #     tb=config.STATISTIC_TB_DESK_ACTIVE,
        #     model=model,
        # )

        push_desk_record_to_redis(config.REDIS_KEY_DESK_RECORD_PREFIX + desk.uuid, model)

    @receiver(mj_signals.mahjong_desk_game_over, weak=False)
    def stat_game_over(sender, **kwargs):
        logger.debug('start_game_over start')

        desk = kwargs['desk']

        user_info = dict()

        # logger.debug('stat_game_over desk:%s', desk)
        # 下过注的玩家就要算进入,玩家可能已经站起了
        logger.debug('valid_players:%s', desk.player_group.valid_players)
        for player in desk.player_group.valid_players:
            logger.debug('stat_game_over valid_player:%s', player)
            user_info[str(player.uin)] = dict(
                uin=player.uin,
                role=player.role,
                chips=player.chips,
                round_win_chips=player.round_win_chips,
                round_chi_num=player.round_chi_num,
                round_peng_num=player.round_peng_num,
                round_gang_list=player.round_gang_list,
                round_hu_list=player.round_hu_list,
                round_win_list=player.round_win_list,
                total_chi_num=player.total_chi_num,
                total_peng_num=player.total_peng_num,
                total_gang_list=player.total_gang_list,
                total_hu_list=player.total_hu_list,
                total_win_list=player.total_win_list,
                piaofen=player.piaofen,
                shanghuo=player.shanghuo,
                bird_num=player.bird_num,
                cards=player.card_group.num_list,
                out_cards=player.card_group.num_out_card_list,
                op_list=player.op_list,
                over_chips_details=player.over_chips_detail,
                nick=player.user.nick,
                seatid=player.seatid,
                sex=player.user.sex,
                portrait=player.user.portrait_path,
            )

        model = dict(
            source=config.STATISTIC_MAHJONG_DESK_GAME_OVER,
            game_round=desk.desk_round - desk.desk_remain_round,
            desk_bird_card=desk.bird_card,
            one_game_round_index=desk.one_game_round_index,
            desk_over_time=desk.over_time,
            desk_winners=desk.winner_uin,
            user_info=user_info,
        )

        push_desk_record_to_redis(config.REDIS_KEY_DESK_RECORD_PREFIX + desk.uuid, model)
