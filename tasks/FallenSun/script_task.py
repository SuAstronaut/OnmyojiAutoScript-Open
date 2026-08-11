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
from tasks.FallenSun.assets import FallenSunAssets
from tasks.FallenSun.config import FallenSun, UserStatus
from tasks.GameUi.page import page_main, page_soul_zones


class ScriptTask(GeneralBattle, GeneralInvite, GeneralBuff, GeneralRoom, SwitchSoul, FallenSunAssets):
    """ 日陨 """

    def run(self) -> bool:
        # 御魂切换方式一
        if self.config.fallen_sun.switch_soul.enable:
            self.run_switch_soul(self.config.fallen_sun.switch_soul.switch_group_team)

        # 御魂切换方式二
        if self.config.fallen_sun.switch_soul.enable_switch_by_name:
            self.run_switch_soul_by_name(self.config.fallen_sun.switch_soul.group_name,
                                         self.config.fallen_sun.switch_soul.team_name)

        limit_count = self.config.fallen_sun.fallen_sun_config.limit_count
        limit_time = self.config.fallen_sun.fallen_sun_config.limit_time
        self.current_count = 0
        self.limit_count: int = limit_count
        self.limit_time: timedelta = timedelta(hours=limit_time.hour, minutes=limit_time.minute, seconds=limit_time.second)

        self.ui_goto_page(page_main)
        config: FallenSun = self.config.fallen_sun

        success = True
        match config.fallen_sun_config.user_status:
            case UserStatus.LEADER: success = self.run_leader()
            case UserStatus.MEMBER: success = self.run_member()
            case UserStatus.ALONE: self.run_alone()
            case UserStatus.WILD: self.run_wild()
            case _: logger.error('未知的用户状态')

        # 下一次运行时间
        if success:
            self.set_next_run('FallenSun', finish=True, success=True)
        else:
            self.set_next_run('FallenSun', finish=False, success=False)

        raise TaskEnd

    def fallen_sun_enter(self) -> bool:
        logger.info('进入日轮之城')
        while True:
            self.screenshot()
            if self.appear(self.I_FORM_TEAM):
                return True
            if self.appear_then_click(self.I_FALLEN_SUN, interval=1):
                continue

    def run_leader(self):
        logger.info('开始运行队长模式')
        self.ui_goto_page(page_soul_zones)
        self.fallen_sun_enter()
        layer = self.config.fallen_sun.fallen_sun_config.layer
        self.check_layer(self.L_LAYER_LIST, layer)
        self.check_lock(self.config.fallen_sun.general_battle_config.lock_team_enable)
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
            if self.check_and_invite(self.config.fallen_sun.invite_config.default_invite):
                continue

            # 检查猫咪奖励
            if self.check_pet_reward():
                continue

            if self.current_count >= self.limit_count:
                if self.is_in_room():
                    logger.info('日轮之城次数已达上限')
                    break

            if datetime.now() - self.start_time >= self.limit_time:
                if self.is_in_room():
                    logger.info('日轮之城时间已达上限')
                    break



            # 如果没有进入房间那就不需要后面的邀请
            if not self.is_in_room():
                # 如果在探索界面或者是出现在组队界面， 那就是可能房间死了
                # 要结束任务
                sleep(0.5)
                if self.appear(self.I_MATCHING) or self.appear(self.I_CHECK_EXPLORATION):
                    sleep(0.5)
                    if self.appear(self.I_MATCHING) or self.appear(self.I_CHECK_EXPLORATION):
                        logger.warning('日轮之城任务失败')
                        success = False
                        break
                continue

            # 点击挑战
            if not is_first:
                if self.run_invite(config=self.config.fallen_sun.invite_config):
                    self.run_general_battle(config=self.config.fallen_sun.general_battle_config)
                else:
                    # 邀请失败，退出日轮之城任务
                    logger.warning('邀请失败，退出日轮之城任务')
                    success = False
                    break

            # 第一次会邀请队友
            if is_first:
                if not self.run_invite(config=self.config.fallen_sun.invite_config, is_first=True):
                    logger.warning('邀请失败，退出本次日轮之城任务')
                    success = False
                    break
                else:
                    is_first = False
                    self.run_general_battle(config=self.config.fallen_sun.general_battle_config)

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
                logger.info('日轮之城次数已达上限')
                break
            if datetime.now() - self.start_time >= self.limit_time:
                logger.info('日轮之城时间已达上限')
                break

            if self.check_then_accept():
                continue

            if self.is_in_room():
                self.device.stuck_record_clear()
                if self.wait_battle(wait_time=self.config.fallen_sun.invite_config.wait_time):
                    self.run_general_battle(config=self.config.fallen_sun.general_battle_config)
                else:
                    break
            # 队长秒开的时候，检测是否进入到战斗中
            elif self.check_take_over_battle(False, config=self.config.fallen_sun.general_battle_config):
                continue
        return True

    def run_alone(self):
        logger.info('开始单人运行')
        self.ui_goto_page(page_soul_zones)
        self.fallen_sun_enter()
        layer = self.config.fallen_sun.fallen_sun_config.layer
        self.check_layer(self.L_LAYER_LIST, layer)
        self.check_lock(self.config.fallen_sun.general_battle_config.lock_team_enable)

        def is_in_fallen_sun(screenshot=False) -> bool:
            if screenshot:
                self.screenshot()
            return self.appear(self.I_FALLEN_SUN_FIRE)

        while 1:
            self.screenshot()

            # 检查猫咪奖励
            if self.check_pet_reward():
                continue

            if not is_in_fallen_sun():
                continue

            if self.current_count >= self.limit_count:
                logger.info('日轮之城次数已达上限')
                break
            if datetime.now() - self.start_time >= self.limit_time:
                logger.info('日轮之城时间已达上限')
                break

            # 点击挑战
            while 1:
                self.screenshot()
                if self.appear_then_click(self.I_FALLEN_SUN_FIRE, interval=1):
                    pass

                if not self.appear(self.I_FALLEN_SUN_FIRE):
                    self.run_general_battle(config=self.config.fallen_sun.general_battle_config)
                    break

        # 回去
        while 1:
            self.screenshot()
            if not self.appear(self.I_FORM_TEAM):
                break
            if self.appear_then_click(self.I_BACK_BLUE, interval=1):
                continue

        self.ui_current = page_soul_zones
        self.ui_goto_page(page_main)



    def run_wild(self):
        logger.error('野队模式未实现')
        pass






if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device
    from memory_profiler import profile
    c = Config('du')
    d = Device(c)
    t = ScriptTask(c, d)

    # t.run()

    # t.check_layer('悲')

    from module.base.timer import timer

    @timer
    @profile
    def test_memory():
        t.screenshot()
        print(t.ocr_appear(t.O_O_TEST_OCR))
        print(t.L_LAYER_LIST.image_appear(t.device.image, '叁'))
    for i in range(4):
        test_memory()
        print('=====================')







