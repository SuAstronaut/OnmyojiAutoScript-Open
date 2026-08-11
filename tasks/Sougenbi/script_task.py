# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from time import sleep

from datetime import datetime, timedelta
from module.exception import TaskEnd
from module.logger import logger
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.GameUi.page import page_main, page_soul_zones
from tasks.Sougenbi.assets import SougenbiAssets
from tasks.Sougenbi.config import SougenbiConfig, SougenbiClass
from tasks.Component.GeneralBuff.config_buff import BuffClass

""" 业原火 """


class ScriptTask(GeneralBattle, SwitchSoul, SougenbiAssets):

    def run(self):
        con = self.config.sougenbi
        s_con: SougenbiConfig = con.sougenbi_config
        limit_time = con.sougenbi_config.limit_time
        self.limit_count = con.sougenbi_config.limit_count
        self.limit_time: timedelta = timedelta(hours=limit_time.hour, minutes=limit_time.minute,
                                               seconds=limit_time.second)

        if con.switch_soul_config.enable:
            self.run_switch_soul(con.switch_soul_config.switch_group_team)
        if con.switch_soul_config.enable_switch_by_name:
            self.run_switch_soul_by_name(con.switch_soul_config.group_name, con.switch_soul_config.team_name)

        if s_con.buff_enable:
            buff = []
            if s_con.buff_gold_50_click:
                buff.append(BuffClass.GOLD_50)
            if s_con.buff_gold_100_click:
                buff.append(BuffClass.GOLD_100)
            if s_con.buff_exp_50_click:
                buff.append(BuffClass.EXP_50)
            if s_con.buff_exp_100_click:
                buff.append(BuffClass.EXP_100)
            self.check_buff(buff)

        self.ui_goto_page(page_soul_zones)
        self.ui_click(self.I_S_SOUGENBI, self.I_COMMON_FIRE, interval=1)
        logger.info('进入业原火')
        sleep(0.5)

        self.check_layer(self.L_LAYER_LIST, con.sougenbi_config.sougenbi_class)

        number_target = None
        match con.sougenbi_config.sougenbi_class:
            case SougenbiClass.GREED:
                number_target = self.O_S_GREED
            case SougenbiClass.Anger:
                number_target = self.O_S_ANGER
            case SougenbiClass.Foolery:
                number_target = self.O_S_FOOLERY
            case _:
                raise ValueError('Sougenbi class error')

        self.check_lock(con.general_battle_config.lock_team_enable)

        # 开始循环
        while 1:
            self.screenshot()

            # 判断是否有更高优先级任务，去执行新任务
            self._check_first_priority_task()

            if self.current_count >= self.limit_count:
                logger.info('业原火次数已达上限')
                break
            if datetime.now() - self.start_time >= self.limit_time:
                logger.info('业原火时间已达上限')
                break

            # 点击挑战
            if self.appear(self.I_COMMON_FIRE):
                ticket = number_target.ocr(self.device.image)
                if ticket == 0:
                    logger.warning(f'{con.sougenbi_config.sougenbi_class}挑战券不足')
                    break
                self.ui_click_until_disappear(self.I_COMMON_FIRE, interval=1)
                self.run_general_battle(config=con.general_battle_config)

        if s_con.buff_enable:
            buff = [BuffClass.GOLD_50_CLOSE, BuffClass.GOLD_100_CLOSE, BuffClass.EXP_50_CLOSE, BuffClass.EXP_100_CLOSE]
            self.check_buff(buff)

        self.set_next_run("Sougenbi", success=True, finish=True)
        # 个人突破
        self.set_next_run(task='RealmRaid', target=datetime.now())

        raise TaskEnd


if __name__ == '__main__':
    from module.config.config import Config
    c = Config('du')
    t = ScriptTask(c)
    # t.screenshot()

    t.run()
    # print(t.appear(t.I_S_FOOLERY, threshold=0.97))

