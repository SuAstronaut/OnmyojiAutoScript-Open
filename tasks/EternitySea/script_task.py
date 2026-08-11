# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from time import sleep

import random
from datetime import datetime, timedelta
from module.exception import RequestHumanTakeover
from module.exception import TaskEnd
from module.logger import logger
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.GeneralInvite.general_invite import GeneralInvite
from tasks.Component.GeneralRoom.general_room import GeneralRoom
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.EternitySea.assets import EternitySeaAssets
from tasks.EternitySea.config import EternitySea
from tasks.GameUi.page import page_main, page_soul_zones
from tasks.Orochi.config import UserStatus


class ScriptTask(GeneralBattle, GeneralRoom, GeneralInvite, SwitchSoul, EternitySeaAssets):
    """ 永生之海 """
    soul_full_push = True

    @property
    def task_name(self):
        return "EternitySea"

    def _two_teams_switch_sous(self, config):
        if config.enable:
            self.run_switch_soul(config.switch_group_team)

        if config.enable_switch_by_name:
            self.run_switch_soul_by_name(config.group_name, config.team_name)

    def run(self) -> None:

        self.limit_count = self._task_config.eternity_sea_config.limit_count
        self.limit_time = self._limit_time

        self._two_teams_switch_sous(self._task_config.switch_soul_config_1)
        self._two_teams_switch_sous(self._task_config.switch_soul_config_2)
        match self._task_config.eternity_sea_config.user_status:
            case UserStatus.LEADER: success = self.run_leader()
            case UserStatus.MEMBER: success = self.run_member()
            case UserStatus.ALONE: success = self.run_alone()
            case _: logger.error('未知的用户状态')

        self.set_next_run(finish=True, success=True)

        raise TaskEnd

    def run_leader(self):
        logger.info('开始运行队长模式')
        self.ui_goto_page(page_soul_zones)
        logger.info("进入永生之海")
        self.ui_click(self.I_ETERNITY_SEA, self.I_FORM_TEAM, interval=1)
        layer = self._task_config.eternity_sea_config.layer
        self.check_layer(self.L_LAYER_LIST, layer)
        self.check_lock(self._task_config.general_battle_config.lock_team_enable)
        # 创建队伍
        logger.info('创建队伍')
        while 1:
            self.screenshot()
            if self.appear(self.I_CHECK_TEAM):
                break
            if self.appear_then_click(self.I_FORM_TEAM, interval=1):
                continue
        # 创建房间
        self.create_room()
        self.ensure_private()
        self.create_ensure()

        # 邀请队友
        success = True
        is_first = True
        # 这个时候我已经进入房间了哦
        while 1:
            self.screenshot()
            # 无论胜利与否, 都会出现是否邀请一次队友
            # 区别在于，失败的话不会出现那个勾选默认邀请的框
            if self.check_and_invite(self._task_config.invite_config.default_invite):
                continue

            if self.current_count >= self.limit_count:
                logger.info("永生之海次数已达上限")
                break
            if datetime.now() - self.start_time >= self.limit_time:
                logger.info("永生之海时间已达上限")
                break

            # 如果没有进入房间那就不需要后面的邀请
            if not self.is_in_room():
                if self.is_room_dead():
                    logger.warning('永生之海任务失败')
                    success = False
                    break
                continue

            # 点击挑战
            if not is_first:
                if self.run_invite(config=self._task_config.invite_config):
                    self.run_general_battle(config=self._task_config.general_battle_config)
                else:
                    # 邀请失败，退出永生之海任务
                    logger.warning('邀请失败，退出永生之海任务')
                    success = False
                    break

            # 第一次会邀请队友
            if is_first:
                if not self.run_invite(config=self._task_config.invite_config, is_first=True):
                    logger.warning('邀请失败，退出本次永生之海任务')
                    success = False
                    break
                else:
                    is_first = False
                    self.run_general_battle(config=self._task_config.general_battle_config)

        # 当结束或者是失败退出循环的时候只有两个UI的可能，在房间或者是在组队界面
        # 如果在房间就退出
        self.save_image(push_flag=True, wait_time=0, content=f'任务已完成{self.current_count}次,用时: {timedelta(seconds=int((datetime.now() - self.start_time).total_seconds()))}')
        return success

    def run_member(self):
        logger.info('开始队员运行')

        # 进入战斗流程
        self.device.stuck_record_add('BATTLE_STATUS_S')
        while 1:
            self.screenshot()

            #限制
            if self.current_count >= self.limit_count:
                logger.info("永生之海次数已达上限")
                break
            if datetime.now() - self.start_time >= self.limit_time:
                logger.info("永生之海时间已达上限")
                break

            if self.check_then_accept():
                continue

            if self.is_in_room():
                self.device.stuck_record_clear()
                if self.wait_battle(wait_time=self._task_config.invite_config.wait_time):
                    self.run_general_battle(config=self._task_config.general_battle_config)
                else:
                    break
            # 队长秒开的时候，检测是否进入到战斗中
            elif self.check_take_over_battle(False, config=self._task_config.general_battle_config):
                continue

        self.save_image(push_flag=True, wait_time=0, content=f'任务已完成{self.current_count}次,用时: {timedelta(seconds=int((datetime.now() - self.start_time).total_seconds()))}')
        return True

    def run_alone(self) -> bool:
        logger.info("开始单人运行")
        self.ui_goto_page(page_soul_zones)
        logger.info("进入永生之海")
        self.ui_click(self.I_ETERNITY_SEA, self.I_FORM_TEAM, interval=1)
        self.check_lock(self._task_config.general_battle_config.lock_team_enable)

        while 1:
            self.screenshot()

            if self.current_count >= self.limit_count:
                logger.info("永生之海次数已达上限")
                break
            if datetime.now() - self.start_time >= self.limit_time:
                logger.info("永生之海时间已达上限")
                break

            # 点击挑战
            if self.appear(self.I_COMMON_FIRE):
                self.ui_click_until_disappear(self.I_COMMON_FIRE, interval=1)
                self.run_general_battle(config=self.config.evo_zone.general_battle_config)

    def is_room_dead(self) -> bool:
        # 如果在探索界面或者是出现在组队界面，那就是可能房间死了
        sleep(0.5)
        if self.appear(self.I_MATCHING) or self.appear(self.I_CHECK_EXPLORATION):
            sleep(0.5)
            if self.appear(self.I_MATCHING) or self.appear(self.I_CHECK_EXPLORATION):
                return True
        return False

    @property
    def _limit_time(self) -> timedelta:
        limit_time = self._task_config.eternity_sea_config.limit_time
        return timedelta(
            hours=limit_time.hour, minutes=limit_time.minute, seconds=limit_time.second
        )

    @property
    def _task_config(self) -> EternitySea:
        return self.config.model.eternity_sea

    def battle_wait(self, random_click_swipt_enable: bool) -> bool:
        """
        重写战斗等待
        # https://github.com/runhey/OnmyojiAutoScript/issues/95
        :param random_click_swipt_enable:
        :return:
        """
        # 重写
        self.device.stuck_record_add('BATTLE_STATUS_S')
        self.device.click_record_clear()
        # 战斗过程 随机点击和滑动 防封
        while 1:
            self.screenshot()
            action_click = self.get_random_win_action()
            if self.appear_then_click(self.I_WIN, action=action_click, interval=0.8):
                # 赢的那个鼓
                continue
            if self.appear(self.I_GREED_GHOST):
                # 贪吃鬼
                logger.info('贪食鬼出现，战斗胜利')
                self.wait_until_appear(self.I_REWARD, wait_time=1.5)
                self.screenshot()
                if not self.appear(self.I_GREED_GHOST):
                    logger.warning('贪食鬼消失，可能是虚假战斗')
                    continue
                while 1:
                    self.screenshot()
                    # 检查自选御魂弹窗
                    if self.current_count <= 1:
                        if self.appear_then_click(self.I_BACK_RED):
                            # 出现关闭御魂弹窗，说明没选择自选御魂，当前自选次数减一
                            self.current_count -= 1
                            continue
                    action_click = self.get_random_reward_action()
                    if not self.appear(self.I_GREED_GHOST):
                        break
                    if self.appear(self.I_SOUL_FULL_ENSURE):
                        self.appear_then_click(self.I_SOUL_FULL_ENSURE)
                        if self.soul_full_push:
                            self.push_notify("御魂溢出")
                            self.soul_full_push = False
                            self.set_next_run(task='SoulsTidy', target=datetime.now())
                        continue
                    if self.click(action_click, interval=1.5):
                        continue
                return True
            if self.appear(self.I_REWARD):
                # 魂
                logger.info('奖励出现，战斗胜利')
                appear_greed_ghost = self.appear(self.I_GREED_GHOST)
                while 1:
                    self.screenshot()
                    # 检查自选御魂弹窗
                    if self.current_count <= 1:
                        if self.appear_then_click(self.I_BACK_RED):
                            # 出现关闭御魂弹窗，说明没选择自选御魂，当前自选次数减一
                            self.current_count -= 1
                            continue
                    action_click = self.get_random_reward_action()
                    if self.appear_then_click(self.I_REWARD, action=action_click, interval=1.5):
                        continue
                    if not self.appear(self.I_REWARD):
                        break
                return True

            if self.appear(self.I_FALSE):
                logger.warning('战斗失败')
                self.ui_click_until_disappear(self.I_FALSE)
                return False

            # 如果开启战斗过程随机滑动
            if random_click_swipt_enable:
                self.random_click_swipt()


if __name__ == "__main__":
    from module.config.config import Config

    c = Config("切换账号")
    t = ScriptTask(c)
    t.run()
    # t.run_alone()
