# -*- coding: utf-8 -*-

"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : 全局配置
"""
# redis 链接
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_DB_TMP = 1

# redis锁超时时间(秒)
# REDIS_LOCK_TIMEOUT = 3
REDIS_LOCK_TIMEOUT = 6
REDIS_LOCK_SLEEP = 0.01

# 心跳最长时间(秒)
HEARTBEAT_MAX_INTERVAL = 300

# 超过多长时间打印消耗log(毫秒)
COUNT_COSTS_TIME = 500

# firefly net ws listen port
GATEWAY_WS_PORT = 21000
# firefly net tcp ip&port
GATEWAY_TCP_HOST = '127.0.0.1'
GATEWAY_TCP_PORT = 20000

APP_STATUS_NOT_UPDATE = 0
APP_STATUS_ADVISE_UPDATE = 1
APP_STATUS_FORCE_UPDATE = 2
PACKAGE_UPDATE_STATUS = [
    (APP_STATUS_NOT_UPDATE, u'不更新'),
    (APP_STATUS_ADVISE_UPDATE, u'建议更新'),
    (APP_STATUS_FORCE_UPDATE, u'强制更新'),
]

CLIENT_OS_UNKNOW = 'unknow'
CLIENT_OS_ANDROID = 'android'
CLIENT_OS_IOS = 'ios'
CLIENT_OS = [
    (CLIENT_OS_UNKNOW, u'未知'),
    (CLIENT_OS_ANDROID, u'安卓'),
    (CLIENT_OS_IOS, u'苹果')
]

USER_LANGUAGE_CHOICES = [
    ('cn', u'汉语'),
    ('jp', u'日语'),
    ('th', u'泰语'),
    ('en', u'英语'),
]

BLOCK_REASON_CHOICES = [

]

SEX_MALE = 0
SEX_FEMALE = 1

USER_SEX = {
    SEX_MALE: u'男',
    SEX_FEMALE: u'女',
}

LOGIN_USER_STATUS_OFFLINE = 0   # 不在线
LOGIN_USER_STATUS_ONLINE = 1    # 在线但没有打麻将
LOGIN_USER_STATUS_PLAYING = 2   # 在打麻将

REDIRECT_DEV_ID = []

CRIME_APP_DICT = {
    'CN_DEXIAN_IOS': [],
    'CN_DEXIAN_ANDROID': [],
}


MIN_MAHJONG_DESK_ID = 100000
MAX_MAHJONG_DESK_ID = 999999

WX_PUBLIC_ID = 'dexianyl'
WX_AGENT_ID = 'dexiandl'

RET_SIT_DOWN_FAILED = 2
RET_SIT_DOWN_RECONNECT = 1
RET_SIT_DOWN_SUCCESS = 0

# 退桌原因
USER_EXIT_REASON_USER_REQUEST = 0
USER_EXIT_REASON_DELETE_DESK = 1

# 桌子的redis记录存在时长
MJ_DESK_TIMEOUT_SEC = 24 * 3600

# 用户 状态
USER_STATE_NORMAL = 1000  # 不存在
USER_STATE_STAND = 1010  # 未准备
USER_STATE_READY = 1020  # 已准备
USER_STATE_INGAME = 1030  # 玩游戏中
USER_STATE_AFTER_GANG = 1031  # 杠完牌后打的牌

# 解散房间状态
USER_STATE_AGREE_DELETE = 1001  # 同意解散房间
USER_STATE_DISAGREE_DELETE = 1002  # 拒绝解散房间

# 用户牌局内角色:
USER_ROLE_NORMAL = 0        # 普通用户
USER_ROLE_DEALER = 1        # 庄家

# 状态
GAME_STATE_WAIT_DELETE = -1  # 即将关闭，用上这个状态代表桌子是肯定要被删除的
GAME_STATE_READY = 0  # 准备中
GAME_STATE_INGAME = 1  # 游戏中
GAME_STATE_APPLY_DELETE = 2  # 等待投票解散中

MAHJONG_NO_GANG = 0
MAHJONG_GANG = 1
MAHJONG_OUT_GANG = 2
MAHJONG_DIAN_GANG = 3

# 控制redis用的
DESK_MANAGE_MJ = 0

# 牌桌类型
DESK_TYPE_MJ_WZ = 1  # 万载麻将
DESK_TYPE_MJ_ZZ = 2  # 转转麻将

# YY麻将
REDIS_KEY_DESK_MGR_MAHJONG = 'desk_mgr_mahjong'

# 叫牌通过桌子内的recv_card_uin标识来发给客户端
OP_TYPE_CHI = 1
OP_TYPE_PENG = 2
OP_TYPE_GANG = 3
OP_TYPE_OUT_GANG = 4
OP_TYPE_DIAN_GANG = 5
OP_TYPE_SEND_CARD = 6
OP_TYPE_PASS = 7

MAHJONG_FORMATION_HETANG = 0
MAHJONG_FORMATION_PINGHU = 1
MAHJONG_FORMATION_PINGHU_QUANQIUREN = 2
MAHJONG_FORMATION_DADUI = 3
MAHJONG_FORMATION_DADUI_QUANQIUREN = 4
MAHJONG_FORMATION_QINGYISE = 5
MAHJONG_FORMATION_QINGYISE_QUANQIUREN = 6
MAHJONG_FORMATION_QINGYISE_DADUI = 7
MAHJONG_FORMATION_QINGYISE_DADUI_QUANQIUREN = 8
MAHJONG_FORMATION_SHISANLAN = 9
MAHJONG_FORMATION_QIXING_SHISANLAN = 10
MAHJONG_FORMATION_QIDUI = 11
MAHJONG_FORMATION_QIDUI_HAOHUA = 12
MAHJONG_FORMATION_QIDUI_SHUANGHAOHUA = 13
MAHJONG_FORMATION_QIDUI_SANHAOHUA = 14
MAHJONG_FORMATION_QINGYISE_QIDUI = 15
MAHJONG_FORMATION_QINGYISE_QIDUI_HAOHUA = 16
MAHJONG_FORMATION_QINGYISE_QIDUI_SHUANGHAOHUA = 17
MAHJONG_FORMATION_QINGYISE_QIDUI_SANHAOHUA = 18

# 配牌开关
PLAY_DEBUG_ASSIGN_CARD = False
ASSIGN_CARD = [1,1,2,2,3,3,7,7,9,9,10,10,13, 1,1,2,2,3,3,7,7,9,9,10,10,13]

# 一张房卡等于几局
ONE_ROOM_CARD_NUM_WZ = 8
ONE_ROOM_CARD_NUM_ZZ = 8

# 可赢牌的方法
DESK_WIN_TYPE_DIANPAO = 1
DESK_WIN_TYPE_ZIMO = 2

# 解散时返回的牌桌状态，是对于整个房间生存周期过程的判定
# 如果开始了那么就是ALREADY，一局都没开才是NONE
# PASS是用来做容错的，如果是PASS就直接过掉，不回消息给客户端
GAME_START_NONE = 0
GAME_START_ALREADY = 1
GAME_START_PASS = 2

# 每个玩家的投票超时时长
PLAYER_APPLY_TIMEOUT = 5*60

# 选择飘分和上火的超时时间，比客户端要稍微晚一点
GAME_PLAYER_CHOOSE_TIMEOUT_SEC = 17
GAME_WAIT_READY_TIMEOUT_SEC = 22  # 等待注销

# 上火选择
GAME_PLAYER_NOT_SHANGHUO = 1
GAME_PLAYER_SHANGHUO = 2

# 赢牌类型
GAME_WIN_TYPE_ZIMO = 1
GAME_WIN_TYPE_JIEPAO = 2
GAME_WIN_TYPE_FANGPAO = 3

# 牌局结束类型
GAME_OVER_NORMAL = 0
GAME_OVER_APPLY_NOT_TIMEOUT = 1
GAME_OVER_APPLY_TIMEOUT = 2


# MONGO
STATISTIC_TB_CARD_INVOICE = 'card_invoice'

# 游戏开始
STATISTIC_MAHJONG_DESK_GAME_START = 1
# 游戏结束
STATISTIC_MAHJONG_DESK_GAME_OVER = 2
# 后台修改用户房卡
STATISTIC_MG_MODIFY_USER_CARD = 100
# 玩牌消耗房卡
STATISTIC_PLAY_GAME_USED_CARD = 101


# 微信配置
WX_GZH_AESKEY = 'N9RHwxTlol1hmLnrB51CWfssnTGxJGPHSQ8Tf0Tw2lz'

WX_GZH_TOKEN = 'wzdexian2016'

WX_PAY_SECREAT = 'OLbgAXLChhEOWplxo81nXSxPGZ0sWrUJ'


# 订单
SUCCESS_BUY_USER_REDIS_KEY = 'success_buy_users'
WX_BUY_RETURN_USER_REDIS_KEY = 'wx_return_buy_users'

# 微信的appid
WX_LOGIN_APPID = 'wxae92b72d366fb3b2'

WX_LOGIN_APPID_CONF = {
    "wxae92b72d366fb3b2": "c4d196c671453ae0c0cc711c21a0632a",
}

# 根据渠道号的映射
WX_LOGIN_CHANNEL_TO_APPID = {
    'CN_DEXIAN_IOS': 'wxae92b72d366fb3b2',
    'CN_DEXIAN_ANDROID': 'wxae92b72d366fb3b2',
}

ONLY_PAY_SECRET = '4Sr0owO2ikp2x3^EJ$s3wn%M92@$Q6VB'


PAY_TYPE_CARD = 0
PAY_TYPE_CHOICE = [
    (PAY_TYPE_CARD, u'房卡'),
]

CURRENCY_TYPE_CNY = 'CNY'
CURRENCY_TYPE_CHOICES = [
    (CURRENCY_TYPE_CNY, u'CNY'),
]

FORBIDDEN_WORDS_LIST = [
    u"习近平",
    u"刁近平",
]

COMMODITY_ITEM_LIST = [
    dict(
        name='card_15_5',
        type=PAY_TYPE_CARD,
        amt=15.0,
        cur=CURRENCY_TYPE_CNY,
        count=5,
    ),
    dict(
        name='card_30_10',
        type=PAY_TYPE_CARD,
        amt=30.0,
        cur=CURRENCY_TYPE_CNY,
        count=10,
    ),
    dict(
        name='card_150_50',
        type=PAY_TYPE_CARD,
        amt=150.0,
        cur=CURRENCY_TYPE_CNY,
        count=50,
    ),
]
COMMODITY_ITEM_DICT = dict([(it['name'], it) for it in COMMODITY_ITEM_LIST])


# 间隔多长时间触发一次redis检查(秒)
TIMER_CHECKER_INTERVAL = 0.1

BRIDGE_CONNECT_INTERVAL = 1.5

REDIS_KEY_DESK_RECORD_PREFIX = 'desk_record:'
REDIS_KEY_DESK_RECORD_EXPIRE_TIME = 60 * 60 * 24 * 2

BILLBOARD_REDIS_KEY = 'hall_billboard'

# sdk http请求的timeout超时
SDK_HTTP_TIMEOUT = 10

# 云信token
SDK_YUNXIN_TOKEN = 'd0cd2d4f66584843cc9a5ba72b33279a'

# 房卡变动原因
ROOM_CHANGE_BY_INVITE_PALYING = 1

# 房卡消耗开关
OPEN_ROOM_CARD_USED = False

# 热更相关
APP_UPDATE_VERSION = 170801231730


