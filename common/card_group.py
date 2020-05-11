# -*- coding: utf-8 -*-

"""
author   : GerryLuo
blog     : blog.gerryluo.cn
function : 用户手牌对象以及算法
"""


import config
from .card import Card
from collections import Counter
import copy
from common.log import logger


class CardGroup(object):

    # 用户手牌
    card_list = None
    # 临时组进来的牌
    extend_card = None
    is_jiaopai = False
    # 扑到牌桌上的牌，是不是明杠时需要拉出来判定
    out_card_list = None
    # 玩家已经打出去的牌
    discard_list = None
    # 临时手牌，用于分析牌型
    tmp_card_list = None

    # 用于胡牌判断
    dui_num = 0
    shun_num = 0
    peng_num = 0
    gang_num = 0
    out_gang_num = 0

    # 清一色判定
    is_same_type = True

    # 玩法：
    # 玩法类型，转转不能胡十三烂
    type = 1
    # 红中癞子
    has_laizi = False
    # 可胡七对
    can_win_by_qidui = False

    def __init__(self, card_list=None, laizi=False, qidui=False, type=None):
        # 必要的初始化
        super(CardGroup, self).__init__()
        self.card_list = None
        self.extend_card = None
        self.is_jiaopai = False
        self.out_card_list = None
        self.discard_list = None
        self.tmp_card_list = None
        self.dui_num = 0
        self.shun_num = 0
        self.peng_num = 0
        self.gang_num = 0
        self.out_gang_num = 0
        self.is_same_type = True
        self.type = 1
        self.has_laizi = False
        self.can_win_by_qidui = False

        # 再进行赋值
        if not card_list:
            return

        if isinstance(card_list[0], int):
            card_list = [Card(num) for num in card_list]

        self.has_laizi = laizi
        self.can_win_by_qidui = qidui
        self.type = type

        # 从小到大排列
        self.card_list = sorted(card_list)
        self.out_card_list = []
        self.discard_list = []

    @property
    def num_list(self):
        if not self.card_list:
            return []
        else:
            # 手牌只在初始化的时候排序一下就好了
            return map(lambda card: card.num, self.card_list)

    @property
    def num_out_card_list(self):
        if not self.out_card_list:
            return []
        else:
            return map(lambda card: card.num, self.out_card_list)

    @property
    def num_discard_list(self):
        if not self.discard_list:
            return []
        else:
            # 丢弃的牌就永远不要排序了
            return map(lambda card: card.num, self.discard_list)

    # 迭代器，想要像序列使用就要实现该方法
    def __iter__(self):
        for card in self.card_list:
            yield card

    def reset_num(self):
        self.dui_num = 0
        self.shun_num = 0
        self.peng_num = 0
        self.gang_num = 0
        self.out_gang_num = 0
        self.tmp_card_list = []

    # @property
    # def formation(self):
    #     """
    #     牌型
    #     """
        # if self.is_baozi():
        #     return config.CARD_FORMATION_BAOZI
        # elif self.is_jinhua() and self.is_shunzi():
        #     return config.CARD_FORMATION_SHUNJIN
        # elif self.is_jinhua():
        #     return config.CARD_FORMATION_JINHUA
        # elif self.is_shunzi():
        #     return config.CARD_FORMATION_SHUNZI
        # elif self.is_duizi():
        #     return config.CARD_FORMATION_DUIZI
        # else:
        #     return config.CARD_FORMATION_DANZHANG

    def __repr__(self):
        return repr(self.card_list)

    def add_card(self, num, jiaopai):
        self.extend_card = Card(num)
        self.card_list.append(self.extend_card)
        # 这里就不要排序了
        # self.card_list = sorted(self.card_list)
        self.is_jiaopai = jiaopai

    def remove_card(self, num):
        if Card(num) in self.card_list:
            self.card_list.remove(Card(num))

    # 听牌判定，提示哪些牌可以胡牌，这个先不写了，后续再补
    def tingpai(self):
        return False

    def is_peng(self):
        same_num = 0
        for Card_it in self.card_list:
            if Card_it == self.extend_card:
                same_num += 1

        if same_num >= 3 and not self.is_jiaopai:
            return True
        else:
            return False

    def is_chi(self):
        # 前两张
        card1 = Card(self.extend_card.num + 1)
        card2 = Card(self.extend_card.num + 2)
        # 后两张
        card3 = Card(self.extend_card.num - 1)
        card4 = Card(self.extend_card.num - 2)
        # 前一张后一张
        card5 = Card(self.extend_card.num - 1)
        card6 = Card(self.extend_card.num + 1)

        chi_list = []

        # 字牌不能吃
        if card1.type == self.extend_card.type == card2.type >= 0 and \
            card1 in self.card_list and card2 in self.card_list and not self.is_jiaopai:
            chi_list.append(card1.num)
            chi_list.append(card2.num)

        if card3.type == self.extend_card.type == card4.type >= 0 and \
            card3 in self.card_list and card4 in self.card_list and not self.is_jiaopai:
            chi_list.append(card3.num)
            chi_list.append(card4.num)

        if card5.type == self.extend_card.type == card6.type >= 0 and \
            card5 in self.card_list and card6 in self.card_list and not self.is_jiaopai:
            chi_list.append(card5.num)
            chi_list.append(card6.num)

        if chi_list:
            return chi_list
        else:
            return None

    # 有明杠，暗杠之分
    # 手里有四张牌并且不杠的情形还要考虑一下
    def is_gang(self):
        same_num = 0
        out_same_num = 0
        # 这个只记录手里有四张牌没杠的情况，单独拉出来好了，别用老协议了，不然会乱的
        # gang_num = 0
        for Card_it in self.card_list:
            if Card_it == self.extend_card:
                same_num += 1

        for Card_it in self.out_card_list:
            if Card_it == self.extend_card:
                out_same_num += 1

        if same_num == 4 and self.is_jiaopai:
            return config.MAHJONG_GANG
        elif same_num == 4 and not self.is_jiaopai:
            return config.MAHJONG_DIAN_GANG
        # 这个就是擦牌了
        elif out_same_num == 3 and self.is_jiaopai:
            return config.MAHJONG_OUT_GANG
        else:
            return config.MAHJONG_NO_GANG

    def calculate_type(self):
        self.is_same_type = True
        # 如果是清一色那么就都一样，随便取一张判定牌型
        first_card_type = self.card_list[0].type
        flag_type_go_on = True

        # 清一色的判定全在这里，out_calculate只是判定杠的
        # 先看看牌桌下面的牌
        if self.out_card_list:
            for Card_it in self.out_card_list:
                if Card_it.type != first_card_type:
                    flag_type_go_on = False
                    self.is_same_type = False
                    break
        # 再看看手上的牌，从后面开始比
        if flag_type_go_on:
            for Card_it in self.card_list[-1::-1]:
                if Card_it.type != first_card_type:
                    self.is_same_type = False
                    break

    # 解析牌组单独拖出来，后续更好写
    # 癞子还有很大的问题，不知道怎么改，好好想想吧
    def calculate_card(self):
        self.tmp_card_list = [Card_it.num for Card_it in self.tmp_card_list]
        Card_count = Counter(self.tmp_card_list)
        self.tmp_card_list = [Card(num) for num in self.tmp_card_list]

        # 先清除掉3张以上同类型的牌
        for Card_it in Card_count:
            # 记录一下三个一样牌的组数
            if Card_count[Card_it] >= 3:
                self.peng_num += 1
                for it in range(0, 3):
                    self.tmp_card_list.remove(Card(Card_it))
            # 记录一下四个一样牌的组数
            # if Card_count[Card_it] == 4:
            #     self.gang_num += 1
            #     for it in range(0, 4):
            #         self.tmp_card_list.remove(Card(Card_it))

        self.tmp_card_list = sorted(self.tmp_card_list)
        my_tmp = copy.deepcopy(self.tmp_card_list)
        my_tmp = sorted(my_tmp)

        # 再清除掉连顺的牌
        for Card_it in my_tmp:
            # 不在里面代表被清掉了，type小于0代表是杂牌，杂牌没有连顺不判断
            if Card_it not in self.tmp_card_list or Card_it.type < 0:
                continue

            # 如果有两个一样的，总是取后面的一个
            Card_index = self.tmp_card_list.index(Card_it)
            # 这里要保证不能越界
            if Card_index + 1 <= len(self.tmp_card_list) - 1 and self.tmp_card_list[Card_index] == self.tmp_card_list[Card_index + 1]:
                Card_index += 1

            # 后面没牌了就别走了
            if Card_index + 2 > len(self.tmp_card_list) - 1 or Card_index + 1 > len(self.tmp_card_list) - 1:
                break

            if self.tmp_card_list[Card_index + 1].type == self.tmp_card_list[Card_index + 2].type == Card_it.type and \
                Card_it.point == self.tmp_card_list[Card_index + 1].point - 1 == self.tmp_card_list[Card_index + 2].point - 2:
                # 记录一下顺子牌的组数
                self.shun_num += 1
                del self.tmp_card_list[Card_index:Card_index + 3]
                continue

            if Card_index + 3 > len(self.tmp_card_list) - 1:
                continue

            if self.tmp_card_list[Card_index + 1] == self.tmp_card_list[Card_index + 2] and \
                self.tmp_card_list[Card_index + 1].type == self.tmp_card_list[Card_index + 3].type == Card_it.type and \
                Card_it.point == self.tmp_card_list[Card_index + 1].point - 1 == self.tmp_card_list[Card_index + 3].point - 2:
                # 把类似1 2 2 3这种的顺子漏掉了，这里加上
                self.shun_num += 1
                del self.tmp_card_list[Card_index:Card_index + 2]
                del self.tmp_card_list[Card_index + 1]

            """
            # 不在里面代表被清掉了，type小于0代表是杂牌，杂牌没有连顺不判断
            if Card_it not in self.tmp_card_list or Card_it.type < 0:
                continue

            Card_index = self.tmp_card_list.index(Card_it)
            # 后面没牌了就别走了
            if Card_index + 2 > len(self.tmp_card_list) - 1 or Card_index + 1 > len(self.tmp_card_list) - 1:
                break

            if self.tmp_card_list[Card_index + 1].type == self.tmp_card_list[Card_index + 2].type == Card_it.type and \
                Card_it.point == self.tmp_card_list[Card_index + 1].point - 1 == self.tmp_card_list[Card_index + 2].point - 2:
                # 记录一下顺子牌的组数
                self.shun_num += 1
                del self.tmp_card_list[Card_index:Card_index+3]
            """

        # logger.debug('last_card:%s', self.tmp_card_list)
        # logger.debug('dui:%s, shun:%s, peng:%s', self.dui_num, self.shun_num, self.peng_num)

    # 过几天再改
    def calculate_card_laizi(self, hongzhong_num=0):
        self.tmp_card_list = [Card_it.num for Card_it in self.tmp_card_list]
        Card_count = Counter(self.tmp_card_list)
        self.tmp_card_list = [Card(num) for num in self.tmp_card_list]

        # 先清除掉3张以上同类型的牌
        for Card_it in Card_count:
            # if self.has_laizi and hongzhong_num > 0:
            #     if Card_count[Card_it] == 2:
            #         self.dui_num += 1
            #         for it in range(0, 2):
            #             self.tmp_card_list.remove(Card(Card_it))
            # 记录一下三个一样牌的组数
            if Card_count[Card_it] >= 3:
                self.peng_num += 1
                for it in range(0, 3):
                    self.tmp_card_list.remove(Card(Card_it))
                    # 记录一下四个一样牌的组数
                    # if Card_count[Card_it] == 4:
                    #     self.gang_num += 1
                    #     for it in range(0, 4):
                    #         self.tmp_card_list.remove(Card(Card_it))

        self.tmp_card_list = sorted(self.tmp_card_list)
        my_tmp = copy.deepcopy(self.tmp_card_list)
        for Card_it in my_tmp:
            # 不在里面代表被清掉了，type小于0代表是杂牌，杂牌没有连顺不判断
            if Card_it not in self.tmp_card_list or Card_it.type < 0:
                continue

            # 如果有两个一样的，总是取后面的一个
            Card_index = self.tmp_card_list.index(Card_it)
            if Card_index + 1 <= len(self.tmp_card_list) - 1 and self.tmp_card_list[Card_index] == self.tmp_card_list[Card_index + 1]:
                Card_index += 1

            # 后面没牌了就别走了
            if Card_index + 2 > len(self.tmp_card_list) - 1 or Card_index + 1 > len(self.tmp_card_list) - 1:
                break

            if self.tmp_card_list[Card_index + 1].type == self.tmp_card_list[Card_index + 2].type == Card_it.type and \
                Card_it.point == self.tmp_card_list[Card_index + 1].point - 1 == self.tmp_card_list[Card_index + 2].point - 2:
                # 记录一下顺子牌的组数
                self.shun_num += 1
                del self.tmp_card_list[Card_index:Card_index + 3]
                continue

            if Card_index + 3 > len(self.tmp_card_list) - 1:
                continue

            # 走到这里就证明三个的已经被拿掉了
            if self.tmp_card_list[Card_index + 1] == self.tmp_card_list[Card_index + 2] and \
                self.tmp_card_list[Card_index + 1].type == self.tmp_card_list[Card_index + 3].type == Card_it.type and \
                Card_it.point == self.tmp_card_list[Card_index + 1].point - 1 == self.tmp_card_list[Card_index + 3].point - 2:
                # 把类似1 2 2 3这种的顺子漏掉了，这里加上
                self.shun_num += 1
                del self.tmp_card_list[Card_index:Card_index + 2]
                del self.tmp_card_list[Card_index + 1]

        # print 'after zhengchang, tmp:%s hongzhong:%s' % (self.tmp_card_list, hongzhong_num)
        logger.debug('after zhengchang, tmp:%s hongzhong:%s', self.tmp_card_list, hongzhong_num)

        # MARK 这里有问题，回去看看
        my_tmp = copy.deepcopy(self.tmp_card_list)
        # 先用红中来凑
        for Card_it in my_tmp:
            if hongzhong_num <= 0:
                break

            if Card_it not in self.tmp_card_list or Card_it.type < 0:
                continue

            Card_index = self.tmp_card_list.index(Card_it)
            # 后面没牌了就别走了
            if Card_index + 1 > len(self.tmp_card_list) - 1:
                break

            # 后一张牌的检测，不够，还要前一张牌的
            # MARK 红中赖子要改改
            # 第一个and后的判断，一定要是大于0的，不能是两张一样的牌
            if self.tmp_card_list[Card_index + 1].type == Card_it.type and \
                0 < self.tmp_card_list[Card_index + 1].point - Card_it.point <= 2 and \
                (Card_index + 2 > len(self.tmp_card_list) - 1 or \
                 self.tmp_card_list[Card_index + 2].type != Card_it.type or \
                 self.tmp_card_list[Card_index + 2].point - Card_it.point > 2) and \
                (Card_index - 1 < 0 or self.tmp_card_list[Card_index - 1].type != Card_it.type or \
                 Card_it.point - self.tmp_card_list[Card_index - 1].point > 1):
                self.shun_num += 1
                hongzhong_num -= 1
                # print Card_index
                del self.tmp_card_list[Card_index:Card_index + 2]

        # print "after hongzhongshun, tmp:%s hongzhong:%s" % (self.tmp_card_list, hongzhong_num)
        logger.debug("after hongzhongshun, tmp:%s hongzhong:%s", self.tmp_card_list, hongzhong_num)

        # 再看看里面还有没有对子，有就记录下来
        self.tmp_card_list = [Card_it.num for Card_it in self.tmp_card_list]
        Card_count = Counter(self.tmp_card_list)
        self.tmp_card_list = [Card(num) for num in self.tmp_card_list]
        for Card_it in Card_count:
            if Card_count[Card_it] == 2:
                self.dui_num += 1
                for it in range(0, 2):
                    self.tmp_card_list.remove(Card(Card_it))

        # print "last, tmp:%s hongzhong:%s" % (self.tmp_card_list, hongzhong_num)
        logger.debug("last, tmp:%s hongzhong:%s", self.tmp_card_list, hongzhong_num)
        if self.dui_num == 0:
            self.tmp_card_list.pop()
            self.dui_num += 1
            hongzhong_num -= 1
        else:
            # 先用多的对子凑碰
            while self.dui_num > 1 and hongzhong_num > 0:
                self.dui_num -= 1
                self.peng_num += 1
                hongzhong_num -= 1

            # 再用剩下的凑碰
            while self.tmp_card_list and hongzhong_num > 1:
                self.tmp_card_list.pop()
                self.peng_num += 1
                hongzhong_num -= 2

        # 如果还有红中就加到tmp里面去
        if hongzhong_num > 0:
            self.tmp_card_list.extend([Card(-3)] * hongzhong_num)

        # if self.has_laizi and hongzhong_num > 0:
            # 对子多了就凑碰
            # while self.dui_num > 1 and hongzhong_num > 0:
            #     self.peng_num += 1
            #     hongzhong_num -= 1
            #     self.dui_num -= 1

            # 没有对子，先把对子凑出来再说
            # if self.dui_num == 0 and hongzhong_num > 0:
            #     if self.tmp_card_list:
            #         self.tmp_card_list.pop(0)
            #         hongzhong_num -= 1
            #         self.dui_num += 1
            #     else:
            #         if hongzhong_num >= 2:
            #             hongzhong_num -= 2
            #             self.dui_num += 1

            # if self.dui_num == 1 and hongzhong_num > 0:
            #     if (len(self.tmp_card_list) == 1 and hongzhong_num == 2) or \
            #             (len(self.tmp_card_list) == 0 and hongzhong_num == 3):
            #         self.peng_num += 1
            #         self.tmp_card_list = []

    # 对于放下去的牌的分析
    # 根据op_list来取
    def out_calculate_card(self, op_list=None):
        # 没摊牌就别走了
        if len(self.out_card_list) == 0 or not op_list:
            return

        for op in op_list:
            if op == 1:
                self.shun_num += 1
            elif op == 2:
                self.peng_num += 1
            elif op >= 3:
                self.out_gang_num += 1

    # 胡牌判定
    # 只有最普通的平胡才不能赢别人打的牌
    def is_pinghu(self):
        # 只有一对牌，而且顺子不为0，而且不是类型不同，就是平胡了
        if not self.tmp_card_list and self.dui_num == 1 and self.shun_num > 0 and \
                not self.is_same_type and (len(self.card_list) > 2 or (len(self.card_list) == 2 and self.is_jiaopai)):
            return True
        else:
            return False

    # 全求人只能是点炮的
    def is_pinghu_quanqiuren(self):
        # 是平胡，但是手牌只剩一张，就是全求人了
        if not self.tmp_card_list and self.dui_num == 1 and self.shun_num > 0 and \
                not self.is_same_type and len(self.card_list) == 2 and not self.is_jiaopai:
            return True
        else:
            return False

    # 大对就是碰碰胡
    def is_dadui(self):
        # 一对牌加全部的碰碰
        if not self.tmp_card_list and self.dui_num == 1 and self.shun_num == 0 and \
                not self.is_same_type and (len(self.card_list) > 2 or (len(self.card_list) == 2 and self.is_jiaopai)):
            return True
        else:
            return False

    def is_dadui_quanqiuren(self):
        if not self.tmp_card_list and self.dui_num == 1 and self.shun_num == 0 and \
                not self.is_same_type and len(self.card_list) == 2 and not self.is_jiaopai:
            return True
        else:
            return False

    def is_qingyise(self):
        if not self.tmp_card_list and self.dui_num == 1 and self.shun_num > 0 and \
                self.is_same_type and (len(self.card_list) > 2 or (len(self.card_list) == 2 and self.is_jiaopai)):
            return True
        else:
            return False

    def is_qingyise_quanqiuren(self):
        if not self.tmp_card_list and self.dui_num == 1 and self.shun_num > 0 and \
                self.is_same_type and len(self.card_list) == 2 and not self.is_jiaopai:
            return True
        else:
            return False

    def is_qingyise_dadui(self):
        if not self.tmp_card_list and self.dui_num == 1 and self.shun_num == 0 and \
                self.is_same_type and (len(self.card_list) > 2 or (len(self.card_list) == 2 and self.is_jiaopai)):
            return True
        else:
            return False

    def is_qingyise_dadui_quanqiuren(self):
        if not self.tmp_card_list and self.dui_num == 1 and self.shun_num == 0 and \
                self.is_same_type and len(self.card_list) == 2 and not self.is_jiaopai:
            return True
        else:
            return False

    # 十三烂没搞懂，后续看看再补上
    def is_shisanlan(self):
        if len(self.tmp_card_list) == 14 and not self.out_card_list and \
                self.dui_num == 0 and self.shun_num == 0 and self.gang_num == 0:
            self.tmp_card_list = sorted(self.tmp_card_list)
            my_tmp = copy.deepcopy(self.tmp_card_list)
            for Card_it in my_tmp:
                if Card_it not in self.tmp_card_list or Card_it.type < 0:
                    continue

                Card_index = self.tmp_card_list.index(Card_it)
                # 后面没牌了就别走了
                if Card_index + 1 > len(self.tmp_card_list) - 1:
                    break

                if self.tmp_card_list[Card_index + 1].type == Card_it.type and \
                        self.tmp_card_list[Card_index + 1].point - Card_it.point <= 2:
                    # 有间隔小于2的牌就直接返回false
                    return False

            # 都在里面就是七星十三烂了呀
            if Card(-7) in self.tmp_card_list and Card(-6) in self.tmp_card_list and Card(-5) in self.tmp_card_list and \
                    Card(-4) in self.tmp_card_list and Card(-3) in self.tmp_card_list and Card(-2) in self.tmp_card_list and \
                        Card(-1) in self.tmp_card_list:
                return False
        else:
            return False

        return True

    def is_qixing_shisanlan(self):
        if len(self.tmp_card_list) == 14 and not self.out_card_list and \
                self.dui_num == 0 and self.shun_num == 0 and self.gang_num == 0:
            self.tmp_card_list = sorted(self.tmp_card_list)
            my_tmp = copy.deepcopy(self.tmp_card_list)
            for Card_it in my_tmp:
                if Card_it not in self.tmp_card_list or Card_it.type < 0:
                    continue

                Card_index = self.tmp_card_list.index(Card_it)
                # 后面没牌了就别走了
                if Card_index + 1 > len(self.tmp_card_list) - 1:
                    break

                if self.tmp_card_list[Card_index + 1].type == Card_it.type and \
                        self.tmp_card_list[Card_index + 1].point - Card_it.point <= 2:
                    # 有间隔小于2的牌就直接返回false
                    return False

            # 只有这种情况返回True
            if Card(-7) in self.tmp_card_list and Card(-6) in self.tmp_card_list and Card(-5) in self.tmp_card_list and \
                    Card(-4) in self.tmp_card_list and Card(-3) in self.tmp_card_list and Card(-2) in self.tmp_card_list and \
                        Card(-1) in self.tmp_card_list:
                return True
        else:
            return False

    def is_qidui(self):
        if not self.tmp_card_list and self.dui_num == 7 and not self.is_same_type:
            return True
        else:
            return False

    def is_qidui_haohua(self):
        if not self.tmp_card_list and self.dui_num == 5 and self.gang_num == 1 and not self.is_same_type:
            return True
        else:
            return False

    def is_qidui_shuanghaohua(self):
        if not self.tmp_card_list and self.dui_num == 3 and self.gang_num == 2 and not self.is_same_type:
            return True
        else:
            return False

    def is_qidui_sanhaohua(self):
        if not self.tmp_card_list and self.dui_num == 1 and self.gang_num == 3 and not self.is_same_type:
            return True
        else:
            return False

    def is_qingyise_qidui(self):
        if not self.tmp_card_list and self.dui_num == 7 and self.is_same_type:
            return True
        else:
            return False

    def is_qingyise_qidui_haohua(self):
        if not self.tmp_card_list and self.dui_num == 5 and self.gang_num == 1 and self.is_same_type:
            return True
        else:
            return False

    def is_qingyise_qidui_shuanghaohua(self):
        if not self.tmp_card_list and self.dui_num == 3 and self.gang_num == 2 and self.is_same_type:
            return True
        else:
            return False

    def is_qingyise_qidui_sanhaohua(self):
        if not self.tmp_card_list and self.dui_num == 1 and self.gang_num == 3 and self.is_same_type:
            return True
        else:
            return False

    # 胡牌返回牌型
    def is_hu(self, op_list=None):
        # 每次判断前先reset一下
        self.reset_num()
        # 看看是不是清一色
        self.calculate_type()

        # 开始执行算法
        self.tmp_card_list = [Card_it.num for Card_it in self.card_list]
        Card_count = Counter(self.tmp_card_list)
        laizi_tmp_card_list = []
        # 如果有红中就先把红中从里面取出来，不加入判断
        hongzhong_num = 0
        tmp_hongzhong_num = 0
        if self.has_laizi:
            if -3 in Card_count:
                hongzhong_num = Card_count.pop(-3)
                tmp_hongzhong_num = hongzhong_num
                # 先把红中都挪走
                for it in range(hongzhong_num):
                    self.tmp_card_list.remove(-3)
                laizi_tmp_card_list = copy.deepcopy(self.tmp_card_list)
            # 四张红中，直接设成平胡的牌型就可以了
            if hongzhong_num == 4:
                return config.MAHJONG_FORMATION_PINGHU

        self.tmp_card_list = [Card(num) for num in set(self.tmp_card_list)]
        # 先判断七对
        if self.can_win_by_qidui:
            for Card_it in Card_count:
                # 记录一下两个一样牌的组数
                if Card_count[Card_it] == 2:
                    self.dui_num += 1
                    self.tmp_card_list.remove(Card(Card_it))
                # 记录一下四个一样牌的组数
                if Card_count[Card_it] == 4:
                    self.gang_num += 1
                    self.tmp_card_list.remove(Card(Card_it))

            if self.has_laizi and hongzhong_num > 0:
                # 七对的判断
                while hongzhong_num > 0 and self.tmp_card_list:
                    self.dui_num += 1
                    hongzhong_num -= 1
                    self.tmp_card_list.pop()

            if self.is_qidui():
                return config.MAHJONG_FORMATION_QIDUI
            elif self.is_qidui_haohua():
                return config.MAHJONG_FORMATION_QIDUI_HAOHUA
            elif self.is_qidui_shuanghaohua():
                return config.MAHJONG_FORMATION_QIDUI_SHUANGHAOHUA
            elif self.is_qidui_sanhaohua():
                return config.MAHJONG_FORMATION_QIDUI_SANHAOHUA
            elif self.is_qingyise_qidui():
                return config.MAHJONG_FORMATION_QINGYISE_QIDUI
            elif self.is_qingyise_qidui_haohua():
                return config.MAHJONG_FORMATION_QINGYISE_QIDUI_HAOHUA
            elif self.is_qingyise_qidui_shuanghaohua():
                return config.MAHJONG_FORMATION_QINGYISE_QIDUI_SHUANGHAOHUA
            elif self.is_qingyise_qidui_sanhaohua():
                return config.MAHJONG_FORMATION_QINGYISE_QIDUI_SANHAOHUA

        # 再来判断3n+2型的胡牌
        # 先找到大于2个的数，然后把它拿出来，判断是否胡牌
        # hongzhong_num在七对判断时已经变化了，用tmp保存的值来判断
        if not self.has_laizi or tmp_hongzhong_num == 0:
            # logger.debug('enter not laizi, hongzhong_num:%s', tmp_hongzhong_num)
            dui_list = []
            for Card_it in Card_count:
                # 记录一下两个一样牌的组数
                if Card_count[Card_it] >= 2:
                    dui_list.append(Card(Card_it))

            if dui_list:
                for dui_it in dui_list:
                    self.reset_num()
                    self.tmp_card_list = [Card_it for Card_it in self.card_list]
                    # 先把这对牌挪走
                    for it in range(0, 2):
                        self.tmp_card_list.remove(dui_it)
                    self.dui_num += 1
                    # logger.debug('card:%s', self.tmp_card_list)
                    # 这里只是判断牌型，别的都不判断
                    self.out_calculate_card(op_list)
                    self.calculate_card()

                    if self.is_pinghu():
                        return config.MAHJONG_FORMATION_PINGHU
                    elif self.is_pinghu_quanqiuren():
                        return config.MAHJONG_FORMATION_PINGHU_QUANQIUREN
                    elif self.is_dadui():
                        return config.MAHJONG_FORMATION_DADUI
                    elif self.is_dadui_quanqiuren():
                        return config.MAHJONG_FORMATION_DADUI_QUANQIUREN
                    elif self.is_qingyise():
                        return config.MAHJONG_FORMATION_QINGYISE
                    elif self.is_qingyise_quanqiuren():
                        return config.MAHJONG_FORMATION_QINGYISE_QUANQIUREN
                    elif self.is_qingyise_dadui():
                        return config.MAHJONG_FORMATION_QINGYISE_DADUI
                    elif self.is_qingyise_dadui_quanqiuren():
                        return config.MAHJONG_FORMATION_QINGYISE_DADUI_QUANQIUREN
            else:
                if self.type == config.DESK_TYPE_MJ_WZ and self.is_shisanlan():
                    return config.MAHJONG_FORMATION_SHISANLAN
                elif self.type == config.DESK_TYPE_MJ_WZ and self.is_qixing_shisanlan():
                    return config.MAHJONG_FORMATION_QIXING_SHISANLAN
        else:
            # logger.debug("enter laizi calculate")
            self.reset_num()
            self.tmp_card_list = [Card(num) for num in laizi_tmp_card_list]
            self.out_calculate_card(op_list)
            hongzhong_num = tmp_hongzhong_num
            print self.tmp_card_list, hongzhong_num
            self.calculate_card_laizi(hongzhong_num)

            if self.is_pinghu():
                return config.MAHJONG_FORMATION_PINGHU
            elif self.is_pinghu_quanqiuren():
                return config.MAHJONG_FORMATION_PINGHU_QUANQIUREN
            elif self.is_dadui():
                return config.MAHJONG_FORMATION_DADUI
            elif self.is_dadui_quanqiuren():
                return config.MAHJONG_FORMATION_DADUI_QUANQIUREN
            elif self.is_qingyise():
                return config.MAHJONG_FORMATION_QINGYISE
            elif self.is_qingyise_quanqiuren():
                return config.MAHJONG_FORMATION_QINGYISE_QUANQIUREN
            elif self.is_qingyise_dadui():
                return config.MAHJONG_FORMATION_QINGYISE_DADUI
            elif self.is_qingyise_dadui_quanqiuren():
                return config.MAHJONG_FORMATION_QINGYISE_DADUI_QUANQIUREN

        # 喝汤就是false了咯，先这样写着，到时候看看是不是
        return config.MAHJONG_FORMATION_HETANG

    # 五位数来标记
    def is_my_turn(self, op_list=None):
        return [self.is_chi(), self.is_peng(), self.is_gang(), self.is_hu(op_list)]

