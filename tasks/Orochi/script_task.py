# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from time import sleep

import random
from datetime import datetime, timedelta
from module.base.timer import Timer
from module.config.utils import parse_tomorrow_server
from module.exception import TaskEnd
from module.logger import logger
from module.team_link import PairPhase, PairSyncRuntime
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.GeneralBuff.general_buff import GeneralBuff
from tasks.Component.GeneralInvite.general_invite import GeneralInvite
from tasks.Component.GeneralRoom.general_room import GeneralRoom
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.GameUi.page import page_main, page_soul_zones
from tasks.Orochi.assets import OrochiAssets
from tasks.Orochi.config import Orochi, UserStatus, Layer, Plan
from tasks.Component.GeneralBuff.config_buff import BuffClass

"""八岐大蛇"""


class ScriptTask(GeneralBattle, GeneralInvite, GeneralBuff, GeneralRoom, SwitchSoul, OrochiAssets):
    soul_full_push = True

    def run(self):
        # now = datetime.now()
        # # 今天晚上6点的时间
        # evening_6pm = now.replace(hour=18, minute=0, second=0, microsecond=0)
        # # 如果当前时间在晚上6点之后，直接结束任务
        # if now >= evening_6pm:
        #     self.config.orochi.next_day_orochi_config.plan = Plan.TEN30
        #     self.config.save()
        #     start_time = self.config.orochi.next_day_orochi_config.start_time
        #     next_run = parse_tomorrow_server(start_time)
        #     self.push_notify(content="当前时间已超过18点，结束任务")
        #     self.set_next_run('Orochi', target=next_run)
        #     raise TaskEnd

        limit_count = self.config.orochi.next_day_orochi_config.limit_count
        # 御魂层数
        layer = self.config.orochi.next_day_orochi_config.layer
        # 御魂任务选择
        plan = self.config.orochi.next_day_orochi_config.plan
        # 根据选层切换御魂
        orochi_switch_soul = self.config.orochi.switch_soul

        match plan:
            case Plan.TEN30:
                logger.info('御魂计划十层30次')
                limit_count = 30
                group_team = orochi_switch_soul.ten_switch
                layer = Layer.TEN
            case Plan.ELEVEN30:
                logger.info('御魂计划十一层30次')
                limit_count = 30
                group_team = orochi_switch_soul.eleven_switch
                layer = Layer.ELEVEN
            case Plan.TWELVE50:
                logger.info('御魂计划十二层50次')
                limit_count = 50
                group_team = orochi_switch_soul.twelve_switch
                layer = Layer.TWELVE
            case Plan.TWELVE120:
                logger.info('御魂计划十二层120次')
                limit_count = 120
                group_team = orochi_switch_soul.twelve_switch
                layer = Layer.TWELVE
            case Plan.default:
                logger.info('御魂计划默认')
            case Plan.ONE:
                logger.info('御魂计划：只执行一次下面设置的层数、次数和时间')
            case Plan.end:
                def update_config():
                    self.config.orochi.next_day_orochi_config.plan = Plan.TEN30
                self.config.safe_save(update_config)

                start_time = self.config.orochi.next_day_orochi_config.start_time
                next_run = parse_tomorrow_server(start_time)
                self.set_next_run('Orochi', target=next_run)
                logger.info('御魂计划结束')
                raise TaskEnd
            case _:
                logger.error('未知的用户计划')

        # Plan.end 会在上方直接结束，不应创建一个永远停留的联动等待状态。
        self._pair_sync_runtime = PairSyncRuntime(self.config)
        self._pair_sync_runtime.begin_campaign(starts_with_raid=False)
        self._pair_sync_runtime.set_phase(PairPhase.WAITING_OROCHI)

        if orochi_switch_soul.enable:
            # 如果是循环根据选层，换御魂
            if plan == Plan.default or plan == Plan.ONE:
                match layer:
                    case Layer.TEN:
                        group_team = orochi_switch_soul.ten_switch
                    case Layer.ELEVEN:
                        group_team = orochi_switch_soul.eleven_switch
                    case Layer.TWELVE:
                        group_team = orochi_switch_soul.twelve_switch
                    case Layer.THIRTEEN:
                        group_team = orochi_switch_soul.thirteen_switch
            self.run_switch_soul(group_team)

        limit_time = self.config.orochi.orochi_config.limit_time
        self.current_count = 0
        self.limit_count: int = limit_count
        self.limit_time: timedelta = timedelta(hours=limit_time.hour, minutes=limit_time.minute,
                                               seconds=limit_time.second)

        config: Orochi = self.config.orochi
        if not self.is_in_battle(True):
            if config.orochi_config.soul_buff_enable:
                self.check_buff(BuffClass.SOUL)

        success = True
        match config.orochi_config.user_status:
            case UserStatus.LEADER:
                success = self.run_leader(layer)
            case UserStatus.MEMBER:
                success = self.run_member()
            case UserStatus.ALONE:
                self.run_alone(layer)
            case _:
                logger.error('未知的用户状态')

        # 记得关掉
        if config.orochi_config.soul_buff_enable:
            self.check_buff(BuffClass.SOUL_CLOSE)

        if self._pair_sync_runtime.enabled:
            if success:
                self._pair_sync_runtime.set_phase(PairPhase.READY_FOR_RAID)
                self._pair_sync_runtime.ensure_realm_raid_enabled()
            else:
                self._pair_sync_runtime.mark_error('御魂任务未正常完成')

        # 下一次运行时间
        if success and plan != Plan.default:
            # 设置明天运行
            start_time = self.config.orochi.next_day_orochi_config.start_time
            next_run = parse_tomorrow_server(start_time)
            self.set_next_run('Orochi', target=next_run)
        else:
            self.set_next_run('Orochi', finish=success, success=success)

        datetime_now = datetime.now()
        # 个人突破。联动模式失败时保持停止，不能把异常轮次当作正常完成。
        if not self._pair_sync_runtime.enabled or success:
            self.set_next_run(task='RealmRaid', target=datetime_now)
        # 花合战
        # self.set_next_run(task='TalismanPass', target=datetime_now)
        # 集体任务
        # self.set_next_run(task='CollectiveMissions', target=datetime_now)
        # 御魂整理
        if self.config.orochi.next_day_orochi_config.soulstidy_enabled or self.limit_count >= 99:
            self.set_next_run(task='SoulsTidy', target=datetime_now)
        # 真八岐大蛇
        if self.config.true_orochi.true_orochi_config.current_success >= 1:
            self.set_next_run(task='TrueOrochi', target=datetime_now)

        raise TaskEnd

    def orochi_enter(self) -> bool:
        logger.info('进入御魂')
        while True:
            self.screenshot()
            if self.appear(self.I_FORM_TEAM):
                return True
            if self.appear_then_click(self.I_OROCHI, interval=1):
                continue


    def run_leader(self, layer):
        logger.info('开始运行队长模式')
        self.ui_goto_page(page_soul_zones)
        self.orochi_enter()
        self.check_layer(self.L_LAYER_LIST, layer)
        self.check_lock(self.config.orochi.general_battle_config.lock_team_enable)
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
            if self.check_and_invite(self.config.orochi.invite_config.default_invite):
                continue

            # 检查猫咪奖励
            if self.check_pet_reward():
                continue

            if self.current_count >= self.limit_count:
                if self.is_in_room():
                    logger.info('御魂次数已达上限')
                    break

            if datetime.now() - self.start_time >= self.limit_time:
                if self.is_in_room():
                    logger.info('御魂时间已达上限')
                    break

            # 如果没有进入房间那就不需要后面的邀请
            if not self.is_in_room(is_screenshot=False):
                if self.is_room_dead():
                    logger.warning('御魂任务失败')
                    self.save_image(wait_time=0, push_flag=True, image_type=True, content='Orochi task failed')
                    success = False
                    break
                continue

            # 点击挑战
            if not is_first:
                if self.run_invite(config=self.config.orochi.invite_config):
                    self.run_general_battle(config=self.config.orochi.general_battle_config)
                else:
                    # 邀请失败，退出任务
                    logger.warning('邀请失败并退出本次御魂任务')
                    success = False
                    break

            # 第一次会邀请队友
            if is_first:
                if not self.run_invite(config=self.config.orochi.invite_config, is_first=True):
                    logger.warning('邀请失败并退出本次御魂任务')
                    success = False
                    break
                else:
                    is_first = False
                    self.run_general_battle(config=self.config.orochi.general_battle_config)

        return success

    def run_member(self):
        logger.info('开始队员运行')

        # 开始等待队长拉人
        wait_time = self.config.orochi.invite_config.wait_time
        wait_timer = Timer(wait_time.hour * 60 * 60 + wait_time.minute * 60 + wait_time.second)
        wait_timer.start()

        success = True

        # 进入战斗流程
        self.device.stuck_record_add('BATTLE_STATUS_S')

        while 1:

            self.screenshot()

            # 等待超时
            if wait_timer.reached():
                self.push_notify(content=f"队员等待超时...")
                success = False
                return success

            if self.check_then_accept():
                break

        while 1:
            self.screenshot()

            # 检查猫咪奖励
            if self.check_pet_reward():
                continue

            if self.current_count >= self.limit_count:
                logger.info('御魂次数已达上限')
                break
            if datetime.now() - self.start_time >= self.limit_time:
                logger.info('御魂时间已达上限')
                break

            if self.check_then_accept():
                continue

            if self.is_in_room():
                self.device.stuck_record_clear()
                if self.wait_battle(wait_time=self.config.orochi.invite_config.wait_time):
                    self.run_general_battle(config=self.config.orochi.general_battle_config)
                else:
                    break
            # 队长秒开的时候，检测是否进入到战斗中
            elif self.check_take_over_battle(False, config=self.config.orochi.general_battle_config):
                continue

        return success

    def run_alone(self, layer):
        logger.info('开始单人运行')
        self.ui_goto_page(page_soul_zones)
        self.orochi_enter()
        self.check_layer(self.L_LAYER_LIST, layer)
        self.check_lock(self.config.orochi.general_battle_config.lock_team_enable)

        while 1:
            self.screenshot()

            # 检查猫咪奖励
            if self.check_pet_reward():
                continue

            if self.current_count >= self.limit_count:
                logger.info('御魂次数已达上限')
                break
            if datetime.now() - self.start_time >= self.limit_time:
                logger.info('御魂时间已达上限')
                break
            # 点击挑战
            if self.appear(self.I_COMMON_FIRE):
                self.ui_click_until_disappear(self.I_COMMON_FIRE, interval=1)
                self.run_general_battle(config=self.config.orochi.general_battle_config)

    def is_room_dead(self) -> bool:
        # 如果在探索界面或者是出现在组队界面，那就是可能房间死了
        sleep(0.5)
        if self.appear(self.I_MATCHING) or self.appear(self.I_CHECK_EXPLORATION):
            sleep(0.5)
            if self.appear(self.I_MATCHING) or self.appear(self.I_CHECK_EXPLORATION):
                return True
        return False

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
                logger.info('贪食鬼出现，御魂战斗胜利')
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
                logger.info('奖励出现，御魂战斗胜利')
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
                self.push_notify(content="战斗失败")
                self.ui_click_until_disappear(self.I_FALSE)
                return False

            # 如果开启战斗过程随机滑动
            if random_click_swipt_enable:
                self.random_click_swipt()


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('yys1')
    t = ScriptTask(c)
    # t.battle_wait(False)
    t.run()
