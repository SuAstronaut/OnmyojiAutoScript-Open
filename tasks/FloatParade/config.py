# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from enum import Enum
from pydantic import BaseModel, Field
from tasks.Component.config_base import ConfigBase
from tasks.Component.config_scheduler import Scheduler


class LevelReward(str, Enum):
    ONE = '蛇皮/青吉鬼'
    TWO = '金币/勾玉'
    THREE = '体力/樱饼'


class FloatParadeConfig(BaseModel):
    collect_placement_reward: bool = Field(default=True, title='是否收集放置奖励')
    collect_exp: bool = Field(default=True, title='是否收集经验')


class FloatParade(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    float_parade: FloatParadeConfig = Field(default_factory=FloatParadeConfig)
