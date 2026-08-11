# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time

import random
from datetime import datetime, timedelta
from module.base.timer import Timer
from module.logger import logger
from module.server.i18n import I18n
from tasks.Component.GeneralBattle.assets import GeneralBattleAssets
from tasks.Component.GeneralBattle.config_general_battle import GreenMarkType, GeneralBattleConfig
from tasks.Component.GeneralBuff.config_buff import BuffClass
from tasks.Component.GeneralBuff.general_buff import GeneralBuff
from tasks.Component.GeneralInvite.assets import GeneralInviteAssets
from tasks.Duel.assets import DuelAssets
from tasks.GameUi.page import exit_list, friends_list, win_list, false_list, prepare_highlight_list
from tasks.Orochi.assets import OrochiAssets
from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_main

class GeneralBattle(GeneralBuff, GeneralBattleAssets):
    """
    使用这个通用的战斗必须要求这个任务的config有config_general_battle
    """
    I_WIN = win_list
    I_FALSE = false_list
    I_PREPARE_HIGHLIGHT = prepare_highlight_list

    def run_general_battle(self, config: GeneralBattleConfig = None, buff: BuffClass or list[BuffClass] = None) -> bool:
        """
        运行脚本
        :return:
        """
        # 本人选择的策略是只要进来了就算一次，不管是不是打完了
        logger.hr("通用战斗开始", 2)
        self.current_count += 1
        if self.config.task:
            logger.info(f'当前任务: {I18n.trans_zh_cn(self.config.task.command)}')
        logger.info(f'当前次数: {self.current_count} / {self.limit_count}')

        task_run_time = datetime.now() - self.start_time
        # 格式化时间，只保留整数部分的秒
        task_run_time_seconds = timedelta(seconds=int(task_run_time.total_seconds()))
        logger.info(f'当前时间: {task_run_time_seconds} / {self.limit_time}')

        if config is None:
            config = GeneralBattleConfig()

        # 如果更换队伍
        if self.current_count == 1:
            self.switch_preset_team(config.preset_enable, config.preset_group, config.preset_team)

        # 打开buff
        self.check_buff(buff, False)

        if self.wait_until_appear_then_click(self.I_PREPARE_HIGHLIGHT, wait_time=5):
            self.ui_click_until_disappear(self.I_PREPARE_HIGHLIGHT, interval=1)

        # 绿标
        self.green_mark(config.green_enable, config.green_mark)

        win = self.battle_wait(config.random_click_swipt_enable)
        return win

    def check_take_over_battle(self, is_screenshot: bool, config: GeneralBattleConfig = None):
        """
        中途接入战斗，并且接管
        :return:  赢了返回True， 输了返回False, 不是在战斗中返回None
        """
        if is_screenshot:
            self.screenshot()
        if not self.is_in_battle():
            return None

        if config is None:
            config = GeneralBattleConfig()

        if self.is_in_prepare(False):
            while 1:
                self.screenshot()
                if self.appear_then_click(self.I_PREPARE_HIGHLIGHT, interval=1.5):
                    continue
                if not self.appear(self.I_BUFF):
                    break

            # 被接管的战斗，只有准备阶段才可以点绿标。
            # 因为如果是战斗中，无法保证点击的时候是否出现动画
            self.wait_until_disappear(self.I_BUFF)
            self.green_mark(config.green_enable, config.green_mark)

        # 本人选择的策略是只要进来了就算一次，不管是不是打完了
        logger.hr("中途接入战斗", 2)
        self.current_count += 1
        logger.info(f'当前任务: {I18n.trans_zh_cn(self.config.task.command)}')
        logger.info(f'当前次数: {self.current_count} / {self.limit_count}')

        task_run_time = datetime.now() - self.start_time
        # 格式化时间，只保留整数部分的秒
        task_run_time_seconds = timedelta(seconds=int(task_run_time.total_seconds()))
        logger.info(f'当前时间: {task_run_time_seconds} / {self.limit_time}')
        return self.battle_wait(config.random_click_swipt_enable)

    def battle_wait(self, random_click_swipt_enable: bool) -> bool:
        """
        等待战斗结束 ！！！
        很重要 这个函数是原先写的， 优化版本在tasks/Secret/script_task下。本着不改动原先的代码的原则，所以就不改了
        :param random_click_swipt_enable:
        :return:
        """
        # 有的时候是长战斗，需要在设置stuck检测为长战斗
        # 但是无需取消设置，因为如果有点击或者滑动的话 handle_control_check会自行取消掉
        self.device.stuck_record_add('BATTLE_STATUS_S')
        self.device.click_record_clear()
        # 战斗过程 随机点击和滑动 防封
        win: bool = False
        while 1:
            self.screenshot()
            # 如果出现赢 就点击, 第二个是针对封魔的图片
            if self.appear(self.I_WIN, threshold=0.8) or self.appear(self.I_DE_WIN):
                logger.info("战斗结果为胜利")
                if self.appear(self.I_DE_WIN):
                    self.ui_click_until_disappear(self.I_DE_WIN)
                win = True
                break

            # 如果出现失败 就点击，返回False
            if self.appear(self.I_FALSE, threshold=0.8):
                logger.info("战斗结果为失败")
                win = False
                break

            # 如果领奖励
            if self.appear(self.I_REWARD, threshold=0.6):
                win = True
                break

            # 如果领奖励出现金币
            if self.appear(self.I_REWARD_GOLD, threshold=0.8):
                win = True
                break
            # 如果开启战斗过程随机滑动
            if random_click_swipt_enable:
                self.random_click_swipt()

        # 再次确认战斗结果
        logger.info("再次确认战斗结果")
        while 1:
            self.screenshot()
            if win:
                # 点击赢了
                action_click = random.choice([self.C_WIN_1, self.C_WIN_2, self.C_WIN_3])
                if self.appear_then_click(self.I_WIN, action=action_click, interval=0.5):
                    continue
                if self.appear(self.I_REWARD) or self.appear(self.I_REWARD_GOLD) or self.appear(self.I_GREED_GHOST) or self.appear(self.I_REWARD_STATISTICS):
                    break
            else:
                # 如果失败且 点击失败后
                if self.appear_then_click(self.I_FALSE, threshold=0.6):
                    continue
                if not self.appear(self.I_FALSE, threshold=0.6):
                    return False

        logger.info("领取奖励")
        while 1:
            self.screenshot()
            # 如果出现领奖励
            action_click = self.get_random_reward_action()
            if self.appear_then_click(self.I_REWARD, action=action_click, interval=1):
                continue
            if self.appear_then_click(self.I_REWARD_GOLD, action=action_click, interval=1):
                continue
            if self.appear_then_click(self.I_REWARD_STATISTICS, action=action_click, interval=1):
                continue
            if self.appear_then_click(self.I_SOUL_FULL_ENSURE):
                self.push_notify("御魂溢出")
                self.set_next_run(task='SoulsTidy', target=datetime.now())
                continue
            if not (self.appear(self.I_REWARD) or self.appear(self.I_REWARD_GOLD) or self.appear(self.I_GREED_GHOST) or self.appear(self.I_REWARD_STATISTICS)):
                break

        return win

    def green_mark(self, enable: bool = False, mark_mode: GreenMarkType = GreenMarkType.GREEN_MAIN):
        """
        绿标， 如果不使能就直接返回
        :param enable:
        :param mark_mode:
        :return:
        """
        if enable:
            logger.info("绿标已启用")
            x, y = None, None
            match mark_mode:
                case GreenMarkType.GREEN_LEFT1:
                    x, y = self.C_GREEN_LEFT_1.coord()
                    logger.info("Green left 1")
                case GreenMarkType.GREEN_LEFT2:
                    x, y = self.C_GREEN_LEFT_2.coord()
                    logger.info("Green left 2")
                case GreenMarkType.GREEN_LEFT3:
                    x, y = self.C_GREEN_LEFT_3.coord()
                    logger.info("Green left 3")
                case GreenMarkType.GREEN_LEFT4:
                    x, y = self.C_GREEN_LEFT_4.coord()
                    logger.info("Green left 4")
                case GreenMarkType.GREEN_LEFT5:
                    x, y = self.C_GREEN_LEFT_5.coord()
                    logger.info("Green left 5")
                case GreenMarkType.GREEN_MAIN:
                    x, y = self.C_GREEN_MAIN.coord()
                    logger.info("绿标主界面")

            # 等待那个准备的消失
            while 1:
                self.screenshot()
                if not self.appear(self.I_PREPARE_HIGHLIGHT):
                    break

            time.sleep(0.3)
            # 点击绿标
            self.device.click(x, y)

    def switch_preset_team(self, enable: bool = False, preset_group: int = 1, preset_team: int = 1):
        """
        切换预设的队伍， 要求是在不锁定队伍时的情况下
        :param enable:
        :param preset_group:
        :param preset_team:
        :return:
        """
        if not enable:
            logger.info("预设未启用")
            return None

        logger.hr("切换预设队伍", 2)
        logger.info(f'Preset switch group {preset_group} team {preset_team}')
        # 点击预设按钮
        timer = Timer(3).start()
        while 1:
            self.screenshot()
            if timer.reached():
                logger.info("预设切换超时")
                return False

            if self.appear(self.I_PRESET_ENSURE):
                break
            # 首个队伍没有满足5个式神，未出现预设按钮的情况下跳出循环
            if self.appear(self.I_PRESENT_LESS_THAN_5):
                break
            if self.appear_then_click(self.I_PRESET, threshold=0.8, interval=1):
                timer.reset()
                continue
            if self.appear_then_click(self.I_PRESET_WIT_NUMBER, threshold=0.8, interval=1):
                timer.reset()
                continue
            if self.ocr_appear(self.O_PRESET, interval=1):
                self.click(self.O_PRESET, interval=1)
                timer.reset()
                continue
            if self.ocr_appear(self.O_PRESET_FULL, interval=1):
                self.click(self.O_PRESET_FULL, interval=1)
                timer.reset()
                continue
        logger.info("点击预设按钮")

        # 选择预设组
        x, y = None, None
        match preset_group:
            case 1:
                x, y = self.C_PRESET_GROUP_1.coord()
            case 2:
                x, y = self.C_PRESET_GROUP_2.coord()
            case 3:
                x, y = self.C_PRESET_GROUP_3.coord()
            case 4:
                x, y = self.C_PRESET_GROUP_4.coord()
            case 5:
                x, y = self.C_PRESET_GROUP_5.coord()
            case 6:
                x, y = self.C_PRESET_GROUP_6.coord()
            case 7:
                x, y = self.C_PRESET_GROUP_7.coord()
            case _:
                logger.info("预设组超出范围")
                return False
        self.device.click(x, y)
        logger.info(f"Select preset group {preset_group}")

        # 选择预设的队伍
        time.sleep(0.5)
        match preset_team:
            case 1:
                x, y = self.C_PRESET_TEAM_1.coord()
            case 2:
                x, y = self.C_PRESET_TEAM_2.coord()
            case 3:
                x, y = self.C_PRESET_TEAM_3.coord()
            case 4:
                x, y = self.C_PRESET_TEAM_4.coord()
            case _:
                logger.info("预设队超出范围")
                return False
        self.device.click(x, y)
        logger.info(f"Select preset team {preset_team}")

        # 点击预设确认
        self.wait_until_appear(self.I_PRESET_ENSURE, wait_time=1)
        timer.reset()
        while 1:
            self.screenshot()

            if timer.reached():
                logger.info("预设切换超时")
                return False

            if self.appear_then_click(self.I_PRESET_ENSURE, threshold=0.8):
                continue
            if not self.appear(self.I_PRESET_ENSURE):
                break
        logger.info(f'Preset done group {preset_group} team {preset_team}')
        return True

    def random_click_swipt(self):
        if 0 <= random.randint(0, 500) <= 3:  # 百分之4的概率
            rand_type = random.randint(0, 2)
            match rand_type:
                case 0:
                    self.click(self.C_RANDOM_CLICK, interval=20)
                case 1:
                    self.swipe(self.S_BATTLE_RANDOM_LEFT, interval=20)
                case 2:
                    self.swipe(self.S_BATTLE_RANDOM_RIGHT, interval=20)
            # 重新设置为长战斗
            self.device.stuck_record_add('BATTLE_STATUS_S')
        else:
            time.sleep(0.4)  # 这样的好像不对

    def get_random_win_action(self):
        """
        获取随机胜利点击动作
        :return: 随机的 C_WIN_1/C_WIN_2/C_WIN_3
        """
        return random.choice([self.C_WIN_1, self.C_WIN_2, self.C_WIN_3])

    def get_random_reward_action(self, actions=None):
        """
        获取随机奖励点击动作
        :param actions: 想要的动作，传 bottom/left/right 或组合，默认全部随机
        :return: 随机奖励动作
        """
        # 默认全部
        if actions is None:
            actions = [self.C_REWARD_BOTTOM, self.C_REWARD_LEFT, self.C_REWARD_RIGHT]

        # 支持传单个
        if not isinstance(actions, list):
            actions = [actions]

        return random.choice(actions)

    def exit_battle(self) -> bool:
        """
        在战斗的时候强制退出战斗
        :return:
        """
        self.ui_click(exit_list, self.I_UI_CONFIRM, interval=1)
        self.ui_click(self.I_UI_CONFIRM, [self.I_FALSE, self.I_WIN], interval=1)
        self.ui_click_until_disappear(self.I_FALSE, interval=1)
        self.ui_click_until_disappear(self.I_WIN, interval=1)
        return True

    # 判断是否在战斗中
    def is_in_battle(self, is_screenshot: bool = True) -> bool:
        """
        判断是否在战斗中
        :return:
        """
        if is_screenshot:
            self.screenshot()
        if self.appear(friends_list):
            return True
        if self.appear([self.I_IN_BATTLE_AUTO, self.I_IN_BATTLE_FIRE]):
            return True
        if self.appear(exit_list + [self.I_BATTLE_INFO, DuelAssets.I_D_VICTORY, DuelAssets.I_D_FAIL, self.I_WIN, self.I_FALSE]):
            return True
        else:
            return False

    def is_in_prepare(self, is_screenshot: bool = True) -> bool:
        """
        判断是否在准备中
        :return:
        """
        if is_screenshot:
            self.screenshot()
        if self.appear([self.I_BUFF, self.I_PREPARE_HIGHLIGHT, self.I_PREPARE_DARK, self.I_PRESET]):
            return True
        else:
            return False

    def check_lock(self, enable: bool, lock_image=None, unlock_image=None):
        """
        检测是否锁定队伍，
        :param enable:
        :param lock_image:
        :param unlock_image:
        :return:
        """
        if not lock_image:
            lock_image = GeneralInviteAssets.I_LOCK
        if not unlock_image:
            unlock_image = GeneralInviteAssets.I_UNLOCK

        if enable:
            logger.info("锁定阵容")
            self.ui_click(unlock_image, lock_image, interval=1)
        else:
            logger.info("解锁阵容")
            self.ui_click(lock_image, unlock_image, interval=1)

    def check_pet_reward(self) -> bool:
        """
        检查并领取猫咪奖励（首次战斗）
        :return: True 如果出现并点击了猫咪奖励, False 否则
        """
        if self.current_count > 1:
            return False

        if self.appear(OrochiAssets.I_PET_PRESENT, interval=1):
            self.save_image(task_name='Pets', wait_time=1)
            if self.appear_then_click(OrochiAssets.I_PET_PRESENT, action=self.C_WIN_3, interval=1):
                logger.info('领取猫咪奖励')
                return True
        return False

    def check_buff(self, buff=None, goto_main=True):
        """
        检测是否开启buff
        :param buff:
        :param goto_main:
        :return:
        """
        if not buff:
            return
        if goto_main:
            GameUi(self.config).ui_goto_page(page_main)
            self.open_buff()
        else:
            self.ui_click(self.I_BUFF, self.I_CLOUD, interval=2)

        if isinstance(buff, BuffClass):
            buff = [buff]
        match_method = {
            BuffClass.AWAKE: (self.awake, True),
            BuffClass.SOUL: (self.soul, True),
            BuffClass.GOLD_50: (self.gold_50, True),
            BuffClass.GOLD_100: (self.gold_100, True),
            BuffClass.EXP_50: (self.exp_50, True),
            BuffClass.EXP_100: (self.exp_100, True),
            BuffClass.AWAKE_CLOSE: (self.awake, False),
            BuffClass.SOUL_CLOSE: (self.soul, False),
            BuffClass.GOLD_50_CLOSE: (self.gold_50, False),
            BuffClass.GOLD_100_CLOSE: (self.gold_100, False),
            BuffClass.EXP_50_CLOSE: (self.exp_50, False),
            BuffClass.EXP_100_CLOSE: (self.exp_100, False),
        }
        for b in buff:
            func, is_open = match_method[b]
            func(is_open)
            time.sleep(0.1)

        if goto_main:
            self.close_buff()
        else:
            while 1:
                self.screenshot()
                if not self.appear(self.I_CLOUD):
                    break
                if self.appear_then_click(self.I_BUFF, interval=1):
                    continue


import cv2
from numpy import uint8, fromfile
from pathlib import Path

def load_image(file: str):
    file = Path(file)
    img = cv2.imdecode(fromfile(file, dtype=uint8), -1)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # height, width, channels = img.shape
    # if height != 720 or width != 1280:
    #     logger.error(f'Image size is {height}x{width}, not 720x1280')
    #     return None
    return img

if __name__ == '__main__':
    from module.config.config import Config

    c = Config('du')
    t = GeneralBattle(c)
    t.device.image = load_image("D:\共享文件夹\Screenshots\大号 7点34分18 2026-06-27.png")
    # t.check_buff([BuffClass.EXP_50, BuffClass.GOLD_50])
    # t.battle_wait(True)
    t.is_in_battle()