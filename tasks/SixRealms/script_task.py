# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

from datetime import datetime, timedelta

from module.exception import TaskEnd
from module.logger import logger
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.GameUi.page import page_six_gates, page_six_gates_jue
from tasks.SixRealms.config import SixRealmsType
from tasks.SixRealms.moon_sea.moon_sea import MoonSea
from tasks.SixRealms_jue.moon_sea.moon_sea import MoonSea as MoonSea_jue
from tasks.base_task_progress import with_progress_tracking


class ScriptTask(SwitchSoul):
    """ 六道之门 """
    def __init__(self, config):
        super().__init__(config)
        self._conf = self.config.six_realms.six_realms_gate  # 在初始化中赋值

        six_realms_type = self._conf.six_realms_type
        if SixRealmsType.JIAOTU == six_realms_type:
            self.moon_sea_page = page_six_gates
            self._moon_sea = MoonSea(self.config)
        elif SixRealmsType.JUE == six_realms_type:
            self.moon_sea_page = page_six_gates_jue
            self._moon_sea = MoonSea_jue(self.config)
        else:
            raise ValueError('Invalid six_realms_type')

    @with_progress_tracking('six_realms.six_realms_gate.saved_count',
                           'six_realms.six_realms_gate.limit_count')
    def run(self):
        limit_time = self._conf.limit_time
        max_time: timedelta = timedelta(
            hours=limit_time.hour,
            minutes=limit_time.minute,
            seconds=limit_time.second
        )

        if self.config.six_realms.switch_soul_config.enable:
            self.run_switch_soul(self.config.six_realms.switch_soul_config.one_switch)

        self.ui_goto_page(self.moon_sea_page)

        # 重置启动的时间
        self.start_time = datetime.now()

        # 在六道界面
        content = ''
        while True:
            # 检查是否有更高优先级任务
            try:
                self._check_first_priority_task()
            except TaskEnd:
                # 切换到高优先级任务前保存进度并抛出中断异常
                self.progress_mgr.save_before_priority_switch()
            
            # 检查是否达到限制次数
            if self.progress_mgr.check_limit():
                logger.info('次数用尽，退出')
                break
            
            # 检查时间是否用尽
            if datetime.now() - self.start_time >= max_time:
                logger.info('时间用尽，退出')
                break
            
            if self._moon_sea.one():
                self.current_count += 1
                # 成功完成一次,增加计数并保存进度
                self.progress_mgr.increment_and_save(reason="成功完成一次")

                total_time = timedelta(seconds=int((datetime.now() - self.start_time).total_seconds()))
                avg_time = timedelta(seconds=int((total_time / self.current_count).total_seconds()))
                content = f'次数: {self.current_count}, 平均用时: {avg_time}, 总用时: {total_time}'
                logger.info(content)
            else:
                break

        self.push_notify(content=content)

        # 设置下一次运行时间是周一
        self.next_run_week(1)
        # self.set_next_run('SixRealms', success=True, finish=False)
        raise TaskEnd




if __name__ == '__main__':
    from module.config.config import Config

    c = Config('百鬼-16512')
    t = ScriptTask(c)
    # t.screenshot()

    t.run()
