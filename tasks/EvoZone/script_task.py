# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from time import sleep

from datetime import datetime, timedelta
from module.exception import TaskEnd
from module.logger import logger
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.GeneralBuff.general_buff import GeneralBuff
from tasks.Component.GeneralInvite.general_invite import GeneralInvite
from tasks.Component.GeneralRoom.general_room import GeneralRoom
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.EvoZone.assets import EvoZoneAssets
from tasks.EvoZone.config import EvoZone, UserStatus, KirinType
from tasks.GameUi.page import page_awake_zones
from tasks.base_task_progress import with_progress_tracking
from tasks.Component.GeneralBuff.config_buff import BuffClass


class ScriptTask(GeneralBattle, GeneralInvite, GeneralBuff, GeneralRoom, EvoZoneAssets, SwitchSoul):
    """ 觉醒副本 """

    def run(self) -> bool:

        limit_count = self.config.evo_zone.evo_zone_config.limit_count
        limit_time = self.config.evo_zone.evo_zone_config.limit_time
        self.current_count = 0
        self.limit_count: int = limit_count
        self.limit_time: timedelta = timedelta(hours=limit_time.hour, minutes=limit_time.minute,
                                               seconds=limit_time.second)
        con = self.config.evo_zone
        if con.switch_soul_config.enable:
            self.run_switch_soul(con.switch_soul_config.switch_group_team)
        if con.switch_soul_config.enable_switch_by_name:
            self.run_switch_soul_by_name(con.switch_soul_config.group_name, con.switch_soul_config.team_name)

        config: EvoZone = self.config.evo_zone
        if config.evo_zone_config.soul_buff_enable:
            self.check_buff(BuffClass.AWAKE)

        success = True
        match config.evo_zone_config.user_status:
            case UserStatus.LEADER:
                success = self.run_leader()
            case UserStatus.MEMBER:
                success = self.run_member()
            case UserStatus.ALONE:
                self.run_alone(config)
            case _:
                logger.error('未知的用户状态')

        if config.evo_zone_config.soul_buff_enable:
            self.check_buff(BuffClass.AWAKE_CLOSE)

        # 下一次运行时间
        if success:
            self.set_next_run('EvoZone', finish=True, success=True)
        else:
            self.set_next_run('EvoZone', finish=False, success=False)

        raise TaskEnd

    def evozone_enter(self) -> bool:
        logger.info('进入觉醒副本')
        kirintype = self.I_LIGHTNING_KIRIN
        match self.config.evo_zone.evo_zone_config.kirin_type:
            case KirinType.FIREKIRIN:
                kirintype = self.I_FIRE_KIRIN
            case KirinType.WINDKIRIN:
                kirintype = self.I_WIND_KIRIN
            case KirinType.WATERKIRIN:
                kirintype = self.I_WATER_KIRIN
            case KirinType.LIGHTNINGKIRIN:
                kirintype = self.I_LIGHTNING_KIRIN
        self.ui_click(kirintype, self.I_FORM_TEAM, interval=1)

    def run_leader(self):
        logger.info('开始运行队长模式')
        self.ui_goto_page(page_awake_zones)
        self.evozone_enter()
        layer = self.config.evo_zone.evo_zone_config.layer
        logger.info("检查层数")
        self.check_layer(self.L_LAYER_LIST, layer)
        logger.info("检查锁定状态")
        self.check_lock(self.config.evo_zone.general_battle_config.lock_team_enable)
        logger.info("准备就绪")
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
            if self.check_and_invite(self.config.evo_zone.invite_config.default_invite):
                continue

            # 检查猫咪奖励
            if self.check_pet_reward():
                continue

            if self.current_count >= self.limit_count:
                if self.is_in_room():
                    logger.info('觉醒次数已达上限')
                    break

            if datetime.now() - self.start_time >= self.limit_time:
                if self.is_in_room():
                    logger.info('觉醒时间已达上限')
                    break

            # 如果没有进入房间那就不需要后面的邀请
            if not self.is_in_room():
                # 如果在探索界面或者是出现在组队界面， 那就是可能房间死了
                # 要结束任务
                sleep(0.5)
                if self.appear(self.I_MATCHING) or self.appear(self.I_CHECK_EXPLORATION):
                    sleep(0.5)
                    if self.appear(self.I_MATCHING) or self.appear(self.I_CHECK_EXPLORATION):
                        logger.warning('觉醒任务失败')
                        success = False
                        break
                continue

            # 点击挑战
            if not is_first:
                if self.run_invite(config=self.config.evo_zone.invite_config):
                    self.run_general_battle(config=self.config.evo_zone.general_battle_config)
                else:
                    # 邀请失败，退出任务
                    logger.warning('邀请失败并退出本次觉醒任务')
                    success = False
                    break

            # 第一次会邀请队友
            if is_first:
                if not self.run_invite(config=self.config.evo_zone.invite_config, is_first=True):
                    logger.warning('邀请失败并退出本次觉醒任务')
                    success = False
                    break
                else:
                    is_first = False
                    self.run_general_battle(config=self.config.evo_zone.general_battle_config)

        return success

    def run_member(self):
        logger.info('开始队员运行')

        # 进入战斗流程
        self.device.stuck_record_add('BATTLE_STATUS_S')
        while 1:
            self.screenshot()

            # 检查猫咪奖励
            if self.check_pet_reward():
                continue

            if self.current_count >= self.limit_count:
                logger.info('觉醒次数已达上限')
                break
            if datetime.now() - self.start_time >= self.limit_time:
                logger.info('觉醒时间已达上限')
                break

            if self.check_then_accept():
                continue

            if self.is_in_room():
                self.device.stuck_record_clear()
                if self.wait_battle(wait_time=self.config.evo_zone.invite_config.wait_time):
                    self.run_general_battle(config=self.config.evo_zone.general_battle_config)
                else:
                    break
            # 队长秒开的时候，检测是否进入到战斗中
            elif self.check_take_over_battle(False, config=self.config.evo_zone.general_battle_config):
                continue

        return True

    @with_progress_tracking('evo_zone.evo_zone_config.saved_count',
                           'evo_zone.evo_zone_config.limit_count')
    def run_alone(self, config):
        logger.info('开始单人运行')
        self.ui_goto_page(page_awake_zones)
        self.evozone_enter()
        layer = self.config.evo_zone.evo_zone_config.layer
        self.check_layer(self.L_LAYER_LIST, layer)
        self.check_lock(self.config.evo_zone.general_battle_config.lock_team_enable)

        while True:
            self.screenshot()

            # 检查猫咪奖励
            if self.check_pet_reward():
                continue

            # 检查是否达到限制次数
            if self.progress_mgr.check_limit():
                logger.info('觉醒次数已达上限')
                break

            # 检查时间是否用尽
            if datetime.now() - self.start_time >= self.limit_time:
                logger.info('觉醒时间已达上限')
                break

            # 点击挑战
            if self.appear(self.I_COMMON_FIRE):
                self.ui_click_until_disappear(self.I_COMMON_FIRE, interval=1)
                # 每次开始，增加计数并保存进度
                self.progress_mgr.increment_and_save('进入战斗')
                self.run_general_battle(config=self.config.evo_zone.general_battle_config)

        if config.evo_zone_config.soul_buff_enable:
            self.check_buff(BuffClass.AWAKE_CLOSE)

        self.set_next_run('EvoZone', finish=True, success=True)
        raise TaskEnd

if __name__ == '__main__':
    from module.config.config import Config

    c = Config('代挂0528')
    t = ScriptTask(c)

    t.run()

    # t.check_layer('悲')
