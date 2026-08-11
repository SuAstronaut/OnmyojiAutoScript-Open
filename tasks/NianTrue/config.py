# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from pydantic import BaseModel, Field

from tasks.Component.SwitchSoul.switch_soul_config import SwitchSoulConfig
from tasks.Component.config_base import ConfigBase, Time
from tasks.Component.config_scheduler import Scheduler


class NianTrueConfig(BaseModel):
    # 限制次数
    limit_count: int = Field(default=1)
    # 限制时间
    limit_time: Time = Field(default=Time(minute=30))


class NianTrue(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    nian_true_config: NianTrueConfig = Field(default_factory=NianTrueConfig)
    switch_soul_config: SwitchSoulConfig = Field(default_factory=SwitchSoulConfig)


