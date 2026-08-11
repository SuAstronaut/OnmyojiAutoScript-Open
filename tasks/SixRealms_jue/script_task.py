# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

from module.exception import TaskEnd
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_six_gates_jue
from tasks.SixRealms_jue.moon_sea.moon_sea import MoonSea


class ScriptTask(SwitchSoul, MoonSea, GameUi):
    """ 六道之门觉"""
    def run(self):
        if self.config.six_realms.switch_soul_config.enable:
            self.run_switch_soul(self.config.six_realms.switch_soul_config.one_switch)

        self.ui_goto_page(page_six_gates_jue)
        self._run_moon_sea()

        self.set_next_run('SixRealms', success=True, finish=False)
        raise TaskEnd


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('du')
    t = ScriptTask(c)
    # t.screenshot()

    t.run()
