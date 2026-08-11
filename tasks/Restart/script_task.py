# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

from datetime import datetime

from module.exception import TaskEnd
from module.logger import logger
from tasks.Restart.big_god.sign_in import BigGodSignIn
from tasks.Restart.back_up.back_up_log import BackUp
from tasks.Restart.login import LoginHandler


class ScriptTask(LoginHandler):

    def run(self) -> None:
        """
        主要就是登录的模块
        :return:
        """
        if self.delay_pending_tasks():
            return

        task_config = self.config.restart.task_config

        # 启动游戏
        self.app_restart()

        # 每日第一次启动游戏
        if task_config.task_date != str(datetime.now().date()):

            logger.set_file_logger(self.config.config_name)

            # 1. 日志备份
            BackUp().run()

            # 2 .首次重启是否调起 大神签到
            if task_config.enable_big_god_sign_in:
                try:
                    BigGodSignIn().start_sign_in(str(self.config.script.device.serial))
                except Exception as e:
                    logger.error(f"大神签到异常: {e}")
                    self.push_notify(content=f"大神签到异常: {e}")

            # 3. 首次重启是否调起 集体任务
            if task_config.enable_collective_missions:
                self.set_next_run(task='CollectiveMissions', target=datetime.now())

            # 最后. 保存重启时间日期
            self.config.restart.task_config.task_date = str(datetime.now().date())
        raise TaskEnd


    def app_restart(self):
        logger.hr('App restart')
        self.device.app_stop()
        self.device.app_start()
        self.app_handle_login()
        self.set_next_run(task='Restart', success=True, finish=True, server=True)

    def delay_pending_tasks(self) -> bool:
        """
        周三更新游戏的时候延迟
        @return:
        """
        datetime_now = datetime.now()
        if not (datetime_now.weekday() == 2 and 7 <= datetime_now.hour <= 8):
            return False
        logger.warning("周三游戏更新,7:00-8:59的任务延迟到9:00")
        # running 中的必然是 Restart
        for task in self.config.pending_task:
            print(task.command)
            self.set_next_run(task=task.command, target=datetime_now.replace(hour=9, minute=0, second=0, microsecond=0))
        return True


if __name__ == '__main__':
    from module.config.config import Config

    config = Config('wy')
    t = ScriptTask(config)
    t.run()
    # task.config.update_scheduler()
    # task.delay_pending_tasks()
    # task.app_restart()
    # task.screenshot()
    # print(task.appear_then_click(task.I_LOGIN_SCROOLL_CLOSE, threshold=0.9))
