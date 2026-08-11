# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from datetime import time
from enum import Enum
from time import sleep

import numpy as np
from cached_property import cached_property

from module.base.timer import Timer
from module.logger import logger
from tasks.BondlingFairyland.assets import BondlingFairylandAssets
from tasks.Component.GeneralInvite.assets import GeneralInviteAssets
from tasks.Component.GeneralInvite.config_invite import InviteConfig, InviteNumber, FindMode
from tasks.GameUi.page import exit_list
from tasks.base_task import BaseTask


class FriendList(str, Enum):
    RECENT_FRIEND = 'recent_friend'
    GUILD_FRIEND = 'guild_friend'
    FRIEND = 'friend'
    OTHER_FRIEND = 'other_friend'


class RoomType(str, Enum):
    # 房间只可以两个人的： 探索
    NORMAL_2 = 'normal_2'
    # 房间可以两三个人的： 觉醒、御魂、日轮、石距（石距是单次没有锁定阵容）
    NORMAL_3 = 'normal_3'
    # 永生之海不一样
    ETERNITY_SEA = 'eternity_sea'
    # 经验妖怪和金币妖怪
    NORMAL_5 = 'normal_5'


class GeneralInvite(BaseTask, GeneralInviteAssets, BondlingFairylandAssets):
    timer_invite = None
    timer_wait = None

    def run_invite(self, config: InviteConfig, is_first: bool = False, is_over: bool = True) -> bool:
        """
        队长！！身份。。。在组队界面邀请好友（ 如果开启is_first） 等待队员进入开启挑战
        请注意，返回的时候成功时是进入战斗了！！！
        如果是失败，那就是没有队友进入，然后会退出房间的界面
        :param config:
        :param is_first: 如果是第一次开房间的那就要邀请队员，其他情况等待队员进入
        :param is_over: 是否执行点击挑战操作（针对某些特殊任务只需确认人员到齐）
        :return:
        """
        logger.hr('邀请好友')
        if not self.ensure_enter():
            logger.warning('未进入邀请页面')
            return False
        if is_first:
            _ = self.room_type
            self.timer_invite = Timer(20)
            self.timer_invite.start()
            self.ensure_room_type(config.invite_number)
            self.invite_friends(config)
        else:
            self.timer_invite = Timer(30)
            self.timer_invite.start()
        wait_second = config.wait_time.second + config.wait_time.minute * 60 + config.wait_time.hour * 60 * 60
        self.timer_wait = Timer(wait_second)
        self.timer_wait.start()
        while 1:
            self.screenshot()
            if self.timer_wait.reached():
                logger.warning('等待超时')
                self.push_notify(content=f"队长等待超时...")
                return False
            if self.appear(self.I_MATCHING):
                logger.warning('超时,当前不在房间中')
                return False

            if not self.is_in_room():
                continue

            fire = False  # 是否开启挑战
            # 如果这个房间最多只容纳两个人（意思是只可以邀请一个人），且已经邀请一个人了，那就开启挑战
            if self.room_type == RoomType.NORMAL_2 and not self.appear([self.I_ADD_1, self.I_ADD_2]):
                logger.info('开始挑战,此房间只能邀请一位好友')
                fire = True
            # 如果这个房间最多容纳三个人（意思是可以邀请两个人），且设定邀请一个就开启挑战，那就开启挑战
            elif self.room_type == RoomType.NORMAL_3 and config.invite_number == InviteNumber.ONE and not self.appear(self.I_ADD_1):
                logger.info('开始挑战,用户只邀请了一位好友')
                fire = True
            # 如果这个房间最多容纳三个人（意思是可以邀请两个人），且设定邀请两个就开启挑战，那就开启挑战
            elif self.room_type == RoomType.NORMAL_3 \
                    and config.invite_number == InviteNumber.TWO and not self.appear(self.I_ADD_2):
                logger.info('开始挑战,用户邀请了两位好友')
                fire = True
            # 如果这个房间是五人的，且设定邀请一个就开启挑战，那就开启挑战
            elif self.room_type == RoomType.NORMAL_5 \
                    and config.invite_number == InviteNumber.ONE and not self.appear(self.I_ADD_5_1):
                logger.info('开始挑战,用户只邀请了一位好友')
                fire = True
            # 如果这个房间是五人的，且设定邀请两个就开启挑战，那就开启挑战
            elif self.room_type == RoomType.NORMAL_5 \
                    and config.invite_number == InviteNumber.TWO and not self.appear(self.I_ADD_5_2):
                logger.info('开始挑战,用户邀请了两位好友')
                fire = True
            # 如果是永生之海
            elif self.room_type == RoomType.ETERNITY_SEA and not self.appear(self.I_ADD_SEA) and self.appear_rgb(self.I_FIRE_SEA):
                logger.info('开始挑战,这是锁海房间')
                fire = True

            # 点击挑战
            if fire:
                if is_over:
                    self.click_fire()
                return True

            if self.timer_invite and self.timer_invite.reached():
                if is_first:
                    logger.info('每20秒触发一次邀请')
                    self.timer_invite.reset()
                else:
                    logger.info('等待30秒后再次邀请')
                    self.timer_invite.reset()
                self.invite_friends(config)

    def ensure_enter(self) -> bool:
        """
        确认是否进入了组队界面
        :return:
        """
        logger.info('确保进入邀请页面')
        while 1:
            self.screenshot()
            if self.appear(self.I_ADD_2):
                return True
            if self.appear(self.I_ADD_5_4):
                return True
            if self.appear(self.I_LOCK_SEA):
                return True
            if self.appear(self.I_UNLOCK_SEA):
                return True
            # 修复三人组队卡住bug，#78
            # 增加左上角协战房间判断，存在就说明在组队界面
            if self.appear(self.I_GI_IN_ROOM):
                return True
            if self.appear(self.I_MATCHING):
                return False

    def switch_friend_tab(self, index: int):
        """
        切换到指定好友标签页
        :param index: 标签索引 (0-3)
        """
        flag_on_off_map = [
            (self.I_FLAG_1_ON, self.I_FLAG_1_OFF),
            (self.I_FLAG_2_ON, self.I_FLAG_2_OFF),
            (self.I_FLAG_3_ON, self.I_FLAG_3_OFF),
            (self.I_FLAG_4_ON, self.I_FLAG_4_OFF),
        ]
        if index < 0 or index >= len(flag_on_off_map):
            logger.warning(f'无效的好友标签索引: {index}')
            return

        flag_on, flag_off = flag_on_off_map[index]
        while True:
            self.screenshot()
            if self.appear(flag_on):
                break
            if self.appear_then_click(flag_off, interval=1):
                continue

    # 判断是否在房间里面
    def is_in_room(self, is_screenshot: bool = True) -> bool:
        """
        判断是否在房间里面
        :return:
        """
        if is_screenshot:
            self.screenshot()
        if self.appear(self.I_GI_IN_ROOM):
            return True
        if self.appear(self.I_GI_EMOJI_1):
            return True
        if self.appear(self.I_GI_EMOJI_2):
            return True
        # if self.appear(self.I_MATCHING):
        #     return False
        return False

    def exit_room(self) -> bool:
        """
        退出房间
        :return:
        """
        if not self.is_in_room():
            return False
        logger.info('退出房间')
        while 1:
            self.screenshot()
            if not self.is_in_room() and not self.appear_then_click(self.I_UI_SURE, interval=0.8) and not self.appear(self.I_BACK_YELLOW):
                break
            if self.appear_then_click(self.I_UI_SURE, interval=0.5):
                continue
            if not self.appear(self.I_UI_SURE) and self.appear_then_click(self.I_BACK_YELLOW, interval=0.8):
                self.wait_until_appear(self.I_UI_SURE, wait_time=0.8)
                continue
            if not self.appear(self.I_UI_SURE) and self.appear_then_click(self.I_BACK_YELLOW_SEA, interval=0.8):
                self.wait_until_appear(self.I_UI_SURE, wait_time=0.8)
                continue
        return True

    def click_fire(self):
        while 1:
            self.screenshot()
            if not self.is_in_room(False):
                break
            if self.appear_then_click(self.I_FIRE, interval=1, threshold=0.7):
                continue
            if self.appear_then_click(self.I_FIRE_SEA, interval=1, threshold=0.7):
                continue

    @cached_property
    def room_type(self) -> RoomType:
        """
        只需要在队长进入的时候判断一次就可以了，任务后面之间使用

        :return:
        """
        self.screenshot()
        room_type = self.check_room_type(image=self.device.image)
        logger.info(f'房间类型: {room_type}')
        return room_type

    def check_room_type(self, image: np.array = None, pre_type: RoomType = None) -> RoomType:
        """
        检查房间类型
        :param image:
        :param pre_type: 可以先指定这个类型，如果不指定，就自动检查
        :return:
        """

        def check_3(img) -> bool:
            appear = False
            if self.I_ADD_1.match(img) and self.I_ADD_2.match(img):
                appear = True
            return appear

        def check_2(img) -> bool:
            appear = False
            # 通用逻辑：没有第一个添加位，但有第二个添加位（双人房）
            if not self.I_ADD_1.match(img) and self.I_ADD_2.match(img):
                appear = True
            # 兼容探索等界面：只要检测到 I_ADD_2 且没有 I_ADD_5_4 等多人标识
            elif self.I_ADD_2.match(img) and not self.I_ADD_5_4.match(img) and not self.I_LOCK_SEA.match(img):
                appear = True
            # 兼容 BondlingFairyland 等特殊界面：只有 I_ADD_1 存在，且没有多人房标识
            elif self.I_ADD_1.match(img) and not self.I_ADD_2.match(img) and not self.I_ADD_5_4.match(img):
                appear = True
            return appear

        def check_5(img) -> bool:
            appear = False
            if self.I_ADD_5_1.match(img) and self.I_ADD_5_2.match(img) \
                    and self.I_ADD_5_3.match(img) and self.I_ADD_5_4.match(img):
                appear = True
            return appear

        def check_eternity_sea(img) -> bool:
            appear = False
            if self.I_LOCK_SEA.match(img) or self.I_UNLOCK_SEA.match(img):
                appear = True
            return appear

        room_type = None
        if pre_type is not None:
            match pre_type:
                case RoomType.NORMAL_2:
                    room_type = RoomType.NORMAL_2 if check_2(image) else None
                case RoomType.NORMAL_3:
                    room_type = RoomType.NORMAL_3 if check_3(image) else None
                case RoomType.NORMAL_5:
                    room_type = RoomType.NORMAL_5 if check_5(image) else None
                case RoomType.ETERNITY_SEA:
                    room_type = RoomType.ETERNITY_SEA if check_eternity_sea(image) else None
        if room_type:
            return room_type

        # 自动检测顺序：优先检测特殊房间，再检测普通房间
        if room_type is None and check_eternity_sea(image):
            room_type = RoomType.ETERNITY_SEA
            return room_type
        if room_type is None and check_5(image):
            room_type = RoomType.NORMAL_5
            return room_type
        if room_type is None and check_3(image):
            room_type = RoomType.NORMAL_3
            return room_type
        if room_type is None and check_2(image):
            room_type = RoomType.NORMAL_2
            return room_type

        logger.warning(f'无法识别房间类型，当前UI元素状态: ADD_1:{self.I_ADD_1.match(image)}, ADD_2:{self.I_ADD_2.match(image)}, ADD_5_4:{self.I_ADD_5_4.match(image)}')
        return room_type

    def ensure_room_type(self, friend_number: int = None) -> bool:
        """
        确认设定的邀请人数是否会超出房间的最大
        :param friend_number: 这个输入的是用户选项中的invite_number
        :return:  如果超出了，就返回False
        """
        if isinstance(friend_number, InviteNumber):
            if friend_number == InviteNumber.ONE:
                friend_number = 1
            elif friend_number == InviteNumber.TWO:
                friend_number = 2

        if friend_number == 2:
            if self.room_type == RoomType.NORMAL_2:
                # 整个房间就可以两个人，还邀请两个 这个是报错的
                logger.error('房间只能容纳一人,但邀请了两人')
                return False
            elif self.room_type == RoomType.ETERNITY_SEA:
                # 永生之海，只能邀请一个人
                logger.error('房间只能容纳一人,但邀请了两人')
                return False
            return True
        return True

    @cached_property
    def friend_class(self) -> list[str]:
        return ['好友', '最近', '跨区', '寮友', '蔡友', '路区', '察友', '区']

    def detect_select(self, name: str = None) -> bool:
        """
        在当前的页面检测是否有好友， 如果有就选中这个好友
        :return:
        """
        if not name:
            return False

        self.screenshot()
        self.O_FRIEND_NAME_1.keyword = name
        self.O_FRIEND_NAME_2.keyword = name
        appear_1 = self.ocr_appear_click(self.O_FRIEND_NAME_1, interval=2)
        appear_2 = self.ocr_appear_click(self.O_FRIEND_NAME_2, interval=2)
        if not appear_1 and not appear_2:
            logger.info('当前页面没有好友')
            return False

        while appear_1 or appear_2:
            self.screenshot()
            if self.appear(self.I_SELECTED):
                break
            appear_1 = self.ocr_appear_click(self.O_FRIEND_NAME_1, interval=2)
            appear_2 = self.ocr_appear_click(self.O_FRIEND_NAME_2, interval=2)

        return True

    def invite_friend(self, name: str = None, find_mode: FindMode = FindMode.AUTO_FIND) -> bool:
        """
        邀请好友
        :param find_mode: 寻找的方式
        :param name:
        :return:
        """
        logger.info('点击添加按钮邀请好友')
        # 点击＋号
        while 1:
            self.screenshot()
            if self.appear(self.I_LOAD_FRIEND):
                break
            if self.appear(self.I_INVITE_ENSURE):
                break
            if self.appear_then_click(self.I_ADD_2, interval=1):
                continue
            if self.appear_then_click(self.I_ADD_1, interval=1):
                continue
            if self.appear_then_click(self.I_ADD_5_4, interval=1):
                continue
            if self.appear_then_click(self.I_ADD_SEA, interval=1):
                continue
            # Exploration solo 逻辑：如果都不存在，可能不需要邀请或已处于特定状态
            if not self.appear(self.I_ADD_2) and not self.appear(self.I_ADD_5_4) and \
               not self.appear(self.I_ADD_1) and not self.appear(self.I_ADD_SEA):
                return True

        friend_class = []
        class_ocr = [self.O_F_LIST_1, self.O_F_LIST_2, self.O_F_LIST_3, self.O_F_LIST_4]
        class_index = 0

        # 尝试获取通用列表标签
        list_1 = self.O_F_LIST_1.ocr(self.device.image) if hasattr(self, 'O_F_LIST_1') else None
        list_2 = self.O_F_LIST_2.ocr(self.device.image) if hasattr(self, 'O_F_LIST_2') else None
        list_3 = self.O_F_LIST_3.ocr(self.device.image) if hasattr(self, 'O_F_LIST_3') else None
        list_4 = self.O_F_LIST_4.ocr(self.device.image) if hasattr(self, 'O_F_LIST_4') else None

        # 如果通用标签未识别到，尝试 Bondling 特有的标签
        if not any([list_1, list_2, list_3, list_4]):
            if hasattr(self, 'O_FRIEND'):
                list_1 = self.O_FRIEND.ocr(self.device.image)
            if hasattr(self, 'O_KUAQU'):
                list_2 = self.O_KUAQU.ocr(self.device.image)

        if list_1: list_1 = list_1.replace(' ', '').replace('、', '')
        if list_2: list_2 = list_2.replace(' ', '').replace('、', '')
        if list_3: list_3 = list_3.replace(' ', '').replace('、', '')
        if list_4: list_4 = list_4.replace(' ', '').replace('、', '')

        if list_1 is not None and list_1 != '' and list_1 in self.friend_class:
            friend_class.append(list_1)
        if list_2 is not None and list_2 != '' and list_2 in self.friend_class:
            friend_class.append(list_2)
        if list_3 is not None and list_3 != '' and list_3 in self.friend_class:
            friend_class.append(list_3)
        if list_4 is not None and list_4 != '' and list_4 in self.friend_class:
            friend_class.append(list_4)

        for i in range(len(friend_class)):
            if friend_class[i] == '蔡友':
                friend_class[i] = '寮友'
            elif friend_class[i] == '路区':
                friend_class[i] = '跨区'
            elif friend_class[i] == '察友':
                friend_class[i] = '寮友'
            elif friend_class[i] == '区':
                friend_class[i] = '跨区'
        logger.info(f'好友分类: {friend_class}')

        is_select: bool = False  # 是否选中了好友
        if find_mode == FindMode.RECENT_FRIEND:
            logger.info('查找最近好友')
            # 获取’最近‘在friend_class中的index
            if '最近' not in friend_class:
                logger.warning('没有最近好友')
                return False
            recent_index = friend_class.index('最近')
            while recent_index == 1:
                self.screenshot()
                if self.appear(self.I_FLAG_2_ON) or self.appear(self.I_SELECT_KUAQU_ON):
                    break
                if self.appear_then_click(self.I_FLAG_2_OFF, interval=1):
                    continue
                if self.appear_then_click(self.I_SELECT_KUAQU_OFF, interval=1):
                    continue

            logger.info(f'Now find friend in ”最近“')
            sleep(1)
            if not is_select:
                if self.detect_select(name):
                    is_select = True
            sleep(1)
            if not is_select:
                if self.detect_select(name):
                    is_select = True

        for index in range(len(friend_class)):
            # 如果不是自动寻找，就跳过
            if find_mode != FindMode.AUTO_FIND:
                continue
            # 如果已经选中了好友，就不需要再选中了
            if is_select:
                continue
            # 首先切换到不同的好友列表
            # 适配通用 UI
            while index == 0:
                self.screenshot()
                if self.appear(self.I_FLAG_1_ON) or self.appear(self.I_SELECT_FRIEND_ON):
                    break
                if self.appear_then_click(self.I_FLAG_1_OFF, interval=1):
                    continue
                if self.appear_then_click(self.I_SELECT_FRIEND_OFF, interval=1):
                    continue
                # 适配 Exploration solo UI (RGB)
                if self.appear_rgb(self.I_HAOYOU):
                    break
                if self.appear_then_click(self.I_HAOYOU, interval=1):
                    continue

            while index == 1:
                self.screenshot()
                if self.appear(self.I_FLAG_2_ON) or self.appear(self.I_SELECT_KUAQU_ON):
                    break
                if self.appear_then_click(self.I_FLAG_2_OFF, interval=1):
                    continue
                if self.appear_then_click(self.I_SELECT_KUAQU_OFF, interval=1):
                    continue
                # 适配 Exploration solo UI (RGB)
                if self.appear_rgb(self.I_LIAOYOU):
                    break
                if self.appear_then_click(self.I_LIAOYOU, interval=1):
                    continue

            while index == 2:
                self.screenshot()
                if self.appear(self.I_FLAG_3_ON):
                    break
                if self.appear_then_click(self.I_FLAG_3_OFF, interval=1):
                    continue
                # 适配 Exploration solo UI (RGB)
                if self.appear_rgb(self.I_KUAQU):
                    break
                if self.appear_then_click(self.I_KUAQU, interval=1):
                    continue

            while index == 3:
                self.screenshot()
                if self.appear(self.I_FLAG_4_ON):
                    break
                if self.appear_then_click(self.I_FLAG_4_OFF, interval=1):
                    continue

            # 选中好友， 在这里游戏获取在线的好友并不是很快，根据不同的设备会有不同的时间，而且没有什么元素提供我们来判断
            # 所以这里就直接等待一段时间
            logger.info(f'当前在 {friend_class[index]} 中查找好友')
            sleep(1)
            if not is_select:
                if self.detect_select(name):
                    is_select = True
            sleep(1)
            if not is_select:
                if self.detect_select(name):
                    is_select = True

        # 点击确定
        logger.info('点击邀请确认')
        if not self.appear(self.I_INVITE_ENSURE):
            logger.warning('邀请好友时未出现邀请确认按钮')
        while 1:
            self.screenshot()
            if not self.appear(self.I_INVITE_ENSURE):
                break
            if self.appear_then_click(self.I_INVITE_ENSURE):
                continue
        # 哪怕没有找到好友也有点击 确认 以退出好友列表
        if not is_select:
            logger.warning('未找到好友')
            # 这个时候任务运行失败
            logger.info('任务失败')
            return False

        return True

    def invite_friends(self, config: InviteConfig) -> bool:
        """
        看情况邀请两个好友
        :return:
        """
        success = self.invite_friend(config.friend_1, config.find_mode)
        if not success:
            logger.warning('邀请好友 1 failed')
        # 如果是邀请第二个人
        if config.invite_number == InviteNumber.TWO:
            success = self.invite_friend(config.friend_2, config.find_mode)
            if not success:
                logger.warning('邀请好友 2 failed')
        sleep(0.5)

    def invite_again(self, default_invite: bool = True) -> bool:
        """
        作为队长战斗胜利后再次邀请队友，
        :param default_invite:  是否勾选默认
        :return:
        """
        logger.info('再次邀请')
        # 判断是否进入界面
        while 1:
            self.screenshot()
            if self.appear(self.I_UI_SURE):
                break
        # 如果勾选了默认邀请
        if default_invite:
            logger.info('点击默认邀请')
            while 1:
                self.screenshot()
                if self.appear(self.I_I_DEFAULT):
                    break
                if self.appear_then_click(self.I_I_NO_DEFAULT, interval=1):
                    continue
        else:
            logger.info('点击非默认邀请')
            while 1:
                self.screenshot()
                if self.appear(self.I_I_NO_DEFAULT):
                    break
                if self.appear_then_click(self.I_I_DEFAULT, interval=1):
                    continue

        # 点击确认
        logger.info('点击邀请确认')
        while 1:
            self.screenshot()
            if not self.appear(self.I_UI_SURE):
                break
            if self.appear_then_click(self.I_UI_SURE):
                continue

    def check_and_invite(self, default_invite: bool = True) -> bool:
        """
        队长战斗后 邀请队友
        :param default_invite:
        :return:
        """
        if not self.appear(self.I_UI_SURE):
            return False

        if default_invite:
            # 有可能是挑战失败的
            if self.appear(self.I_I_DEFAULT) or self.appear(self.I_I_NO_DEFAULT):
                logger.info('点击默认邀请')
                while 1:
                    self.screenshot()
                    if self.appear(self.I_I_DEFAULT):
                        break
                    if self.appear_then_click(self.I_I_NO_DEFAULT, interval=1):
                        continue
        # 点击确认
        while 1:
            self.screenshot()
            if not self.appear(self.I_UI_SURE):
                break
            if self.appear_then_click(self.I_UI_SURE, interval=1):
                continue

        return True

    def check_then_accept(self) -> bool:
        """
        队员接受邀请
        :return:
        """
        if not self.appear(self.I_I_ACCEPT):
            return False
        if self.appear(self.I_I_ACCEPT_JY):
            logger.info('寄养邀请忽略')
            return False
        logger.info('点击接受')
        while 1:
            self.screenshot()
            if self.is_in_room():
                return True
            # 被秒开
            # https://github.com/runhey/OnmyojiAutoScript/issues/230
            if self.appear(exit_list):
                return False
            if self.appear_then_click(self.I_I_NO_DEFAULT, interval=1):
                continue
            if self.appear_then_click(self.I_UI_SURE, interval=1):
                continue
            if self.appear_then_click(self.I_I_ACCEPT_DEFAULT, interval=1):
                continue
            if self.appear_then_click(self.I_I_ACCEPT, interval=1):
                continue
        return True

    def wait_battle(self, wait_time: time) -> bool:
        """
        在房间等待,(要求保证在房间里面) 队长开启战斗
        如果队长跑路了，或者的等待了很久还没开始
        :return: 如果成功进入战斗（反正就是不在房间 ）返回 True
                 如果失败了，（退出房间）返回 False
        """
        wait_second = wait_time.second + wait_time.minute * 60 + wait_time.hour * 60 * 60
        self.timer_wait = Timer(wait_second)
        self.timer_wait.start()
        logger.info(f'等待战斗 {wait_second} 秒')
        success = True
        while 1:
            self.screenshot()

            # 如果自己在探索界面或者是庭院，那就是房间已经被销毁了
            if self.appear(self.I_GI_HOME) or self.appear(self.I_GI_EXPLORE):
                logger.warning('房间已解散')
                success = False
                break

            if self.timer_wait.reached():
                logger.warning('等待战斗超时')
                success = False
                break

            # 如果队长跑路了，自己变成了队长: 自己也要跑路
            if self.appear(self.I_FIRE) or self.appear(self.I_FIRE_SEA):
                logger.warning('队长在等待战斗时逃跑,现在成为队长')
                success = False
                break

            # 判断是否进入战斗
            if self.is_in_room(is_screenshot=False):
                pass
            else:
                break

        # 调出循环只有这些可能性：
        # 1. 进入战斗（ui是战斗）
        # 2. 队长跑路（自己还是在房间里面）
        # 3. 等待时间到没有开始（还是在房间里面）
        # 4. 房间的时间到了被迫提出房间（这个时候来到了探索界面）
        if not success:
            logger.info('离开房间')
            self.exit_room()

        return success


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('du')
    t = GeneralInvite(c)

    # t.run_invite(c.orochi.invite_config, is_first=True)
    t.screenshot()
    print(t.appear(t.I_FIRE, threshold=0.8))
