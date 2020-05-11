# coding: utf8

"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : 公共模块server
"""

import datetime
from firefly.server.globalobject import GlobalObject, remoteserviceHandle
from common.log import logger
from common.mahjong_pb2 import MyPlayRecordListRsp, RoundPlayRecordsReq, DeskChatReq, DeskChatEvt, UserCreatePreBill, \
        CreateFormalBill, RoundPlayRecordsRsp, SetInviteUserRsp, SetInviteUserReq
from common.models import DeskRecord, Commodity, User
from common import error_contrast, proto
from common.firefly_utils import write_to_users
from common.forbidden_words_mgr import ForbiddenWordsMgr
import config
from common.redis_user_manager import RedisUserMgr
from common.bus_func import user_room_card_notify, desk_required, pre_game_function


def doWhenStop():
    """
    服务器关闭前的处理
    :return:
    """
    logger.debug("****    The [common] server is shut down ...    ****")


GlobalObject().stophandler = doWhenStop


@remoteserviceHandle('_transfer_')
# CMD_QUERY_PLAY_RECORD_LIST = 10001
@pre_game_function
def common_function_10001(request):
    user = request['user']
    record_ids = user.desk_records or list()

    records = list()
    if record_ids:
        records = DeskRecord.objects.filter(uuid__in=record_ids).order_by('-id')[:100]

    rsp = MyPlayRecordListRsp()
    rsp.ret = 0

    # logger.debug('records:%s', records)

    tmp_pre_game_round = 0
    for record in records:
        # 如果后一条记录的game_round大于等于前一条记录的game_round，那肯定就是新记录了
        if record.game_round >= tmp_pre_game_round:
            # 赋值
            rsp_record = rsp.record_list.add()
            rsp_record.roundid = record.uuid
            rsp_record.deskid = record.desk_id
            rsp_record.game_round = record.game_round
            rsp_record.desk_round = record.desk_model['desk_round']
            rsp_record.bird_card.extend(record.desk_model['desk_bird_card'])
            rsp_record.type = record.desk_model['desk_type']
            rsp_record.seat_limit = record.desk_model['desk_seat_limit']
            rsp_record.win_type = record.desk_model['desk_win_type']
            rsp_record.extra_type.hongzhong = record.desk_model['desk_has_laizi']
            rsp_record.extra_type.qidui = record.desk_model['desk_can_win_by_qidui']
            rsp_record.extra_type.zhuaniao = record.desk_model['desk_bird_num']
            rsp_record.extra_type.piaofen = record.desk_model['desk_piaofen_max_num']
            rsp_record.extra_type.shanghuo = record.desk_model['desk_has_shanghuo']
            rsp_record.over_time = record.desk_model['desk_over_time']
            rsp_record.master_uin = record.desk_model['desk_master_uin']
            rsp_record.winners.extend(record.desk_model['desk_winners'])

            for uin, data in record.user_data.items():
                evt_user_info = rsp_record.result.add()
                evt_user_info.uin = int(uin)
                evt_user_info.role = data['role']
                evt_user_info.chips = data['chips']
                evt_user_info.round_win_chips = data['round_win_chips']
                evt_user_info.round_chi_num = data['round_chi_num']
                evt_user_info.round_peng_num = data['round_peng_num']
                evt_user_info.round_gang_list.extend(data['round_gang_list'])
                evt_user_info.round_hu_list.extend(data['round_hu_list'])
                evt_user_info.round_win_list.extend(data['round_win_list'])
                evt_user_info.total_chi_num = data['total_chi_num']
                evt_user_info.total_peng_num = data['total_peng_num']
                evt_user_info.total_gang_list.extend(data['total_gang_list'])
                evt_user_info.total_hu_list.extend(data['total_hu_list'])
                evt_user_info.total_win_list.extend(data['total_win_list'])
                evt_user_info.piaofen = data['piaofen']
                evt_user_info.shanghuo = data['shanghuo']
                evt_user_info.bird_num = data['bird_num']
                evt_user_info.cards.extend(data['cards'])
                evt_user_info.out_cards.extend(data['out_cards'])
                evt_user_info.op_list.extend(data['op_list'])
                evt_user_info.over_chips_details.extend(data['over_chips_details'])
                evt_user_info.nick = data['nick']
                evt_user_info.seatid = data['seatid']
                evt_user_info.sex = data['sex']
                evt_user_info.portrait = data['portrait'] if data['portrait'] else ''
        tmp_pre_game_round = record.game_round

    # logger.debug('rsp:%s', rsp)
    return rsp.SerializeToString()


@remoteserviceHandle('_transfer_')
# CMD_QUERY_PLAY_RECORD_DETAIL = 10002
@pre_game_function
def common_function_10002(request):
    """
    查询牌局纪录详情
    :param request:
    :return:
    """
    req = RoundPlayRecordsReq()
    req.ParseFromString(request['body'])
    rsp = RoundPlayRecordsRsp()
    rsp.ret = 0

    records = DeskRecord.objects.filter(uuid=req.round_id)
    if not records:
        rsp.ret = error_contrast.ERROR_INVALID_PARAMS
        return rsp.SerializeToString()

    # 客户端不带值时是0
    if req.game_round_index:
        logger.debug('one game record, game_index:%s', req.game_round_index)
        for record in records:
            if record.game_round == req.game_round_index:
                rsp_record = rsp.record_list.add()
                rsp_record.roundid = record.uuid
                rsp_record.deskid = record.desk_id
                rsp_record.game_round = record.game_round
                rsp_record.desk_round = record.desk_model['desk_round']
                rsp_record.bird_card.extend(record.desk_model['desk_bird_card'])
                rsp_record.type = record.desk_model['desk_type']
                rsp_record.seat_limit = record.desk_model['desk_seat_limit']
                rsp_record.win_type = record.desk_model['desk_win_type']
                rsp_record.extra_type.hongzhong = record.desk_model['desk_has_laizi']
                rsp_record.extra_type.qidui = record.desk_model['desk_can_win_by_qidui']
                rsp_record.extra_type.zhuaniao = record.desk_model['desk_bird_num']
                rsp_record.extra_type.piaofen = record.desk_model['desk_piaofen_max_num']
                rsp_record.extra_type.shanghuo = record.desk_model['desk_has_shanghuo']
                rsp_record.over_time = record.desk_model['desk_over_time']
                rsp_record.master_uin = record.desk_model['desk_master_uin']
                rsp_record.winners.extend(record.desk_model['desk_winners'])

                for uin, data in record.user_data.items():
                    evt_user_info = rsp_record.result.add()
                    evt_user_info.uin = int(uin)
                    evt_user_info.role = data['role']
                    evt_user_info.chips = data['chips']
                    evt_user_info.round_win_chips = data['round_win_chips']
                    evt_user_info.round_chi_num = data['round_chi_num']
                    evt_user_info.round_peng_num = data['round_peng_num']
                    evt_user_info.round_gang_list.extend(data['round_gang_list'])
                    evt_user_info.round_hu_list.extend(data['round_hu_list'])
                    evt_user_info.round_win_list.extend(data['round_win_list'])
                    evt_user_info.total_chi_num = data['total_chi_num']
                    evt_user_info.total_peng_num = data['total_peng_num']
                    evt_user_info.total_gang_list.extend(data['total_gang_list'])
                    evt_user_info.total_hu_list.extend(data['total_hu_list'])
                    evt_user_info.total_win_list.extend(data['total_win_list'])
                    evt_user_info.piaofen = data['piaofen']
                    evt_user_info.shanghuo = data['shanghuo']
                    evt_user_info.bird_num = data['bird_num']
                    evt_user_info.cards.extend(data['cards'])
                    evt_user_info.out_cards.extend(data['out_cards'])
                    evt_user_info.op_list.extend(data['op_list'])
                    evt_user_info.over_chips_details.extend(data['over_chips_details'])
                    evt_user_info.nick = data['nick']
                    evt_user_info.seatid = data['seatid']
                    evt_user_info.sex = data['sex']
                    evt_user_info.portrait = data['portrait'] if data['portrait'] else ''
    else:
        logger.debug('one desk record')
        for record in records:
            rsp_record = rsp.record_list.add()
            rsp_record.roundid = record.uuid
            rsp_record.deskid = record.desk_id
            rsp_record.game_round = record.game_round
            rsp_record.desk_round = record.desk_model['desk_round']
            rsp_record.bird_card.extend(record.desk_model['desk_bird_card'])
            rsp_record.type = record.desk_model['desk_type']
            rsp_record.seat_limit = record.desk_model['desk_seat_limit']
            rsp_record.win_type = record.desk_model['desk_win_type']
            rsp_record.extra_type.hongzhong = record.desk_model['desk_has_laizi']
            rsp_record.extra_type.qidui = record.desk_model['desk_can_win_by_qidui']
            rsp_record.extra_type.zhuaniao = record.desk_model['desk_bird_num']
            rsp_record.extra_type.piaofen = record.desk_model['desk_piaofen_max_num']
            rsp_record.extra_type.shanghuo = record.desk_model['desk_has_shanghuo']
            rsp_record.over_time = record.desk_model['desk_over_time']
            rsp_record.master_uin = record.desk_model['desk_master_uin']
            rsp_record.winners.extend(record.desk_model['desk_winners'])

            for uin, data in record.user_data.items():
                evt_user_info = rsp_record.result.add()
                evt_user_info.uin = int(uin)
                evt_user_info.role = data['role']
                evt_user_info.chips = data['chips']
                evt_user_info.round_win_chips = data['round_win_chips']
                evt_user_info.round_chi_num = data['round_chi_num']
                evt_user_info.round_peng_num = data['round_peng_num']
                evt_user_info.round_gang_list.extend(data['round_gang_list'])
                evt_user_info.round_hu_list.extend(data['round_hu_list'])
                evt_user_info.round_win_list.extend(data['round_win_list'])
                evt_user_info.total_chi_num = data['total_chi_num']
                evt_user_info.total_peng_num = data['total_peng_num']
                evt_user_info.total_gang_list.extend(data['total_gang_list'])
                evt_user_info.total_hu_list.extend(data['total_hu_list'])
                evt_user_info.total_win_list.extend(data['total_win_list'])
                evt_user_info.piaofen = data['piaofen']
                evt_user_info.shanghuo = data['shanghuo']
                evt_user_info.bird_num = data['bird_num']
                evt_user_info.cards.extend(data['cards'])
                evt_user_info.out_cards.extend(data['out_cards'])
                evt_user_info.op_list.extend(data['op_list'])
                evt_user_info.over_chips_details.extend(data['over_chips_details'])
                evt_user_info.nick = data['nick']
                evt_user_info.seatid = data['seatid']
                evt_user_info.sex = data['sex']
                evt_user_info.portrait = data['portrait'] if data['portrait'] else ''

    return rsp.SerializeToString()


@remoteserviceHandle('_transfer_')
# CMD_GAME_DESK_CHAT = 10003
@pre_game_function
@desk_required(lock_desk=False, restore_later=False)
def common_function_10003(request):
    """
    桌子内聊天
    """
    req = DeskChatReq()
    req.ParseFromString(request['body'])
    rsp = DeskChatEvt()
    rsp.ret = 0

    logger.debug('req:%s', req)
    # 只有坐着的玩家才能聊天
    sit_uins = [player.uin for player in request['desk'].player_group.valid_players]
    if request['user'].uin not in sit_uins:
        return

    logger.debug('enter type')
    # 文字聊天
    if req.type == 1:
        if not req.content:
            rsp.ret = error_contrast.ERROR_DESK_CHAT_NONE
            return rsp.SerializeToString()

        if req.content:
            # 这里要检查是否包含非法字符
            rsp.content = ForbiddenWordsMgr.replace_word(req.content)
    # 语音聊天
    elif req.type == 2:
        # 索引不能为0
        if req.index == 0:
            rsp.ret = error_contrast.ERROR_DESK_CHAT_NONE
            return rsp.SerializeToString()

        rsp.index = req.index
    else:
        return

    rsp.op_uin = request['user'].uin
    rsp.sex = request['user'].sex

    # In me the tiger sniffs the rose
    logger.debug('send evt')
    for player in request['desk'].player_group.valid_players:
        evt = rsp.SerializeToString()
        write_to_users(player.uin, proto.CMD_GAME_DESK_CHAT, evt)


@remoteserviceHandle('_transfer_')
# CMD_QUERY_CREATE_PRE_BILL = 10004
def common_function_10004(request):
    ntf = UserCreatePreBill()
    ntf.ParseFromString(request['body'])
    uin = ntf.uin
    name = ntf.name
    item_id = ntf.item_id

    user = RedisUserMgr().get_user(uin)

    logger.debug('create_pre_bill, uin:%s, name:%s, item_id:%s', uin, name, item_id)
    # 把预付单先加进去
    Commodity(
        uin=user.uin,
        channel=user.channel,
        name=config.COMMODITY_ITEM_DICT[name].get('name'),
        item_type=config.COMMODITY_ITEM_DICT[name].get('type'),
        currency=config.COMMODITY_ITEM_DICT[name].get('cur'),
        amount=config.COMMODITY_ITEM_DICT[name].get('amt'),
        item_id=item_id,
        bill_state=0, # 0代表订单生成
    ).save()


@remoteserviceHandle('_transfer_')
# CMD_QUERY_CREATE_BILL = 10005
def common_function_10005(request):
    ntf = CreateFormalBill()
    ntf.ParseFromString(request['body'])
    uin = ntf.uin
    item_id = ntf.item_id

    bill = Commodity.objects.filter(uin=uin, item_id=item_id)
    if bill:
        bill.update(bill_state=1)

    # 下发房卡变化通知
    user = RedisUserMgr().get_user(uin)
    user_room_card_notify(user)

    # 通知支付成功信号
    # signals.user_recharge.send(user, user=user, item_id=item_id, cost=cost, pay_type=ntf.pay_type)


@remoteserviceHandle('_transfer_')
# CMD_SET_INVITE_USER = 10009
def common_function_10009(request):
    req = SetInviteUserReq()
    rsp = SetInviteUserRsp()

    req.ParseFromString(request['body'])

    db_user = User.objects.filter(id=req.uin).first()
    if not db_user:
        rsp.ret = error_contrast.ERROR_USER_INVITED_NOT_EXIST
        return rsp.SerializeToString()

    uin = request['uin']
    user = RedisUserMgr().get_user(uin)
    if user.has_invited:
        rsp.ret = error_contrast.ERROR_USER_HASBEEN_INVITED
        return rsp.SerializeToString()

    # logger.debug('req.uin:%d', req.uin)
    rsp.ret = 0
    user.update(dict(
        user_inviter=req.uin,
        has_invited=True,
    ))
    # user.user_inviter = req.uin
    # user.has_invited = True

    return rsp.SerializeToString()

