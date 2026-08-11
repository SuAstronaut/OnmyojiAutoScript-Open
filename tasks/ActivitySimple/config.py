# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey


from pydantic import BaseModel, Field

from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.Component.config_base import ConfigBase, Time
from tasks.Component.config_scheduler import Scheduler


class ActivitySimpleConfig(BaseModel):
    # 限制时间
    limit_time: Time = Field(default=Time(minute=30))
    # 限制次数
    limit_count: int = Field(default=100)


class ActivitySimple(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    simple_config: ActivitySimpleConfig = Field(default_factory=ActivitySimpleConfig, title='注意：要在挑战页面开启任务, 需要自己切换御魂')
    general_battle: GeneralBattleConfig = Field(default_factory=GeneralBattleConfig)
