# -*- coding: utf-8 -*-
import copy
import functools
import random
import time, datetime
from common.base_desk import BaseDesk
import config
from card import Card
from card_group import CardGroup
from player_group import PlayerGroup
from player import Player
from common.log import logger
from common import proto
from common.mahjong_pb2 import EvtUserExit, GameInfoEvt, EvtGameOver, GameEnterDeskRsp
from common.redis_fd import rds_tmp
import uuid
import hashlib
import error_contrast
from common.redis_timer import Timer
from common.firefly_utils import write_to_users
from common.bus_func import fill_user_enter_desk_info, one_round_over_checker, celery_delay, user_room_card_notify, \
                            right_turn_required
import mj_signals
from common.tasks import parse_desk_record_to_db
from common.redis_user_manager import RedisUserMgr


DEBUG_LOG = True


def save_later(func):
    @functools.wraps(func)
    def func_wrapper(desk, *args, **kwargs):
        desk.need_save = True
        return func(desk, *args, **kwargs)
    return func_wrapper


# 真是恶心，什么都喜欢封一下，明明直接object就能搞定，硬是要拉上django Fiel
class MjDesk(BaseDesk):
    """
    桌子
    """
    # 为了防止删除后又被重新保存回去，用一个标志来标记一下
    deleted = None
    need_save = False
    # 是否把restore_to_group放到unlock后执行
    _need_restore = False
    # 函数内直接调用restore_to_group
    restore_later = False
    timeout_info = {}
    id = 0
    player_group = None
    share_cards = []  # 公共牌，一开始配牌的时候就分配好，这样想作弊才可能
    bird_card = []

    status = 0
    seat_limit = 0

    # 投票解散牌桌时用来保存桌子之前的状态，用于恢复桌子
    pre_status = None

    current_uin = -1

    # 庄的位置，要一直++即可
    # 这是他妈的谁写的，真的是蠢，要着干嘛？注销掉
    # dealer_index = Field(default=0, null=True)
    # 现在dealer开局后是不会变的
    dealer_seatid = -1

    # 一局游戏中的第几轮，看看多长时间内解决一局的战斗
    one_game_round_index = 1

    # desk 类型： 万载：1 转转：2
    # 转转麻将可以胡十三烂么，早上起来看看
    type = 0

    # 房间密码
    password = None

    # 房间类型 我这里没用到，不用它了
    # room_type = config.ROOM_TYPE_MJ_WZ

    # 赢牌类型： 1 点炮 2 自摸
    win_type = 1
    # 红中癞子
    has_laizi = False
    # 可胡七对
    can_win_by_qidui = True
    # 抓鸟
    bird_num = 0
    # 飘分上限，客户端会默认传2进来
    piaofen_max_num = 0
    # 是否具备上火属性
    has_shanghuo = False

    # 一局牌的唯一标志
    uuid = 0

    # 剩余公共牌数目
    share_cards_len = 0

    # 牌桌内需要用来计算的牌，要么是其它人打的，要么是自己叫的
    extend_card = None
    # 叫牌标志位
    is_jiaopai = False
    # 保存出牌人的uin，为空代表是自己叫的牌，传下去的时候记得传给客户端上一个玩家的状态
    # 如果上个玩家的状态是擦杠或者是杠牌，那就可以平胡，否则就不能平胡
    # 擦杠后，需要判定一下其它玩家能不能胡牌
    send_card_uin = 0

    # 保存预备可以赢的人的uin
    can_win_list = {}
    process_hu_counts = 0
    winner_uin = []

    # 添加一个第二顺位的操作列表，用于Pass的判断，主要防止胡牌操作被Pass后，其它的人不能碰吃杠，那就不好了
    # 废弃掉
    # can_op_without_hu = Field(default=dict())
    # 叫牌的人
    recv_card_uin = 0

    # 结算番数倍数
    calculate_multi = 1

    # 请求解散牌桌的人
    apply_uin = 0

    # 结算时间
    over_time = 0

    # 牌局开始时间
    begin_timestamp = None
    # 桌子的最大局数
    desk_round = None
    # 房主uin
    master_uin = 0
    # 是否可以删除桌子
    # 主要处理有些请求创建了房间,但是玩家并没有坐下,而是在下一个请求才坐下
    # 这时桌子里面没人,保存桌子时桌子就会被删除
    can_delete = False
    # 牌桌内的第几局游戏，根据这个来算房卡吧
    desk_remain_round = 0
    # 已经用掉的房卡数
    used_card = 0

    @property
    def desk_name(self):
        return 'd%s' % self.id

    @classmethod
    def load(cls, desk_id, with_lock=False, r_obj=None):
        # return BaseDesk.load(r_obj or rds_tmp, desk_id, with_lock=with_lock)
        desk = BaseDesk.load(r_obj or rds_tmp, desk_id, with_lock=with_lock)
        if desk and desk.type not in [config.DESK_TYPE_MJ_WZ, config.DESK_TYPE_MJ_ZZ]:
            raise Exception('Invalid desk_type %s, desk_id %s' % (desk.type, desk_id))
        return desk

    def save(self, r_obj=None, force_save=False):
        if self.deleted and not force_save:
            return

        # try:
        #     while len(self.player_group.viewers) > config.MAX_VIEWER_NUM:
        #         self.user_exit(self.player_group.viewers[-1].uin)
        # except Exception, e:
        #     logger.critical(e.message, exc_info=True)

        ret = super(MjDesk, self).save(r_obj or self.r_obj)
        if not ret:
            logger.critical('save desk %s into redis failed!!', self.id)
            logger.error(self)
        self.update_expire(self.id, r_obj=r_obj or self.r_obj, timeout=config.MJ_DESK_TIMEOUT_SEC)
        self.need_save = False

    @save_later
    def handle_timeout(self, type):
        self.timeout_info.pop(type, None)

        handler = dict(
            game_start=self.check_to_start_play,
            count_down=self.on_count_down,
        ).get(type, lambda x: self)

        return handler()

    @property
    def game_start_timeout_mgr(self):
        return self.get_timer('game_start')

    @property
    def desk_count_down_mgr(self):
        return self.get_timer('count_down')

    def get_timer(self, op_type):
        return Timer('mj_desk', self.id, op_type)

    def __init__(self, id=None, type=None, password=None, r_obj=rds_tmp, seat_limit=None, \
                 win_type=None, laizi=False, qidui=True, zhuaniao=None, piaofen=None, shanghuo=None,
                 user_id=None, card_num=0):
        # 先是必要的初始化
        super(MjDesk, self).__init__(id=id)
        self.deleted = None
        self.need_save = False
        self._need_restore = False
        self.restore_later = False
        self.timeout_info = {}
        self.id = 0
        self.player_group = None
        self.share_cards = []  # 公共牌，一开始配牌的时候就分配好，这样想作弊才可能
        self.bird_card = []
        self.status = 0
        self.seat_limit = 0
        self.pre_status = None
        self.current_uin = -1
        self.dealer_seatid = -1
        self.one_game_round_index = 1
        self.type = 0
        self.password = None
        self.win_type = 1
        self.has_laizi = False
        self.can_win_by_qidui = True
        self.bird_num = 0
        self.piaofen_max_num = 0
        self.has_shanghuo = False
        self.uuid = 0
        self.share_cards_len = 0
        self.extend_card = None
        self.is_jiaopai = False
        self.send_card_uin = 0
        self.can_win_list = {}
        self.process_hu_counts = 0
        self.winner_uin = []
        self.recv_card_uin = 0
        self.calculate_multi = 1
        self.apply_uin = 0
        self.over_time = 0
        self.begin_timestamp = None
        self.desk_round = None
        self.master_uin = 0
        self.can_delete = False
        self.desk_remain_round = 0
        self.used_card = 0

        # 然后再赋值
        self.uuid = uuid.uuid4().hex
        self.timeout_info = dict()
        self.r_obj = r_obj
        # 设置桌子类型
        self.type = config.DESK_TYPE_MJ_WZ
        if type is not None:
            self.type = type

        # 设置房间密码
        self.password = password
        # 统一使用desk来创建desk
        if id:
            self.id = id
            self.seat_limit = seat_limit
            self.win_type = win_type
            self.has_laizi = laizi
            self.can_win_by_qidui = qidui
            self.bird_num = zhuaniao
            self.piaofen_max_num = piaofen
            self.has_shanghuo = shanghuo
            self.player_group = PlayerGroup(self.seat_limit)
            self.reset()
        else:
            self.player_group = PlayerGroup()

        self.begin_timestamp = int(time.time())
        self.master_uin = user_id
        self.can_delete = False
        self.used_card = card_num
        if self.type == config.DESK_TYPE_MJ_WZ:
            self.desk_round = card_num * config.ONE_ROOM_CARD_NUM_WZ
            self.desk_remain_round = card_num * config.ONE_ROOM_CARD_NUM_WZ
        elif self.type == config.DESK_TYPE_MJ_ZZ:
            self.desk_round = card_num * config.ONE_ROOM_CARD_NUM_ZZ
            self.desk_remain_round = card_num * config.ONE_ROOM_CARD_NUM_ZZ

    def delete(self, r_obj=None):
        self.deleted = True
        (r_obj or self.r_obj).delete(self.get_desk_redis_key(self.id))

    def unlock(self):
        if self.need_save:
            if self.can_delete_desk():
                self.delete()
            else:
                self.save()

        try:
            super(MjDesk, self).unlock()
        except Exception, e:
            logger.critical("%s\n", e.message, exc_info=True)

        self._need_restore and self.restore_to_group()

    def is_master(self, uin):
        return uin == self.master_uin

    @property
    def current_player(self):
        return self.player_group.get_player_by_uin(self.current_uin)

    @current_player.setter
    def current_player(self, player):
        self.current_uin = player.uin if player else -1

    @property
    def send_card_player(self):
        return self.player_group.get_player_by_uin(self.send_card_uin)

    @property
    def master_player(self):
        return self.player_group.get_player_by_uin(self.master_uin)

    def reset(self, desk_game_reset=True, broadcast_over=False):
        if broadcast_over:
            if desk_game_reset:
                self.dealer_seatid = -1
                if 'game_start' in self.timeout_info:
                    self.game_start_timeout_mgr.stop_timer()
                if 'count_down' in self.timeout_info:
                    self.desk_count_down_mgr.stop_timer()
                self.timeout_info = dict()
                self.status = config.GAME_STATE_WAIT_DELETE
            else:
                self.status = config.GAME_STATE_READY

            self.current_player = None
            self.share_cards = []
            self.bird_card = []
            self.share_cards_len = 0

            self.winner_uin = []
            self.process_hu_counts = 0
            self.one_game_round_index = 0
            self.over_time = 0

        if self.player_group:
            for player in self.player_group.valid_players:
                # 重置玩家数据
                if desk_game_reset:
                    player.re_init_for_desk(broadcast_over=broadcast_over)
                else:
                    player.re_init_for_game(broadcast_over=broadcast_over)

    def release(self):
        """
        释放
        """
        self.player_group.clear_players()
        self.game_start_timeout_mgr.stop_timer()
        self.desk_count_down_mgr.stop_timer()
        self.timeout_info = dict()

    def next_one(self):
        # prev_player = self.current_player if self.current_player else self.dealer

        # current_player = self.current_player
        # if current_player:
        #     current_player.clear_bit(current_player.delay_op_bit)

        current_seatid = self.current_player.seatid if self.current_player else self.dealer_seatid

        for idx in range(current_seatid+1, current_seatid + len(self.player_group.valid_players)):
            seatid = idx % len(self.player_group.valid_players)
            player = self.player_group.valid_players[seatid]
            # 要找到能下注的
            if not player:
                continue

            found = True

            # if current_seatid == self.dealer_seatid and not self.current_player:
                # 一定要加上判断current_player，否则两个人玩的时候，就结束不了了
                # found = True

            if found:
                self.current_player = player
                # self.monitor_player_op_timeout()
                return self.current_player

        self.current_player = None
        # self.clear_player_op_timeout()
        return None

    # 填充通用信息
    @classmethod
    def adapt_game_user_info_list(cls, evt, player_info_list):
        if not hasattr(evt, 'users'):
            return

        # 先清除
        evt.ClearField('users')

        for user_info in player_info_list:
            evt_user_info = evt.users.add()

            evt_user_info.seatid = user_info.get('seatid')
            evt_user_info.status = user_info.get('status')
            evt_user_info.uin = user_info.get('uin')
            evt_user_info.nick = user_info.get('nick')
            evt_user_info.sex = user_info.get('sex')
            evt_user_info.portrait = user_info.get('portrait')
            evt_user_info.is_master = user_info.get('is_master')
            evt_user_info.shanghuo = user_info.get('shanghuo')
            evt_user_info.piaofen = user_info.get('piaofen')
            evt_user_info.ip = user_info.get('ip')

    def adapt_game_round_info(self, evt, uin):
        if not hasattr(evt, 'users'):
            return

        # 先清除
        evt.ClearField('users')

        for player in self.player_group.active_players:
            if player.uin == uin:
                evt.deskid = player.desk_id
                evt.next_uin = self.current_uin
                evt.max_round = self.desk_round
                evt.cards.extend(player.card_group.num_list)
                evt.dealer_seatid = self.dealer_seatid
                evt.share_cards_len = self.share_cards_len
                evt.game_round = self.one_game_round_index
                evt.my_option.op_chi = player.op_chi
                evt.my_option.op_peng = player.op_peng
                evt.my_option.op_gang = player.op_gang
                evt.my_option.op_hu = player.op_hu
                evt.my_option.need_wait = player.need_wait
                if player.op_type and player.op_type[0]:
                    evt.my_option.chi_cards.extend(player.op_type[0])
                    evt.my_option.chi_cards.extend([self.extend_card])
                evt.status = self.status
                if not self.send_card_uin:
                    evt.recv_card_uin = self.recv_card_uin
                evt.desk_remain_round = self.desk_remain_round
                evt.seat_num = self.seat_limit

            evt_user_info = evt.users.add()
            evt_user_info.uin = player.uin
            evt_user_info.card_len = player.card_len
            evt_user_info.out_cards.extend(player.card_group.num_out_card_list)
            evt_user_info.discard.extend(player.card_group.num_discard_list)
            evt_user_info.seatid = player.seatid
            evt_user_info.status = player.status
            evt_user_info.op_list.extend(player.op_list)
            evt_user_info.chips = player.chips

    def broadcast_game_over_info(self, game_over=False, over_reason=config.GAME_OVER_NORMAL):
        # 发送结束广播
        evt = EvtGameOver()
        evt.winners.extend(self.winner_uin)
        evt.deskid = self.id
        evt.status = self.status
        evt.remain_round_num = self.desk_remain_round
        evt.bird_card.extend(self.bird_card)
        evt.type = self.type
        evt.seat_limit = self.seat_limit
        evt.win_type = self.win_type
        evt.extra_type.hongzhong = self.has_laizi
        evt.extra_type.qidui = self.can_win_by_qidui
        evt.extra_type.zhuaniao = self.bird_num
        evt.extra_type.piaofen = self.piaofen_max_num
        evt.extra_type.shanghuo = self.has_shanghuo
        evt.last_round = game_over
        evt.over_time = self.over_time
        # 是否是牌局中结束的标识
        evt.over_reason = over_reason

        for in_player in self.player_group.valid_players:
            evt_user_info = evt.result.add()
            evt_user_info.uin = in_player.uin
            evt_user_info.chips = in_player.chips
            evt_user_info.round_chi_num = in_player.round_chi_num
            evt_user_info.round_peng_num = in_player.round_peng_num
            evt_user_info.round_gang_list.extend(in_player.round_gang_list)
            evt_user_info.round_hu_list.extend(in_player.round_hu_list)
            evt_user_info.round_win_list.extend(in_player.round_win_list)
            evt_user_info.status = in_player.status
            evt_user_info.piaofen = in_player.piaofen
            evt_user_info.shanghuo = in_player.shanghuo
            evt_user_info.bird_num = in_player.bird_num
            if self.pre_status != config.GAME_STATE_READY:
                evt_user_info.cards.extend(in_player.card_group.num_list)
                evt_user_info.out_cards.extend(in_player.card_group.num_out_card_list)
            evt_user_info.op_list.extend(in_player.op_list)
            evt_user_info.round_win_chips = in_player.round_win_chips
            if game_over:
                evt_user_info.total_chi_num = in_player.total_chi_num
                evt_user_info.total_peng_num = in_player.total_peng_num
                evt_user_info.total_gang_list.extend(in_player.total_gang_list)
                evt_user_info.total_hu_list.extend(in_player.total_hu_list)
                evt_user_info.total_win_list.extend(in_player.total_win_list)
                evt_user_info.over_chips_details.extend(in_player.over_chips_detail)

        logger.debug('evt:\n%s', evt)
        evt = evt.SerializeToString()

        for in_player in self.player_group.valid_players:
            write_to_users(in_player.uin, proto.CMD_EVENT_GAME_OVER, evt)

    @save_later
    def user_enter(self, request):
        uin = request['user'].uin
        result = self.user_auto_sit_down(request)

        # 重新计算
        if not self.restore_later:
            self.restore_to_group()
        self._need_restore = self.restore_later

        # 说明成功了
        if result < config.RET_SIT_DOWN_FAILED:
            player = self.player_group.get_player_by_uin(uin)
            if player:
                player.user.update(dict(
                    desk_id=self.id,
                    status=config.LOGIN_USER_STATUS_PLAYING,
                ))
            else:
                logger.debug('client request not the same with server')

        return result

    def broadcast_user_enter(self, request):
        uin = request['user'].uin
        player = self.player_group.get_player_by_uin(uin)
        if not player:
            return

        rsp = GameEnterDeskRsp()
        rsp.ret = 0
        # 客户端是先接收一个进桌的操作，然后再等待广播
        write_to_users(uin, proto.CMD_USER_ENTER_DESK, rsp.SerializeToString())

        for to_player in self.player_group.valid_players:
            evt = fill_user_enter_desk_info(self, player, to_player)
            logger.debug('evt:\n%s', evt)
            evt = evt.SerializeToString()
            write_to_users(to_player.uin, proto.CMD_EVENT_USER_ENTER_DESK, evt)

    @save_later
    @one_round_over_checker
    def user_exit(self, uin, ntf_me=True, reason=0):
        player = self.player_group.get_player_by_uin(uin)
        if not player:
            if reason == config.USER_EXIT_REASON_USER_REQUEST:
                logger.error('not find player in desk, uin:%s', uin)
                return error_contrast.ERROR_CANNOT_FIND_PLAYER
            else:
                return 0

        if self.status == config.GAME_STATE_INGAME:
            # 暂时先注销掉
            # return error_code.ERROR_CANNOT_EXIT_DESK_IN_GAME
            return 0

        # 退桌信号
        # signals.normal_desk_user_exit.send(self, player=player, desk=self)

        player.status = config.USER_STATE_STAND

        # 清除挑战状态
        # if self.type == config.DESK_TYPE_CHALLENGE:
        #     player.user.challenge_alive = False

        # 之所以要放到remove之前，是因为先删除，再调用next_one会导致seatid为None
        # if self.current_uin == uin:
        #     self.next_one()

        # 先发消息，后删除，是为了通知到自己。因为当前不够的时候，要踢人，是会发给自己的。
        # 广播新用户离开的消息
        if reason == config.USER_EXIT_REASON_USER_REQUEST:
            self.broadcast_user_exit(player, exclude=None if ntf_me else player.uin, reason=reason)

        # 删除用户
        self.player_group.remove_player(player)

        # 如果用户掉线，那么起码在后面的300秒内，他进入游戏的话，还是会进来原来的桌子
        # if player.user.status > 0:
        #     player.user.update(dict(
        #         desk_id=-1,
        #     ))

        # 退桌就要把desk_id清掉
        player.user.update(dict(
            desk_id=0,
            status=config.LOGIN_USER_STATUS_ONLINE,
        ))

        # 重新计算
        if not self.restore_later:
            self.restore_to_group()
        self._need_restore = self.restore_later

        return 0

    def broadcast_user_exit(self, player, exclude=None, reason=0):
        evt = EvtUserExit()
        evt.next_uin = self.current_uin
        evt.dealer = self.dealer_uin
        evt.dealer_seatid = self.dealer_seatid
        # evt.player_op_past_time = self.player_op_past_time
        evt.op_uin = player.uin
        evt.op_status = player.status
        evt.reason = reason
        evt.deskid = self.id
        evt = evt.SerializeToString()

        for it_player in self.player_group.valid_players:
            if it_player.uin == exclude:
                # 可以选择过滤谁不发
                logger.debug('exclude:%s', exclude)
                continue

            # 这里先屏蔽掉，desk_play_info后续准备全部删掉
            # self.adapt_play_info(evt, player)
            # 难道这里退化成了string？ 回家看看 MARK
            write_to_users(it_player.uin, proto.CMD_EVENT_USER_EXIT_DESK, evt)

    @save_later
    def user_auto_sit_down(self, request, seat_id=None):
        uin = request['user'].uin
        player = self.player_group.get_player_by_uin(uin)

        # 断线或者是游戏中退出再进来
        if player:
            # 如果用户已经是坐下状态，就直接返回成功
            return config.RET_SIT_DOWN_RECONNECT
        # 首次进桌
        else:
            # 创建用户
            player = Player(uin, self.id)

            player.status = config.USER_STATE_STAND
            player.enter_time = time.time()

            if self.player_group.add_player(player, seat_id=seat_id) >= 0:
                player.status = config.USER_STATE_STAND
                # 先发进桌广播
                self.broadcast_user_enter(request)

                # 检查是否还能进机器人
                # logger.debug(find_caller())
                return config.RET_SIT_DOWN_SUCCESS
            else:
                return config.RET_SIT_DOWN_FAILED

    # 只有转转有，而且只有赢牌的人可以抓鸟
    def catch_bird(self, win_player):
        if self.bird_num == 0:
            return
        # 一马全中
        if self.bird_num == 1:
            bird_card = [Card(num) for num in random.sample(4 * (range(0, 27) + [-3] * 4), self.bird_num)]
            self.bird_card = [Card_it.num for Card_it in bird_card]
            logger.debug('yima:%s', bird_card)
            for card_it in bird_card:
                # 红中多十倍
                if card_it.type == -3:
                    win_player.bird_num += 10
                else:
                    win_player.bird_num = card_it.point + 1
        else:
            bird_card = [Card(num) for num in random.sample(4 * (range(0, 27)), self.bird_num)]
            self.bird_card = [Card_it.num for Card_it in bird_card]
            logger.debug('bird:%s', self.bird_card)
            for card_it in bird_card:
                if card_it.point in [1, 5, 9]:
                    win_player.bird_num += 1

    def add_or_reduce_chips(self, delta_chips, win_player, lose_player=None, type_hu=0):
        # 抢杠肯定不可能是叫牌
        # 自摸
        if not type_hu:
            logger.error('no type_hu')
            return

        if self.is_jiaopai:
            for in_player in self.player_group.sit_players:
                # 输的人
                if in_player.uin != win_player.uin:
                    in_player.round_hu_list.append(-type_hu)
                    in_player.total_hu_list.append(-type_hu)
                    in_player.round_win_list.append(-config.GAME_WIN_TYPE_ZIMO)
                    in_player.total_win_list.append(-config.GAME_WIN_TYPE_ZIMO)
                    in_player.round_win_chips += -delta_chips * win_player.shanghuo * in_player.shanghuo * \
                                                (1 + win_player.bird_num) - (win_player.piaofen + in_player.piaofen)
                    in_player.over_chips_detail[23+type_hu] += -delta_chips * win_player.shanghuo * in_player.shanghuo * \
                                                (1 + win_player.bird_num) - (win_player.piaofen + in_player.piaofen)
                    # in_player.chips += in_player.round_win_chips
                    win_player.round_win_chips += delta_chips * win_player.shanghuo * in_player.shanghuo * \
                                                (1 + win_player.bird_num) + (win_player.piaofen + in_player.piaofen)
                    win_player.over_chips_detail[5+type_hu] += delta_chips * win_player.shanghuo * in_player.shanghuo * \
                                                (1 + win_player.bird_num) + (win_player.piaofen + in_player.piaofen)
            win_player.round_win_list.append(config.GAME_WIN_TYPE_ZIMO)
            win_player.total_win_list.append(config.GAME_WIN_TYPE_ZIMO)
            win_player.round_hu_list.append(type_hu)
            win_player.total_hu_list.append(type_hu)
            # win_player.chips += win_player.round_win_chips
        # 放炮
        else:
            if lose_player:
                lose_player.round_hu_list.append(-type_hu)
                lose_player.total_hu_list.append(-type_hu)
                lose_player.round_win_list.append(config.GAME_WIN_TYPE_FANGPAO)
                lose_player.total_win_list.append(config.GAME_WIN_TYPE_FANGPAO)
                lose_player.round_win_chips += -delta_chips * self.calculate_multi * win_player.shanghuo * lose_player.shanghuo * \
                                              (1 + win_player.bird_num) - (win_player.piaofen + lose_player.piaofen)
                lose_player.over_chips_detail[59+type_hu] += -delta_chips * self.calculate_multi * win_player.shanghuo * lose_player.shanghuo * \
                                              (1 + win_player.bird_num) - (win_player.piaofen + lose_player.piaofen)
                win_player.round_hu_list.append(type_hu)
                win_player.total_hu_list.append(type_hu)
                win_player.round_win_list.append(config.GAME_WIN_TYPE_JIEPAO)
                win_player.total_win_list.append(config.GAME_WIN_TYPE_JIEPAO)
                win_player.round_win_chips += delta_chips * self.calculate_multi * win_player.shanghuo * lose_player.shanghuo * \
                                              (1 + win_player.bird_num) + (win_player.piaofen + lose_player.piaofen)
                win_player.over_chips_detail[41+type_hu] += delta_chips * self.calculate_multi * win_player.shanghuo * lose_player.shanghuo * \
                                              (1 + win_player.bird_num) + (win_player.piaofen + lose_player.piaofen)
            else:
                logger.error('not find lose_player')

    def calculate_win_chips(self):
        # 不是叫牌才做输家的判断，不然全部都是输家了
        # 加上赢牌的人的判断，如果没人赢就是亡庄了，也不用取输家了
        lose_player = None
        if not self.is_jiaopai and self.can_win_list:
            lose_player = self.player_group.get_player_by_uin(self.send_card_uin)
            if not lose_player:
                logger.debug('not find lose_player')
                return

        # 引入win_list，就是为了应付一炮多响的情况
        # 如果是亡庄can_win_list就是空的，就不会走结算逻辑了
        tmp_can_win_list = copy.deepcopy(self.can_win_list)
        for win_player_uin in tmp_can_win_list:
            logger.debug('win:%s', tmp_can_win_list)
            self.can_win_list.pop(win_player_uin)

            win_player = self.player_group.get_player_by_uin(int(win_player_uin))
            if not win_player:
                logger.debug('not find win_player')
                continue

            # 这里不加好像也可以，保险起见加上
            win_player.op_type = []
            win_player.op_chi = False
            win_player.op_peng = False
            win_player.op_gang = False
            win_player.op_hu = False
            win_player.need_wait = True
            win_player.status = config.USER_STATE_INGAME

            # 不是叫牌才加进来，免得再加一次
            if not self.is_jiaopai:
                win_player.card_group.add_card(self.extend_card, self.is_jiaopai)
                win_player.card_len += 1

            type_hu = win_player.card_group.is_hu(win_player.op_list)

            # 两次判断的胡型不一样，那肯定是有问题的
            if type_hu != tmp_can_win_list[win_player_uin]:
                logger.debug('diff hu, uin:%s, type_hu:%s, list_hu:%s', win_player_uin, type_hu,
                             tmp_can_win_list[win_player_uin])
                continue

            # 确实是赢牌了，就加到里面来
            if type_hu > 0:
                self.winner_uin.append(int(win_player_uin))
                logger.debug('winner:%s', self.winner_uin)

            delta = 0
            # 平胡只能自己叫牌，胡牌逻辑里面已经加上是否是叫牌的判定了
            # 还是不要在平胡里面加上是否叫牌的判定，因为这样会牵扯出杠牌后出牌的问题
            # 而且这样再加的话里面的逻辑就越来越复杂了
            if type_hu == config.MAHJONG_FORMATION_PINGHU:
                delta = 1
            elif type_hu == config.MAHJONG_FORMATION_PINGHU_QUANQIUREN:
                delta = 2
            elif type_hu == config.MAHJONG_FORMATION_DADUI:
                delta = 3
            elif type_hu == config.MAHJONG_FORMATION_DADUI_QUANQIUREN:
                delta = 6
            elif type_hu == config.MAHJONG_FORMATION_QINGYISE:
                delta = 4
            elif type_hu == config.MAHJONG_FORMATION_QINGYISE_QUANQIUREN:
                delta = 8
            elif type_hu == config.MAHJONG_FORMATION_QINGYISE_DADUI:
                delta = 7
            elif type_hu == config.MAHJONG_FORMATION_QINGYISE_DADUI_QUANQIUREN:
                delta = 14
            elif type_hu == config.MAHJONG_FORMATION_SHISANLAN:
                delta = 2
            elif type_hu == config.MAHJONG_FORMATION_QIXING_SHISANLAN:
                delta = 4
            elif type_hu == config.MAHJONG_FORMATION_QIDUI:
                delta = 5
            elif type_hu == config.MAHJONG_FORMATION_QIDUI_HAOHUA:
                delta = 10
            elif type_hu == config.MAHJONG_FORMATION_QIDUI_SHUANGHAOHUA:
                delta = 20
            elif type_hu == config.MAHJONG_FORMATION_QIDUI_SANHAOHUA:
                delta = 40
            elif type_hu == config.MAHJONG_FORMATION_QINGYISE_QIDUI:
                delta = 9
            elif type_hu == config.MAHJONG_FORMATION_QINGYISE_QIDUI_HAOHUA:
                delta = 14
            elif type_hu == config.MAHJONG_FORMATION_QINGYISE_QIDUI_SHUANGHAOHUA:
                delta = 24
            elif type_hu == config.MAHJONG_FORMATION_QINGYISE_QIDUI_SANHAOHUA:
                delta = 44

            # 转转赢了只算一分
            if self.type == config.DESK_TYPE_MJ_ZZ:
                delta = 1
                # 再抓个鸟
                self.catch_bird(win_player)

            self.add_or_reduce_chips(delta, win_player, lose_player=lose_player, type_hu=type_hu)

    # 整个游戏结束
    # 这个好像都没必要了
    def desk_game_over(self, uin=None):
        # 先清除部分数据，然后全部清除
        logger.debug('desk_game_over')
        mj_signals.mahjong_desk_game_over.send(self, desk=self)

        # 重置桌子数据,保留需要下发下去的结算数据
        self.reset(desk_game_reset=True, broadcast_over=False)
        # 发游戏结束的广播
        self.broadcast_game_over_info(game_over=True)
        # 清除所有信息
        self.reset(desk_game_reset=True, broadcast_over=True)

    @save_later
    def check_to_start_play(self):
        if self.status == config.GAME_STATE_INGAME or self.status == config.GAME_STATE_APPLY_DELETE or \
                self.status == config.GAME_STATE_WAIT_DELETE:
            return

        if self.desk_remain_round <= 0:
            return

        if len(self.player_group.sit_players) >= self.seat_limit:
            # 先看看飘分上火状态，没选择就重置
            # 重置后本来就是一倍，所以不需要控制了
            for player in self.player_group.sit_players:
                if player.shanghuo == -1:
                    player.shanghuo = 1
                if player.piaofen == -1:
                    player.piaofen = 0
            # 检测玩家状态，都准备了才能开始
            self.start_play()

    def on_count_down(self):
        self.can_delete = True

        # 超时在这里 2017-06-16策划说把定时器干掉咯 那就恢复回去咯，真是操蛋
        if self.status == config.GAME_STATE_APPLY_DELETE:
            self.status = self.pre_status
            self.pre_status = None
            self.can_delete = False
            self.need_save = True
            return

            """
            for in_player in self.player_group.sit_players:
                in_player.chips += in_player.round_win_chips
            self.over_time = int(time.time())
            if self.pre_status != config.GAME_STATE_READY:
                # MARK 先这样写着
                mj_signals.mahjong_desk_game_over.send(self, desk=self)
            self.broadcast_game_over_info(game_over=True, over_reason=config.GAME_OVER_APPLY_TIMEOUT)
            """

        if self.desk_remain_round != self.desk_round:
            celery_delay(
                parse_desk_record_to_db,
                self.uuid
            )

        # 先发游戏结束的广播，然后全部踢掉
        # logger.debug('start delete player')
        for player in self.player_group.valid_players:
            # 清除牌桌内所有的玩家
            if player:
                self.user_exit(player.uin, reason=config.USER_EXIT_REASON_DELETE_DESK)

        self._need_restore = self.restore_later

    def start_play(self):
        """
        开始游戏
        """
        logger.debug('game start')

        self.status = config.GAME_STATE_INGAME

        for player in self.player_group.sit_players:
            player.status = config.USER_STATE_INGAME

        # 也需要dealer，摇色子的
        self._assign_dealer(game_start=True)
        # 发手牌
        self._assign_cards()

        # 把房卡扣掉
        if config.OPEN_ROOM_CARD_USED:
            card = -self.used_card
            if self.used_card:
                self.master_player.user.update(dict(card__=card))
                # 告知客户端房卡变了
                user_room_card_notify(self.master_player.user)
                self.used_card = 0

        self.desk_remain_round -= 1

        # 麻将里面不管是几人牌局，都是dealer先说话
        self.current_player = self.dealer

        for player in self.player_group.active_players:
            # 游戏次数
            player.user.update(dict(play_times__=1))
            # 看看兄弟有没有邀请人，有就给邀请人加2张房卡
            if player.user.user_inviter:
                user_inviter = RedisUserMgr().get_user(player.user.user_inviter)
                user_inviter.update(dict(card__=2))
                user_room_card_notify(user_inviter, reason=config.ROOM_CHANGE_BY_INVITE_PALYING)
                player.user.update(dict(user_inviter=0))

        # 游戏开始的信号,先不要记录
        mj_signals.mahjong_desk_start_play.send(self,
                                                desk=self,
                                                delta_card=card if config.OPEN_ROOM_CARD_USED else 0,
                                                )

        # 设置牌桌内的信息，把叫牌移植过来
        self._recv_card()

        for player in self.player_group.valid_players:
            evt = GameInfoEvt()
            self.adapt_game_round_info(evt, player.uin)
            print_once = False
            if not print_once:
                logger.debug('start_play\n player:%s\n evt:\n%s', player.uin, evt)
                print_once = True
            evt = evt.SerializeToString()
            write_to_users(player.uin, proto.CMD_EVENT_GAME_START, evt)

    def check_one_round_over(self):
        if len(self.player_group.valid_players) == 0:
            # 这里是说明在等待飘分上火
            if 'game_start' in self.timeout_info:
                self.game_start_timeout_mgr.stop_timer()
                self.timeout_info.pop('game_start', None)
            # if self.status != config.GAME_STATE_WAIT_DELETE and self.status != config.GAME_STATE_APPLY_DELETE:
            if self.status == config.GAME_STATE_READY:
                # 牌局没开始时的结束
                if 'count_down' not in self.timeout_info:
                    delay = 5
                    self.timeout_info['count_down'] = self.desk_count_down_mgr.start_timer(delay)
                self.status = config.GAME_STATE_WAIT_DELETE
        else:
            # 胡牌或者亡庄的情况就是正常结束
            # 胡牌的结束操作不能放到这里啊
            # 要叫牌发现没牌了，直接结束这一局
            if self.share_cards_len == -1:
                # for in_player in self.player_group.sit_players:
                #     in_player.chips += in_player.round_win_chips
                self.on_one_round_over()

    # 当一局牌局结束的时候做的事情，比如当前用户设置为None
    # one_round是正常结束的必经方法，但是还有游戏中结束
    def on_one_round_over(self):
        # 如果游戏已经结束，就什么也不做
        if self.status == config.GAME_STATE_READY:
            return

        self.over_time = int(time.time())
        # 每个人都要算一遍
        for in_player in self.player_group.sit_players:
            in_player.chips += in_player.round_win_chips

        # 桌子没有剩余次数了，走桌子结算的逻辑
        if self.desk_remain_round <= 0:
            self.desk_game_over()
            for player in self.player_group.valid_players:
                player.delete_status = config.USER_STATE_AGREE_DELETE
            # 轮数用完了就都踢出去，解散牌桌
            if 'count_down' not in self.timeout_info:
                delay = 5
                self.timeout_info['count_down'] = self.desk_count_down_mgr.start_timer(delay)
            return

        mj_signals.mahjong_desk_game_over.send(self, desk=self)
        # 提前分配下一局的dealer
        self._assign_dealer(game_start=False)
        # 重置每一轮游戏的数据
        self.reset(desk_game_reset=False, broadcast_over=False)
        # 给玩家预留看战绩的时间
        # self.delay_restart_game()
        # 下发本局游戏结束的广播
        self.broadcast_game_over_info()
        # 清除之前保留的数据
        self.reset(desk_game_reset=False, broadcast_over=True)

        # 异步解析牌局记录
        celery_delay(
            parse_desk_record_to_db,
            self.uuid
        )

    def restore_to_group(self):
        # 同步写入到新的数据结构里面
        self.restore_to_desk_mgr()

    def restore_to_desk_mgr(self):
        # 这个类的导入不能放在文件开头,会导致循环导入
        from common.desk_mgr_controller import MjDeskMgrController
        desk_controller = MjDeskMgrController()

        if self.can_delete_desk():
            desk_controller.remove_desk(self.id)
        else:
            # 更新桌子人数
            desk_controller.add_desk(self.id, self.exist_players_num)

    def can_delete_desk(self):
        if self.exist_players_num == 0:
            return self.can_delete

        return False

    @property
    def exist_players_num(self):
        return len(self.player_group.valid_players)

    def get_sit_players_info_dict(self):
        info_dict = dict()

        for player in self.player_group.valid_players:
            user = player.user

            info_dict[player.uin] = dict(
                seatid=player.seatid,
                status=player.delete_status if self.status == config.GAME_STATE_APPLY_DELETE else player.status,
                uin=player.uin,
                nick=user.nick,
                sex=user.sex,
                portrait=user.portrait_path if user.portrait_path else '',
                is_master=int(self.is_master(player.uin)),
                shanghuo=player.shanghuo,
                piaofen=player.piaofen,
                ip=user.client_ip,
                # user对象也放进来,方便后面取用
                user=user,
            )

        return info_dict

    @property
    def dealer(self):
        if self.dealer_seatid < 0:
            return None

        # 直接返回对应位置的player即可，无论是否为None
        return self.player_group.valid_players[self.dealer_seatid]

    @property
    def dealer_uin(self):
        return self.dealer.uin if self.dealer else -1

    def _assign_dealer(self, game_start=True):
        logger.debug('winner:%s, dealer:%s', self.winner_uin, self.dealer_seatid)
        # 第一局，还没开始，那么dealer就是房主了
        if self.dealer_seatid == -1 and game_start:
            for idx in range(0, len(self.player_group.sit_players)):
                seatid = (self.dealer_seatid + 1 + idx) % len(self.player_group.sit_players)
                player = self.player_group.sit_players[seatid]
                # 房主是第一个dealer
                if self.is_master(player.uin):
                    if player and player.status >= config.USER_STATE_INGAME:
                        self.dealer_seatid = seatid
                        player.role = config.USER_ROLE_DEALER
                        return

        if not game_start:
            if self.winner_uin:
                for win_player_uin in self.winner_uin:
                    win_player = self.player_group.get_player_by_uin(win_player_uin)
                    if win_player:
                        self.dealer_seatid = win_player.seatid
                        win_player.role = config.USER_ROLE_DEALER
                    return
            else:
                for idx in range(0, len(self.player_group.sit_players)):
                    seatid = (self.dealer_seatid + 1 + idx) % len(self.player_group.sit_players)
                    player = self.player_group.sit_players[seatid]
                    if player and player.status >= config.USER_STATE_INGAME:
                        self.dealer_seatid = seatid
                        player.role = config.USER_ROLE_DEALER
                        return

        if self.dealer_seatid == -1:
            logger.critical('Cannot find a dealer. desk id:%s', self.id)

    def _assign_cards(self):
        # 转转没有字牌
        card_list = []
        share_cards = []
        if self.type == config.DESK_TYPE_MJ_WZ:
            card_list = 4*(range(0, 27) + range(-1, -8, -1))  # (27 + 7) * 4 = 136张
        elif self.type == config.DESK_TYPE_MJ_ZZ:
            if self.has_laizi:
                card_list = 4 * (range(0, 27)) + 4 * [-3]  # 28 * 4 = 112张
            else:
                card_list = 4 * (range(0, 27))  # 27 * 4 = 108张

        if config.PLAY_DEBUG_ASSIGN_CARD:
            for it in config.ASSIGN_CARD:
                card_list.remove(it)
        random.shuffle(card_list)

        # 先把公共牌分出来
        if self.type == config.DESK_TYPE_MJ_WZ:
            share_cards, card_list = card_list[:84], card_list[84:]
        elif self.type == config.DESK_TYPE_MJ_ZZ:
            share_cards, card_list = card_list[:56], card_list[56:]
            # share_cards, card_list = card_list[:2], card_list[56:]

        random.shuffle(card_list)

        player_card_list = list()
        random.shuffle(card_list)
        random.shuffle(card_list)

        if config.PLAY_DEBUG_ASSIGN_CARD:
            card_list = config.ASSIGN_CARD + card_list
            share_cards.extend([13,14,14])
        card_tmp = 0
        for player in self.player_group.active_players:
            # 先要把牌发出去
            if player == self.dealer:
                player_card_list.append(card_list[card_tmp:card_tmp + 13])
                card_tmp += 13
            else:
                player_card_list.append(card_list[card_tmp:card_tmp + 13])
                card_tmp += 13
            # 玩法在这里透传下去
            player.card_group = CardGroup(
                [Card(num) for num in player_card_list.pop()],
                self.has_laizi,
                self.can_win_by_qidui,
                self.type,
            )
            player.card_len = len(player.cards)

        self.share_cards = share_cards
        self.share_cards_len = len(share_cards)

    # 碰和杠肯定是只有一家会有，不需要检视，主要就是碰杠与胡牌之间的冲突
    # 碰比吃大，如果碰和吃都有，还需要判断一下
    # 碰&杠，吃&杠不可能一起出现，不用管了
    def set_who_need_wait(self, uin_list):
        # 先置位
        for player in self.player_group.sit_players:
            player.need_wait = True
            player.op_chi = False
            player.op_peng = False
            player.op_gang = False
            player.op_hu = False

        # 引入优先级，胡为2，碰杠为1，吃为0, 啥都没有就是-1
        desk_level = [-1]
        player_level = {}
        can_interrupt = False
        for player in self.player_group.sit_players:
            # 初始化
            player_level[player.uin] = [-1]
            # 排除掉出牌的人，自己不能对自己的牌有反应
            if player.uin not in uin_list and player.op_type:
                # 有人可以胡牌
                if player.op_type[3] and self.win_type == config.DESK_WIN_TYPE_DIANPAO:
                    desk_level.append(2)
                    player_level[player.uin].append(2)
                if player.op_type[2]:
                    desk_level.append(1)
                    player_level[player.uin].append(1)
                if player.op_type[1]:
                    desk_level.append(1)
                    player_level[player.uin].append(1)
                if player.op_type[0]:
                    desk_level.append(0)
                    player_level[player.uin].append(0)
            # 算出每个人的level
            player_level[player.uin] = max(player_level[player.uin])

        # 算出桌子的level
        desk_level = max(desk_level)

        # 把这个放到这里来
        send_card_player = self.player_group.get_player_by_uin(self.send_card_uin)
        seat_len = len(self.player_group.sit_players)

        for player in self.player_group.sit_players:
            # 排除掉出牌的人，自己不能对自己的牌有反应
            if player.uin not in uin_list and player.op_type and player_level[player.uin] >= desk_level:
                # 场上没有碰牌和胡牌，吃牌才特么的不需要等待，吃牌的优先级最低，放最上面
                # 只有有出牌的人才做吃和碰的判断
                if send_card_player:
                    # 只有万载可以吃
                    if player.op_type[0] and player.seatid == (send_card_player.seatid + 1) % seat_len and \
                            self.type == config.DESK_TYPE_MJ_WZ:
                        if self.share_cards_len > 0:
                            player.need_wait = False
                            # self.current_uin = player.uin
                            player.op_chi = True
                            can_interrupt = True
                    if player.op_type[1]:
                        if self.share_cards_len > 0:
                            player.need_wait = False
                            # self.current_uin = player.uin
                            player.op_peng = True
                            can_interrupt = True
                # 场上没胡牌，其它的才不需要等待
                if player.op_type[2]:
                    if self.share_cards_len > 0:
                        player.need_wait = False
                        # self.current_uin = player.uin
                        # 点杠肯定就可以碰，不在这里做限制，在判断碰那里判断就好了
                        # if player.op_type[2] == config.MAHJONG_DIAN_GANG:
                        #     player.op_peng = True
                        player.op_gang = True
                        can_interrupt = True
                # 胡牌永远不等待，这里不要直接返回，不然多人可胡的情况别人收不到胡的消息
                # if player.op_type[3] > 2 or \
                #         (player.op_type[3] == 1 and send_card_player.status == config.USER_STATE_AFTER_GANG):
                if player.op_type[3] > 0 and self.win_type == config.DESK_WIN_TYPE_DIANPAO:
                    # 万载麻将赢牌锁判断
                    if self.type == config.DESK_TYPE_MJ_WZ and self.extend_card in player.win_mutex_card:
                        continue
                    player.need_wait = False
                    # self.current_uin = player.uin
                    player.op_hu = True
                    self.can_win_list[player.uin] = player.op_type[3]
                    can_interrupt = True

        # 返回放在这里
        if can_interrupt:
            return True

        return False

    @save_later
    @right_turn_required
    def send_card(self, uin, user_card, timeout=None):
        """
        出牌
        """
        self.can_win_list = {}
        self.calculate_multi = 1

        if self.status != config.GAME_STATE_INGAME:
            logger.error('desk not in game')
            # 不是在游戏中的话，就不往下走了
            return error_contrast.ERROR_NOT_IN_GAME

        player = self.player_group.get_player_by_uin(uin)
        if not player:
            logger.error('not find player in desk, uin:%s', uin)
            return error_contrast.ERROR_CANNOT_FIND_PLAYER

        if not (-7 <= user_card <= 26):
            logger.error('invalid params, user_card:%s', user_card)
            return error_contrast.ERROR_INVALID_PARAMS

        # 修改用户手牌，同时同步一下服务器手牌
        self.extend_card = user_card
        self.is_jiaopai = False
        self.send_card_uin = uin
        # self.hand_cards[uin].remove(user_card)
        player.card_group.remove_card(user_card)
        player.card_len -= 1
        player.need_wait = True

        # 解锁
        if player.win_mutex_card:
            player.win_mutex_card = []

        # 对手牌的操作逻辑明天在这里写
        # 先判断每个人对手牌的反应，如果有就发送对应的广播
        for in_player in self.player_group.sit_players:
            if in_player.uin != uin:
                in_player.card_group.add_card(user_card, self.is_jiaopai)
                in_player.op_type = in_player.card_group.is_my_turn(in_player.op_list)
                in_player.card_group.remove_card(user_card)

        # 先加到出牌的人的discard里面，有特殊操作再取走
        player.card_group.discard_list.append(Card(user_card))
        # 先判断一下有没有胡、杠、碰，有就下发广播等待响应
        # 响应要么是碰、要么是杠、要么是胡，要么就特么超时了
        # 如果一段时间没等到响应就自动进入下一轮叫牌了
        # 吃碰杠操作有等待一说
        if self.set_who_need_wait([uin]):
            # send_card_player = self.player_group.get_player_or_viewer_by_uin(self.send_card_uin)
            # 先把操作设置好
            # for in_player in self.player_group.sit_players:
            #     if in_player.uin != uin:
            #         if not in_player.need_wait:
                        # 只有这个人在出牌人之后才能吃牌
                        # 如果最后没牌了，吃碰杠就都停掉，这个操作是很必要的
                        # if in_player.op_type[0] and in_player.seatid == (send_card_player.seatid + 1) % seat_len:
                        #     if self.share_cards_len > 0:
                        #         self.current_uin = in_player.uin
                        #         in_player.op_chi = True
                        # if in_player.op_type[1]:
                        #     if self.share_cards_len > 0:
                        #         self.current_uin = in_player.uin
                        #         in_player.op_peng = True
                        # if in_player.op_type[2]:
                        #     if self.share_cards_len > 0:
                        #         self.current_uin = in_player.uin
                        #         in_player.op_gang = True
                        # 胡牌中的平胡需要判定一下
                        # if in_player.op_type[3] > 2 or \
                        #     (in_player.op_type[3] == 1 and send_card_player.status == config.USER_STATE_AFTER_GANG):
                        #     self.current_uin = in_player.uin
                        #     in_player.op_hu = True
                        #     self.can_win_list[in_player.uin] = in_player.op_type[3]
                        #     self.tmp_can_win_list.append(in_player.uin)

            # 这里加一个操作超时的定时器，不然等待别人操作的时候别人如果不操作，那就卡死了
            # self.monitor_player_op_timeout()
            # 下发各种操作广播
            for in_player in self.player_group.valid_players:
                evt = GameInfoEvt()
                evt.op_user.uin = player.uin
                evt.op_user.type = config.OP_TYPE_SEND_CARD
                self.adapt_game_round_info(evt, in_player.uin)
                print_once = False
                if not print_once:
                    logger.debug('send_card player:%s evt:\n%s', in_player.uin, evt)
                    print_once = True
                evt = evt.SerializeToString()
                write_to_users(in_player.uin, proto.CMD_GAME_RECV_INFO_EVT, evt)

            return 0
        else:

            # 没人进行特殊操作就加到用户的废弃手牌中，这些手牌是所有人都可见的
            # 这里应该是提前加进来，然后如果用户有操作再从discard里面拿走
            # player.out_card_len += 1
            # 选择下一个同志叫牌
            # 下一个同志在不在的判断已经写在recv里面了
            self.next_one()
            self._recv_card()

            # 叫牌成功才下发游戏广播
            if self.share_cards_len != -1:
                for in_player in self.player_group.valid_players:
                    evt = GameInfoEvt()
                    evt.op_user.uin = player.uin
                    evt.op_user.type = config.OP_TYPE_SEND_CARD
                    self.adapt_game_round_info(evt, in_player.uin)
                    print_once = False
                    if not print_once:
                        logger.debug('recv_card player:%s evt:\n%s', in_player.uin, evt)
                        print_once = True
                    evt = evt.SerializeToString()
                    write_to_users(in_player.uin, proto.CMD_GAME_RECV_INFO_EVT, evt)

            return 0

    # 叫了牌最终还是要出牌，出牌后下个人叫牌时没牌就结束
    @one_round_over_checker
    def _recv_card(self, after_gang=False, after_pass=False):
        """
        叫牌
        """
        self.can_win_list = {}
        self.calculate_multi = 1

        if self.status != config.GAME_STATE_INGAME:
            logger.error('desk not in game')
            return

        if self.share_cards_len <= 0:
            # 轮到我叫牌但是没牌可以叫上来了，那就是亡庄了
            # 亡庄了，这张牌要先显示给别人看到，所以有下面的广播
            # 这个广播先加到这里，到时候测测看
            # 既不是杠牌后叫牌也不是PASS后叫牌，那肯定就是和出牌合在一起的叫牌，把发牌广播弄出去
            if not after_gang and not after_pass:
                for in_player in self.player_group.valid_players:
                    evt = GameInfoEvt()
                    evt.op_user.uin = self.current_uin
                    evt.op_user.type = config.OP_TYPE_SEND_CARD
                    self.adapt_game_round_info(evt, in_player.uin)
                    evt = evt.SerializeToString()
                    # logger.debug('recv_card player:%s evt:\n%s', in_player.uin, evt)
                    write_to_users(in_player.uin, proto.CMD_GAME_RECV_INFO_EVT, evt)
            logger.debug('share card is None')
            # 如果等于-1代表真的完了
            self.share_cards_len = -1
            return

        player = self.current_player
        if not player:
            logger.error('not find player. uin:%s', self.current_uin)
            return

        # 杠了之后再叫的牌就不要置位了
        if not after_gang:
            player.status = config.USER_STATE_INGAME

        card = self.share_cards.pop()
        self.share_cards_len -= 1
        # 叫牌的时候轮数才加一
        self.one_game_round_index += 1
        # self.hand_cards[self.current_uin].append(card)
        self.extend_card = card
        self.is_jiaopai = True
        self.send_card_uin = None
        self.recv_card_uin = self.current_uin
        player.card_group.add_card(self.extend_card, self.is_jiaopai)
        player.card_len += 1

        player.op_type = player.card_group.is_my_turn(player.op_list)

        # 都走到这里了，肯定是不需要等待的
        player.need_wait = False

        if player.op_type[2]:
            player.op_gang = True
        if player.op_type[3]:
            player.op_hu = True
            self.can_win_list[player.uin] = player.op_type[3]
            # 没有额外翻
            # if after_gang:
            #     self.calculate_multi = 2

    @save_later
    def option_chi(self, uin, index):
        """
        吃牌
        """
        if self.status != config.GAME_STATE_INGAME:
            logger.error('desk not in game')
            # 不是在游戏中的话，就不往下走了
            return error_contrast.ERROR_NOT_IN_GAME

        # 如果这张牌是自己叫的，那你吃个鬼啊，返回
        if self.is_jiaopai or not self.send_card_uin:
            logger.error('invalid request op_chi')
            return error_contrast.ERROR_INVALID_REQUEST

        player = self.player_group.get_player_by_uin(uin)
        if not player:
            logger.error('not find player in desk, uin:%s', uin)
            return error_contrast.ERROR_CANNOT_FIND_PLAYER

        player.op_type = []
        player.op_chi = False
        player.op_gang = False
        player.op_peng = False
        player.op_hu = False
        player.status = config.USER_STATE_INGAME

        # 先判定一下是不是吃牌，防止客户端作弊
        player.card_group.add_card(self.extend_card, self.is_jiaopai)
        chi_list = player.card_group.is_chi()
        player.card_group.remove_card(self.extend_card)

        # 如果吃牌列表返回的不为空，证明有吃的牌
        if chi_list:
            send_card_player = self.player_group.get_player_by_uin(self.send_card_uin)
            send_card_player.card_group.discard_list.remove(Card(self.extend_card))

            player.round_chi_num += 1
            player.total_chi_num += 1

            for it in chi_list[index:index+2]:
                player.card_group.remove_card(it)
                player.card_group.out_card_list.append(Card(it))
            player.card_group.out_card_list.append(Card(self.extend_card))

            player.card_len -= 2
            player.op_list.append(config.OP_TYPE_CHI)
            # 排个序
            # 这里不要排序，是啥样就是啥样
            # player.card_group.out_card_list.sort()
            self.current_player = player

            # 返回消息
            for in_player in self.player_group.valid_players:
                evt = GameInfoEvt()
                evt.op_user.uin = player.uin
                evt.op_user.type = config.OP_TYPE_CHI
                self.adapt_game_round_info(evt, in_player.uin)
                evt = evt.SerializeToString()
                # logger.debug('op_chi player:%s evt:\n%s', in_player.uin, evt)
                write_to_users(in_player.uin, proto.CMD_GAME_RECV_INFO_EVT, evt)

            return 0
        else:
            # 返回错误消息
            logger.error('invalid request op_chi')
            return error_contrast.ERROR_INVALID_REQUEST

    @save_later
    def option_peng(self, uin):
        """
        碰牌
        """
        if self.status != config.GAME_STATE_INGAME:
            logger.error('desk not in game')
            # 不是在游戏中的话，就不往下走了
            return error_contrast.ERROR_NOT_IN_GAME

        if self.is_jiaopai or not self.send_card_uin:
            logger.error('invalid request op_peng')
            return error_contrast.ERROR_INVALID_REQUEST

        player = self.player_group.get_player_by_uin(uin)
        if not player:
            logger.error('can not find player, uin:%s', uin)
            return error_contrast.ERROR_CANNOT_FIND_PLAYER

        # 操作位变回来
        player.op_type = []
        player.op_chi = False
        player.op_gang = False
        player.op_peng = False
        player.op_hu = False
        player.status = config.USER_STATE_INGAME

        # 先判定一下，防止客户端作弊
        player.card_group.add_card(self.extend_card, self.is_jiaopai)
        player.card_len += 1

        if player.card_group.is_peng():
            send_card_player = self.player_group.get_player_by_uin(self.send_card_uin)
            send_card_player.card_group.discard_list.remove(Card(self.extend_card))

            player.round_peng_num += 1
            player.total_peng_num += 1

            # 直接移走要的三张就好了，手牌在上面已经加了，就不需要再删了
            for it in range(3):
                player.card_group.remove_card(self.extend_card)
                player.card_group.out_card_list.append(Card(self.extend_card))

            player.card_len -= 3
            player.op_list.append(config.OP_TYPE_PENG)
            # 排个序
            # player.card_group.out_card_list.sort()
            self.current_player = player
            # 返回消息
            for in_player in self.player_group.valid_players:
                evt = GameInfoEvt()
                evt.op_user.uin = player.uin
                evt.op_user.type = config.OP_TYPE_PENG
                self.adapt_game_round_info(evt, in_player.uin)
                evt = evt.SerializeToString()
                # logger.debug('op_peng player:%s evt:\n%s', in_player.uin, evt)
                write_to_users(in_player.uin, proto.CMD_GAME_RECV_INFO_EVT, evt)

            return 0
        else:
            player.card_group.remove_card(self.extend_card)
            player.card_len -= 1
            # 返回错误消息
            logger.error('invalid request op_peng')
            return error_contrast.ERROR_INVALID_REQUEST

    # 抢杠的场景真是他妈的恶心，死了多少脑细胞了？
    @save_later
    def option_gang(self, uin):
        """
        杠牌，杠牌跟其它的最大的区别在于可以是自己叫的牌
        """
        if self.status != config.GAME_STATE_INGAME:
            logger.error('desk not in game')
            # 不是在游戏中的话，就不往下走了
            return error_contrast.ERROR_NOT_IN_GAME

        player = self.player_group.get_player_by_uin(uin)
        lose_player = self.player_group.get_player_by_uin(self.send_card_uin)
        if not player:
            logger.error('can not find player, uin:%s', uin)
            return error_contrast.ERROR_CANNOT_FIND_PLAYER

        # 首要的任务是把操作位变回来
        player.op_type = []
        player.op_chi = False
        player.op_gang = False
        player.op_peng = False
        player.op_hu = False

        # 先判定一下，防止客户端作弊
        # 如果这张牌不是自己叫的，那么才加进来
        if not self.is_jiaopai:
            player.card_group.add_card(self.extend_card, self.is_jiaopai)
            player.card_len += 1

        # 杠完之后应该加个结算标识放在这里，最后打完结算的时候来用
        type_gang = player.card_group.is_gang()

        if type_gang > 0:
            if not self.is_jiaopai:
                send_card_player = self.player_group.get_player_by_uin(self.send_card_uin)
                send_card_player.card_group.discard_list.remove(Card(self.extend_card))

            self.current_player = player

        # 自己叫的杠，暗杠
        if type_gang == config.MAHJONG_GANG:
            for it in range(4):
                player.card_group.remove_card(self.extend_card)
                player.card_group.out_card_list.append(Card(self.extend_card))

            player.card_len -= 4
            # 排个序
            # player.card_group.out_card_list.sort()

            for in_player in self.player_group.sit_players:
                if in_player.uin != uin:
                    in_player.round_gang_list.append(-type_gang)
                    in_player.total_gang_list.append(-type_gang)
                    in_player.round_win_chips += -2 * player.shanghuo * in_player.shanghuo
                    in_player.over_chips_detail[1] += -2 * player.shanghuo * in_player.shanghuo
                    player.round_win_chips += 2 * player.shanghuo * in_player.shanghuo
                    player.over_chips_detail[0] += 2 * player.shanghuo * in_player.shanghuo
            player.round_gang_list.append(type_gang)
            player.total_gang_list.append(type_gang)

            # 加一个标识告诉客户端这个牌是暗杠
            player.op_list.append(config.OP_TYPE_GANG)

            # 杠完之后再叫一张牌
            self._recv_card(after_gang=True)
            player.status = config.USER_STATE_AFTER_GANG

            # 返回消息
            for in_player in self.player_group.valid_players:
                evt = GameInfoEvt()
                evt.op_user.uin = player.uin
                evt.op_user.type = config.OP_TYPE_GANG
                self.adapt_game_round_info(evt, in_player.uin)
                logger.debug('op_gang player:%s evt:\n%s', in_player.uin, evt)
                evt = evt.SerializeToString()
                write_to_users(in_player.uin, proto.CMD_GAME_RECV_INFO_EVT, evt)

            return 0
        # 明杠，证明下面本来就有三张牌了
        # 擦杠还要考虑到抢扛的情况，所以先判断一下你擦的这张牌别人能不能赢，不能赢你特么才能擦出来
        elif type_gang == config.MAHJONG_OUT_GANG:
            rob_out_gang_list = []
            # 点了擦之后这张牌的属性就变成False了，出牌人就变成擦的人了
            self.is_jiaopai = False
            self.send_card_uin = uin

            player.card_group.remove_card(self.extend_card)
            # 这里有点意思，要先把碰的op_list干掉，然后换成杠
            out_gang_index = player.card_group.num_out_card_list.index(self.extend_card)
            player.card_group.out_card_list.insert(out_gang_index, Card(self.extend_card))
            player.card_len -= 1
            player.op_list[out_gang_index / 3] = config.OP_TYPE_OUT_GANG

            # 先看看别人能不能胡牌
            # 杠的操作先做下去，然后等待叫牌，没有抢杠才叫牌
            for in_player in self.player_group.sit_players:
                if in_player.uin != uin:
                    in_player.card_group.add_card(self.extend_card, self.is_jiaopai)
                    in_player.op_type = in_player.card_group.is_my_turn(in_player.op_list)
                    in_player.card_group.remove_card(self.extend_card)

                    if in_player.op_type[3]:
                        in_player.op_hu = True
                        in_player.need_wait = False
                        rob_out_gang_list.append(in_player.uin)
                        self.can_win_list[in_player.uin] = in_player.op_type[3]

            # 有抢杠的就把胡的操作发给对应的人
            if rob_out_gang_list:
                self.calculate_multi = self.seat_limit - 1
                # 返回消息
                for in_player in self.player_group.valid_players:
                    evt = GameInfoEvt()
                    evt.op_user.uin = player.uin
                    evt.op_user.type = config.OP_TYPE_OUT_GANG
                    self.adapt_game_round_info(evt, in_player.uin)
                    logger.debug('rob_hu_out player:%s evt:\n%s', in_player.uin, evt)
                    evt = evt.SerializeToString()
                    write_to_users(in_player.uin, proto.CMD_GAME_RECV_INFO_EVT, evt)

                return 0
            else:
                for in_player in self.player_group.sit_players:
                    if in_player.uin != uin:
                        in_player.round_gang_list.append(-type_gang)
                        in_player.total_gang_list.append(-type_gang)
                        in_player.round_win_chips += -1 * player.shanghuo * in_player.shanghuo
                        in_player.over_chips_detail[3] = -1 * player.shanghuo * in_player.shanghuo
                        player.round_win_chips += 1 * player.shanghuo * in_player.shanghuo
                        player.over_chips_detail[2] = 1 * player.shanghuo * in_player.shanghuo
                player.round_gang_list.append(type_gang)
                player.total_gang_list.append(type_gang)

                # 杠完之后再叫一张牌
                self._recv_card(after_gang=True)
                player.status = config.USER_STATE_AFTER_GANG

                # 返回消息
                for in_player in self.player_group.valid_players:
                    evt = GameInfoEvt()
                    evt.op_user.uin = player.uin
                    evt.op_user.type = config.OP_TYPE_OUT_GANG
                    self.adapt_game_round_info(evt, in_player.uin)
                    logger.debug('op_gang player:%s evt:\n%s', in_player.uin, evt)
                    evt = evt.SerializeToString()
                    write_to_users(in_player.uin, proto.CMD_GAME_RECV_INFO_EVT, evt)

                return 0
        # 点杠，不是自己叫的
        # 点杠不能抢胡
        elif type_gang == config.MAHJONG_DIAN_GANG:
            """
            rob_out_gang_list = []
            self.is_jiaopai = False
            self.send_card_uin = uin
            # 先看看别人能不能胡牌
            for in_player in self.player_group.sit_players:
                if in_player.uin != uin:
                    in_player.card_group.add_card(self.extend_card, self.is_jiaopai)
                    in_player.op_type = in_player.card_group.is_my_turn()
                    in_player.card_group.remove_card(self.extend_card)

                    if in_player.op_type[3]:
                        in_player.op_hu = True
                        in_player.need_wait = False
                        rob_out_gang_list.append(in_player.uin)

            # 有抢杠的就把胡的操作发给对应的人
            if rob_out_gang_list:
                player.card_group.remove_card(self.extend_card)
                player.card_len -= 1

                self.calculate_multi = 3
                # 返回消息
                for in_player in self.player_group.players_and_viewers:
                    evt = GameInfoEvt()
                    self.adapt_game_round_info(evt, in_player.uin)
                    logger.debug('rob_hu_dian player:%s evt:\n%s', in_player.uin, evt)
                    write_to_user(in_player.uin, proto.CMD_GAME_RECV_INFO_EVT, evt)
                return 0
            else:
            """
            for it in range(4):
                player.card_group.remove_card(self.extend_card)
                player.card_group.out_card_list.append(Card(self.extend_card))

            player.card_len -= 4
            # 排个序
            # player.card_group.out_card_list.sort()

            lose_player.round_gang_list.append(-type_gang)
            lose_player.total_gang_list.append(-type_gang)
            lose_player.round_win_chips += -2 * player.shanghuo * lose_player.shanghuo
            lose_player.over_chips_detail[5] = -2 * player.shanghuo * lose_player.shanghuo
            player.round_gang_list.append(type_gang)
            player.total_gang_list.append(type_gang)
            player.round_win_chips += 2 * player.shanghuo * lose_player.shanghuo
            player.over_chips_detail[4] = 2 * player.shanghuo * lose_player.shanghuo

            player.op_list.append(config.OP_TYPE_DIAN_GANG)
            # 杠完之后再叫一张牌
            self._recv_card(after_gang=True)
            player.status = config.USER_STATE_AFTER_GANG

            # 返回消息
            for in_player in self.player_group.valid_players:
                evt = GameInfoEvt()
                evt.op_user.uin = player.uin
                evt.op_user.type = config.OP_TYPE_DIAN_GANG
                self.adapt_game_round_info(evt, in_player.uin)
                logger.debug('op_gang player:%s evt:\n%s', in_player.uin, evt)
                evt = evt.SerializeToString()
                write_to_users(in_player.uin, proto.CMD_GAME_RECV_INFO_EVT, evt)

            return 0
        # 没杠，喝汤去吧，哥哥
        else:
            if not self.is_jiaopai:
                player.card_group.remove_card(self.extend_card)
                player.card_len -= 1

            logger.error('invaild request, op_gang')
            return error_contrast.ERROR_INVALID_REQUEST

    @save_later
    def option_hu(self, uin):
        """
        胡牌，跟杠牌的逻辑应该是差不多的
        胡牌手动结束，别用one_round_over_checker结束了，好蠢
        妈的，想了一下午这个逻辑，之前谁构建的代码，坑死爹了
        """
        self.process_hu_counts += 1

        # 防止同时多个胡牌消息一起上来，保证服务器一次只处理一个胡牌消息
        # 在一个胡牌消息里面把所有可以胡的操作都做了
        if self.process_hu_counts >= 2:
            logger.error('two much op_hu')
            return

        if self.status != config.GAME_STATE_INGAME:
            # 不是在游戏中的话，就不往下走了
            self.process_hu_counts -= 1
            logger.error('desk not in game')
            return error_contrast.ERROR_NOT_IN_GAME

        player = self.player_group.get_player_by_uin(uin)
        if not player:
            self.process_hu_counts -= 1
            logger.error('can not find player, uin:%s', uin)
            return error_contrast.ERROR_CANNOT_FIND_PLAYER

        # 证明是有抢杠的
        if self.calculate_multi == self.seat_limit - 1:
            self.send_card_player.card_group.out_card_list.remove(Card(self.extend_card))
            out_gang_index = player.card_group.num_out_card_list.index(self.extend_card)
            player.op_list[out_gang_index / 3] = config.OP_TYPE_PENG

        # 结算了，就不用再管discard了
        self.calculate_win_chips()
        # 可以直接手动结束游戏了
        # 游戏结束的广播放到on_one_round_over里面去
        self.on_one_round_over()
        self.process_hu_counts -= 1

        return 0

    # pass操作需要判断第二顺位的操作，比如可以同时胡和碰，如果胡被Pass了，那就轮到碰了
    # 暂时的设想是先加一个第二顺位操作列表
    @save_later
    def option_pass(self, uin):
        """
        收到吃、碰、杠之后选择的pass操作
        """
        if self.status != config.GAME_STATE_INGAME:
            logger.error('desk not in game')
            # 不是在游戏中的话，就不往下走了
            return error_contrast.ERROR_NOT_IN_GAME

        player = self.player_group.get_player_by_uin(uin)
        if not player:
            logger.error('can not find player, uin:%s', uin)
            return error_contrast.ERROR_CANNOT_FIND_PLAYER

        player.op_type = []
        player.op_chi = False
        player.op_peng = False
        player.op_gang = False
        player.op_hu = False
        player.need_wait = True

        tmp_can_win_list = [int(k) for k, v in self.can_win_list.items()]
        logger.debug('tmp_can_win_list:%s', tmp_can_win_list)
        # 先判断pass掉的是不是胡牌的人
        if repr(uin) in self.can_win_list:
            self.can_win_list.pop(repr(uin))
            mutex_player = self.player_group.get_player_by_uin(uin)
            if mutex_player:
                # 加赢牌锁
                mutex_player.win_mutex_card.append(self.extend_card)
            else:
                logger.error('not find mutex_player')

        # 如果还有可以赢的人，就别往下走了，等待另外胡牌的人的操作上来
        if self.can_win_list:
            return 0

        seat_len = len(self.player_group.sit_players)
        # 先把可以赢牌的人加上过牌的人全部干掉，后续就不做判断了
        # 再算一次操作级别
        if self.set_who_need_wait(tmp_can_win_list):
            # send_card_player = self.player_group.get_player_or_viewer_by_uin(self.send_card_uin)
            # 先把操作设置好
            # for in_player in self.player_group.sit_players:
            #     if in_player.uin != uin:
            #         if not in_player.need_wait:
                        # 只有这个人在出牌人之后才能吃牌
                        # 如果最后没牌了，吃碰杠就都停掉，这个操作是很必要的
                        # if in_player.op_type[0] and in_player.seatid == (self.send_card_uin + 1) % seat_len:
                        #     if self.share_cards_len > 0:
                        #         in_player.op_chi = True
                        # if in_player.op_type[1]:
                        #     if self.share_cards_len > 0:
                        #         in_player.op_peng = True
                        # if in_player.op_type[2]:
                        #     if self.share_cards_len > 0:
                        #         in_player.op_gang = True
                        # 胡牌中的平胡需要判定一下
                        # if in_player.op_type[3] > 2 or \
                        #     (in_player.op_type[3] == 1 and send_card_player.status == config.USER_STATE_AFTER_GANG):
                        #     in_player.op_hu = True
                        #     self.can_win_list[in_player.uin] = in_player.op_type[3]

            # 这里加一个操作超时的定时器，不然等待别人操作的时候别人如果不操作，那就卡死了
            # self.monitor_player_op_timeout()
            # 下发各种操作广播
            for in_player in self.player_group.valid_players:
                evt = GameInfoEvt()
                self.adapt_game_round_info(evt, in_player.uin)
                logger.debug('op_pass op player:%s evt:\n%s', in_player.uin, evt)
                evt = evt.SerializeToString()
                write_to_users(in_player.uin, proto.CMD_GAME_RECV_INFO_EVT, evt)

            return 0
        # 上面这些操作都没有就选择下一个人叫牌了
        else:
            # 不是抢杠胡牌的pass才选择下一个人
            # 出牌的人的下一个，这里如果选择current的下一个会有问题，因为在need_wait的判断那里改变了current_uin
            if self.calculate_multi != self.seat_limit - 1 and self.send_card_uin:
                self.current_player = self.player_group.valid_players[(self.send_card_player.seatid + 1) % seat_len]
            if self.recv_card_uin != uin:
                # 过的这个人不是叫牌的人，那就继续叫牌
                # 抢杠pass的叫牌也在这里
                self._recv_card(after_pass=True)
            else:
                # 过的人是叫牌的人，那么不叫牌，并且还是轮到我出牌
                player.need_wait = False

            # 下发游戏广播就好了
            for in_player in self.player_group.valid_players:
                evt = GameInfoEvt()
                self.adapt_game_round_info(evt, in_player.uin)
                evt.op_user.uin = player.uin
                evt.op_user.type = config.OP_TYPE_PASS
                logger.debug('op_pass player:%s evt:\n%s', in_player.uin, evt)
                evt = evt.SerializeToString()
                write_to_users(in_player.uin, proto.CMD_GAME_RECV_INFO_EVT, evt)

            return 0

    @save_later
    def player_status_change(self, uin, req):
        status = req.status
        if self.status == config.GAME_STATE_INGAME or self.status == config.GAME_STATE_WAIT_DELETE:
            # 在游戏中或者即将被解散，就不往下走了
            logger.error('desk status:%s, can not change status', self.status)
            return

        player = self.player_group.get_player_by_uin(uin)
        if not player:
            logger.error('can not find player, uin:%s', uin)
            return

        # 准备
        if status == 1:
            # 玩游戏不能准备
            if player.status >= config.USER_STATE_INGAME:
                return
            player.status = config.USER_STATE_READY
            if self.status == config.GAME_STATE_READY and 'game_start' not in self.timeout_info and \
                    len(self.player_group.sit_players) == self.seat_limit:
                logger.debug('start game_start timer')
                self.timeout_info['game_start'] = self.game_start_timeout_mgr.start_timer(
                    config.GAME_PLAYER_CHOOSE_TIMEOUT_SEC)
        # 取消准备，也就是站起
        elif status == 0:
            # 玩游戏不能取消准备
            if player.status >= config.USER_STATE_INGAME:
                return
            player.status = config.USER_STATE_STAND
        # 同意删除牌桌
        elif status == 2:
            player.delete_status = config.USER_STATE_AGREE_DELETE
            # 同意人数过半直接解散
            if len(self.player_group.agree_players) > self.seat_limit/2:
                # 算分
                for in_player in self.player_group.sit_players:
                    in_player.chips += in_player.round_win_chips
                self.status = config.GAME_STATE_WAIT_DELETE
                self.over_time = int(time.time())
                if self.pre_status != config.GAME_STATE_READY:
                    mj_signals.mahjong_desk_game_over.send(self, desk=self)
                self.broadcast_game_over_info(game_over=True, over_reason=config.GAME_OVER_APPLY_NOT_TIMEOUT)
                if 'count_down' in self.timeout_info:
                    self.desk_count_down_mgr.stop_timer()
                delay = 5
                self.timeout_info['count_down'] = self.desk_count_down_mgr.start_timer(delay)
        # 拒绝删除牌桌
        elif status == 3:
            player.delete_status = config.USER_STATE_DISAGREE_DELETE
            # 不同意的人数不小于过半就删除定时器
            if len(self.player_group.disagree_players) >= self.seat_limit - self.seat_limit/2:
                # 先把桌子的状态变回来
                self.status = self.pre_status
                self.pre_status = None
                # 看看定时器对不对
                if 'count_down' in self.timeout_info:
                    self.desk_count_down_mgr.stop_timer()
                    self.timeout_info.pop('count_down', None)
        # 同意上火
        elif status == 4 and self.type == config.DESK_TYPE_MJ_WZ and self.has_shanghuo:
            player.shanghuo = config.GAME_PLAYER_SHANGHUO
        # 拒绝上火
        elif status == 5 and self.type == config.DESK_TYPE_MJ_WZ and self.has_shanghuo:
            player.shanghuo = config.GAME_PLAYER_NOT_SHANGHUO
        # 飘分
        elif status == 6 and self.type == config.DESK_TYPE_MJ_WZ:
            if req.piaofen <= self.piaofen_max_num:
                player.piaofen = req.piaofen

    @save_later
    def apply_delete_desk(self, uin):
        logger.debug("uin:%s, pre_status:%s, status:%s", uin, self.pre_status, self.status)
        # 这里desk和player的处理有点不一样，desk是用的pre来保存先前状态，player里面是新开了一个字段delete_status区分开来放
        # 这里注意pre_status只存放game状态，申请状态不要存放，不然连续发两次申请就找不回之前的状态了
        if self.pre_status is None:
            self.pre_status = self.status
        else:
            return config.GAME_START_PASS

        self.status = config.GAME_STATE_APPLY_DELETE

        self.apply_uin = uin
        # 牌局没开始，直接关闭
        # 客户端会负责发退桌消息把玩家退桌，服务器只需要最后清掉桌子信息就好了
        if self.desk_remain_round == self.desk_round:
            if 'count_down' not in self.timeout_info:
                delay = 10
                self.timeout_info['count_down'] = self.desk_count_down_mgr.start_timer(delay)
            self.status = config.GAME_STATE_WAIT_DELETE
            for player in self.player_group.valid_players:
                player.delete_status = config.USER_STATE_AGREE_DELETE
            return config.GAME_START_NONE

        # 如果在游戏中，起个定时器挂着
        if 'count_down' not in self.timeout_info:
            delay = config.PLAYER_APPLY_TIMEOUT
            self.timeout_info['count_down'] = self.desk_count_down_mgr.start_timer(delay)
        # 初始化玩家的delete状态
        for player in self.player_group.valid_players:
            if player.uin != uin:
                player.delete_status = 0
            else:
                player.delete_status = config.USER_STATE_AGREE_DELETE

        return config.GAME_START_ALREADY

    # 这种只能是暗杠了，由客户端判断
    @save_later
    def option_gang_not_first(self, uin, gang_card):
        if self.status != config.GAME_STATE_INGAME:
            logger.error('desk not in game')
            # 不是在游戏中的话，就不往下走了
            return error_contrast.ERROR_NOT_IN_GAME

        player = self.player_group.get_player_by_uin(uin)
        if not player:
            logger.error('not find player, uin:%s', uin)
            return error_contrast.ERROR_CANNOT_FIND_PLAYER

        # 首要的任务是把操作位变回来
        player.op_type = []
        player.op_gang = False

        # 判断一下是否有四张牌
        same_num = 0
        for Card_it in player.card_group.card_list:
            if Card_it == Card(gang_card):
                same_num += 1

        if same_num == 4:
            self.current_player = player

            # 自己叫的杠
            for it in range(4):
                player.card_group.remove_card(gang_card)
                player.card_group.out_card_list.append(Card(gang_card))

            player.card_len -= 4

            for in_player in self.player_group.sit_players:
                if in_player.uin != uin:
                    in_player.round_gang_list.append(-config.MAHJONG_GANG)
                    in_player.total_gang_list.append(-config.MAHJONG_GANG)
                    in_player.round_win_chips += -2 * player.shanghuo * in_player.shanghuo
                    in_player.over_chips_detail[1] += -2 * player.shanghuo * in_player.shanghuo
                    player.round_win_chips += 2 * player.shanghuo * in_player.shanghuo
                    player.over_chips_detail[0] += 2 * player.shanghuo * in_player.shanghuo
            player.round_gang_list.append(config.MAHJONG_GANG)
            player.total_gang_list.append(config.MAHJONG_GANG)

            player.status = config.USER_STATE_AFTER_GANG

            # 加一个标识告诉客户端这个牌是暗杠
            player.op_list.append(config.OP_TYPE_GANG)

            # 杠完之后再叫一张牌
            self._recv_card(after_gang=True)

            # 返回消息
            for in_player in self.player_group.valid_players:
                evt = GameInfoEvt()
                evt.op_user.uin = player.uin
                evt.op_user.type = config.OP_TYPE_GANG
                self.adapt_game_round_info(evt, in_player.uin)
                evt = evt.SerializeToString()
                write_to_users(in_player.uin, proto.CMD_GAME_RECV_INFO_EVT, evt)

            return 0
        else:
            logger.error('invalid not_first_gang request')
            return error_contrast.ERROR_INVALID_REQUEST

    def test_signal(self):
        # 游戏开始的信号,先不要记录
        mj_signals.mahjong_desk_start_play.send(self, desk=self)

