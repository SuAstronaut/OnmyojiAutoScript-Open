# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import random
from datetime import datetime
from module.exception import TaskEnd
from module.logger import logger
from tasks.GameUi.page import page_pet, page_soul_zones
from tasks.Orochi.config import Layer
from tasks.Orochi.script_task import ScriptTask as OrochiScriptTask
from tasks.Pets.assets import PetsAssets
from tasks.Pets.config import PetsConfig

"""喂宠物 猫咪"""


class ScriptTask(OrochiScriptTask, PetsAssets):

    def run(self):
        self.ui_goto_page(page_pet)
        con: PetsConfig = self.config.pets.pets_config
        logger.info('进入宠物界面')
        if con.pets_feast:
            self._feed()

        # 打一次魂十
        if con.orochi_enable:
            self.orochi_ten()

        # # 获取当前日期和时间
        # now = datetime.now()
        # # 判断当前时间是否大于12点
        # if now.time() > time(12, 00):
        #     # 如果当前时间大于12点，则将任务'Pets'的下一次运行时间设置为明天凌晨0点01分
        #     self.custom_next_run(task='Pets', custom_time=Time(hour=0, minute=1, second=0), time_delta=1)
        # elif now.time() <= time(12, 00):
        #     # 如果当前时间小于或等于12点，则将任务'Pets'的下一次运行时间设置为明天晚上23点30分
        #     self.custom_next_run(task='Pets', custom_time=Time(hour=23, minute=30, second=0), time_delta=1)

        self.set_next_run(task='Pets', success=True, finish=True)
        # 八岐大蛇
        self.set_next_run(task='Orochi', target=datetime.now())
        raise TaskEnd('Pets')

    def orochi_ten(self):
        # 御魂切换方式一
        if self.config.true_orochi.switch_soul.enable:
            # 换上真蛇御魂
            self.run_switch_soul(self.config.true_orochi.switch_soul.switch_group_team)

        self.ui_goto_page(page_soul_zones)
        self.orochi_enter()

        self.check_layer(self.L_LAYER_LIST, Layer.TEN)
        self.check_lock(True)
        count_orochi_ten = 0
        while 1:
            self.screenshot()
            # 检查猫咪奖励
            self.check_pet_reward()

            if count_orochi_ten >= 1:
                logger.warning('未找到真蛇')
                break
            # 否则点击挑战
            if self.appear(self.I_COMMON_FIRE):
                self.ui_click_until_disappear(self.I_COMMON_FIRE)
                self.config.orochi.general_battle_config.lock_team_enable = True
                self.run_general_battle(config=self.config.orochi.general_battle_config)
                count_orochi_ten += 1
                continue

    def _feed(self):
        """
        投喂
        :return:
        """
        logger.hr('投喂', 3)
        self.ui_click(self.I_PET_CLAW, self.I_PET_FEAST)
        self.ui_click(self.I_PET_FEAST, self.I_PET_FEED)
        number = self.O_PET_FEED_AP.ocr(self.device.image)
        logger.info(f'投喂 {number}')
        self.save_image()
        if number == 0:
            # 已经投喂过了
            logger.warning('已喂食')
            return
        self.ui_click(self.I_PET_FEED, self.I_PET_SKIP)
        self.ui_click_until_disappear(self.I_PET_SKIP)

    def _play(self):
        """
        玩耍
        :return:
        """
        logger.hr('Play', 3)
        self.ui_click(self.I_PET_HAPPY, self.I_PET_PLAY)
        number = self.O_PET_PLAY_GOLD.ocr(self.device.image)
        if number == 0:
            # 金币不足
            logger.warning('金币不足')
            return
        # 点击玩耍三次不出现就退出
        play_count = 0
        while 1:
            self.screenshot()
            if self.appear(self.I_PET_SKIP):
                break
            if play_count >= 3:
                logger.warning('玩耍次数 > 3')
                break
            if self.appear_then_click(self.I_PET_PLAY, interval=1):
                play_count += 1
                logger.info(f'玩耍 {play_count}')
                continue
        self.ui_click_until_disappear(self.I_PET_SKIP)

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
                self.wait_until_appear(self.I_REWARD, wait_time=2)
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



if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    c = Config('du')
    d = Device(c)
    t = ScriptTask(c, d)
    t.screenshot()

    t.run()
