# -*- coding: utf-8 -*-
"""
author: GerryLuo
error_contrast.py 错误码对照表
"""

# 参数错误
ERROR_INVALID_PARAMS = 1
# 不在牌桌内
ERROR_NOT_IN_DESK = 2
# 没有足够的房卡
ERROR_NOT_ENOUGH_CARD = 3
# 牌桌不存在
ERROR_DESK_NOT_EXIST = 4
# 牌桌内找不到玩家
ERROR_CANNOT_FIND_PLAYER = 5
# 游戏中不能退出
ERROR_CANNOT_EXIT_DESK_IN_GAME = 6
# 不在游戏中
ERROR_NOT_IN_GAME = 7
# 错误请求
ERROR_INVALID_REQUEST = 8
# 还在游戏中
ERROR_ALREADY_IN_GAME = 9
# 请同时输入用户名和密码
ERROR_ENTER_USERNAME_AND_PASSWORD = 10
# 用户名已被注册
ERROR_USERNAME_HAS_EXIST = 11
# 用户名不存在
ERROR_USERNAME_NOT_EXIST = 12
# 密码错误
ERROR_PASSWORD_IS_ERROR = 13
# 用户未登录
ERROR_NOT_LOGIN = 14
# 操作与当前应当操作人员不匹配
ERROR_NOT_RIGHT_TURN = 15
# 进入牌桌失败
ERROR_SIT_DOWN_FAIL = 16
# 举报太频繁，注意身体
ERROR_COMPLAINT_TOO_OFTEN = 17
# 非法名称
ERROR_ILLEGAL_WORD = 18
# 微信绑定不匹配
ERROR_USER_BIND_NOT_MATCH = 19
# 微信登录失败
ERROR_WX_LOGIN_FAILED = 20
# 该账号已绑定微信
ERROR_WX_BIND_ALREADY = 21
# 每个账号只能被邀请一次
ERROR_USER_HASBEEN_INVITED = 22
# 该用户不存在
ERROR_USER_INVITED_NOT_EXIST = 23
# 聊天文字不能为空
ERROR_DESK_CHAT_NONE = 24


# 对照表
ERROR_CODE_LIST = [
    {
        "id": ERROR_INVALID_PARAMS,
        "desc": u"参数错误"
    },
    {
        "id": ERROR_NOT_IN_DESK,
        "desc": u"不在牌桌内"
    },
    {
        "id": ERROR_NOT_ENOUGH_CARD,
        "desc": u"没有足够的房卡"
    },
    {
        "id": ERROR_DESK_NOT_EXIST,
        "desc": u"牌桌不存在"
    },
    {
        "id": ERROR_CANNOT_FIND_PLAYER,
        "desc": u"牌桌内找不到玩家"
    },
    {
        "id": ERROR_CANNOT_EXIT_DESK_IN_GAME,
        "desc": u"游戏中不能退出"
    },
    {
        "id": ERROR_NOT_IN_GAME,
        "desc": u"不在游戏中"
    },
    {
        "id": ERROR_INVALID_REQUEST,
        "desc": u"错误请求"
    },
    {
        "id": ERROR_ALREADY_IN_GAME,
        "desc": u"还在游戏中"
    },
    {
        "id": ERROR_ENTER_USERNAME_AND_PASSWORD,
        "desc": u"请同时输入用户名和密码"
    },
    {
        "id": ERROR_USERNAME_HAS_EXIST,
        "desc": u"用户名已被注册"
    },
    {
        "id": ERROR_USERNAME_NOT_EXIST,
        "desc": u"用户名不存在"
    },
    {
        "id": ERROR_PASSWORD_IS_ERROR,
        "desc": u"密码错误"
    },
    {
        "id": ERROR_NOT_LOGIN,
        "desc": u"用户未登录"
    },
    {
        "id": ERROR_NOT_RIGHT_TURN,
        "desc": u"操作与当前应当操作人员不匹配"
    },
    {
        "id": ERROR_SIT_DOWN_FAIL,
        "desc": u"进入牌桌失败"
    },
    {
        "id": ERROR_COMPLAINT_TOO_OFTEN,
        "desc": u"举报太频繁，注意身体"
    },
    {
        "id": ERROR_ILLEGAL_WORD,
        "desc": u"非法名称"
    },
    {
        "id": ERROR_USER_BIND_NOT_MATCH,
        "desc": u"微信绑定不匹配"
    },
    {
        "id": ERROR_WX_LOGIN_FAILED,
        "desc": u"微信登录失败"
    },
    {
        "id": ERROR_WX_BIND_ALREADY,
        "desc": u"该账号已绑定微信"
    },
    {
        "id": ERROR_USER_HASBEEN_INVITED,
        "desc": u"该账号已有邀请人"
    },
    {
        "id": ERROR_USER_INVITED_NOT_EXIST,
        "desc": u"该用户不存在"
    },
    {
        "id": ERROR_DESK_CHAT_NONE,
        "desc": u"聊天文字不能为空"
    }
]