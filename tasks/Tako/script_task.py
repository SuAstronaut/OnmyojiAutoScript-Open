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
from tasks.Component.GeneralBuff.config_buff import BuffClass

"""石距 喷怒的石距"""


class ScriptTask(GeneralBattle, GeneralRoom, GeneralInvite, SwitchSoul):

    def run(self):
        conf = self.config.tako
        if conf.switch_soul.enable:
            self.run_switch_soul(conf.switch_soul.switch_group_team)

        if conf.switch_soul.enable_switch_by_name:
            self.run_switch_soul_by_name(conf.switch_soul.group_name, conf.switch_soul.team_name)
        # 加成
        conf_buff = conf.tako_config
        if conf_buff.enable:
            buff = []
            if conf.buff_gold_50_click:
                buff.append(BuffClass.GOLD_50)
            if conf.buff_gold_100_click:
                buff.append(BuffClass.GOLD_100)
            if conf.buff_exp_50_click:
                buff.append(BuffClass.EXP_50)
            if conf.buff_exp_100_click:
                buff.append(BuffClass.EXP_100)
            self.check_buff(buff)

        # 进入
        self.ui_goto_page(page_team)
        if 5 <= self.start_time.weekday() <= 6:
            # 周末
            self.check_zones('喷怒的石距')
        else:
            self.check_zones('石距')
        if not self.create_room():
            self.exit_task()
        self.ensure_public()
        self.create_ensure()
        # 进入到了房间里面
        wait_timer = Timer(60)
        wait_timer.start()
        while 1:
            self.screenshot()

            if not self.is_in_room():
                continue
            if wait_timer.reached():
                logger.warning('等待时间过长，退出')
                self.exit_room()
                break
            if not self.appear(self.I_ADD_1):
                # 有人进来了，可以进行挑战
                logger.info('房间有人,开始挑战')
                self.click_fire()
                self.run_general_battle()
                break
        self.exit_task()

    def exit_task(self):
        """
        退出任务
        :return:
        """
        conf_buff = self.config.tako.tako_config
        self.ui_goto_page(page_main)
        if conf_buff.enable:
            buff = [BuffClass.GOLD_50_CLOSE, BuffClass.GOLD_100_CLOSE, BuffClass.EXP_50_CLOSE, BuffClass.EXP_100_CLOSE]
            self.check_buff(buff)

        self.set_next_run(task='Tako', success=True, finish=False)
        raise TaskEnd


if __name__ == '__main__':
    from module.config.config import Config
    c = Config('du')
    t = ScriptTask(c)
    t.screenshot()

    t.run()



