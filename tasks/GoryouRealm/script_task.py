# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from datetime import datetime, timedelta
from module.exception import TaskEnd
from module.logger import logger
from random import randint
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.GameUi.page import page_goryou_realm
from tasks.GoryouRealm.assets import GoryouRealmAssets
from tasks.GoryouRealm.config import GoryouClass


class ScriptTask(GeneralBattle, SwitchSoul, GoryouRealmAssets):
    """ 御灵 """

    def run(self):
        con = self.config.goryou_realm
        limit_time = con.goryou_config.limit_time
        self.limit_count = con.goryou_config.limit_count
        self.limit_time: timedelta = timedelta(hours=limit_time.hour, minutes=limit_time.minute,
                                               seconds=limit_time.second)
        if con.switch_soul_config.enable:
            self.run_switch_soul(con.switch_soul_config.switch_group_team)
        if con.switch_soul_config.enable_switch_by_name:
            self.run_switch_soul_by_name(con.switch_soul_config.group_name, con.switch_soul_config.team_name)

        self.ui_goto_page(page_goryou_realm)

        match_click = {
            GoryouClass.Dark_Divine_Dragon: self.C_GR_C_1,
            GoryouClass.Dark_Hakuzousu: self.C_GR_C_2,
            GoryouClass.Dark_Black_Panther: self.C_GR_C_3,
            GoryouClass.Dark_Peacock: self.C_GR_C_4,
        }
        while 1:
            self.screenshot()
            if self.appear(self.I_COMMON_FIRE):
                logger.info('进入御灵')
                break
            if self.click(match_click[con.goryou_config.goryou_class], interval=1):
                continue
        self.check_lock(con.general_battle_config.lock_team_enable)

        # 开始循环
        while 1:
            self.screenshot()

            # 判断是否有更高优先级任务，去执行新任务
            self._check_first_priority_task()

            if self.current_count >= self.limit_count:
                logger.info('御灵次数已达上限')
                break
            if datetime.now() - self.start_time >= self.limit_time:
                logger.info('御灵时间已达上限')
                break

            # 点击挑战
            if self.appear(self.I_COMMON_FIRE):
                ticket = self.O_GR_TICKET.ocr(self.device.image)
                if ticket == 0:
                    break
                self.ui_click_until_disappear(self.I_COMMON_FIRE, interval=1)
                self.run_general_battle(config=con.general_battle_config)

        self.set_next_run(task='GoryouRealm', success=True, finish=True)
        # 是否开启绘卷捐赠任务
        if con.goryou_config.open_memory_scrolls:
            self.set_next_run(task='MemoryScrolls', target=datetime.now())
        raise TaskEnd


if __name__ == '__main__':
    from module.config.config import Config
    c = Config('百鬼-16480')
    t = ScriptTask(c)
    t.screenshot()

    t.run()
