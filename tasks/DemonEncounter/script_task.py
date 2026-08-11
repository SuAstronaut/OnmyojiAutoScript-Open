# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time

import re
from cached_property import cached_property
from datetime import datetime, timedelta
from enum import Enum
from module.base.timer import Timer
from module.exception import TaskEnd
from module.logger import logger
from module.server.i18n import I18n
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.GeneralBuff.config_buff import BuffClass
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.DemonEncounter.assets import DemonEncounterAssets
from tasks.DemonEncounter.data.answer import Answer
from tasks.GameUi.page import page_demon_encounter, page_shikigami_records


def remove_symbols(text):
    return re.sub(r'[^\w\s]', '', text)


class LanternClass(Enum):
    BATTLE = 0  # 打怪  --> 无法判断因为怪的图片不一样，用排除法
    BOX = 1  # 开宝箱
    MAIL = 2  # 邮件答题
    REALM = 3  # 打结界
    EMPTY = 4  # 空
    MYSTERY = 5  # 神秘任务
    BOSS = 6  # 大鬼王


class ScriptTask(GeneralBattle, DemonEncounterAssets, SwitchSoul):
    boss_count = 1

    def run(self):
        if not self.check_time():
            logger.warning('时间不正确')
            self.set_next_run(task='DemonEncounter', success=True, finish=False)
            raise TaskEnd('DemonEncounter')

        # 切换通用御魂
        if self.config.demon_encounter.switch_soul.enable:
            self.run_switch_soul(self.config.demon_encounter.switch_soul.switch_group_team)

        # 根据周几切换指定御魂
        soul_config = self.config.demon_encounter.demon_soul_config
        best_soul_config = self.config.demon_encounter.best_demon_soul_config
        if soul_config.enable or best_soul_config.enable:
            self.ui_goto_page(page_shikigami_records)
            self.checkout_soul()

        self.ui_goto_page(page_demon_encounter)
        self.execute_lantern()

        if self.config.demon_encounter.switch_soul.enable_boss:
            self.execute_boss()

        self.set_next_run(task='DemonEncounter', success=True, finish=False)
        raise TaskEnd('DemonEncounter')

    def checkout_soul(self):
        """
        切换御魂
        """
        # 判断今天是周几
        today = datetime.now().weekday()

        # 普通逢魔御魂
        soul_config = self.config.demon_encounter.demon_soul_config
        # 极逢魔御魂
        best_soul_config = self.config.demon_encounter.best_demon_soul_config

        # 极逢魔选择
        best_demon_boss_config = self.config.demon_encounter.best_demon_boss_config

        group, team = None, None
        if today == 0:
            # 获取group,team
            if best_soul_config.enable and best_demon_boss_config.best_demon_kiryou_select:
                group, team = best_soul_config.best_demon_kiryou_utahime.split(",")
            else:
                group, team = soul_config.demon_kiryou_utahime.split(",")
        elif today == 1:
            if best_soul_config.enable and best_demon_boss_config.best_demon_shinkirou_select:
                group, team = best_soul_config.best_demon_shinkirou.split(",")
            else:
                group, team = soul_config.demon_shinkirou.split(",")
        elif today == 2:
            if best_soul_config.enable and best_demon_boss_config.best_demon_tsuchigumo_select:
                group, team = best_soul_config.best_demon_tsuchigumo.split(",")
            else:
                group, team = soul_config.demon_tsuchigumo.split(",")
        elif today == 3:
            if best_soul_config.enable and best_demon_boss_config.best_demon_gashadokuro_select:
                group, team = best_soul_config.best_demon_gashadokuro.split(",")
            else:
                group, team = soul_config.demon_gashadokuro.split(",")
        elif today == 4:
            if best_soul_config.enable and best_demon_boss_config.best_demon_namazu_select:
                group, team = best_soul_config.best_demon_namazu.split(",")
            else:
                group, team = soul_config.demon_namazu.split(",")
        elif today == 5:
            group, team = soul_config.demon_oboroguruma.split(",")
        elif today == 6:
            group, team = soul_config.demon_nightly_aramitama.split(",")
        if group and team:
            self.run_switch_soul_by_name(group, team)

    def execute_boss(self):
        """
        打boss
        :return:
        """
        logger.hr('开始Boss战斗', 1)
        # 判断今天是周几
        today = datetime.now().weekday()
        wait_timer = Timer(60)
        wait_timer.start()
        while 1:
            self.screenshot()

            # 等待超时
            if wait_timer.reached():
                # self.push_notify(content=f"逢魔Boss 搜寻超时...")
                wait_timer.reset()
                break

            if self.appear(self.I_BOSS_FIRE) or self.appear(self.I_BEST_BOSS_FIRE):
                current, remain, total = self.O_DE_BOSS_PEOPLE.ocr(self.device.image)
                if total == 300 and current >= 260:
                    logger.info('Boss战斗人数已满')
                    if not self.appear(self.I_BACK_RED):
                        logger.warning('Boss战斗人数已满但无红标')
                        continue
                    self.ui_click_until_disappear(self.I_BACK_RED)
                    # 退出重新选一个没满员的boss
                    logger.info('退出并重新选择')
                    continue
                else:
                    logger.info('Boss战斗人数未满')
                    break

            if self.config.demon_encounter.best_demon_boss_config.enable and today < 5:
                if self.appear_then_click(self.I_DE_BOSS_BEST, interval=4):
                    continue
            else:
                if self.appear_then_click(self.I_DE_BOSS, interval=4):
                    continue

            if self.appear_then_click(self.I_BOSS_NAMAZU, interval=1):
                continue
            if self.appear_then_click(self.I_BOSS_SHINKIRO, interval=1):
                continue
            if self.appear_then_click(self.I_BOSS_ODOKURO, interval=1):
                continue
            if self.appear_then_click(self.I_BOSS_OBOROGURUMA, interval=1):
                continue
            if self.appear_then_click(self.I_BOSS_TSUCHIGUMO, interval=1):
                continue
            if self.appear_then_click(self.I_BOSS_SONGSTRESS, interval=1):
                continue
            if self.ui_click_until_smt_disappear(self.I_DE_FIND, self.I_JADE_50):
                continue

            if self.click(self.C_DM_BOSS_CLICK, interval=1.7):
                continue

        logger.info('Boss战斗开始')
        # 点击集结挑战
        boss_fire_count = 0  # 3次没点到就意味着今天已经挑战过了
        while 1:
            self.screenshot()
            if self.appear(self.I_BOSS_CONFIRM):
                self.ui_click(self.I_BOSS_NO_SELECT, self.I_BOSS_SELECTED)
                self.ui_click(self.I_BOSS_CONFIRM, self.I_BOSS_GATHER)
                break
            if self.appear(self.I_BOSS_GATHER):
                break
            if boss_fire_count >= 3:
                logger.warning('Boss战斗已完成')
                # self.push_notify(content=f"封魔BOSS, 5次点击未进入...")
                self.ui_click_until_disappear(self.I_BACK_RED)
                logger.info('重新选择封魔BOSS')
                # self.push_notify(content=f"重新选择封魔BOSS...")
                if self.boss_count < 3:
                    self.boss_count += 1
                    self.execute_boss()
                return
            if self.appear_then_click(self.I_BOSS_FIRE, interval=3) or self.appear_then_click(self.I_BEST_BOSS_FIRE,
                                                                                              interval=3):
                boss_fire_count += 1
                continue
        logger.info('Boss战斗确认并进入')
        # 等待挑战, 5秒也是等
        time.sleep(5)
        self.device.stuck_record_add('BATTLE_STATUS_S')
        self.wait_until_disappear(self.I_BOSS_GATHER)
        self.device.stuck_record_clear()
        self.device.stuck_record_add('BATTLE_STATUS_S')
        # 延长时间并在战斗结束后改回来
        self.device.stuck_timer_long = Timer(480, count=480).start()
        self.run_general_battle(self.con)
        self.device.stuck_timer_long = Timer(300, count=300).start()

    def execute_lantern(self):
        """
        点灯笼 四次
        :return:
        """
        # 先点四次
        ocr_timer = Timer(0.8)
        ocr_timer.start()
        while 1:
            self.screenshot()
            if not ocr_timer.reached():
                continue
            else:
                ocr_timer.reset()
            cu, re, total = self.O_DE_COUNTER.ocr(self.device.image)
            if cu + re != total:
                logger.warning('灯笼数量错误')
                continue
            if cu == 0 and re == 4:
                break

            if self.appear_then_click(self.I_DE_FIND, interval=2.5):
                continue
        logger.info('灯笼数量正确')
        # 然后领取红色达摩
        self.screenshot()
        if not self.appear(self.I_DE_AWARD):
            self.ui_get_reward(self.I_DE_RED_DHARMA)
        self.wait_until_appear(self.I_DE_AWARD)
        # 然后到四个灯笼
        match_click = {
            1: self.C_DE_1,
            2: self.C_DE_2,
            3: self.C_DE_3,
            4: self.C_DE_4,
        }
        for i in range(1, 5):
            logger.hr(f'检查灯笼 {i}', 3)
            lantern_type = self.check_lantern(i)
            match lantern_type:
                case LanternClass.BOX:
                    self._box(match_click[i])
                case LanternClass.MAIL:
                    self._mail(match_click[i])
                case LanternClass.REALM:
                    self._realm(match_click[i])
                case LanternClass.EMPTY:
                    logger.warning(f'灯笼 {i} 为空')
                case LanternClass.BATTLE:
                    if not self.config.demon_encounter.switch_soul.enable_four:
                        continue
                    self._battle(match_click[i])
                case LanternClass.MYSTERY:
                    self._mystery(match_click[i])
                case LanternClass.BOSS:
                    self._boss(match_click[i])
            time.sleep(1)

    @cached_property
    def con(self) -> GeneralBattleConfig:
        return GeneralBattleConfig()

    def check_lantern(self, index: int = 1):
        """
        检查灯笼的类型
        :param index: 四个灯笼，从1开始
        :return:
        """
        match_roi = {
            1: self.C_DE_1.roi_front,
            2: self.C_DE_2.roi_front,
            3: self.C_DE_3.roi_front,
            4: self.C_DE_4.roi_front,
        }
        match_empty = {
            1: self.I_DE_DEFEAT_1,
            2: self.I_DE_DEFEAT_2,
            3: self.I_DE_DEFEAT_3,
            4: self.I_DE_DEFEAT_4,
        }
        self.I_DE_BOX.roi_back = match_roi[index]
        self.I_DE_LETTER.roi_back = match_roi[index]
        self.I_DE_MYSTERY.roi_back = match_roi[index]
        self.I_DE_REALM.roi_back = match_roi[index]
        self.I_DE_FIND_BOSS.roi_back = match_roi[index]
        target_box = self.I_DE_BOX
        target_letter = self.I_DE_LETTER
        target_mystery = self.I_DE_MYSTERY
        target_realm = self.I_DE_REALM
        target_find_boss = self.I_DE_FIND_BOSS
        target_empty = match_empty[index]

        # 开始判断
        self.screenshot()
        if self.appear(target_box):
            logger.info(f'灯笼 {index} 是宝箱')
            return LanternClass.BOX
        elif self.appear(target_letter):
            logger.info(f'灯笼 {index} 是邮件')
            return LanternClass.MAIL
        elif self.appear(target_mystery):
            logger.info(f'灯笼 {index} 是神秘任务')
            return LanternClass.MYSTERY
        elif self.appear(target_realm):
            logger.info(f'灯笼 {index} 是结界')
            return LanternClass.REALM
        elif self.appear(target_empty):
            logger.info(f'灯笼 {index} 为空')
            return LanternClass.EMPTY
        elif self.appear(target_find_boss):
            logger.info(f'灯笼 {index} 是大鬼王')
            return LanternClass.BOSS
        else:
            # 无法判断是否是战斗的还是结界的
            logger.info(f'灯笼 {index} 是战斗')
            return LanternClass.BATTLE

    def _box(self, target_click):
        while 1:
            self.screenshot()
            if self.appear(self.I_JADE_50):
                break
            if self.appear(self.I_BOSS_FIRE) or self.appear(self.I_BEST_BOSS_FIRE):
                self.appear_then_click(self.I_BACK_RED)
                continue
            if self.click(target_click, interval=1):
                continue
        while 1:
            self.screenshot()
            if self.appear(self.I_BLUE_PIAO):
                self.click(self.I_JADE_50)
                logger.info('50 勾玉购买蓝票')
                continue
            if self.config.demon_encounter.switch_soul.enable_100ap:
                if self.appear(self.I_SUSHI_100):
                    self.click(self.I_JADE_50)
                    logger.info('50 勾玉购买体力')
                    continue
            self.ui_click_until_smt_disappear(self.I_DE_FIND, self.I_JADE_50)
            break

    def _mail(self, target_click):
        # 答题
        def answer():
            click_match = {
                1: self.C_ANSWER_1,
                2: self.C_ANSWER_2,
                3: self.C_ANSWER_3,
            }
            index = None
            self.screenshot()
            question = self.O_LETTER_QUESTION.detect_text(self.device.image)
            if not question:
                logger.warning(f'题目为空: [{question}]')
                return None, None, None, None
            question = question.replace('「', '').replace('」', '').replace('?', '').replace('？', '').replace('，', '').replace(',', '')
            answer_1 = self.O_LETTER_ANSWER_1.detect_text(self.device.image)
            answer_2 = self.O_LETTER_ANSWER_2.detect_text(self.device.image)
            answer_3 = self.O_LETTER_ANSWER_3.detect_text(self.device.image)
            if answer_1 == '其余选项皆对' and '兵俑施放坚不可破的效果是' not in question:
                index = 1
            elif answer_2 == '其余选项皆对' and '兵俑施放坚不可破的效果是' not in question:
                index = 2
            elif answer_3 == '其余选项皆对' and '兵俑施放坚不可破的效果是' not in question:
                index = 3
            if not index:
                index = Answer().answer_one(question=question, options=[answer_1, answer_2, answer_3])
            if index is None:
                index = 1
            logger.info(f'题目: {question}')
            logger.info(f'答案: {index}')
            return click_match[index], index, question, [answer_1, answer_2, answer_3]

        while 1:
            self.screenshot()
            if self.appear(self.I_LETTER_CLOSE):
                break
            if self.appear(self.I_BOSS_FIRE) or self.appear(self.I_BEST_BOSS_FIRE):
                self.appear_then_click(self.I_BACK_RED)
                continue
            if self.click(target_click, interval=1):
                continue
        logger.info('答题开始')
        for i in range(1, 10):

            # 如果没有出现红色关闭按钮，说明答题结束
            if not (self.appear(self.I_LETTER_CLOSE) or self.appear(self.I_MALL)):
                if not self.appear_then_click(self.I_DE_LETTER):
                    logger.hr('答题结束', 3)
                    return

            logger.hr(f'第{i}题', 3)
            answer_click, index, question, options = answer()
            if not question:
                logger.warning('题目为空')
                continue
            question = remove_symbols(question)
            options = [remove_symbols(option) for option in options]

            self.screenshot()

            if self.click(answer_click, interval=1):
                str_result = self.wait_until_appear_answer_result(answer_error=self.I_MAIL_ANSWER_ERROR, answer_success=self.I_MAIL_ANSWER_SUCCESS, wait_time=3)
                if 'time_out' == str_result:
                    # self.save_image(task_name='答题超时', content=f"❌ 答题超时 {question} {options}", wait_time=0, image_type=True)
                    # Answer()._save_question(question=question, options=options, file_name='答题超时.csv')
                    self.appear_then_click(self.I_DE_FIND)
                    self.ui_click_until_smt_disappear(self.I_DE_FIND, self.I_UI_REWARD)
                elif 'answer_error' == str_result:
                    self.save_image(task_name='答题错误', content=f"❌ 答题错误 {question} {options}", wait_time=0.5, image_type=True)
                    Answer()._save_question(question=question, options=options, file_name='答题错误.csv')
                    time.sleep(2)
                elif 'answer_success' == str_result:
                    # self.save_image(task_name='答题成功', content=f"✅ 答题成功 {question} {options}", push_flag=False, wait_time=0, image_type=False)
                    # Answer()._save_question(question=question, options=[options[index-1]], file_name='答题成功.csv')
                    logger.info(f'✅ 答题成功 {question} {options}')
                    self.wait_until_appear(self.I_UI_REWARD, wait_time=3)
                    self.ui_click_until_smt_disappear(self.I_DE_FIND, self.I_UI_REWARD)
            time.sleep(0.5)

    def _battle(self, target_click):
        config = self.con
        while 1:
            self.screenshot()
            if self.appear(self.I_PREPARE_HIGHLIGHT):
                logger.info('战斗开始')
                break
            if self.appear(self.I_DE_SMALL_FIRE):
                # 小鬼王
                logger.info('小鬼王')
                while 1:
                    self.screenshot()
                    if not self.appear(self.I_DE_SMALL_FIRE):
                        break
                    if self.appear_then_click(self.I_DE_SMALL_FIRE, interval=1):
                        continue
                break

            if self.click(target_click, interval=1):
                continue
        if self.run_general_battle(config):
            logger.info('小鬼王战斗结束')

    def _realm(self, target_click):
        # 结界
        config = self.con
        while 1:
            self.screenshot()
            if self.appear(self.I_PREPARE_HIGHLIGHT):
                logger.info('地域鬼王战斗开始')
                break
            if self.appear(self.I_BOSS_FIRE) or self.appear(self.I_BEST_BOSS_FIRE):
                self.appear_then_click(self.I_BACK_RED)
                continue
            if self.appear_then_click(self.I_DE_REALM_FIRE, interval=0.7):
                continue

            if self.click(target_click, interval=1):
                continue
        if self.run_general_battle(config):
            logger.info('地域鬼王战斗结束')

    def _mystery(self, target_click):
        # 神秘任务， 不做
        pass

    def _boss(self, target_click):
        # 运气爆表，点灯笼出现大鬼王
        while 1:
            self.screenshot()
            if self.appear(self.I_BOSS_KILLED):
                # 这个大鬼王已经击败
                logger.warning('Boss已被击杀')
                self.ui_click_until_disappear(self.I_BACK_RED)
                break
            if self.appear(self.I_BOSS_FIRE):
                self.execute_boss()
                break
            if self.click(target_click, interval=2.3):
                continue

    def check_time(self):
        now = datetime.now()

        server_update = self.config.demon_encounter.scheduler.server_update
        target_time = datetime(now.year, now.month, now.day, server_update.hour, server_update.minute,
                               server_update.second)

        if now.hour < 17:
            logger.info(f'17点前, 等待至 {target_time.strftime("%Y-%m-%d %H:%M:%S")} (今天)')
            self.set_next_run(task='DemonEncounter', success=False, finish=False, target=target_time)
            return False
        elif now.hour >= 23:
            target_time += timedelta(days=1)  # Set to next day's 19:00
            logger.info(f'23点后, 等待至 {target_time.strftime("%Y-%m-%d %H:%M:%S")} (明天)')
            self.set_next_run(task='DemonEncounter', success=False, finish=False, target=target_time)
            return False
        else:
            return True

    def run_general_battle(self, config: GeneralBattleConfig = None, buff: BuffClass or list[BuffClass] = None) -> bool:
        """
        运行脚本
        :return:
        """
        # 本人选择的策略是只要进来了就算一次，不管是不是打完了
        logger.hr("通用战斗开始", 2)
        self.current_count += 1
        logger.info(f'当前任务: 逢魔之时')
        logger.info(f'当前次数: {self.current_count}')

        task_run_time = datetime.now() - self.start_time
        # 格式化时间，只保留整数部分的秒
        task_run_time_seconds = timedelta(seconds=int(task_run_time.total_seconds()))
        logger.info(f'当前时间: {task_run_time_seconds} / {self.limit_time}')

        if config is None:
            config = GeneralBattleConfig()

        return self.battle_wait(config.random_click_swipt_enable)

    def battle_wait(self, random_click_swipt_enable: bool) -> bool:
        # 重写
        self.device.stuck_record_add('BATTLE_STATUS_S')
        self.device.click_record_clear()
        # 战斗过程 随机点击和滑动 防封
        win = False
        while 1:
            self.screenshot()
            if self.appear(self.I_DE_FIND):
                logger.info('战斗结束')
                return True
            if self.appear(self.I_BATTLE_OVER):
                logger.info('战斗结束')
                return True
            if win and self.appear(self.I_BOSS_GATHER):
                logger.info('逢魔Boss战斗结束')
                return win
            if self.appear_then_click(self.I_PREPARE_HIGHLIGHT, interval=2):
                self.device.stuck_record_add('BATTLE_STATUS_S')
                continue
            if self.appear_then_click(self.I_DE_WIN, interval=1):
                logger.info('出现逢魔胜利按钮')
                win = True
                continue
            if self.appear_then_click(self.I_WIN, interval=1):
                logger.info('出现胜利按钮')
                win = True
                continue
            if self.appear_then_click(self.I_REWARD, interval=1):
                logger.info('战斗胜利')
                win = True
                continue
            # 失败的
            if self.appear_then_click(self.I_FALSE, interval=1):
                logger.warning('战斗失败')
                self.device.stuck_record_add('BATTLE_STATUS_S')
                win = False
                continue

    def wait_until_appear_answer_result(self,
                                        answer_error, answer_success,
                                        skip_first_screenshot=False,
                                        wait_time: int = None):
        """
        等待直到出现目标
        :param wait_time: 等待时间，单位秒
        :param answer_error:
        :param answer_success:
        :param skip_first_screenshot:
        :return:
        """
        wait_timer = None
        if wait_time:
            wait_timer = Timer(wait_time)
            wait_timer.start()
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.screenshot()
            if wait_timer and wait_timer.reached():
                logger.warning(f"等待答题结果超时")
                return 'time_out'
            if self.appear(answer_success) and not self.appear(answer_error):
                return 'answer_success'
            if self.appear(answer_error):
                return 'answer_error'

    def de_reward(self, action=None) -> bool:
        """
        如果出现 ‘获得奖励’ 就点击
        :return:
        """
        if not action:
            action = self.C_UI_REWARD
        if self.appear(self.I_UI_REWARD):
            self.save_image(image_type='png', wait_time=0)
            return self.appear_then_click(self.I_UI_REWARD, action=action, interval=0.4, threshold=0.6)
        return False


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('du')
    t = ScriptTask(c)

    t.run()
    # t.battle_wait(True)
