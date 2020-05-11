# -*- coding: utf-8 -*-
import json
import functools
import config
import uuid
import os
from operator import attrgetter
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from common.redis_user_manager import RedisUserMgr
from common.redis_user import MemUser
from common.redis_fd import rds_tmp, rds
from common.bus_func import load_desk, load_desks, modify_card
from background.forms import ModifyRoomCardForm, DeskQueryForm, BillBroadcast
from common.log import logger
from common.desk_mgr_controller import MjDeskMgrController
from collections import defaultdict
from django.http import HttpResponse


@login_required
def index(request):
    return render(request, 'index.html')


@login_required
def online_users(request):
    dict_desk_id = defaultdict(int)
    for _, desk_type, desk_list in MjDeskMgrController.get_all_desks():
        dict_desk_id[desk_list[0]] += desk_list[1]

    keys = rds.keys(MemUser.KEY_PRE + '*')

    # logger.debug('keys:%s, user_json_list:%s', keys, user_json_list)
    hall_online = 0
    desk_online = 0
    for key in keys:
        user_dict = rds.hgetall(key)
        logger.debug('user_dict:%s, status:%s', user_dict, user_dict.get('status'))
        if not user_dict.has_key('status'):
            continue
        if user_dict.get('status') == str(config.LOGIN_USER_STATUS_ONLINE):
            hall_online += 1
        if user_dict.get('status') == str(config.LOGIN_USER_STATUS_PLAYING):
            desk_online += 1

    # logger.debug('total_online : %s', total_online)
    list_room_id = [(k, dict_desk_id[k]) for k in sorted(dict_desk_id.keys())]

    # 因为暂时没有心跳来维护status状态，所以会出现桌子里面有人而总人数为0的情况
    return render(request, 'online_info.html', dict(
        type_items=list_room_id,
        hall_online=hall_online,
        desk_online=desk_online,
    ))


@login_required
def desk_query(request):
    """
    获取desk信息
    :param request:
    :return:
    """
    if not request.GET:
        # 说明是第一次进
        return render(request, 'read.html', dict(
            form=DeskQueryForm()
        ))

    form = DeskQueryForm(request.GET)
    if not form.is_valid():
        return render(request, 'read.html', dict(
            form=form
        ))

    from common.mj_desk import MjDesk

    desk_json = rds_tmp.get(MjDesk.get_desk_redis_key(form.cleaned_data['desk_id']))
    if not desk_json:
        return render(request, 'read.html', dict(
            form=form,
            result='no such desk'
        ))

    tpl = u"""
    <pre>{code}</pre>
    """

    desk_json = json.loads(desk_json)
    return render(request, 'read.html', dict(
        form=form,
        result=tpl.format(
            code=json.dumps(desk_json, indent=4, ensure_ascii=False)
        )
    ))


@login_required
def desk_card_info(request):
    from common.card import Card

    if not request.GET:
        # 说明是第一次进
        return render(request, 'desk_card_info.html', dict(
            form=DeskQueryForm()
        ))

    form = DeskQueryForm(request.GET)
    if not form.is_valid():
        return render(request, 'desk_card_info.html', dict(
            form=form
        ))

    dst_desk = load_desk(form.cleaned_data['desk_id'])
    if not dst_desk:
        return render(request, 'desk_card_info.html', dict(
            form=form,
            result='no such desk'
        ))

    if dst_desk.status != config.GAME_STATE_INGAME:
        return render(request, 'desk_card_info.html', dict(
            form=form,
            result='game not begin'
        ))

    share_cards = [Card(num).human_str for num in dst_desk.share_cards]
    _list = []
    if dst_desk.send_card_uin:
        is_send_card = True
        extend_card = Card(dst_desk.extend_card).human_str
        current_uin = dst_desk.send_card_uin
    else:
        is_send_card = False
        current_player = dst_desk.player_group.get_player_by_uin(dst_desk.recv_card_uin)
        extend_card = current_player.card_group.card_list[-1].human_str
        current_uin = dst_desk.recv_card_uin

    for player in dst_desk.player_group.active_players:
        _list.append(dict(
            belong=u'%s-%s' % (player.user.nick, player.uin),
            cards=[p_card.human_str for p_card in player.card_group.card_list],
            out_cards=[p_card.human_str for p_card in player.card_group.out_card_list],
            dis_cards=[p_card.human_str for p_card in player.card_group.discard_list],
            op_list=player.op_list,
            op_type=player.op_type if not player.need_wait else None,
        ))

    return render(request, 'desk_card_info.html', dict(
        form=form,
        card_list=_list,
        share_cards_list=share_cards,
        is_send_card=is_send_card,
        extend_card=extend_card,
        current_uin=current_uin,
    ))


@login_required
def set_system_announcement(request):
    """
    设置系统公告
    :param request:
    :return:
    """
    content_all = rds.get(config.BILLBOARD_REDIS_KEY) or ''
    content_all = content_all.encode('utf-8')
    if content_all:
        content_id, content = content_all.split('|')
    else:
        content_id = content = ''

    # logger.debug('id:%s, content:%s', content_id, content)

    if request.method == "GET":
        return render(request, 'write.html', dict(
            form=BillBroadcast(initial=dict(content=content)),
            prompt=u"设置系统公告",
        ))

    form = BillBroadcast(request.POST)
    if not form.is_valid():
        return render(request, 'write.html', dict(
            form=form,
            prompt=u"设置系统公告",
        ))

    content = form.cleaned_data['content']
    content_id = uuid.uuid4().hex
    content_all = content_id + '|' + content

    # logger.error(content)

    rds.set(config.BILLBOARD_REDIS_KEY, content_all)

    return render(request, 'write.html', dict(
        form=form,
        result=u"设置成功，新的公告内容：<br><h3>%s</h3>" % content,
        prompt=u"设置系统公告",
    ))


# 查询所有在线牌桌信息
@login_required
def query_active_desks(request):
    return render(request, 'query_active_desks.html', dict(
        desk_list=sorted(load_desks(), key=attrgetter('id')),
    ))


# 修改房卡数
@login_required
def modify_room_card(request):
    # 判断用户存在不存在

    # 修改使用post请求
    form = ModifyRoomCardForm(request.POST)
    if not form.is_valid():
        return render(request, 'write.html', dict(
            form=form,
        ))

    uin = form.cleaned_data['user_id']
    room_card_num = form.cleaned_data['room_card_num']
    remark = request.user.username + ' : ' + form.cleaned_data['remark']

    user = RedisUserMgr().get_user(uin)

    modify_card(user, room_card_num, None, remark, user_in_web=True)

    return render(request, 'write.html', dict(
        form=form,
    ))


@login_required
def upload_file(request):
    # logger.debug("enter")
    if request.method == 'POST':
        logger.debug("enter upload_file")
        path_root = "/data/release/download"  # 上传文件的主目录
        myFile = request.FILES.get("file", None)  # 获取上传的文件，如果没有文件，则默认为None
        if not myFile:
            dstatus = "请选择需要上传的文件!"
        else:
            path_ostype = os.path.join(path_root, request.POST.get("ostype"))
            path_version = os.path.join(path_ostype, str(config.APP_UPDATE_VERSION))
            # 还是不要这样命名吧，是什么就写什么名称
            # if request.POST.get("ostype") == 'code':
            #     myFile.name = 'game_code_{0}.zip'.format(config.APP_UPDATE_VERSION)
            path_dst_file = os.path.join(path_version, myFile.name)
            if os.path.isfile(path_dst_file):
                dstatus = "%s 已存在!" % (myFile.name)
            else:
                if os.path.isdir(path_version):
                    pass
                else:
                    os.mkdir(path_version)

                destination = open(path_dst_file, 'wb+')  # 打开特定的文件进行二进制的写操作
                for chunk in myFile.chunks():  # 分块写入文件
                    destination.write(chunk)
                destination.close()
                dstatus = "%s 上传成功!" % (myFile.name)
        return HttpResponse(str(dstatus))

    return render(request, 'upload_file.html')

