# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

from module.base.timer import Timer
from module.exception import TaskEnd
from module.logger import logger
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.GeneralInvite.general_invite import GeneralInvite
from tasks.Component.GeneralRoom.general_room import GeneralRoom
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.GameUi.page import page_main, page_team
from tasks.GoldYoukai.assets import GoldYoukaiAssets
from tasks.Restart.assets import RestartAssets
from tasks.Component.GeneralBuff.config_buff import BuffClass


class ScriptTask(GeneralBattle, GeneralRoom, GeneralInvite, SwitchSoul, GoldYoukaiAssets):
    """ 金币妖怪 """

    def run(self):
        # 切换御魂
        if self.config.gold_youkai.switch_soul.enable:
            self.run_switch_soul(self.config.gold_youkai.switch_soul.switch_group_team)

        if self.config.gold_youkai.switch_soul.enable_switch_by_name:
            self.run_switch_soul_by_name(self.config.gold_youkai.switch_soul.group_name,
                                         self.config.gold_youkai.switch_soul.team_name)

        # 开启加成
        con = self.config.gold_youkai.gold_youkai
        if con.buff_gold_50_click or con.buff_gold_100_click:
            buff = []
            if con.buff_gold_50_click:
                buff.append(BuffClass.GOLD_50)
            if con.buff_gold_100_click:
                buff.append(BuffClass.GOLD_100)
            self.check_buff(buff)

        count = 0
        while count < con.battle_count:
            self.ui_goto_page(page_team)
            self.check_zones('金币妖怪')
            # 开始
            if not self.create_room():
                self.gold_exit(con)
            self.ensure_public()
            self.create_ensure()
            # 进入到了房间里面
            wait_timer = Timer(20)
            wait_timer.start()
            while 1:
                self.screenshot()

                if not self.is_in_room():
                    continue
                if wait_timer.reached():
                    # 超过时间依然挑战
                    logger.warning('等待太久并开始挑战')
                    self.click_fire()
                    count += 1
                    self.run_general_battle()
                    break
                if not self.appear(self.I_ADD_5_1):
                    # 有人进来了，可以进行挑战
                    logger.info('房间有人,开始挑战')
                    self.click_fire()
                    count += 1
                    self.run_general_battle()
                    break
        # 退出 (要么是在组队界面要么是在庭院)
        self.gold_exit(con)

    def battle_wait(self, random_click_swipt_enable: bool) -> bool:
        # 重写
        self.device.stuck_record_add('BATTLE_STATUS_S')
        self.device.click_record_clear()
        # 战斗过程 随机点击和滑动 防封
        while 1:
            self.screenshot()
            if self.appear(self.I_DE_WIN):
                logger.info('战斗胜利')
                while 1:
                    self.screenshot()

                    if self.appear_then_click(self.I_DE_WIN):
                        continue
                    if self.appear_then_click(RestartAssets.I_HARVEST_CHAT_CLOSE, interval=2):
                        continue
                    if self.appear(self.I_BUFF_1):
                        logger.info('因为出现buff所以中断')
                        break
                return True
            if self.appear(self.I_GOLD_WIN):
                logger.info('战斗胜利')
                self.ui_click_until_disappear(self.I_GOLD_WIN)
                return True

            if self.appear(self.I_FALSE):
                logger.warning('战斗失败')
                self.ui_click_until_disappear(self.I_FALSE)
                return False

    def gold_exit(self, con):
        self.ui_goto_page(page_main)
        if con.buff_gold_50_click or con.buff_gold_100_click:
            buff = [BuffClass.GOLD_50_CLOSE, BuffClass.GOLD_100_CLOSE]
            self.check_buff(buff)
        self.set_next_run(task='GoldYoukai', success=True, finish=False)
        raise TaskEnd('GoldYoukai')


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('4399')
    t = ScriptTask(c)
    t.screenshot()

    t.run()
