# coding: utf8

"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : 牌桌内的玩家对象
"""

import config
from common.redis_user_manager import RedisUserMgr


class Player(object):
    """
    牌桌上的用户
    """

    # 所属的用户组
    uin = 0

    desk_id = None
    seatid = None
    status = None
    card_group = None

    # 开始置为0 普通人
    role = 0

    # 玩家分数
    chips = None

    # 结算明细
    over_chips_detail = []

    # 记录每局的输赢筹码，下一局清零
    round_win_chips = 0
    # 没有飘分上火之前的分
    round_win_chips_before = 0

    # 记录用户进桌时间戳
    enter_time = 0

    # 一些标记, 32位
    flags = 0

    # 现在有多少张牌
    card_len = 0

    # 可以进行什么操作，根据这个对player的操作状态做判定
    op_type = []

    # 这些都是传递下去的状态
    op_chi = False
    op_peng = False
    op_gang = False
    op_hu = False

    # 记录用户总的吃碰杠胡次数
    round_chi_num = 0
    round_peng_num = 0
    # 杠也一样，一局可能出现多次杠
    round_gang_list = []
    # 胡牌有一炮多响，所以用list吧
    round_hu_list = []
    round_win_list = []
    total_chi_num = 0
    total_peng_num = 0
    total_gang_list = []
    total_hu_list = []
    total_win_list = []

    # 操作前是否需要等待更高优先级的人操作
    need_wait = True

    # 进行的操作列表
    op_list = []

    # 解散房间状态
    delete_status = 0
    # 飘分 不飘分：0 飘1分：1 飘两分：2 还没选：-1
    # 结算时算总飘分，比如总分是2分，那就是3倍
    piaofen = -1
    # 上火 选择上火2 不选择上火1 这样方便结算
    shanghuo = -1
    shanghuo_keeps_num = 4
    # 抓到的鸟数
    bird_num = 0

    # 万载麻将赢牌锁，只有当被加锁的人出牌后才解锁
    win_mutex_card = []

    @property
    def user(self):
        return RedisUserMgr().get_user(self.uin)

    def __init__(self, uin=None, desk_id=None):
        # 加上这个，不会优化指向上一个相同对象，正宗的全新建一个对象（深拷贝）
        # 不是注释掉这个原因导致浅拷贝，应该是初始化不完全导致的浅拷贝
        super(Player, self).__init__()

        # 这里都要写一遍，不然__dict__里面没有对应的属性
        self.uin = uin
        self.desk_id = desk_id
        self.chips = 0
        self.seatid = None
        self.status = None
        self.card_group = None
        self.role = 0
        self.over_chips_detail = []
        self.round_win_chips = 0
        self.round_win_chips_before = 0
        self.enter_time = 0
        self.flags = 0
        self.card_len = 0
        self.op_type = []
        self.op_chi = False
        self.op_peng = False
        self.op_gang = False
        self.op_hu = False
        self.round_chi_num = 0
        self.round_peng_num = 0
        self.round_gang_list = []
        self.round_hu_list = []
        self.round_win_list = []
        self.total_chi_num = 0
        self.total_peng_num = 0
        self.total_gang_list = []
        self.total_hu_list = []
        self.total_win_list = []
        self.need_wait = True
        self.op_list = []
        self.delete_status = 0
        self.piaofen = -1
        self.shanghuo = -1
        self.shanghuo_keeps_num = 4
        self.bird_num = 0
        self.win_mutex_card = []
        self.reset_details()
        # 放到这里，暂把飘分和上火当做固定属性，选完就不用再选了
        # 如果是每局都需要选就放到re_init里面去
        # self.piaofen = -1
        # self.shanghuo = -1

        # self.re_init_for_game()

    def reset_details(self):
        # 0-5暗杠 被暗杠 擦杠 被擦杠 点杠 被点杠 6-23自摸 24-41被自摸 42-59接炮 60-77放炮
        for type_index in range(0, 78):
            self.over_chips_detail.append(0)

    @property
    def cards(self):
        if self.card_group:
            return self.card_group.num_list
        return []

    def re_init_for_game(self, status=config.USER_STATE_STAND, broadcast_over=False):
        """
        保持游戏中的东西不变
        """
        if self.shanghuo_keeps_num > 0:
            self.shanghuo_keeps_num -= 1

        # 默认就是在看
        if not broadcast_over:
            self.status = status
            self.role = config.USER_ROLE_NORMAL
            self.card_len = 0
            self.op_type = []
            self.op_chi = False
            self.op_peng = False
            self.op_gang = 0
            self.op_hu = 0
            self.need_wait = True
            self.delete_status = 0
            # 如果没设置上火，就置位 MARK
            # 拖到上面来判定，让客户端获取正确的上火值
            if self.shanghuo == config.GAME_PLAYER_NOT_SHANGHUO or not self.shanghuo_keeps_num:
                self.shanghuo = -1
                self.shanghuo_keeps_num = 4
        else:
            self.op_list = []
            self.card_group = None
            self.piaofen = -1
            self.bird_num = 0
            self.round_chi_num = 0
            self.round_peng_num = 0
            self.round_gang_list = []
            self.round_win_chips = 0
            self.round_win_chips_before = 0
            self.round_hu_list = []
            self.round_win_list = []

    def re_init_for_desk(self, status=config.USER_STATE_STAND, broadcast_over=False):
        """
        重置桌子时需要重置的玩家信息
        """
        # 默认就是在看
        if not broadcast_over:
            self.status = status
            self.role = config.USER_ROLE_NORMAL
            self.card_len = 0
            self.op_type = []
            self.op_chi = False
            self.op_peng = False
            self.op_gang = 0
            self.op_hu = 0
            self.need_wait = True
            self.delete_status = 0
        else:
            self.op_list = []
            self.card_group = None
            self.piaofen = -1
            self.shanghuo = -1
            self.bird_num = 0
            self.round_chi_num = 0
            self.round_peng_num = 0
            self.round_gang_list = []
            self.round_win_chips = 0
            self.round_win_chips_before = 0
            self.round_hu_list = []
            self.round_win_list = []
            self.chips = 0
            self.total_chi_num = 0
            self.total_peng_num = 0
            self.total_gang_list = []
            self.total_hu_list = []
            self.total_win_list = []
            self.over_chips_detail = []