# coding: utf8

"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : 和proto cmd相关的都放这里
"""

# ------------------------------
#     内部消息
# ------------------------------
CMD_WEBSOCKET_HEARTHEAT = 1
CMD_WEB_SEND_MSG_TO_USER = 999      # WEB SERVER给指定用户发消息
CMD_EVENT_USER_BROADCAST = 1000     # 给全部在线用户发送广播
CMD_TIME_OUT_CHECK = 10000          # 定时器消息

# ------------------------------
#     Auth消息(1001 - 4000)
# ------------------------------
CMD_REG = 1001                      # 注册
CMD_LOGIN = 1002                    # 登陆

# ------------------------------
#     Hall消息(4001 - 7000)
# ------------------------------
CMD_USER_ENTER_DESK = 4001          # 用户进入牌桌
CMD_EVENT_USER_CARD_CHANGE = 4002   # 用户房卡变化


# ------------------------------
#     Play消息(7001 - 10000)
# ------------------------------
CMD_REDIRECT_ENTER_DESK = 7001      # 内部转发进桌
CMD_REDIRECT_EXIT_DESK = 7002       # 内部转发退桌
CMD_GAME_EXIT_DESK = 7003           # 客户端请求退桌
CMD_CLIENT_NTF_START_GAME = 7004    # 客户端请求立刻开始游戏
CMD_GAME_SEND_CARD = 7005           # 出牌
CMD_GAME_CHI = 7006                 # 吃牌
CMD_GAME_PENG = 7007                # 碰牌
CMD_GAME_GANG = 7008                # 杠牌
CMD_GAME_HU = 7009                  # 胡牌
CMD_GAME_PASS = 7010                # 过牌
CMD_GAME_RECV_INFO_EVT = 7011       # 游戏内的操作通知
CMD_PLAYER_STATUS_CHANGE = 7012     # 用户状态变化通知
CMD_GAME_GANG_NOT_FIRST = 7013      # 客户端主动杠牌
CMD_APPLY_DELETE_DESK = 7014        # 申请解散牌桌
CMD_EVENT_GAME_OVER = 7015          # 通知： 游戏结束
CMD_EVENT_USER_ENTER_DESK = 7016    # 通知： 用户进入牌桌
CMD_EVENT_USER_EXIT_DESK = 7017     # 通知： 用户离开牌桌
CMD_EVENT_GAME_START = 7018         # 通知： 游戏开始


# ------------------------------
#     Common消息(10001 - 13000)
# ------------------------------
CMD_QUERY_PLAY_RECORD_LIST = 10001     # 查询麻将粗略记录
CMD_QUERY_PLAY_RECORD_DETAIL = 10002   # 查询麻将详细记录
CMD_GAME_DESK_CHAT = 10003             # 牌桌内聊天
CMD_QUERY_CREATE_PRE_BILL = 10004      # 创建预付单
CMD_QUERY_CREATE_BILL = 10005          # 收到回调创建正式订单
CMD_SET_INVITE_USER = 10009            # 设置邀请人


