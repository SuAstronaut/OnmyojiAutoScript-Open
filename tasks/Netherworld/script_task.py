# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import random
from datetime import datetime, timedelta
from time import sleep

from module.base.timer import Timer
from module.exception import TaskEnd
from module.logger import logger
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.GeneralBuff.general_buff import GeneralBuff
from tasks.Component.GeneralInvite.general_invite import GeneralInvite
from tasks.Component.GeneralRoom.general_room import GeneralRoom
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.GameUi.page import page_town
from tasks.Netherworld.assets import NetherworldAssets
from tasks.Netherworld.config import UserStatus
from tasks.Restart.assets import RestartAssets

"""彼世逢魔"""


class ScriptTask(GeneralBattle, GeneralInvite, GeneralBuff, GeneralRoom, SwitchSoul, NetherworldAssets):
    soul_full_push = True
    con = None
    
    def run(self):
        self.con = self.config.netherworld

        # 根据选层切换御魂
        if self.con.switch_soul_config.enable:
            self.run_switch_soul(self.con.switch_soul_config.switch_group_team)
        # 御魂切换方式二
        if self.con.switch_soul_config.enable_switch_by_name:
            self.run_switch_soul_by_name(self.con.switch_soul_config.group_name, self.con.switch_soul_config.team_name)
            
        self.current_count = 0
        self.limit_count: int = self.con.netherworld_config.limit_count

        limit_time = self.con.netherworld_config.limit_time
        self.limit_time: timedelta = timedelta(hours=limit_time.hour, minutes=limit_time.minute, seconds=limit_time.second)

        match self.con.netherworld_config.user_status:
            case UserStatus.LEADER:
                self.run_leader()
                self.exit_room()
            case UserStatus.MEMBER:
                self.run_member()
            case UserStatus.ALONE:
                self.run_alone()
            case _:
                logger.error('未知的用户角色')

        self.set_next_run()
        raise TaskEnd

    def run_leader(self):
        logger.info('开始运行队长模式')
        self.ui_goto_page(page_town)
        self.ui_click([self.I_TOWN_GOTO_DEMON_ENCOUNTER, self.I_ENTER_NETHERWORLD], self.I_PAGE_NETHERWORLD, interval=1)
        self.check_lock(self.con.general_battle_config.lock_team_enable)
        # 创建队伍
        logger.info('创建队伍')
        while 1:
            self.screenshot()
            if self.appear(self.I_CHECK_TEAM):
                break
            if self.appear_then_click(NetherworldAssets.I_FORM_TEAM, interval=1):
                continue
        # 创建房间
        self.create_room()
        self.ensure_private()
        self.create_ensure()

        # 邀请队友
        is_first = True
        # 这个时候我已经进入房间了哦
        while 1:
            self.screenshot()
            # 无论胜利与否, 都会出现是否邀请一次队友
            # 区别在于，失败的话不会出现那个勾选默认邀请的框
            if self.check_and_invite(self.con.invite_config.default_invite):
                continue

            # 检查猫咪奖励
            if self.check_pet_reward():
                continue

            if self.current_count >= self.limit_count:
                if self.is_in_room():
                    logger.info('次数已达上限')
                    break

            if datetime.now() - self.start_time >= self.limit_time:
                if self.is_in_room():
                    logger.info('时间已达上限')
                    break

            # 如果没有进入房间那就不需要后面的邀请
            if not self.is_in_room(is_screenshot=False):
                if self.is_room_dead():
                    logger.warning('任务失败')
                    self.save_image(wait_time=0, push_flag=True, image_type=True, content='Orochi task failed')
                    break
                continue

            # 点击挑战
            if not is_first:
                if self.run_invite(config=self.con.invite_config):
                    self.run_general_battle(config=self.con.general_battle_config)
                else:
                    # 邀请失败，退出任务
                    logger.warning('邀请失败并退出本次任务')
                    break

            # 第一次会邀请队友
            if is_first:
                if not self.run_invite(config=self.con.invite_config, is_first=True):
                    logger.warning('邀请失败并退出本次任务')
                    break
                else:
                    is_first = False
                    self.run_general_battle(config=self.con.general_battle_config)

    def run_member(self):
        logger.info('开始队员运行')

        # 开始等待队长拉人
        wait_time = self.con.invite_config.wait_time
        wait_timer = Timer(wait_time.hour * 60 * 60 + wait_time.minute * 60 + wait_time.second)
        wait_timer.start()

        # 进入战斗流程
        self.device.stuck_record_add('BATTLE_STATUS_S')

        while 1:
            self.screenshot()

            # 等待超时
            if wait_timer.reached():
                self.push_notify(content=f"队员等待超时...")
                break

            if self.check_then_accept():
                continue

            if self.is_in_room():
                self.device.stuck_record_clear()
                if self.wait_battle(wait_time=self.con.invite_config.wait_time):
                    self.run_general_battle(config=self.con.general_battle_config)
                    wait_timer.reset()
                    logger.info("进入邀请等待")
                    self.device.stuck_record_add('BATTLE_STATUS_S')
                else:
                    break
            # 队长秒开的时候，检测是否进入到战斗中
            elif self.check_take_over_battle(False, config=self.con.general_battle_config):
                wait_timer.reset()
                logger.info("进入邀请等待")
                self.device.stuck_record_add('BATTLE_STATUS_S')
                continue

    def run_alone(self):
        logger.info('开始单人运行')
        self.ui_goto_page(page_town)
        self.ui_click([self.I_TOWN_GOTO_DEMON_ENCOUNTER, self.I_ENTER_NETHERWORLD], self.I_PAGE_NETHERWORLD, interval=1)
        self.check_lock(self.con.general_battle_config.lock_team_enable)

        while 1:
            self.screenshot()

            # 检查猫咪奖励
            if self.check_pet_reward():
                continue

            if self.current_count >= self.limit_count:
                logger.info('次数已达上限')
                break
            if datetime.now() - self.start_time >= self.limit_time:
                logger.info('时间已达上限')
                break
            # 点击挑战
            if self.appear(NetherworldAssets.I_FIRE):
                self.ui_click_until_disappear(NetherworldAssets.I_FIRE, interval=1)
                self.run_general_battle(config=self.con.general_battle_config)

    def is_room_dead(self) -> bool:
        # 如果在探索界面或者是出现在组队界面，那就是可能房间死了
        sleep(0.5)
        if self.appear(self.I_MATCHING) or self.appear(self.I_CHECK_EXPLORATION):
            sleep(0.5)
            if self.appear(self.I_MATCHING) or self.appear(self.I_CHECK_EXPLORATION):
                return True
        return False

    def battle_wait(self, random_click_swipt_enable: bool):
        self.device.stuck_record_add('BATTLE_STATUS_S')
        self.device.click_record_clear()
        click_list = [self.I_WIN, self.I_FALSE, self.I_UI_REWARD, self.I_REWARD, self.I_REWARD_GOLD, self.I_GREED_GHOST,
                      self.I_REWARD_STATISTICS, self.I_REWARD_PURPLE_SNAKE_SKIN,
                      self.I_SOUL_JADE]
        while 1:
            sleep(0.5)
            self.screenshot()

            if self.appear(self.I_GI_IN_ROOM) or self.appear(NetherworldAssets.I_FIRE):
                logger.info('战斗成功,退出')
                return True

            # 处理战斗类元素
            action_click = self.get_random_reward_action([self.C_REWARD_LEFT, self.C_REWARD_RIGHT])
            if any(self.appear_then_click(item, action=action_click, interval=1) for item in click_list):
                continue
            if self.appear_then_click(self.I_BACK_RED):
                continue
            # 误点聊天频道会自动关闭
            if self.appear_then_click(RestartAssets.I_HARVEST_CHAT_CLOSE):
                self.device.stuck_record_add('BATTLE_STATUS_S')
                continue
            if self.appear_then_click(self.I_SOUL_FULL_ENSURE):
                if not self.soul_full_push:
                    self.push_notify("御魂溢出")
                    self.soul_full_push = True
                    self.set_next_run(task='SoulsTidy', target=datetime.now())
                continue


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('du')
    t = ScriptTask(c)
    # t.battle_wait(False)
    t.run()
