# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url

urlpatterns = patterns(
    '',
    url(r'^$', 'background.views.index', name="background_index"),

    # 查询在线用户
    url(r'^online_users$', 'background.views.online_users'),

    # 查询牌桌信息
    url(r'^desk_query$', 'background.views.desk_query', name='desk_query'),

    # 牌桌监控，好吧
    url(r'^desk_card_info$', 'background.views.desk_card_info', name='desk_card_info'),

    # 设置公告
    url(r'^set/system_announcement$', 'background.views.set_system_announcement', name="set_system_announcement"),

    # 查询在线桌子
    url(r'^query_active_desks$', 'background.views.query_active_desks', name='query_active_desks'),

    # 修改用户房卡
    url(r'^room_card$', 'background.views.modify_room_card'),

    # 上传热更包
    url(r'^upload', 'background.views.upload_file'),
)
