# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from time import sleep

from datetime import time
from module.base.timer import Timer
from module.exception import TaskEnd
from module.logger import logger
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.GeneralInvite.general_invite import GeneralInvite
from tasks.Component.GeneralRoom.general_room import GeneralRoom
from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_team, page_main
from tasks.NianTrue.assets import NianTrueAssets
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from datetime import datetime, timedelta

""" 现世年兽 """


class ScriptTask(GeneralBattle, NianTrueAssets, GeneralRoom, GeneralInvite, SwitchSoul):
    battel_finsh = False

    def run(self):
        config = self.config.nian_true
        # 限制次数
        self.limit_count = config.nian_true_config.limit_count
        # 限制时间
        limit_time = config.nian_true_config.limit_time
        self.limit_time: timedelta = timedelta(hours=limit_time.hour, minutes=limit_time.minute,
                                               seconds=limit_time.second)

        # 切换御魂
        if config.switch_soul_config.enable:
            self.run_switch_soul(config.switch_soul_config.switch_group_team)
        if config.switch_soul_config.enable_switch_by_name:
            self.run_switch_soul_by_name(config.switch_soul_config.group_name, config.switch_soul_config.team_name)


        self.ui_goto_page(page_main)
        while 1:
            if datetime.now() - self.start_time > self.limit_time:
                self.push_notify(f"{self.limit_time} 时间限制已到，结束任务")
                break
            if self.current_count >= self.limit_count:
                self.push_notify(f"{self.limit_count} 次数限制已到，结束任务")
                break

            self.screenshot()
            if self.battel_finsh:
                logger.info('战斗结束, 没有获得奖励, 结束任务')
                break
            if self.appear(self.I_FIRE_BUTTON):
                self.wait_in_room(30)
            if self.appear(self.I_CREATE_TEAM, interval=1):
                self.ensure_public()
                self.ui_click_until_disappear(self.I_CREATE_TEAM)
                continue
            if self.appear_then_click(self.I_FIRE_TEAM, interval=2):
                continue
            if self.appear_then_click(self.I_IS_NIAN, interval=1):
                continue
            if self.appear_then_click(self.I_NIAN_SEARCH, interval=1):
                continue
            if self.appear_then_click(self.I_GOTO_NIAN, interval=1):
                continue
            if self.appear_then_click(self.I_REFRESH, interval=1):
                continue
        # 退出结束
        self.set_next_run(task='NianTrue', success=True, finish=True)
        raise TaskEnd('NianTrue')

    def run1(self) -> None:

        while 1:

            self.ui_goto_page(page_team)

            count = 0
            while 1:
                # 进入
                self.screenshot()
                if count >= 4:
                    self.next_nian_true()

                self.check_zones('现世年兽')
                if self.appear_then_click(self.I_N_HUABEI, interval=1):
                    break
                else:
                    count += 1

            cd_count = 0
            count = 0
            while 1:
                self.screenshot()
                sleep(1)
                if self.appear(self.I_N_WAITING):
                    break
                if cd_count >= 4:
                    # 4 x 1.5 = 6秒没有进入说明是在冷却中
                    self.next_nian_true()
                if count >= 10:
                    break
                if self.appear_then_click(self.I_GR_AUTO_MATCH, interval=1.5):
                    cd_count += 1
                    continue
                else:
                    count += 1

            # 匹配个8分钟，要是八分钟还没人拿没啥了
            logger.info('等待匹配')
            click_timer = Timer(240)
            check_timer = Timer(480)
            click_timer.start()
            check_timer.start()
            self.device.stuck_record_add('BATTLE_STATUS_S')
            while 1:
                self.screenshot()
                # 如果被秒开进入战斗, 被秒开不支持开启buff
                if self.check_take_over_battle(False, config=self.battle_config):
                    logger.info('真年兽接管战斗')
                    break
                # 如果进入房间
                elif self.is_in_room():
                    self.device.stuck_record_clear()
                    if self.wait_battle(wait_time=time(minute=1)):
                        self.run_general_battle(config=self.battle_config)
                        # 打完后返回庭院，记得关闭buff
                        break
                    else:
                        break
                # 如果时间到了
                if click_timer and click_timer.reached():
                    logger.warning('已等待240秒，但战斗未开始。')
                    logger.warning('将再等待240秒并重试。')
                    self.screenshot()
                    self.click(self.C_CLIC_SAFE)
                    click_timer = None
                    self.device.stuck_record_clear()
                    self.device.stuck_record_add('BATTLE_STATUS_S')
                    continue

                if check_timer.reached():
                    logger.warning('真年兽匹配超时')
                    while 1:
                        self.screenshot()
                        if not self.appear(self.I_N_WAITING):
                            break
                        if self.appear_then_click(self.I_UI_SURE, interval=1):
                            continue
                        if self.appear_then_click(self.I_UI_CONFIRM, interval=1):
                            continue
                        if self.appear_then_click(self.I_N_WAITING, interval=1):
                            continue
                    logger.info('真年兽匹配超时，退出')
                    break
                # 如果还在匹配中
                if self.appear(self.I_N_WAITING):
                    continue

    def wait_in_room(self, wait_time):
        # 进入到了房间里面
        wait_timer = Timer(wait_time)
        wait_timer.start()
        while 1:
            self.screenshot()

            if not self.is_in_room():
                continue
            if wait_timer.reached():
                # 超过时间依然挑战
                logger.warning(f'等待进入房间超过{wait_time}S, 开始单人挑战')
                self.click_fire()
                self.run_general_battle()
                break
            if not self.appear(self.I_ADD_5_1):
                # 有人进来了，可以进行挑战
                logger.info('有人进来了，开始组队挑战')
                self.click_fire()
                self.run_general_battle()
                break

    def battle_wait(self, random_click_swipt_enable: bool) -> bool:
        # 重写
        self.device.stuck_record_add('BATTLE_STATUS_S')
        self.device.click_record_clear()
        # 战斗过程 随机点击和滑动 防封
        is_first = True
        while 1:
            self.screenshot()
            if self.appear_then_click(self.I_WIN, interval=1) or self.appear_then_click(self.I_FALSE, interval=1):
                self.battel_finsh = True
            if self.appear(self.I_N_PAGE):
                logger.info('现世年兽来袭页面')
                return True
            if self.appear(self.I_BATTLE_OVER):
                if is_first:
                    logger.info('现世年兽战斗结束，通关奖励')
                    self.save_image()
                    is_first = False
                if self.click(self.C_CLIC_SAFE, interval=1):
                    continue
            if self.appear(self.I_UI_SURE):
                self.save_image()
                self.appear_then_click(self.I_UI_SURE)
                logger.info('现世年兽战斗结束，已拥有物品转为金币，点击确认')
                continue

    def next_nian_true(self):
        # 退出结束
        self.set_next_run(task='NianTrue', success=True, finish=True)
        raise TaskEnd('NianTrue')


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    c = Config('test')
    d = Device(c)
    t = ScriptTask(c, d)
    t.screenshot()

    t.run()
