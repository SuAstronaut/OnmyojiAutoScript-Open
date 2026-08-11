# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import random  # type: ignore
import random  # type: ignore
import tasks.GameUi.page as pages
from datetime import datetime, timedelta, time
from module.exception import TaskEnd
from module.logger import logger
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.GeneralBuff.config_buff import BuffClass
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.HeroTest.assets import HeroTestAssets
from tasks.HeroTest.config import Layer, HeroTest, SkillMode
from typing import Callable


class ScriptTask(GeneralBattle, HeroTestAssets, SwitchSoul):

    conf: HeroTest
    page_hero_mode: pages.Page  # 当前英杰对应模式界面(经验or技能)
    success: bool = True

    def run(self) -> None:
        self.conf = self.config.hero_test
        self.limit_time: timedelta = self.conf.herotest.limit_time
        if isinstance(self.limit_time, time):
            self.limit_time = timedelta(
                hours=self.limit_time.hour,
                minutes=self.limit_time.minute,
                seconds=self.limit_time.second,
            )
        self.limit_count = self.conf.herotest.limit_count
        self.check_and_switch_soul()
        self.open_exp_buff()
        self.switch_hero(self.conf.herotest.layer)
        self.init_pages()
        self.ui_goto_page(self.page_hero_mode)
        self.check_and_lock_team()
        while True:
            if self.limit_time is not None and self.limit_time + self.start_time < datetime.now():
                logger.info("时间已到")
                break
            if self.current_count >= self.limit_count:
                logger.info("次数已到")
                break
            self.ui_goto_page(self.page_hero_mode)
            if not self.can_run(self.conf.herotest.layer):
                break
            entered = self.enter_battle()
            if not entered:
                break
            if self.run_general_battle(config=self.conf.general_battle):
                logger.info("通用战斗成功")

        self.close_exp_buff()
        self.set_next_run(task="HeroTest", success=self.success)
        self.push_notify("英杰试炼完成")
        raise TaskEnd

    def enter_battle(self) -> bool:
        """进入战斗
        :return: True:进入成功 False:进入失败
        """
        logger.info("点击战斗")
        click_cnt, max_click = 0, random.randint(3, 4)
        while True:
            self.screenshot()
            if self.is_in_battle(False):
                return True  # 成功进入战斗
            if click_cnt >= max_click:  # 异常情况,怎么都无法进入
                break
            if self.appear_then_click(self.I_START_CHALLENGE, interval=1):  # 兵藏秘境确认挑战
                continue
            if self.appear_then_click(self.I_BCMJ_RESET_CONFIRM, interval=1):  # 兵藏秘境确认重置
                continue
            if self.appear(self.I_REAL_MONEY, interval=1):  # 这里因为门票不够而不是其他异常所以success默认还是true
                logger.warning('券不足')
                return False
            if self.appear_then_click(self.I_HERO_FIRE, interval=2):  # 挑战按钮
                self.device.stuck_record_clear()
                click_cnt += 1
                continue
        logger.error('无法进入战斗，可能是识别失败')
        self.success = False  # 进入失败且不知道发生了什么情况
        return False

    def battle_wait(self, random_click_swipt_enable: bool) -> bool:
        self.device.stuck_record_add("BATTLE_STATUS_S")
        self.device.click_record_clear()
        win = None
        # 处理不同模式下的结算界面
        mode_wait_dict: dict[Layer, Callable] = {
            Layer.MIJING: self.hero1_skill_wait,
            Layer.MENGXU: self.hero2_skill_wait,
        }
        while True:
            self.screenshot()
            if self.appear(self.I_HERO_FIRE, interval=2.5):
                break
            if mode_wait_dict.get(self.conf.herotest.layer, None) is not None and \
                    mode_wait_dict[self.conf.herotest.layer]():
                win = True
                continue
            if self.appear([self.I_WIN, self.I_DE_WIN, self.I_REWARD],  interval=1.2):
                win = True
                action_click = self.get_random_reward_action([self.C_REWARD_LEFT, self.C_REWARD_RIGHT])
                self.click(action_click, interval=1)
                continue
            if self.appear(self.I_FALSE, interval=1.5):
                win = False
                action_click = self.get_random_reward_action([self.C_REWARD_LEFT, self.C_REWARD_RIGHT])
                self.click(action_click, interval=1)
                continue
            if win is None and random_click_swipt_enable:
                self.random_click_swipt()
        logger.info(f'战斗结果: {win}')
        return win

    def hero1_skill_wait(self):
        if not self.appear(self.I_BCMJ_SKILL_ADD_CONFIRM):
            return False
        hero1_skill_list = [
            self.I_AS_BCMJ_SKILL_ADD4,
            self.I_AS_BCMJ_SKILL_ADD3,
            self.I_BCMJ_SKILL_ADD1,
            self.I_BCMJ_SKILL_ADD2,
            self.I_BCMJ_BLESS,
            self.I_BCMJ_PROPERTY_ADD_CRITICAL,
            self.I_BCMJ__DEFALUT_ATTRIBUTE,
        ]
        while True:
            self.screenshot()
            if any(self.appear_then_click(ts, interval=1) for ts in hero1_skill_list):
                break
        self.ui_click_until_disappear(self.I_BCMJ_SKILL_ADD_CONFIRM, interval=1.5)
        return True

    def hero2_skill_wait(self):
        if not self.appear(self.I_BCMJ_SKILL_ADD_CONFIRM):
            return False
        # pve技能列表, 按优先级顺序
        pve_skill = [
            self.I_HERO2_SKILL1,  # 同调祝福
            self.I_HERO2_SKILL3,  # 弥天祝福
            self.I_HERO2_SKILL4,  # 叠辉祝福
            self.I_HERO2_SKILL5,  # 敛神祝福
            self.I_HERO2_SKILL6,  # 速度祝福
        ]
        pvp_skill = [
            self.I_HERO2_SKILL9,  # 泛音祝福
            self.I_HERO2_SKILL10,  # 凝啸祝福
            self.I_HERO2_SKILL2,  # 韵迟祝福
            self.I_HERO2_SKILL11,  # 逐空祝福
            self.I_HERO2_SKILL7,  # 遏云祝福
            self.I_HERO2_SKILL8,  # 音迹祝福
            self.I_HERO2_SKILL12,  # 伤害加成
        ]
        target_skill_dict: dict[SkillMode, list] = {
            SkillMode.PVE: pve_skill,
            SkillMode.PVP: pvp_skill,
        }
        target_skills = target_skill_dict[self.conf.herotest.skill_mode]
        while True:
            self.screenshot()
            if any(self.appear_then_click(ts, interval=1) for ts in target_skills):
                break
        self.ui_click_until_disappear(self.I_BCMJ_SKILL_ADD_CONFIRM, interval=1.5)
        return True

    def switch_hero(self, layer: Layer):
        """切换英杰"""
        self.ui_goto_page(pages.page_hero_test)
        switch_hero_dict: dict = {
            Layer.YANWU: (self.I_CHECK_HERO1, self.I_SWITCH_HERO1),  # 源赖光
            Layer.MIJING: (self.I_CHECK_HERO1, self.I_SWITCH_HERO1),  # 源赖光
            Layer.CHUANCHENG: (self.I_CHECK_HERO2, self.I_SWITCH_HERO2),  # 藤原道长
            Layer.MENGXU: (self.I_CHECK_HERO2, self.I_SWITCH_HERO2),  # 藤原道长
        }
        check_hero_img, switch_hero_img = switch_hero_dict[layer]
        while True:
            self.screenshot()
            if self.appear_then_click(switch_hero_img, interval=1):
                continue
            appeared = self.appear(check_hero_img, interval=1)
            if not appeared and self.appear(self.I_CHECK_HERO_TEST):
                self.click(self.C_SWITCH_HERO_BTN, interval=1.5)
                continue
            if appeared:
                break

    def can_run(self, layer: Layer) -> bool:
        """检查是否可以运行
        :return: True(default): can run, False: cannot run
        """
        check_func: dict[Layer, Callable] = {
            Layer.MIJING: self.check_art_war_card,
            Layer.CHUANCHENG: self.check_level_max,
            Layer.MENGXU: self.check_art_war_card,
        }
        if check_func.get(layer, None) is not None:
            return check_func[layer]()
        return True

    def check_art_war_card(self) -> bool:
        """兵藏秘境/梦虚秘境 看看门票是否足够"""
        self.screenshot()
        cu = self.O_ART_WAR_CARD.ocr(image=self.device.image)
        if cu[0] >= 1:
            logger.info("门票足够")
            return True
        cu = self.O_ART_WAR_CARD_PLUS.ocr(image=self.device.image)
        cu = 0 if cu == '' else int(cu)
        if cu >= 1:
            logger.info("门票不足，但加成卡足够")
            return True
        logger.warning("门票不足")
        return False

    def check_level_max(self):
        """检查御灵等级是否已经满级"""
        self.screenshot()
        if self.appear(self.I_HERO_EXP_MAX):
            logger.warning("御灵已经满级，退出战斗")
            return False
        return True

    def check_and_switch_soul(self):
        """检查并切换御魂"""
        if self.conf.switch_soul_config.enable:
            self.ui_goto_page(pages.page_shikigami_records)
            self.run_switch_soul(self.conf.switch_soul_config.switch_group_team)
        if self.conf.switch_soul_config.enable_switch_by_name:
            self.ui_goto_page(pages.page_shikigami_records)
            self.run_switch_soul_by_name(self.conf.switch_soul_config.group_name, self.conf.switch_soul_config.team_name)

    def open_exp_buff(self):
        """启用经验加成"""
        exp_50_buff_enable = self.conf.herotest.exp_50_buff_enable_help
        exp_100_buff_enable = self.conf.herotest.exp_100_buff_enable_help
        if exp_50_buff_enable or exp_100_buff_enable:
            buff = []
            if exp_50_buff_enable:
                buff.append(BuffClass.EXP_50)
            if exp_100_buff_enable:
                buff.append(BuffClass.EXP_100)
            self.check_buff(buff)

    def close_exp_buff(self):
        """关闭经验加成"""
        exp_50_buff_enable = self.conf.herotest.exp_50_buff_enable_help
        exp_100_buff_enable = self.conf.herotest.exp_100_buff_enable_help
        if exp_50_buff_enable or exp_100_buff_enable:
            self.ui_goto_page(pages.page_main)
            buff = [BuffClass.EXP_50_CLOSE, BuffClass.EXP_100_CLOSE]
            self.check_buff(buff)

    def check_and_lock_team(self):
        """检查并锁定阵容"""
        lock_img = self.I_LOCK
        unlock_img = self.I_UNLOCK
        match self.conf.herotest.layer:
            case Layer.YANWU | Layer.CHUANCHENG:
                pass
            case Layer.MIJING | Layer.MENGXU:
                lock_img = self.I_BCMJ_LOCK
                unlock_img = self.I_BCMJ_UNLOCK
            case _:
                raise ValueError(f'Unknown layer on lock: {self.conf.herotest.layer}')
        if self.conf.general_battle.lock_team_enable:
            logger.info("锁定阵容")
            self.ui_click(unlock_img, lock_img, interval=0.8)
        else:
            logger.info("解锁阵容")
            self.ui_click(lock_img, unlock_img, interval=0.8)

    def init_pages(self):
        """初始化页面"""
        match self.conf.herotest.layer:
            case Layer.YANWU:
                self.page_hero_mode = pages.Page(self.I_CHECK_HERO1_EXP)
                pages.page_hero_test.link(button=self.I_GBB, destination=self.page_hero_mode)
            case Layer.MIJING:
                self.page_hero_mode = pages.Page(self.I_CHECK_HERO1_SKILL)
                pages.page_hero_test.link(button=self.I_BCMJ, destination=self.page_hero_mode)
            case Layer.CHUANCHENG:
                self.page_hero_mode = pages.Page(self.I_CHECK_HERO2_EXP)
                pages.page_hero_test.link(button=self.I_ENTER_CCSL, destination=self.page_hero_mode)
            case Layer.MENGXU:
                self.page_hero_mode = pages.Page(self.I_CHECK_HERO2_SKILL)
                pages.page_hero_test.link(button=self.I_ENTER_MXMJ, destination=self.page_hero_mode)
            case _:
                raise ValueError(f'Unknown Layer {Layer}')
        self.page_hero_mode.link(button=self.I_BACK_YELLOW, destination=pages.page_hero_test)


if __name__ == "__main__":
    from module.config.config import Config

    c = Config("99-wy")
    t = ScriptTask(c)
    t.run()

    t.check_and_lock_team()
