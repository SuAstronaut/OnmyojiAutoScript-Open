# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from enum import Enum
from pydantic import BaseModel, Field
from tasks.Component.config_base import ConfigBase
from tasks.Component.config_scheduler import Scheduler


class MissionsType(str, Enum):
    AW = '觉醒'
    GR = '御灵'
    SO = '御魂'
    FEED = 'N卡'  # 喂N卡


class MissionsConfig(BaseModel):
    missions_type: MissionsType = Field(default=MissionsType.GR)
    # 捐献勾玉
    juan_jade: bool = Field(default=False, title='捐献勾玉')


class CollectiveMissions(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    missions_config: MissionsConfig = Field(default_factory=MissionsConfig)





