# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time

import re
import unicodedata
from cached_property import cached_property
from datetime import timedelta, datetime
from difflib import SequenceMatcher
from module.atom.image_grid import ImageGrid
from module.atom.ocr import RuleOcr
from module.base.timer import Timer
from module.base.utils import crop
from module.exception import TaskEnd
from module.logger import logger
from tasks.Component.ReplaceShikigami.replace_shikigami import ReplaceShikigami
from tasks.GameUi.page import page_realm, page_guild, page_main
from tasks.KekkaiUtilize.assets import KekkaiUtilizeAssets
from tasks.KekkaiUtilize.config import UtilizeRule, SelectFriendList, no_takeover_resume_at
from tasks.KekkaiUtilize.utils import CardClass
from tasks.Utils.config_enum import ShikigamiClass
from tasks.GameUi.game_ui import GameUi


class ScriptTask(GameUi, ReplaceShikigami, KekkaiUtilizeAssets):
    """ 结界蹭卡 """
    last_best_index = 99
    run_utilize_count = 0
    ap_max_num = 0
    jade_max_num = 0
    first_utilize = True

    # 1280x720 寄养好友搜索界面的固定区域。名字区域单独 OCR，避免区服名称干扰。
    FRIEND_SEARCH_PANEL_BUTTON = (603, 126)
    FRIEND_SEARCH_INPUT = (360, 188)
    FRIEND_SEARCH_BUTTON = (578, 188)
    FRIEND_SEARCH_SUBMIT_RETRIES = 2
    # 右侧结界卡“未公开”红色挂牌所在区域（1280x720）。区域刻意避开下方斗鱼红色名称条。
    FRIEND_UNPUBLISHED_ROI = (960, 210, 1025, 335)
    FRIEND_UNPUBLISHED_RED_RATIO = 0.08
    FRIEND_RESULT_ROWS = (
        ((300, 215, 260, 65), (420, 267)),
        ((300, 320, 260, 65), (420, 374)),
        ((300, 425, 260, 65), (420, 479)),
        ((300, 530, 260, 65), (420, 584)),
    )
    FRIEND_EMPTY_OCR = RuleOcr(
        roi=(470, 205, 400, 60), area=(470, 205, 400, 60),
        mode='Single', method='Default', keyword='', name='specified_friend_empty'
    )
    FRIEND_SEARCH_BUTTON_OCR = RuleOcr(
        roi=(525, 160, 110, 60), area=(525, 160, 110, 60),
        mode='Single', method='Default', keyword='', name='specified_friend_search_button'
    )

    def run(self):
        resume_at = no_takeover_resume_at(self.config.kekkai_utilize.no_takeover_config)
        if resume_at is not None:
            logger.info(f'当前处于结界寄养不顶号时段，本次寄养顺延至 {resume_at}')
            self.set_next_run(task='KekkaiUtilize', target=resume_at)
            raise TaskEnd('KekkaiUtilize')

        self._wait_for_prewarm_due()

        con = self.config.kekkai_utilize.utilize_config

        # 育成界面去蹭卡
        self.check_utilize_add()
        # 查看育成满级
        self.check_max_lv(con.shikigami_class)
        # 检查蹭卡收获
        if con.is_utilize_harvest:
            self.check_utilize_harvest()
        # 收体力盒子或者是经验盒子
        self.check_box_ap_or_exp()
        # 收取寮资金和体力
        self.check_guild_ap_or_assets()

        raise TaskEnd

    def _wait_for_prewarm_due(self) -> bool:
        """游戏本来就在运行时，也必须等到原定时间，不能因预热而提前寄养。"""
        kekkai = self.config.kekkai_utilize
        prewarm = kekkai.prewarm_config
        if not prewarm.enable:
            return False
        due_at = kekkai.scheduler.next_run
        remaining = (due_at - datetime.now()).total_seconds()
        max_expected_wait = max(30, min(300, int(prewarm.lead_seconds))) + 15
        if remaining <= 0 or remaining > max_expected_wait:
            return False

        logger.info('结界寄养已提前就绪，等待原定时间 %s（剩余 %.1f 秒）', due_at, remaining)
        while True:
            remaining = (due_at - datetime.now()).total_seconds()
            if remaining <= 0:
                break
            self.device.stuck_record_clear()
            time.sleep(min(0.5, remaining))
        logger.info('结界寄养原定时间已到，开始执行任务')
        return True

    def check_utilize_add(self):
        self.ui_goto_page(page_realm)

        con = self.config.kekkai_utilize.utilize_config
        while 1:
            if self.run_utilize_count >= 2:
                self.push_notify(content=f"{self.run_utilize_count}次没有发现适合蹭的卡, 5分钟后运行")
                self.set_next_run(task='KekkaiUtilize', target=datetime.now() + timedelta(minutes=5))
                return

            # 无论收不收到菜，都会进入看看至少看一眼时间还剩多少
            # 进入进入式神育成界面
            self.realm_goto_grown()
            if not self.appear(self.I_UTILIZE_ADD):
                remaining_time = self.O_UTILIZE_RES_TIME.ocr(self.device.image)
                if not isinstance(remaining_time, timedelta):
                    logger.warning('OCR剩余时间错误')
                logger.info(f'蹭卡剩余时间: {remaining_time}')
                # 已经蹭上卡了，设置下次蹭卡时间  # 减少30秒
                # remaining_time = remaining_time - timedelta(seconds=30)
                next_time = datetime.now() + remaining_time
                self.set_next_run(task='KekkaiUtilize', target=next_time)
                return
            # 从式神育成界面到 蹭卡界面
            self.grown_goto_utilize()
            # 开始执行寄养
            self.run_utilize(con.select_friend_list, con.shikigami_class, con.shikigami_order)
            # 回到寮结界
            self.ui_goto_page(page_realm)

    def check_max_lv(self, shikigami_class: ShikigamiClass = ShikigamiClass.N):
        """
        在结界界面，进入式神育成，检查是否有满级的，如果有就换下一个
        退出的时候还是结界界面
        :return:
        """
        self.realm_goto_grown()
        self.ui_click_until_disappear(self.I_RS_SMART_EXCHANGE)
        # if self.appear(self.I_RS_LEVEL_MAX):
        #     # 存在满级的式神
        #     logger.info('存在满级式神并替换')
        #     self.unset_shikigami_max_lv()
        #     self.switch_shikigami_class(shikigami_class)
        #     self.set_shikigami(shikigami_order=7, stop_image=self.I_RS_NO_ADD)
        # else:
        #     logger.info('没有满级式神')
        # if self.detect_no_shikigami():
        #     logger.warning('没有任何式神育成房间')
        #     self.switch_shikigami_class(shikigami_class)
        #     self.set_shikigami(shikigami_order=7, stop_image=self.I_RS_NO_ADD)
        # 进入寮结界
        self.ui_goto_page(page_realm)

    def recive_guild_ap_or_assets(self):
        for i in range(1, 5):
            # 在寮的主界面 检查是否有收取体力或者是收取寮资金
            if self.check_guild_ap_or_assets():
                logger.warning(f'第[{i}]次检查寮收获,成功')
                return
            else:
                logger.warning(f'第[{i}]次检查寮收获寮收获,失败')
                self.ui_goto_page(page_main)

    def check_guild_ap_or_assets(self, ap_enable: bool = True, assets_enable: bool = True) -> bool:
        """
        在寮的主界面 检查是否有收取体力或者是收取寮资金
        如果有就顺带收取
        :return:
        """
        self.ui_goto_page(page_guild)

        timer_check = Timer(2)
        timer_check.start()
        click_ap = False
        while 1:
            self.screenshot()

            # 获得奖励
            if self.ui_reward_appear_click():
                timer_check.reset()
                continue

            if timer_check.reached():
                logger.warning('检查寮收获超时')
                return False

            if click_ap and not self.appear(self.I_GUILD_AP) and not self.appear(self.I_UI_REWARD):
                return True

            # 关闭展开的寮活动横幅
            if self.appear_then_click(self.I_GUILD_EXPAND):
                timer_check.reset()
                continue

            # 资金收取确认
            if self.appear_then_click(self.I_GUILD_ASSETS_RECEIVE, interval=1):
                time.sleep(1)
                timer_check.reset()
                continue

            # 收资金
            if self.appear_then_click(self.I_GUILD_ASSETS, interval=1.5, threshold=0.6):
                timer_check.reset()
                continue

            # 收体力
            if self.appear_then_click(self.I_GUILD_AP, interval=1):
                # 等待1秒，看到获得奖励
                time.sleep(1)
                logger.info('点击公会体力成功')
                if self.ui_reward_appear_click(True):
                    logger.info('点击奖励成功')
                    click_ap = True
                    timer_check.reset()
                continue

    def check_box_ap_or_exp(self):
        """
        收体力盒子或者是经验盒子
        """
        # 先是体力盒子
        def _check_ap_box():
            # 点击盒子
            timer_ap = Timer(6)
            timer_ap.start()
            while 1:
                self.screenshot()

                if self.appear(self.I_UI_REWARD):
                    while 1:
                        self.screenshot()
                        if not self.appear(self.I_UI_REWARD):
                            break
                        if self.appear_then_click(self.I_UI_REWARD, self.C_UI_REWARD, interval=1, threshold=0.6):
                            continue
                    logger.info('奖励盒子')
                    break

                if self.appear_then_click(self.I_BOX_AP, interval=1):
                    continue
                if self.appear_then_click(self.I_AP_EXTRACT, interval=2):
                    continue
                if timer_ap.reached():
                    logger.warning('提取体力盒超时')
                    break

        # 经验盒子
        def _check_exp_box():
            time_exp = Timer(2)
            time_exp.start()
            while 1:
                self.screenshot()
                # 如果出现结界皮肤， 表示收取好了
                if self.appear(self.I_REALM_SHIN) and not self.appear(self.I_BOX_EXP, threshold=0.6):
                    break
                # 如果出现收取确认，表明进入到了有满级的
                if self.appear(self.I_UI_SURE):
                    self.screenshot()
                    if not self.appear(self.I_CANCEL):
                        logger.info('没有取消按钮')
                        continue
                    while 1:
                        self.screenshot()
                        if not self.appear(self.I_UI_SURE):
                            break
                        if self.appear_then_click(self.I_UI_SURE, interval=1):
                            continue
                    break

                # if self.appear(self.I_EXP_EXTRACT):
                #     # 如果达到今日领取的最大，就不领取了
                #     cur, res, totol = self.O_BOX_EXP.ocr(self.device.image)
                #     if cur == res == totol == 0:
                #         continue
                #     if cur == totol and cur + res == totol:
                #         logger.info('经验盒已达最大不收集')
                #         break
                if self.appear_then_click(self.I_BOX_EXP, threshold=0.6, interval=1):
                    continue
                if self.appear_then_click(self.I_EXP_EXTRACT, interval=1):
                    break

                if time_exp.reached():
                    logger.warning('提取经验盒超时')
                    break

        self.screenshot()
        box_ap = self.appear(self.I_BOX_AP)
        box_exp = self.appear(self.I_BOX_EXP, threshold=0.6) or self.appear(self.I_BOX_EXP_MAX, threshold=0.6)
        if box_ap:
            _check_ap_box()
            logger.info('提取体力盒完成')
            self.ui_goto_page(page_realm)
        if box_exp:
            _check_exp_box()
            logger.info('提取经验盒完成')

    def check_utilize_harvest(self) -> bool:
        """
        在寮结界界面检查是否有收获
        :return: 如果没有返回False, 如果有就收菜返回True
        """
        self.screenshot()
        appear = self.appear(self.I_UTILIZE_EXP)
        if not appear:
            logger.info('没有利用收获')
            return False

        # 收获
        self.ui_get_reward(self.I_UTILIZE_EXP)
        return True

    def realm_goto_grown(self):
        """
        进入式神育成界面
        :return:
        """
        while 1:
            self.screenshot()

            if self.in_shikigami_growth():
                break

            if self.appear_then_click(self.I_SHI_GROWN, interval=1):
                continue
        logger.info('进入式神育成')

    def grown_goto_utilize(self):
        """
        从式神育成界面到 蹭卡界面
        :return:
        """
        self.screenshot()
        if not self.appear(self.I_UTILIZE_ADD):
            logger.warning('没有利用加成')
            return False

        while 1:
            self.screenshot()

            if self.appear(self.I_U_ENTER_REALM):
                break
            if self.appear_then_click(self.I_UTILIZE_ADD, interval=2):
                continue
        logger.info('进入利用')
        return True

    def switch_friend_list(self, friend: SelectFriendList = SelectFriendList.SAME_SERVER) -> bool:
        """
        切换不同的服务区
        :param friend:
        :return:
        """
        logger.info('切换好友列表到 %s', friend)
        if friend == SelectFriendList.SAME_SERVER:
            check_image = self.I_UTILIZE_FRIEND_GROUP
        else:
            check_image = self.I_UTILIZE_ZONES_GROUP

        timer_click = Timer(1)
        timer_click.start()
        while 1:
            self.screenshot()
            if self.appear(check_image):
                break
            if timer_click.reached():
                timer_click.reset()
                x, y = check_image.coord()
                self.device.click(x=x, y=y, control_name=check_image.name)
        if friend == SelectFriendList.DIFFERENT_SERVER:
            time.sleep(1)
        time.sleep(0.5)

    @cached_property
    def order_targets(self) -> ImageGrid:
        rule = self.config.kekkai_utilize.utilize_config.utilize_rule
        if rule == UtilizeRule.DEFAULT:
            return ImageGrid([self.I_U_FISH_6, self.I_U_TAIKO_6, self.I_U_FISH_5, self.I_U_TAIKO_5])
        elif rule == UtilizeRule.FISH:
            return ImageGrid([self.I_U_FISH_6, self.I_U_FISH_5])
        elif rule == UtilizeRule.TAIKO:
            return ImageGrid([self.I_U_TAIKO_6, self.I_U_TAIKO_5])
        else:
            logger.error('未知的利用规则')
            raise ValueError('未知的结界利用规则')

    @cached_property
    def order_cards(self) -> list[CardClass]:
        rule = self.config.kekkai_utilize.utilize_config.utilize_rule
        result = []
        if rule == UtilizeRule.DEFAULT:
            result = [CardClass.FISH6, CardClass.TAIKO6, CardClass.FISH5, CardClass.TAIKO5,
                      CardClass.TAIKO4, CardClass.FISH4, CardClass.TAIKO3, CardClass.FISH3]
        elif rule == UtilizeRule.FISH:
            result = [CardClass.FISH6, CardClass.FISH5,
                      CardClass.TAIKO6, CardClass.TAIKO5, CardClass.FISH4, CardClass.TAIKO4, CardClass.FISH3,
                      CardClass.TAIKO3]
        elif rule == UtilizeRule.TAIKO:
            result = [CardClass.TAIKO6, CardClass.TAIKO5,
                      CardClass.FISH6, CardClass.FISH5, CardClass.TAIKO4, CardClass.FISH4, CardClass.TAIKO3,
                      CardClass.FISH3]
        else:
            logger.error('未知的利用规则')
            raise ValueError('未知的结界利用规则')
        return result

    def run_utilize(self, friend: SelectFriendList = SelectFriendList.SAME_SERVER,
                    shikigami_class: ShikigamiClass = ShikigamiClass.N,
                    shikigami_order: int = 7):
        """
        执行寄养
        :param shikigami_class:
        :param friend:
        :param shikigami_order:
        """
        logger.hr('开始利用')
        con = self.config.kekkai_utilize.utilize_config
        if self.first_utilize:
            self.first_utilize = False
            if not con.specified_friend_enable:
                if friend == SelectFriendList.SAME_SERVER:
                    self.swipe(self.S_U_END, interval=3)
                    self.switch_friend_list(SelectFriendList.DIFFERENT_SERVER)
                    self.switch_friend_list(SelectFriendList.SAME_SERVER)
                else:
                    self.switch_friend_list(SelectFriendList.DIFFERENT_SERVER)
                    self.swipe(self.S_U_END, interval=3)
                    self.switch_friend_list(SelectFriendList.SAME_SERVER)
                    self.switch_friend_list(SelectFriendList.DIFFERENT_SERVER)
            else:
                logger.info('指定好友模式：跳过旧版好友列表滑动与往返切区')
        elif not con.specified_friend_enable:
            self.switch_friend_list(friend)

        # --------------- 好友与结界卡选择 ---------------
        if con.specified_friend_enable:
            selected = self._select_specified_friend(
                con.specified_same_server_friend_names,
                con.specified_different_server_friend_names,
                con.specified_friend_names,
                friend
            )
        else:
            selected = self._select_optimal_resource_card()

        if not selected:
            self.run_utilize_count += 1
            return False

        # 找到卡,重置次数
        self.run_utilize_count = 0
        logger.info('开始执行进入结界蹭卡流程')
        self.screenshot()
        # 进入结界
        if not self.appear(self.I_U_ENTER_REALM):
            logger.warning('找不到进入结界按钮')
            # 可能是滑动的时候出错
            logger.warning('最好的原因是滑动错误')
            return False
        wait_timer = Timer(20)
        wait_timer.start()
        while 1:
            self.screenshot()
            if self.appear(self.I_U_ADD_1) or self.appear(self.I_U_ADD_2):
                logger.info('出现进入好友结界按钮')
                break
            if self.appear(self.I_CHECK_FRIEND_REALM_1):
                self.wait_until_stable(self.I_CHECK_FRIEND_REALM_1)
                logger.info('出现进入好友结界按钮')
                break
            if self.appear(self.I_CHECK_FRIEND_REALM_3):
                self.wait_until_stable(self.I_CHECK_FRIEND_REALM_3)
                logger.info('出现进入好友结界按钮')
                break
            if wait_timer.reached():
                self.save_image(wait_time=0, push_flag=False, content='进入好友结界超时', image_type='png')
                logger.warning('出现好友结界超时')
                return False
            if self.appear_then_click(self.I_CHECK_FRIEND_REALM_2, interval=1.5):
                logger.info('Click too fast to enter the friend\'s realm pool')
                continue
            if self.appear_then_click(self.I_U_ENTER_REALM, interval=2.5):
                time.sleep(0.5)
                continue
        logger.info('进入好友结界')

        # 判断好友的有两个位置还是一个坑位
        stop_image = None
        self.screenshot()
        if self.appear(self.I_U_ADD_1):  # 右侧第一个有（无论左侧有没有）
            logger.info('右侧有一个')
            stop_image = self.I_U_ADD_1
        elif self.appear(self.I_U_ADD_2) and not self.appear(self.I_U_ADD_1):  # 右侧第二个有 但是最左边的没有，这表示只留有一个坑位
            logger.info('右侧有两个')
            stop_image = self.I_U_ADD_2
        if not stop_image:
            # 没有坑位可能是其他人的手速太快了抢占了
            self.save_image(content='没有坑位了', wait_time=0, push_flag=False, image_type='png')
            logger.warning('没有坑位可能是其他人的手速太快了抢占了')
            return False
        # 切换式神的类型
        self.switch_shikigami_class(shikigami_class)
        # 上式神
        self.set_shikigami(shikigami_order, stop_image)
        return True

    @staticmethod
    def _normalize_friend_name(name: str) -> str:
        """统一全角字符并移除 OCR 中常见的空白和标点。"""
        normalized = unicodedata.normalize('NFKC', str(name or ''))
        return re.sub(r'[\s·•.。,_，、:：;；\-—]+', '', normalized)

    @staticmethod
    def _parse_friend_names(raw_names: str) -> list[str]:
        """把配置中的中英文逗号、分号或换行拆成有序昵称列表。"""
        names = re.split(r'[,，、;；\r\n]+', str(raw_names or ''))
        result = []
        for name in names:
            name = name.strip()
            if name and name not in result:
                result.append(name)
        return result

    @classmethod
    def _parse_friend_targets(cls, raw_names: str, default_zone: SelectFriendList):
        """解析“同区:昵称/跨区:昵称”；没有区服前缀时沿用全局蹭卡区服。"""
        targets = []
        for item in cls._parse_friend_names(raw_names):
            zone = default_zone
            friend_name = item
            same_match = re.match(r'^(?:同区|好友)\s*[:：]\s*(.+)$', item)
            different_match = re.match(r'^跨区\s*[:：]\s*(.+)$', item)
            if same_match:
                zone = SelectFriendList.SAME_SERVER
                friend_name = same_match.group(1).strip()
            elif different_match:
                zone = SelectFriendList.DIFFERENT_SERVER
                friend_name = different_match.group(1).strip()
            target = (zone, friend_name)
            if friend_name and target not in targets:
                targets.append(target)
        return targets

    @staticmethod
    def _friend_zone_label(zone: SelectFriendList) -> str:
        return '同区' if zone == SelectFriendList.SAME_SERVER else '跨区'

    @classmethod
    def _build_friend_targets(cls, same_names: str, different_names: str,
                              legacy_names: str, default_zone: SelectFriendList):
        """优先使用两个独立输入框；都为空时兼容旧版单输入框配置。"""
        targets = []
        for friend_name in cls._parse_friend_names(same_names):
            target = (SelectFriendList.SAME_SERVER, friend_name)
            if target not in targets:
                targets.append(target)
        for friend_name in cls._parse_friend_names(different_names):
            target = (SelectFriendList.DIFFERENT_SERVER, friend_name)
            if target not in targets:
                targets.append(target)
        if targets:
            return targets
        return cls._parse_friend_targets(legacy_names, default_zone)

    @classmethod
    def _friend_name_score(cls, expected: str, detected: str) -> float:
        """计算昵称相似度；完整一致始终优先，OCR 多识别一个字符时仍可容错。"""
        expected = cls._normalize_friend_name(expected)
        detected = cls._normalize_friend_name(detected)
        if not expected or not detected:
            return 0.0
        if expected == detected:
            return 1.0
        return SequenceMatcher(None, expected, detected).ratio()

    @classmethod
    def _single_friend_result_matches(cls, expected: str, detected: str) -> bool:
        """长昵称只有一条结果时，允许 OCR 漏字，但必须保留足够多的有序字符。"""
        expected = cls._normalize_friend_name(expected)
        detected = cls._normalize_friend_name(detected)
        if cls._friend_name_score(expected, detected) >= 0.88:
            return True
        if len(expected) < 4 or not detected:
            return False
        matched = sum(
            block.size
            for block in SequenceMatcher(None, expected, detected).get_matching_blocks()
        )
        return matched >= 2 and matched / len(expected) >= 0.4

    def _restore_input_method(self, original_ime: str):
        """中文输入完成后恢复用户原本的输入法。"""
        fast_ime = 'com.github.uiautomator/.FastInputIME'
        try:
            if original_ime == fast_ime:
                return
            if original_ime and original_ime != 'null':
                self.device.adb_shell(['ime', 'enable', original_ime])
                self.device.adb_shell(['ime', 'set', original_ime])
            self.device.adb_shell(['ime', 'disable', fast_ime])
        except Exception as exc:
            # 输入已经完成，恢复失败不应导致整个寄养任务中断。
            logger.warning('恢复原输入法失败: %s', exc)

    def _current_input_method(self) -> str:
        return self.device.adb_shell(
            ['settings', 'get', 'secure', 'default_input_method']
        ).strip()

    def _search_friend_name(self, friend_name: str,
                            restore_input_method: bool = True) -> bool:
        """输入中文昵称并确认游戏确实执行了搜索。"""
        original_ime = ''
        try:
            if not self._ensure_friend_search_panel():
                return False
            if restore_input_method:
                original_ime = self._current_input_method()
            self.device.click(*self.FRIEND_SEARCH_INPUT, control_name='specified_friend_search_input')
            time.sleep(0.3)
            self.device.u2.send_keys(friend_name, clear=True)
            logger.info('已输入指定好友昵称: %s', friend_name)
            time.sleep(0.5)

            # 游戏输入框处于编辑状态时，第一次点击“搜索”只会结束文字输入，
            # 不会提交搜索。先明确退出编辑状态，再单独执行真正的搜索点击。
            self.device.u2.click(*self.FRIEND_SEARCH_BUTTON)
            logger.info('已退出指定好友昵称输入状态: %s', friend_name)
            time.sleep(0.5)

            # 中文输入和后续点击都走 uiautomator2，避免两套控制通道交接时丢触摸。
            # 正式提交后仍会检查结果；没有生效就留在当前分区重试，不直接切区。
            for attempt in range(1, self.FRIEND_SEARCH_SUBMIT_RETRIES + 1):
                self.device.u2.click(*self.FRIEND_SEARCH_BUTTON)
                logger.info(
                    '已点击指定好友搜索按钮（uiautomator2，第%s/%s次）',
                    attempt, self.FRIEND_SEARCH_SUBMIT_RETRIES
                )
                time.sleep(1.2)
                self.screenshot()
                if self._friend_search_submitted(friend_name):
                    logger.info('指定好友搜索已生效: %s', friend_name)
                    return True
                if attempt < self.FRIEND_SEARCH_SUBMIT_RETRIES:
                    logger.warning('搜索已提交但暂未确认目标结果，保持当前分区并重试: %s', friend_name)

            logger.warning('搜索已提交但连续两次未能确认目标结果: %s', friend_name)
            return False
        except Exception as exc:
            logger.exception('中文好友昵称输入失败: %s', exc)
            return False
        finally:
            if restore_input_method:
                self._restore_input_method(original_ime)

    def _friend_search_submitted(self, friend_name: str) -> bool:
        """用搜索结果确认提交成功，避免只凭“点击没有报错”就继续切区。"""
        empty_text = str(self.FRIEND_EMPTY_OCR.ocr(self.device.image) or '')
        if '未添加好友' in empty_text or '未创建结界' in empty_text:
            return True

        rows = self._ocr_friend_result_rows()
        if any(
            self._friend_name_score(friend_name, detected) >= 0.88
            for detected, _ in rows
        ):
            return True
        return len(rows) == 1 and self._single_friend_result_matches(
            friend_name, rows[0][0]
        )

    def _friend_search_panel_opened(self) -> bool:
        """通过界面中的“搜索”文字判断输入面板是否已经展开。"""
        text = str(self.FRIEND_SEARCH_BUTTON_OCR.ocr(self.device.image) or '')
        return '搜索' in text

    def _ensure_friend_search_panel(self) -> bool:
        """先点击顶部放大镜展开搜索面板，再进入中文输入流程。"""
        self.screenshot()
        if self._friend_search_panel_opened():
            return True

        logger.info('搜索面板尚未展开，点击顶部放大镜')
        self.device.click(
            *self.FRIEND_SEARCH_PANEL_BUTTON,
            control_name='specified_friend_open_search_panel'
        )
        wait_timer = Timer(5).start()
        while not wait_timer.reached():
            time.sleep(0.4)
            self.screenshot()
            if self._friend_search_panel_opened():
                logger.info('指定好友搜索面板已展开')
                return True
        logger.warning('点击顶部放大镜后，指定好友搜索面板仍未展开')
        return False

    def _ocr_friend_result_rows(self) -> list[tuple[str, tuple[int, int]]]:
        """识别当前搜索结果的四个可见好友昵称。"""
        results = []
        for index, (roi, click_point) in enumerate(self.FRIEND_RESULT_ROWS, start=1):
            rule = RuleOcr(
                roi=roi, area=roi, mode='Single', method='Default', keyword='',
                name=f'specified_friend_result_{index}'
            )
            detected = str(rule.ocr(self.device.image) or '').strip()
            if detected:
                results.append((detected, click_point))
        return results

    def _find_exact_friend_result(self, friend_name: str):
        """从模糊搜索结果中选出唯一、最接近完整昵称的一行。"""
        empty_text = str(self.FRIEND_EMPTY_OCR.ocr(self.device.image) or '')
        if '未添加好友' in empty_text or '未创建结界' in empty_text:
            logger.info('搜索好友[%s]无结果', friend_name)
            return None

        rows = self._ocr_friend_result_rows()
        if not rows:
            logger.warning('搜索好友[%s]后没有识别到结果行', friend_name)
            return None

        scored = sorted(
            ((self._friend_name_score(friend_name, detected), detected, click_point)
             for detected, click_point in rows),
            reverse=True,
            key=lambda item: item[0]
        )
        best_score, best_name, best_point = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else 0.0
        logger.info('指定好友匹配: 目标[%s] 最佳OCR[%s] 分数%.2f', friend_name, best_name, best_score)

        single_result_match = len(rows) == 1 and self._single_friend_result_matches(
            friend_name, best_name
        )
        # OCR 偶尔会在昵称末尾多识别一个装饰字符，因此允许高相似度；
        # 但两个候选分数太接近时拒绝点击，避免寄养错人。
        if not single_result_match and (
                best_score < 0.88 or (best_score < 1.0 and best_score - second_score < 0.08)):
            logger.warning('无法唯一确认指定好友[%s]，本次不点击任何搜索结果', friend_name)
            return None
        if single_result_match and best_score < 0.88:
            logger.info(
                '指定好友长昵称OCR不完整，但搜索结果唯一且保留关键字符，接受该结果: %s',
                best_name
            )
        return best_point

    @classmethod
    def _friend_unpublished_red_ratio(cls, image) -> float:
        """计算“未公开”挂牌区域中独有的深红色像素比例。"""
        region = crop(image, cls.FRIEND_UNPUBLISHED_ROI)
        if region.size == 0:
            return 0.0
        red = region[:, :, 0].astype(float)
        green = region[:, :, 1].astype(float)
        blue = region[:, :, 2].astype(float)
        red_mask = (
            (red >= 100)
            & (red >= green * 1.7)
            & (red >= blue * 1.7)
        )
        return float(red_mask.mean())

    def _friend_realm_unpublished(self) -> bool:
        """识别右侧红色“未公开”挂牌，未公开结界不得参与收益比较。"""
        red_ratio = self._friend_unpublished_red_ratio(self.device.image)
        logger.info('指定好友结界公开状态检测: 红色挂牌占比 %.3f', red_ratio)
        return red_ratio >= self.FRIEND_UNPUBLISHED_RED_RATIO

    def _specified_friend_card_info(self):
        """返回指定好友的卡片类型、原始收益和统一折算收益，不符合条件则返回 None。"""
        self.screenshot()
        if self._friend_realm_unpublished():
            logger.info('指定好友结界未公开，跳过该好友，不计入收益候选')
            return None
        if not (self.appear(self.I_U_BIG_5) or self.appear(self.I_U_BIG_6)):
            logger.info('指定好友当前不是五星或六星结界卡')
            return None

        card_type, card_value = self.check_card_num()
        con = self.config.kekkai_utilize.utilize_config
        rule = con.utilize_rule
        allowed = (
            card_type in ('斗鱼', '太鼓') if rule == UtilizeRule.DEFAULT else
            card_type == '斗鱼' if rule == UtilizeRule.FISH else
            card_type == '太鼓' if rule == UtilizeRule.TAIKO else False
        )
        if not allowed:
            logger.info('指定好友结界卡[%s@%s]不符合蹭卡类型[%s]', card_type, card_value, rule)
            return None

        # 与原自动选卡的“蹭卡系数”含义一致：
        # 斗鱼直接使用体力值；太鼓按“多少勾玉折算100体力”换算为可比较的体力价值。
        if card_type == '斗鱼':
            comparable_value = float(card_value)
        else:
            coefficient = max(1, int(con.tai_ko_percentage))
            comparable_value = card_value * 100.0 / coefficient
        logger.info(
            '指定好友结界卡符合要求: %s@%s，折算收益%.1f',
            card_type, card_value, comparable_value
        )
        return card_type, card_value, comparable_value

    def _select_specified_friend(self, same_names: str, different_names: str,
                                 legacy_names: str, default_zone: SelectFriendList) -> bool:
        """整个好友收益比较共用一次 FastInputIME，结束后统一恢复原输入法。"""
        original_ime = self._current_input_method()
        try:
            return self._select_specified_friend_with_active_ime(
                same_names, different_names, legacy_names, default_zone
            )
        finally:
            self._restore_input_method(original_ime)

    def _select_specified_friend_with_active_ime(
            self, same_names: str, different_names: str,
            legacy_names: str, default_zone: SelectFriendList) -> bool:
        """跨同区/跨区搜索全部指定好友，比较收益后重新选中最佳好友。"""
        friend_targets = self._build_friend_targets(
            same_names, different_names, legacy_names, default_zone
        )
        if not friend_targets:
            logger.warning('已开启指定好友寄养，但没有填写指定好友昵称')
            return False

        candidates = []
        current_selected = None
        total = len(friend_targets)
        for index, (friend_zone, friend_name) in enumerate(friend_targets, start=1):
            zone_label = self._friend_zone_label(friend_zone)
            logger.info('搜索指定好友[%s/%s][%s]: %s', index, total, zone_label, friend_name)
            self.switch_friend_list(friend_zone)
            if not self._search_friend_name(friend_name, restore_input_method=False):
                continue
            self.screenshot()
            click_point = self._find_exact_friend_result(friend_name)
            if not click_point:
                continue
            self.device.click(*click_point, control_name='specified_friend_exact_result')
            current_selected = (friend_zone, friend_name)
            time.sleep(1)
            card_info = self._specified_friend_card_info()
            if not card_info:
                continue
            card_type, card_value, comparable_value = card_info
            candidates.append((comparable_value, friend_zone, friend_name, card_type, card_value))
            logger.info(
                '收益候选[%s][%s]: %s %s@%s，折算收益%.1f',
                len(candidates), zone_label, friend_name, card_type, card_value, comparable_value
            )

        if not candidates:
            logger.warning('所有指定好友均无可用的五星/六星斗鱼或太鼓卡')
            return False

        # 相同收益时，max 会保留配置顺序中最先出现的好友。
        best_value = max(candidate[0] for candidate in candidates)
        best = next(candidate for candidate in candidates if candidate[0] == best_value)
        _, best_zone, best_name, best_type, best_card_value = best
        summary = '；'.join(
            f'{self._friend_zone_label(zone)}-{name}:{card_type}{card_value}(折算{value:.1f})'
            for value, zone, name, card_type, card_value in candidates
        )
        logger.info('指定好友收益对比完成: %s', summary)
        logger.info(
            '收益最高好友[%s]: %s，%s@%s，折算收益%.1f',
            self._friend_zone_label(best_zone), best_name, best_type, best_card_value, best_value
        )

        # 最后一位检查的好友就是最高收益者时，当前已经选中，无需重复搜索。
        if current_selected == (best_zone, best_name):
            logger.info('当前已选中收益最高好友，跳过重复搜索: %s', best_name)
            return True

        # 当前停留在其他好友，需要重新搜索并选中最高收益好友。
        self.switch_friend_list(best_zone)
        if not self._search_friend_name(best_name, restore_input_method=False):
            return False
        self.screenshot()
        click_point = self._find_exact_friend_result(best_name)
        if not click_point:
            logger.warning('收益比较完成后无法重新定位最佳好友[%s]', best_name)
            return False
        self.device.click(*click_point, control_name='specified_friend_best_result')
        time.sleep(1)
        if not self._specified_friend_card_info():
            logger.warning('重新选择最佳好友[%s]后，结界卡状态已经变化', best_name)
            return False
        logger.info('已重新选中收益最高好友: %s', best_name)
        return True

    def _select_optimal_resource_card(self):
        """整合后的智能选卡主逻辑（无嵌套函数版）"""
        # 动态生成资源配置（需根据实际配置传入）
        # 最高会多少勾玉换100体力就填入何值，数值越小代表勾玉价值越高（比如：你每天60勾玉就换取100体力就填入60）
        tai_ko_percentage = self.config.kekkai_utilize.utilize_config.tai_ko_percentage
        # 固定体力值，动态计算勾玉值
        FISH_VALUES = [151, 143, 134, 126, 118, 109, 101, 92, 84]  # 体力值不变
        TAIKO_VALUES = [round(val * tai_ko_percentage / 100) for val in FISH_VALUES]   # 按百分比调整，四舍五入
        RESOURCE_PRESETS = {
            '斗鱼': FISH_VALUES,
            '太鼓': TAIKO_VALUES
        }
        # 动态获取最大值
        RESOURCE_CONFIG = {
            '斗鱼': {'max': max(FISH_VALUES), 'record_attr': 'ap_max_num'},
            '太鼓': {'max': max(TAIKO_VALUES), 'record_attr': 'jade_max_num'}
        }

        MAX_INDEX = 99

        def get_resource_index(resource_name, current_value, preset_values):
            """获取资源匹配的档位索引"""
            for idx, val in enumerate(preset_values):
                if current_value >= val:
                    logger.info(f'📊 {resource_name}区间匹配: {current_value} ≥ {val} (档位{idx})')
                    return idx
            logger.warning(f'⚠️ {resource_name}值[{current_value}]低于所有预设')
            return MAX_INDEX

        while True:
            self.screenshot()

            # 第一阶段：初始记录获取
            if self.ap_max_num == 0 and self.jade_max_num == 0:
                logger.hr('第一阶段：初始记录获取', 2)
                if self._current_select_best(RESOURCE_CONFIG):
                    logger.info(f'✅ 完美结界卡确认成功，重置状态')
                    self.ap_max_num, self.jade_max_num = 0, 0
                    return True
                logger.info(f'📝 记录最佳值 | 斗鱼:{self.ap_max_num} 太鼓:{self.jade_max_num}')
                return False

            logger.hr('第二阶段：资源优先级判断', 2)
            # 获取双资源档位
            ap_index = get_resource_index('斗鱼', self.ap_max_num, RESOURCE_PRESETS['斗鱼'])
            jade_index = get_resource_index('太鼓', self.jade_max_num, RESOURCE_PRESETS['太鼓'])

            # 双资源超限处理
            if ap_index == MAX_INDEX and jade_index == MAX_INDEX:
                logger.warning('🔄 斗鱼和太鼓均低于预设，重置初始记录')
                self.ap_max_num, self.jade_max_num = 0, 0
                return False

            # 决策优先级
            res_type, target = ('斗鱼', self.ap_max_num) if ap_index <= jade_index else ('太鼓', self.jade_max_num)
            logger.info(f'⚖️ 选择{res_type}卡 | 目标: {target}')

            # 第三阶段：执行选卡操作
            logger.hr('第三阶段：执行选卡操作', 2)
            if self._current_select_best(RESOURCE_CONFIG, res_type, target, selected_card=True):
                logger.info(f'✅ {res_type}卡确认成功，重置状态')
                self.ap_max_num, self.jade_max_num = 0, 0
                return True
            else:
                logger.warning(f'❌ {res_type}卡确认失败，重置状态')
                self.ap_max_num, self.jade_max_num = 0, 0
                return False

    def _current_select_best(self, resource_config, best_card_type=None, best_card_num=0, selected_card=False):
        """结界卡选择核心逻辑（集成版）
        功能：滑动屏幕寻找最优资源卡，支持两种模式：
        - 探索模式：记录当前遇到的最佳结界卡数值
        - 确认模式：根据给定条件选择指定类型结界卡

        :param best_card_type: 目标卡类型('太鼓'/'斗鱼')
        :param best_card_num:  要求的最低数值
        :param selected_card:  是否处于确认选择模式
        :return: 找到符合条件返回True，否则None
        """
        # ============== 配置常量 ==============#
        RESOURCE_CONFIG = resource_config

        swipe_count = 0  # 滑动次数
        MAX_SWIPES = 3  # 最大滑动次数
        CONSEC_MISS = 2  # 允许连续无卡次数
        TIMEOUT = 120  # 操作超时(秒)

        # ============== 初始化阶段 ==============#
        logger.info(f'启动{"探索模式" if not selected_card else f"确认模式 | 目标: {best_card_type} @ {best_card_num}"}')
        timer = Timer(TIMEOUT).start()
        miss_count = 0  # 连续无卡计数器

        # ============== 主滑动循环 ==============#
        while True:
            # 超时检测
            if timer.reached():
                logger.warning('⏰ 操作超时，终止流程')
                return None

            # ------ 步骤1: 截图识别结界卡 ------#
            self.screenshot()
            cards = self.order_targets.find_everyone(self.device.image)

            # 处理无卡情况
            if not cards:
                miss_count += 1
                logger.info(f'第{swipe_count}次滑动 | 未检测到结界卡' if swipe_count > 0 else '初始界面 | 未检测到结界卡')
                # 连续无卡超过阈值则终止
                if miss_count > CONSEC_MISS:
                    logger.warning(f'⚠️ 连续{miss_count}次 | 未检测到结界卡, 终止流程')
                    return None
                # 执行滑动操作
                self.perform_swipe_action()
                swipe_count += 1
                continue

            miss_count = 0  # 重置无卡计数器

            # ------ 步骤2: 处理识别到的结界卡 ------
            cards_list = [target for target, _, _ in cards]
            logger.info((f'第{swipe_count}次滑动' if swipe_count > 0 else '初始界面') + f' | 检测到结界卡：{cards_list}')

            # 遍历所有结界卡（已按位置排序）
            for _, _, area in cards:
                # 设置点击区域并获取结界卡详情
                self.C_SELECT_CARD.roi_front = area
                self.click(self.C_SELECT_CARD)
                time.sleep(2)  # 等待结界卡详情加载

                # 解析结界卡类型和数值
                card_type, card_value = self.check_card_num()

                # 跳过无效结界卡（类型未知或数值异常）
                if card_type == 'unknown' or card_value <= 0 or card_type not in RESOURCE_CONFIG:
                    logger.info(f'⏭️ 跳过无效卡: {card_type}@{card_value}')
                    continue

                # ====== 模式分支处理 ======#
                current_max = RESOURCE_CONFIG[card_type]['max']
                record_attr = RESOURCE_CONFIG[card_type]['record_attr']
                current_record = getattr(self, record_attr, 0)
                logger.info(f'🔍 识别卡片: {card_type} | 当前值: {card_value}, 最优值: {current_record}')

                # 更新最佳记录
                if card_value > current_record:
                    logger.info(f'📈 更新记录: {card_type} | {current_record} → {card_value}')
                    setattr(self, record_attr, card_value)

                if selected_card:  # 确认选择模式
                    # 检查是否符合选择条件
                    if (card_type == best_card_type) and (card_value >= best_card_num):
                        logger.info(f'🎉 确认蹭卡: {card_type} | 当前值: {card_value} ≥ 目标值: {best_card_num}')
                        self.save_image(push_flag=False, wait_time=0, content=f'🎉 确认蹭卡（{card_type}: {card_value}）')
                        return True
                else:  # 探索记录模式
                    # 发现完美卡直接返回
                    if card_value >= current_max:
                        message = f'🎉 完美蹭卡 | {card_type}: {card_value}'
                        logger.info(message)
                        self.save_image(push_flag=False, wait_time=0, content=message)
                        return True

            # ------ 步骤3: 滑动到下一屏 ------#
            if swipe_count >= MAX_SWIPES:
                break
            self.perform_swipe_action()
            swipe_count += 1

        # ============== 终止处理 ==============#
        logger.warning(f'⚠️ 已达到最大滑动次数{MAX_SWIPES}, 终止流程')
        return None

    def perform_swipe_action(self):
        """统一滑动操作"""
        # duration = 2
        # safe_pos_x = random.randint(340, 600)
        # safe_pos_y = random.randint(500, 565)
        # p1 = (safe_pos_x, safe_pos_y)
        # p2 = (safe_pos_x, safe_pos_y - 416)
        # logger.info('Swipe %s -> %s, %sS ' % (point2str(*p1), point2str(*p2), duration))
        # self.device.swipe_adb(p1, p2, duration=duration)

        self.swipe(self.S_U_UP, duration=1, wait_up_time=1)
        self.device.click_record_clear()
        time.sleep(2)

    def check_card_num(self) -> tuple[str, int]:
        """优化版数值提取方法，返回结界卡类型及对应数值"""
        self.screenshot()
        # OCR识别
        raw_text = self.O_CARD_NUM.ocr(self.device.image)
        # logger.info(f'OCR原始结果: {raw_text}')

        # 判断结界卡类型
        if any(c in raw_text for c in ['体', 'カ', '力']):
            card_type = '斗鱼'
        elif any(c in raw_text for c in ['勾', '玉']):
            card_type = '太鼓'
        else:
            logger.warning(f'结界卡类型识别失败，原始内容: {raw_text}')
            # self.push_notify(content=f'结界卡类型识别失败: {raw_text}')
            return 'unknown', 0  # 未知类型返回0

        # 提取纯数字部分（兼容带+号的情况，如+100）
        cleaned = re.sub(r'[^\d+]', '', raw_text)  # 保留数字和加号
        match = re.search(r'\d+', cleaned)  # 匹配连续数字

        try:
            value = int(match.group()) if match else 0
        except ValueError:
            logger.warning(f'数值转换异常，清理后文本: {cleaned}')
            value = 0

        if value <= 0:
            self.push_notify(content=f'数值异常: {raw_text} -> 解析值: {value}')
            return card_type, 0

        # logger.info(f'识别成功: 卡类型: {card_type}, 数值: {value}')
        return card_type, value


if __name__ == "__main__":
    from module.config.config import Config

    c = Config('du')
    t = ScriptTask(c)
    t.check_box_ap_or_exp()
    # t._select_optimal_resource_card()
    # for i in range(10):
    #     t.perform_swipe_action()
    # t.recive_guild_ap_or_assets()
    # t.check_utilize_add()
    # t.check_card_num('勾玉', 67)
    # t.screenshot()
    # print(t.appear(t.I_BOX_EXP, threshold=0.6))
    # print(t.appear(t.I_BOX_EXP_MAX, threshold=0.6))
