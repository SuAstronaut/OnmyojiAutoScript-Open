# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
from tasks.Component.config_base import ConfigBase, Time, TimeDelta
from tasks.Component.config_scheduler import Scheduler
from tasks.Utils.config_enum import ShikigamiClass


class SelectFriendList(str, Enum):
    SAME_SERVER = 'same_server'
    DIFFERENT_SERVER = 'different_server'


class UtilizeRule(str, Enum):
    DEFAULT = 'default'  # 默认就好
    TAIKO = 'kaiko'  # 太鼓优先
    FISH = 'fish'  # 斗鱼优先


class UtilizeScheduler(Scheduler):
    priority: int = Field(default=2, description='priority_help')
    success_interval: TimeDelta = Field(default=TimeDelta(hours=6), description='success_interval_help')
    failure_interval: TimeDelta = Field(default=TimeDelta(hours=6), description='failure_interval_help')


class NoTakeoverConfig(BaseModel):
    enable: bool = Field(
        default=False,
        title='设置不顶号时间段',
        description='仅顺延结界寄养任务，不会暂停整个 OAS，也不会影响其他任务。'
    )
    start_time_1: Time = Field(default=Time(hour=0), title='第一段开始时间')
    end_time_1: Time = Field(
        default=Time(hour=0),
        title='第一段结束时间',
        description='开始和结束相同表示不启用该时段；支持跨午夜，例如 23:00 到 07:00。'
    )
    start_time_2: Time = Field(default=Time(hour=0), title='第二段开始时间')
    end_time_2: Time = Field(
        default=Time(hour=0),
        title='第二段结束时间',
        description='开始和结束相同表示不启用该时段。'
    )


class PrewarmConfig(BaseModel):
    enable: bool = Field(
        default=False,
        title='提前唤起并等待寄养',
        description='仅对结界寄养生效。提前启动模拟器和游戏，停在“进入游戏”界面，原定寄养时间到达后才进入游戏。'
    )
    lead_seconds: int = Field(
        default=60,
        ge=30,
        le=300,
        title='提前唤起秒数',
        description='建议60秒。只提前做启动准备，不会提前执行寄养。'
    )


def _active_window_end(now: datetime, start: Time, end: Time) -> datetime | None:
    if start == end:
        return None
    for offset in (-1, 0):
        start_date = now.date() + timedelta(days=offset)
        start_at = datetime.combine(start_date, start)
        end_date = start_date if start < end else start_date + timedelta(days=1)
        end_at = datetime.combine(end_date, end)
        if start_at <= now < end_at:
            return end_at
    return None


def no_takeover_resume_at(config: NoTakeoverConfig, now: datetime | None = None) -> datetime | None:
    """Return when KekkaiUtilize may run again, or None when it may run now."""
    if not config.enable:
        return None
    original = (now or datetime.now()).replace(microsecond=0)
    probe = original
    windows = (
        (config.start_time_1, config.end_time_1),
        (config.start_time_2, config.end_time_2),
    )
    # Four passes are enough to merge two overlapping daily windows, including overnight ones.
    for _ in range(4):
        active_ends = [
            active_end
            for start, end in windows
            if (active_end := _active_window_end(probe, start, end)) is not None
        ]
        if not active_ends:
            return probe if probe != original else None
        probe = max(active_ends)
    return probe


def kekkai_prewarm_dispatch_at(config, due_at: datetime,
                               now: datetime | None = None) -> datetime | None:
    """返回预热调度时间；不顶号时段内或功能关闭时不预热。"""
    now = (now or datetime.now()).replace(microsecond=0)
    if not config.prewarm_config.enable or due_at <= now:
        return None
    if no_takeover_resume_at(config.no_takeover_config, now) is not None:
        return None
    if no_takeover_resume_at(config.no_takeover_config, due_at) is not None:
        return None
    lead_seconds = max(30, min(300, int(config.prewarm_config.lead_seconds)))
    return due_at - timedelta(seconds=lead_seconds)


class UtilizeConfig(BaseModel):
    utilize_rule: UtilizeRule = Field(default=UtilizeRule.DEFAULT, title='蹭卡类型')
    tai_ko_percentage: int = Field(default=50, title='蹭卡系数', description='最高会多少勾玉换100体力就填入何值，数值越小代表勾玉价值越高（比如：你每天60勾玉就换取100体力就填入60）')
    select_friend_list: SelectFriendList = Field(default=SelectFriendList.SAME_SERVER, title='蹭卡区服')
    specified_friend_enable: bool = Field(
        default=False,
        title='指定好友寄养',
        description='关闭时完全沿用原来的自动选卡；开启后按下面填写的中文昵称搜索并寄养。'
    )
    specified_same_server_friend_names: str = Field(
        default='',
        title='同区好友昵称',
        description='填写需要参与收益比较的同区好友完整昵称或备注，多个名字用逗号、顿号或换行隔开。'
    )
    specified_different_server_friend_names: str = Field(
        default='',
        title='跨区好友昵称',
        description='填写需要参与收益比较的跨区好友完整昵称或备注，多个名字用逗号、顿号或换行隔开。'
    )
    specified_friend_names: str = Field(
        default='',
        title='旧版指定好友昵称',
        description='仅用于兼容已经保存的旧配置。',
        hidden=True
    )
    is_utilize_harvest: bool = Field(default=True, title='是否领取蹭卡收获')
    shikigami_class: ShikigamiClass = Field(default=ShikigamiClass.N, description='shikigami_class_help')
    shikigami_order: int = Field(default=4, description='shikigami_order_help')


class KekkaiUtilize(ConfigBase):
    scheduler: UtilizeScheduler = Field(default_factory=UtilizeScheduler)
    prewarm_config: PrewarmConfig = Field(default_factory=PrewarmConfig)
    no_takeover_config: NoTakeoverConfig = Field(default_factory=NoTakeoverConfig)
    utilize_config: UtilizeConfig = Field(default_factory=UtilizeConfig)
