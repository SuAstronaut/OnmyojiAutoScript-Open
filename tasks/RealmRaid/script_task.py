# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time

import re
from cached_property import cached_property
from module.atom.click import RuleClick
from module.atom.image import RuleImage
from module.atom.image_grid import ImageGrid
from module.exception import TaskEnd
from module.logger import logger
from module.team_link import PairPhase, PairSyncRuntime
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.GeneralBuff.config_buff import BuffClass
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.GameUi.page import page_realm_raid, page_main
from tasks.RealmRaid.assets import RealmRaidAssets
from tasks.RealmRaid.config import WhenAttackFail
from datetime import datetime, timedelta
from tasks.GameUi.page import exit_list
from tasks.Component.ReplaceShikigami.assets import ReplaceShikigamiAssets
from tasks.RealmRaid.config import ExitType
"""个人突破"""


class ScriptTask(RealmRaidAssets, GeneralBattle, SwitchSoul):
    medal_grid: ImageGrid = None
    success_count = 0
    max_success_count = 0

    def run(self):
        self._pair_sync_runtime = PairSyncRuntime(self.config, require_realm_raid_opt_in=True)
        self._pair_sync_runtime.begin_campaign(starts_with_raid=True)
        self._pair_sync_runtime.set_phase(PairPhase.RAID_RUNNING)
        con = self.config.realm_raid.raid_config
        if con.exit_type == ExitType.EightExitFour:
            self.run_3()
        else:
            self.run_2()

    def medal_fire(self) -> bool:
        """
        点击勋章
        :return:
        """
        # 点击勋章的挑战 和挑战
        time.sleep(0.2)
        is_click = False
        while 1:
            self.screenshot()

            if self.appear(self.I_FIRE, threshold=0.8):
                break

            if self.appear_then_click(self.I_SOUL_RAID, interval=1.5):
                while 1:
                    self.screenshot()
                    if self.appear_then_click(self.I_SOUL_RAID, interval=1.5):
                        continue
                    if not self.appear(self.I_SOUL_RAID, threshold=0.6):
                        break
                continue

            target = self.medal_grid.find_anyone(self.device.image)
            if target:
                self.appear_then_click(target, interval=2)  # 点击勋章,但是设置为两秒的间隔，适应不同的模拟器速度
                is_click = not is_click

            if is_click:
                continue
        logger.info(f'点击勋章')

        # 点击挑战
        self.wait_until_appear(self.I_FIRE)
        while 1:
            self.screenshot()
            if self.appear_then_click(self.I_FIRE, interval=2):
                continue
            if not self.appear(self.I_FIRE, threshold=0.8):
                break
        logger.info(f'点击 {self.I_FIRE.name}')

    # ------------------------------------------------------------------------------------------------------------------
    def run_2(self):
        con = self.config.realm_raid
        self.limit_count = con.raid_config.number_attack_all
        self.max_success_count = con.raid_config.number_attack_success

        if con.switch_soul_config.enable:
            self.run_switch_soul(con.switch_soul_config.switch_group_team)
        if con.switch_soul_config.enable_switch_by_name:
            self.run_switch_soul_by_name(con.switch_soul_config.group_name, con.switch_soul_config.team_name)

        self.ui_goto_page(page_realm_raid)

        # 有呱太活动的时候第一次进入还会 出现一个弹窗
        self.screenshot()
        if self.appear(self.I_FROG_RAID):
            logger.info(f'点击 {self.I_FROG_RAID.name}')
            while 1:
                self.screenshot()
                if not self.appear(self.I_FROG_RAID):
                    break
                if self.appear_then_click(self.I_FROG_RAID, interval=1):
                    continue
        # 判断是不是锁定阵容
        self.ensure_lock(con.general_battle_config.lock_team_enable)
        # 判断是否是呱太活动
        frog = self.is_frog(True)
        if frog:
            logger.info(f'呱太突破')

        # 开始循环
        success = True
        # 更改循环顺序
        while 1:
            self.screenshot()
            self._check_first_priority_task()
            # 检查票数
            if not self.check_ticket(con.raid_config.number_base):
                break
            # 挑战次数
            if self.success_count >= self.max_success_count:
                logger.info(f'✅ 胜利战斗次数: {self.success_count} / {self.max_success_count} , 结束任务')
                break
            if self.current_count >= self.limit_count:
                logger.info(f'总战斗次数: {self.current_count} / {self.limit_count} , 结束任务')
                break
            # ----------------------------------------开始进攻
            medal, index = self.find_one(False)
            if not medal and not index:
                # 已经没有可以挑战的了，只能刷新
                if con.raid_config.when_attack_fail == WhenAttackFail.CONTINUE:
                    logger.info('无人可攻击然后刷新')
                    if self.check_refresh():
                        continue
                    else:
                        success = False
                        break
                else:
                    logger.info('无人可攻击, 退出')
                    success = False
                    break
            # 判断是不是左上角第一个
            lock_before = con.general_battle_config.lock_team_enable
            if index == 1:
                logger.info('现在是位置1 (退四位置)')
                if con.raid_config.exit_type == ExitType.NineExitFour:
                    # 退四
                    self.fire(index)
                    for _ in range(4):
                        self.ui_click(exit_list, self.I_UI_CONFIRM, interval=1)
                        self.ui_click(self.I_UI_CONFIRM, self.I_AGAIN_BATTLE, interval=1)
                        while 1:
                            self.screenshot()
                            if self.appear(exit_list):
                                break
                            if self.appear_then_click(ReplaceShikigamiAssets.I_RS_NO_SUGGEST):
                                continue
                            if self.appear_then_click(self.I_UI_SURE):
                                continue
                            if self.appear_then_click(self.I_AGAIN_BATTLE):
                                continue

            elif self.check_medal_is_frog(frog, medal, index):
                # 如果挑战的这只是呱太的话，就要把锁定改为不锁定
                con.general_battle_config.lock_team_enable = False
            if index != 1:
                self.fire(index)
            last_battle = self.run_general_battle(con.general_battle_config)
            if last_battle:
                logger.info(f'战斗胜利')
                self.success_count += 1
            else:
                logger.info(f'战斗失败')

            if lock_before:
                con.general_battle_config.lock_team_enable = lock_before
            # 检查是否每三次领一个奖励
            if self.reward_detect_click(False):
                logger.info('三胜奖励')
                continue
            # 刷新 >> 如果勾选了三次刷新并且到达了三次，就刷新
            if con.raid_config.three_refresh and self.appear(self.I_RR_THREE, threshold=0.8):
                logger.info('三次刷新')
                if self.check_refresh():
                    continue
                else:
                    success = False
                    break
            # 刷新 >> 如果上一轮的失败并且勾选了失败刷新，就刷新
            if not last_battle and con.raid_config.when_attack_fail == WhenAttackFail.REFRESH:
                logger.info('战斗失败后刷新')
                if self.check_refresh():
                    continue
                else:
                    success = False
                    break
            # 如果上一轮失败 -> 退出
            if not last_battle and con.raid_config.when_attack_fail == WhenAttackFail.EXIT:
                logger.info('战斗失败并退出')
                break

        self._finish_realm_raid(success)

    def run_3(self):
        """
        两阶段个突循环:
        第一阶段: 5→6→3→2→1→4→7→8→9(退四+攻击) → 刷新
        第二阶段: 9→6→3→2→1→4→7→8→5 → 刷新
        每轮如此循环
        """
        con = self.config.realm_raid
        self.limit_count = con.raid_config.number_attack_all
        self.max_success_count = con.raid_config.number_attack_success

        if con.switch_soul_config.enable:
            self.run_switch_soul(con.switch_soul_config.switch_group_team)
        if con.switch_soul_config.enable_switch_by_name:
            self.run_switch_soul_by_name(con.switch_soul_config.group_name, con.switch_soul_config.team_name)

        self.ui_goto_page(page_realm_raid)

        # 有呱太活动的时候第一次进入还会 出现一个弹窗
        self.screenshot()
        if self.appear(self.I_FROG_RAID):
            logger.info(f'点击 {self.I_FROG_RAID.name}')
            while 1:
                self.screenshot()
                if not self.appear(self.I_FROG_RAID):
                    break
                if self.appear_then_click(self.I_FROG_RAID, interval=1):
                    continue
        # 判断是不是锁定阵容
        self.ensure_lock(con.general_battle_config.lock_team_enable)
        # 判断是否是呱太活动
        frog = self.is_frog(True)
        if frog:
            logger.info(f'呱太突破')

        # 两阶段顺序配置
        phase1_order = [5, 6, 3, 2, 1, 4, 7, 8, 9]
        phase2_order = [9, 6, 3, 2, 1, 4, 7, 8, 5]
        
        # 检测当前阶段: 扫描已完成位置,匹配阶段前缀
        completed = self._detect_completed_positions()
        current_phase, next_idx = self._detect_current_phase(completed, phase1_order, phase2_order)
        logger.info(f'🔍 已完成位置: {sorted(completed)}, 判定为第{current_phase}阶段')
        
        # 开始循环
        success = True
        if next_idx is not None:
            order_name = 'phase1' if current_phase == 1 else 'phase2'
            logger.info(f'⏭ 从{order_name}的第{next_idx + 1}个位置继续')
        else:
            logger.info('⏭ 所有位置已完成,等待自动刷新')
        
        while 1:
            self.screenshot()
            # self._check_first_priority_task()
            # 检查票数
            if not self.check_ticket(con.raid_config.number_base):
                break
            # 挑战次数
            if self.success_count >= self.max_success_count:
                logger.info(f'✅ 胜利战斗次数: {self.success_count} / {self.max_success_count} , 结束任务')
                break
            if self.current_count >= self.limit_count:
                logger.info(f'总战斗次数: {self.current_count} / {self.limit_count} , 结束任务')
                break
            
            # 根据当前阶段选择攻击顺序
            attack_order = phase1_order if current_phase == 1 else phase2_order
            
            # ----------------------------------------按顺序查找可攻击位置
            medal, index = self._find_one_by_position_order(attack_order, False)
            if not medal and not index:
                # 当前阶段完成,切换阶段并刷新
                if current_phase == 1:
                    current_phase = 2
                    logger.info('⚡ 第一阶段完成,切换到第二阶段')
                else:
                    current_phase = 1
                    logger.info('⚡ 一轮完成,刷新开始新一轮')
                continue
            
            # 判断是否到达位置9(退四位置)
            lock_before = con.general_battle_config.lock_team_enable
            exit_four_done = False
            if index == 9 and current_phase == 1:
                logger.info('现在是位置9 (退四位置)')
                # 退四
                self.fire(index)
                for _ in range(4):
                    self.ui_click(exit_list, self.I_UI_CONFIRM, interval=1)
                    self.ui_click(self.I_UI_CONFIRM, self.I_AGAIN_BATTLE, interval=1)
                    while 1:
                        self.screenshot()
                        if self.appear(exit_list):
                            break
                        if self.appear_then_click(ReplaceShikigamiAssets.I_RS_NO_SUGGEST):
                            continue
                        if self.appear_then_click(self.I_UI_SURE):
                            continue
                        if self.appear_then_click(self.I_AGAIN_BATTLE):
                            continue
                exit_four_done = True

            elif self.check_medal_is_frog(frog, medal, index):
                # 如果挑战的这只是呱太的话，就要把锁定改为不锁定
                con.general_battle_config.lock_team_enable = False
            
            if not exit_four_done:
                self.fire(index)
            last_battle = self.run_general_battle(con.general_battle_config)
            if last_battle:
                logger.info(f'战斗胜利')
                self.success_count += 1
            else:
                logger.info(f'战斗失败')

            if lock_before:
                con.general_battle_config.lock_team_enable = lock_before
            # 检查是否每三次领一个奖励
            if self.reward_detect_click(False):
                logger.info('三胜奖励')
                # 三胜奖励后游戏会自动刷新,检查是否需要切换阶段
                completed_after = self._detect_completed_positions()
                if len(completed_after) == 0:
                    if current_phase == 1:
                        current_phase = 2
                        logger.info('⚡ 三胜刷新后,切换到第二阶段')
                    else:
                        current_phase = 1
                        logger.info('⚡ 三胜刷新后,开始新一轮')
                continue
            # 刷新 >> 如果勾选了三次刷新并且到达了三次，就刷新
            if con.raid_config.three_refresh and self.appear(self.I_RR_THREE, threshold=0.8):
                logger.info('三次刷新')
                if self.check_refresh():
                    continue
                else:
                    success = False
                    break
            # 刷新 >> 如果上一轮的失败并且勾选了失败刷新，就刷新
            if not last_battle and con.raid_config.when_attack_fail == WhenAttackFail.REFRESH:
                logger.info('战斗失败后刷新')
                if self.check_refresh():
                    continue
                else:
                    success = False
                    break
            # 如果上一轮失败 -> 退出
            if not last_battle and con.raid_config.when_attack_fail == WhenAttackFail.EXIT:
                logger.info('战斗失败并退出')
                break
            # 战斗胜利后检测: 游戏自动刷新(已完成数为0)说明当前阶段已结束
            if last_battle:
                completed_after = self._detect_completed_positions()
                if len(completed_after) == 0:
                    if current_phase == 1:
                        current_phase = 2
                        logger.info('⚡ 检测到自动刷新,切换到第二阶段')
                    else:
                        current_phase = 1
                        logger.info('⚡ 检测到自动刷新,开始新一轮')

        self._finish_realm_raid(success)

    def _finish_realm_raid(self, success: bool) -> None:
        self.set_next_run(task='RealmRaid', success=success, finish=True)
        if self._pair_sync_runtime.enabled:
            if success:
                if self._pair_sync_runtime.wait_for_raid_release():
                    self._pair_sync_runtime.schedule_orochi_now(self)
                else:
                    logger.info('已达到设置的联动轮数，本次不再唤起御魂')
            else:
                self._pair_sync_runtime.mark_error('个人突破任务未正常完成')
        raise TaskEnd

    # ----------------------------------------------------------------------------------------------------------------------
    # 2023.7.21 改版个人突破

    def ensure_lock(self, lock_team_enable: bool):
        """
        确保锁定阵容
        :param lock_team_enable:
        :return:
        """
        if lock_team_enable:
            while 1:
                self.screenshot()
                if self.appear_then_click(self.I_UNLOCK, interval=1):
                    continue
                if self.appear_then_click(self.I_UNLOCK_2, interval=1):
                    continue
                if self.appear(self.I_LOCK_2, threshold=0.9):
                    break
                if self.appear(self.I_LOCK, threshold=0.9):
                    break
            logger.info(f'点击 {self.I_UNLOCK.name}')
        else:
            while 1:
                self.screenshot()
                if self.appear_then_click(self.I_LOCK, interval=1):
                    continue
                if self.appear_then_click(self.I_LOCK_2, interval=1):
                    continue
                if self.appear(self.I_UNLOCK_2, threshold=0.9):
                    break
                if self.appear(self.I_UNLOCK, threshold=0.9):
                    break
            logger.info(f'点击 {self.I_LOCK.name}')

    def is_frog(self, screenshot: bool = True) -> bool:
        """
        判断是不是呱太活动
        :return:
        """
        if screenshot:
            self.screenshot()
        if self.appear(self.I_FROG_MEDAL):
            return True
        return False

    def check_ticket(self, base: int = 0) -> bool:
        """
        检查是不是有票， 检查这个票是否大于等于基准
        :param base:
        :return:
        """
        if base < 0 or base > 30:
            logger.warning(f'无效的基准值 {base}')
            base = 0
        self.wait_until_appear(self.I_BACK_RED)
        self.screenshot()
        cu, res, total = self.O_NUMBER.ocr(self.device.image)

        if total == 0:
            self.reward_detect_click(False)
            # 增加出现聊天框遮挡，处理奖励之后，重新识别票数
            cu, res, total = self.O_NUMBER.ocr(self.device.image)

        # 持续循环，直到成功读取到数字
        while 1:
            # 如果cu、res和total都为0，表示尚未读取到数字
            if cu == 0 and res == 0 and total == 0:
                # 增加出现聊天框遮挡，处理奖励之后，重新识别票数
                self.reward_detect_click(False)
                # 使用O_NUMBER.ocr方法尝试读取数字
                cu, res, total = self.O_NUMBER.ocr(self.device.image)
            else:
                # 如果已经读取到数字，跳出循环
                break

        if total != 30:
            # 识别出错直接返回
            logger.warning(f'识别出错直接返回')
            return True
        if cu == 0 and res == 30 and cu + res == total:
            logger.info(f'突破票为0')
            return False
        elif cu + res == total and cu < base:
            logger.warning(f'突破票不足')
            return False
        return True

    @cached_property
    def order_medal(self) -> ImageGrid:
        order_attack = self.config.realm_raid.raid_config.order_attack
        support_number = [0, 1, 2, 3, 4, 5]
        match = {
            0: self.I_MEDAL_0,
            1: self.I_MEDAL_1,
            2: self.I_MEDAL_2,
            3: self.I_MEDAL_3,
            4: self.I_MEDAL_4,
            5: self.I_MEDAL_5,
        }
        order = order_attack.replace(' ', '').replace('\n', '')
        order = re.split(r'>', order)
        order = [int(i) for i in order]
        order = [i for i in order if i in support_number]

        images = []
        for i in order:
            images.append(match[i])
        return ImageGrid(images)

    @cached_property
    def partition(self) -> list[RuleClick]:
        return [self.C_PARTITION_1, self.C_PARTITION_2, self.C_PARTITION_3, self.C_PARTITION_4, self.C_PARTITION_5,
                self.C_PARTITION_6, self.C_PARTITION_7, self.C_PARTITION_8, self.C_PARTITION_9]

    def find_one(self, screenshot: bool = True) -> tuple:
        """
        找到一个可以打的，并且检查一下是不是这一个的是第几个的
        我们约定次序是：从左到右 上到下
        1 2 3
        4 5 9
        7 8 9
        :return: 返回的第一个参数是一个RuleImage, 第二个参数是位置信息
        如果没有找到，返回None, None
        """
        if screenshot:
            self.screenshot()
        image = self.device.image
        # https://github.com/runhey/OnmyojiAutoScript/issues/71
        # 如果开始失败后继挑战剩下的
        if self.config.realm_raid.raid_config.when_attack_fail == WhenAttackFail.CONTINUE:
            for i, roi in enumerate(self.false_roi):
                self.false_image.roi_back = roi
                self.success_image.roi_back = self.partition[i].roi_back
                # logger.info(f"{self.success_image.roi_front} + {self.success_image.roi_back}")
                # logger.info(self.appear(self.success_image))
                if self.appear(self.false_image) or self.appear(self.success_image):
                    logger.info(f'位置 {i + 1} 已完成')
                    x, y, w, h = self.partition[i].roi_back
                    image[y:y + h, x:x + w, ...] = 0

        # # 保存调试图片（已涂黑击破区域）
        # self.device.image = image
        # self.save_image(wait_time=0)

        # -----------------------------------------------------
        target = self.order_medal.find_anyone(image)
        if target:
            center = target.front_center()
            for i, click in enumerate(self.partition):
                x1, x2, y1, y2 = click.roi_front[0], click.roi_front[0] + click.roi_front[2], \
                    click.roi_front[1], click.roi_front[1] + click.roi_front[3]
                if x1 < center[0] < x2 and y1 < center[1] < y2:
                    logger.info(f'找到一个勋章 [{target}], 顺序是 {i + 1}')
                    return target, i + 1

        return None, None

    def _find_one_by_position_order(self, position_order: list, screenshot: bool = True) -> tuple:
        """
        按指定位置顺序查找可攻击的位置
        :param position_order: 位置顺序列表,如 [5,6,3,2,1,4,7,8,9]
        :param screenshot: 是否截图
        :return: (medal_image, position_index), 未找到返回 (None, None)
        """
        if screenshot:
            self.screenshot()
        
        all_medals = [self.I_MEDAL_5, self.I_MEDAL_4, self.I_MEDAL_3,
                      self.I_MEDAL_2, self.I_MEDAL_1, self.I_MEDAL_0]
        
        for pos in position_order:
            click = self.partition[pos - 1]
            # 检查该位置是否已完成
            is_completed = False
            self.false_image.roi_back = click.roi_back
            self.success_image.roi_back = click.roi_back
            if self.appear(self.false_image) or self.appear(self.success_image):
                is_completed = True
            if is_completed:
                continue
            # 在该位置区域查找任意勋章
            for medal_img in all_medals:
                old_roi_back = medal_img.roi_back
                medal_img.roi_back = click.roi_back
                found = self.appear(medal_img)
                medal_img.roi_back = old_roi_back
                if found:
                    logger.info(f'按位置顺序找到一个勋章, 位置是 {pos}')
                    return medal_img, pos
        
        return None, None

    def _detect_completed_positions(self) -> set:
        """
        扫描9个位置,返回已完成(已进攻/已击破)的位置编号集合
        :return: 已完成位置的set, 如 {1, 3, 5}
        """
        self.screenshot()
        completed = set()
        for i in range(9):
            click = self.partition[i]
            self.false_image.roi_back = click.roi_back
            self.success_image.roi_back = click.roi_back
            if self.appear(self.false_image) or self.appear(self.success_image):
                completed.add(i + 1)
        return completed

    def _detect_current_phase(self, completed: set, phase1_order: list, phase2_order: list) -> tuple:
        """
        根据已完成位置集合,匹配当前处于哪个阶段
        匹配逻辑: 已完成集合 == order的前N个元素构成的集合
        :param completed: 已完成的位置编号集合
        :param phase1_order: 第一阶段攻击顺序
        :param phase2_order: 第二阶段攻击顺序
        :return: (phase, next_order_index)
                 phase: 1或2
                 next_order_index: 在order中下一个要攻击的索引, None表示该阶段全部完成需刷新
        """
        n = len(completed)

        # 没有已完成的,从第一阶段开始
        if n == 0:
            return 1, 0

        # 全部完成,需要刷新后开始第一阶段
        if n == 9:
            return 1, None

        # 尝试匹配第一阶段前缀
        p1_prefix = set(phase1_order[:n])
        if completed == p1_prefix:
            return 1, n

        # 尝试匹配第二阶段前缀
        p2_prefix = set(phase2_order[:n])
        if completed == p2_prefix:
            return 2, n

        # 都不匹配(可能手动打过一些),默认第一阶段,让_find_one_by_position_order自动跳过已完成的
        logger.warning(f'已完成位置 {completed} 不匹配任何阶段前缀,默认第一阶段')
        return 1, 0

    def check_medal_is_frog(self, is_activity: False, target: RuleImage, order: int) -> bool:
        """
        检查这个是不是呱太，为此之前你还需要判断是不是 处于呱太活动的
        :param target:
        :param is_activity: 如果不是呱太活动，那么就不需要检查了
        :param order:
        :return:
        """
        if not is_activity:
            return False
        # 好像呱太的位置是只有 789这三个
        if order < 7:
            return False
        # 有时候四星可能和五星的混一起
        if target != self.I_MEDAL_5 and target != self.I_MEDAL_4:
            return False
        match_ocr = {
            1: self.O_FROG_1,
            2: self.O_FROG_2,
            3: self.O_FROG_3,
            4: self.O_FROG_4,
            5: self.O_FROG_5,
            6: self.O_FROG_6,
            7: self.O_FROG_7,
            8: self.O_FROG_8,
            9: self.O_FROG_9,
        }
        target_ocr = match_ocr[order]
        self.screenshot()
        if target_ocr.ocr(self.device.image) == 20:
            logger.info(f'找到呱太勋章 [{target}]')
            return True
        return False

    def reward_detect_click(self, screenshot: bool = True) -> bool:
        """
        检测是否出现 每三次就有奖励的界面, 有就领取
        :return:
        """
        if screenshot:
            self.screenshot()
        # 由于更改识别顺序，退出战斗之后，需要先等待回到个人突破界面，即识别到红色退出按钮，再进行奖励判断
        self.wait_until_appear(self.I_BACK_RED)
        self.ui_click_until_disappear(self.I_SOUL_RAID, interval=1)
        text = self.O_TEXT.ocr(self.device.image)
        # 识别突破卷区域，如果识别到了且其中含有文字，即有聊天框遮挡则进入循环，等待三胜奖励出现并点击，循环退出条件为识别到票（即*/*的形式）
        if text != "":
            if re.search(r'[\u4e00-\u9fff]', text):
                while 1:
                    self.screenshot()
                    result = self.O_TEXT.ocr(self.device.image)
                    if not re.search(r'[\u4e00-\u9fff]', result) and re.search(r'(\d+)/(\d+)', result):
                        return True
                    if self.appear_then_click(self.I_SOUL_RAID, interval=1):
                        continue

        # if self.appear(self.I_SOUL_RAID):
        #     self.screenshot()
        #     # 稳定一次的截图时间
        #     # 再次判断是否出现的
        #     if not self.appear(self.I_SOUL_RAID):
        #         return False
        #     while 1:
        #         self.screenshot()
        #         if not self.appear(self.I_SOUL_RAID, threshold=0.7):
        #             return True
        #         if self.appear_then_click(self.I_SOUL_RAID, interval=1.5):
        #             continue

    def check_refresh(self, screenshot: bool = True) -> bool:
        """
        检查是否出现了刷新的按钮
        如果可以刷新就刷新，返回True
        如果在CD中，就返回False
        :return:
        """
        if screenshot:
            self.screenshot()
        if not self.appear(self.I_FRESH):
            logger.info(f'未找到刷新按钮，可能在CD中')
            return False

        self.ui_click(self.I_FRESH, self.I_UI_SURE, interval=1)
        self.ui_click_until_disappear(self.I_UI_SURE, interval=1)
        return True

    def fire(self, order: int):
        """
        挑战
        :param order:  第几个
        :return:
        """
        click = self.partition[order - 1]
        self.wait_until_appear(self.I_RR_PERSON)
        while 1:
            if self.is_in_battle():
                break
            if self.appear_then_click(self.I_FIRE, interval=1):
                continue
            if self.click(click, interval=1.8):
                continue
        logger.info(f'点击挑战 {order} 成功')

    @cached_property
    def false_roi(self) -> list:
        width = 86
        height = 64
        x1 = 386
        x2 = 714
        x3 = 1047
        y1 = 143
        y2 = 277
        y3 = 414
        return [
            [x1, y1, width, height],  # 左上角
            [x2, y1, width, height],
            [x3, y1, width, height],
            [x1, y2, width, height],  # 左中
            [x2, y2, width, height],
            [x3, y2, width, height],
            [x1, y3, width, height],  # 左下
            [x2, y3, width, height],
            [x3, y3, width, height],
        ]

    @cached_property
    def false_image(self):
        return RuleImage(roi_front=(0, 0, 63, 32),
                         roi_back=(0, 0, 100, 100),
                         threshold=0.8,
                         method="Template matching",
                         file="./tasks/RyouToppa/dev/loser_sign_1.png")

    @cached_property
    def success_image(self):
        return RuleImage(roi_front=(0, 0, 63, 32),
                         roi_back=(0, 0, 100, 100),
                         threshold=0.8,
                         method="Template matching",
                         file="./tasks/RyouToppa/dev/finished_1.png")

    def run_general_battle(self, config: GeneralBattleConfig = None, buff: BuffClass or list[BuffClass] = None) -> bool:
        """
        运行脚本
        :return:
        """
        # 本人选择的策略是只要进来了就算一次，不管是不是打完了
        logger.hr("通用战斗开始", 2)
        self.current_count += 1
        logger.info(f'当前任务: 个人突破')
        logger.info(f'当前次数: {self.current_count} / {self.limit_count}')
        logger.info(f'胜利次数: {self.success_count} / {self.max_success_count}')

        task_run_time = datetime.now() - self.start_time
        # 格式化时间，只保留整数部分的秒
        task_run_time_seconds = timedelta(seconds=int(task_run_time.total_seconds()))
        logger.info(f'当前时间: {task_run_time_seconds} / {self.limit_time}')

        if config is None:
            config = GeneralBattleConfig()

        # 如果没有锁定队伍。那么可以根据配置设定队伍
        if not config.lock_team_enable:
            logger.info("锁定阵容未启用")
            # 如果更换队伍
            if self.current_count == 1:
                self.switch_preset_team(config.preset_enable, config.preset_group, config.preset_team)

            # 打开buff
            self.check_buff(buff)

            # 点击准备按钮
            self.wait_until_appear(self.I_PREPARE_HIGHLIGHT)
            self.wait_until_appear(self.I_BUFF)
            while 1:
                self.screenshot()
                if not self.appear(self.I_BUFF):
                    break
                if self.appear_then_click(self.I_PREPARE_HIGHLIGHT, interval=1.5):
                    continue
            logger.info("点击准备确认按钮")

            # 照顾一下某些模拟器慢的
            time.sleep(0.1)

        # 绿标
        self.wait_until_disappear(self.I_BUFF)
        if self.is_in_battle(False):
            self.green_mark(config.green_enable, config.green_mark)

        win = self.battle_wait(config.random_click_swipt_enable)
        return win


if __name__ == "__main__":
    from module.config.config import Config

    config = Config('切换账号')
    t = ScriptTask(config)

    t.run_3()
