# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

from tasks.ActivityCommon.challenge import Challenge


class ScriptTask(Challenge):
    """ 活动爬塔 """
    def run(self):
        config = self.config.activity_common
        self.run_config(config)


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('du')
    t = ScriptTask(c)

    t.run()
