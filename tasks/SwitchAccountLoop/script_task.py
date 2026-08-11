# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

import json
from datetime import datetime
from datetime import timedelta
from module.exception import SwitchAccountError
from module.exception import TaskEnd
from module.logger import logger
from tasks.Component.SwitchAccount.switch_account import SwitchAccount
from tasks.Component.SwitchAccount.switch_account_config import AccountInfo
from tasks.GameUi.game_ui import GameUi
from tasks.SwitchAccountOnce.base_channel_task import BaseChannelTask

""" 账号切换 """


class ScriptTask(GameUi):
    def __init__(self, config):
        super().__init__(config)
        self.BaseChannelTask = BaseChannelTask(self.config)

    account_info = ""
    task_finsh = False

    def run(self):
        con = self.config.switch_account_loop
        accounts_file = con.loop_config.accounts_file

        task_type = "loop_task_time"

        # 加载所有账号数据
        with open(f'config/SwitchAccount/{accounts_file}', 'r', encoding='utf-8') as file:
            all_accounts_data = json.load(file)

        for index, current_account_data in enumerate(all_accounts_data):
            # 初始化任务信息
            self.account_info = f"{current_account_data.get('svr')}-{current_account_data.get('character')}"
            # 开始账号切换 设置循环任务
            self.switch_account(con, current_account_data, index, task_type)

        # 所有角色任务均已完成
        self.BaseChannelTask.set_wait_task_time()
        self.set_next_run(task=self.config.task.command, target=self.get_next_execution_times())
        self.push_notify("✅ 本轮循环任务结束")
        self.BaseChannelTask.update_all_account_data(accounts_file, all_accounts_data,  task_type, "未执行")
        raise TaskEnd

    def switch_account(self, con, current_account_data, index, task_type):

        # 任务完成情况检查
        now = datetime.now()
        taskCompleteTime = current_account_data.get(f"{task_type}")
        if taskCompleteTime == str(now.date()):
            logger.info(f"[角色] {self.account_info}, 已完成[循环任务], 跳过")
            return

        # account_info = f"{current_account_data.get('svr')}-{current_account_data.get('character')}"
        account_info = current_account_data.get('character')

        toAccount = AccountInfo(
            account=current_account_data.get("account"),
            password=current_account_data.get("password", False),
            account_alias=current_account_data.get("accountAlias"),
            apple_or_android=current_account_data.get("appleOrAndroid", True),
            character=current_account_data.get("character"),
            svr=current_account_data.get("svr"),
        )

        sa = SwitchAccount(self.config, toAccount)
        login = sa.switchAccount()
        if login:
            def update_config():
                self.config.switch_account_config.config.account_name = account_info
            self.config.safe_save(update_config)

            logger.info(f"[角色] {account_info}, 切换完成")
            loop_tasks = current_account_data.get("loop_tasks").split(",")
            if loop_tasks != ['']:  # 只有非空任务才执行
                for loop_task in loop_tasks:
                    self.set_next_run(task=loop_task, target=datetime.now())
            # 本次任务设置下次运行时间
            task_loop_interval = con.loop_config.task_loop_interval
            self.set_next_run(target=self.datetime_add_timedelta(task_loop_interval))

            self.BaseChannelTask.update_account_data(con.loop_config.accounts_file, current_account_data, index, task_type, None)
            raise TaskEnd
        else:
            raise SwitchAccountError(f"[角色] {account_info}, 切换失败")

    def get_next_execution_times(self):
        """
        计算并返回下一个任务执行时间。

        该函数根据配置中的任务开始时间、结束时间和执行间隔，生成一系列可能的执行时间，
        并返回第一个大于当前时间的执行时间。如果所有生成的时间都小于等于当前时间，
        则返回第二天的开始时间。

        返回值:
            datetime: 下一个任务执行时间，若当天无符合条件的时间，则返回第二天的开始时间。
        """

        # 获取配置信息：任务开始时间、结束时间和执行间隔
        con = self.config.switch_account_loop.loop_config
        start_time = con.task_start_time
        end_time = con.task_end_time
        interval = con.task_interval

        # 获取当前时间，并构造今天的开始和结束时间
        now = datetime.now()
        start_datetime = now.replace(hour=start_time.hour, minute=start_time.minute, second=start_time.second, microsecond=0)
        end_datetime = now.replace(hour=end_time.hour, minute=end_time.minute, second=end_time.second, microsecond=0)

        # 将时间间隔转换为总秒数，用于后续计算
        interval_total_seconds = interval.hour * 3600 + interval.minute * 60 + interval.second

        # 根据间隔时间，生成从开始时间到结束时间范围内下一个可执行任务的时间点
        current_time = start_datetime
        while current_time <= end_datetime:
            logger.info(f"[任务] 可选执行时间: {current_time}")
            if current_time > now:
                logger.info(f"[任务] 当前时间: {now} → 下次执行时间: {current_time}")
                return current_time
            current_time += timedelta(seconds=interval_total_seconds)

        # 今日无合适时间，返回明日开始时间
        next_day_start = start_datetime + timedelta(days=1)
        logger.info(f"[任务] 今日无剩余执行时间，安排明日: {next_day_start}")
        return next_day_start


if __name__ == '__main__':
    from module.config.config import Config
    from tasks.Component.config_base import Time

    # 创建配置和设备实例
    config = Config('4399')

    # 创建任务实例
    task = ScriptTask(config)
    # task.run()

    # 设置测试时间参数
    # 注意：需要根据实际的Time类型设置
    task.config.switch_account_loop.loop_config.task_start_time = Time(7, 0, 0)
    task.config.switch_account_loop.loop_config.task_end_time = Time(23, 0, 0)
    task.config.switch_account_loop.loop_config.task_interval = Time(1, 30, 0)

    # 调用方法并打印结果
    next_time = task.get_next_execution_times()
    print(f"下次执行时间: {next_time}")
