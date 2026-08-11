# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import operator

from module.config.config_manual import ConfigManual
from module.logger import logger

from tasks.Script.config_optimization import ScheduleRule


class TaskScheduler:
    # ⚡ 预计算顺序映射，实现 O(1) 快速查找
    _order_map = {name: idx for idx, name in enumerate(ConfigManual.TASK_ORDER)}

    @staticmethod
    def schedule(rule: ScheduleRule, pending: list["Function"]) -> list["Function"]:
        """
        执行 任务的调度
        :param rule:
        :param pending:
        :return:
        """
        if rule != ScheduleRule.FILTER and rule != ScheduleRule.FIFO and rule != ScheduleRule.PRIORITY:
            logger.error(f"Invalid rule: {rule}")
            return pending
        if isinstance(pending, list) is False:
            logger.error(f"Invalid pending: {pending}")
            return pending

        # 第一种：基于预设顺序的过滤与排序
        if rule == ScheduleRule.FILTER:
            # ⚡ 使用字典映射进行高效排序
            return sorted(pending, key=lambda x: TaskScheduler._order_map.get(x.command, 999))

        # 第二种
        if rule == ScheduleRule.FIFO:
            pending_task = TaskScheduler.fifo(pending)
            return pending_task

        # 第三种
        if rule == ScheduleRule.PRIORITY:
            pending_task = TaskScheduler.priority(pending)
            return pending_task

    @staticmethod
    def fifo(pending: list["Function"]) -> list["Function"]:
        """
        先来后到，（按照任务的先后顺序进行调度）
        :param pending:
        :return:
        """
        tasks_pending = sorted(pending, key=operator.attrgetter("next_run"))
        for task in tasks_pending:
            # 永远保证 Restart 任务在第一个
            if task.command == 'Restart':
                tasks_pending.remove(task)
                tasks_pending.insert(0, task)
                break
        return tasks_pending

    @staticmethod
    def priority(pending: list["Function"]) -> list["Function"]:
        """
        最优排序：先按 priority 数值，再按预设顺序（组内排序）
        :param pending:
        :return:
        """
        return sorted(pending, key=lambda x: (x.priority, TaskScheduler._order_map.get(x.command, 999)))
    
    @staticmethod
    def priority_with_time(pending: list["Function"]) -> list["Function"]:
        """
        三级排序：先按时间，同时间按优先级，同优先级按预设顺序（用于waiting_task）
        :param pending:
        :return:
        """
        # ⚡ 单次排序：时间 -> 优先级数值 -> 预设顺序索引
        return sorted(pending, key=lambda x: (x.next_run, x.priority, TaskScheduler._order_map.get(x.command, 999)))


# 测试代码
if __name__ == '__main__':
    pass

