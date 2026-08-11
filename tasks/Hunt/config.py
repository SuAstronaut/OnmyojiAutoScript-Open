# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from pydantic import BaseModel, Field
from tasks.Component.config_base import ConfigBase
from tasks.Component.config_scheduler import Scheduler
from tasks.Component.GeneralBattle.config_general_battle import GreenMarkType


class KirinConfig(BaseModel):
    enable_task: bool = Field(default=True, description='是否开启麒麟任务')
    enable: bool = Field(default=False, description='是否启用御魂切换')
    preset_enable: bool = Field(default=False, description='preset_enable_help')
    switch_group_team: str = Field(default='-1,-1', description='switch_group_team_help')
    # 是否开启绿标
    green_enable: bool = Field(default=False, description='green_enable_help')
    # 选哪一个绿标
    green_mark: GreenMarkType = Field(default=GreenMarkType.GREEN_LEFT1, description='green_mark_help')
    # 超时退出战斗
    exit_battle_second: int = Field(default=0, description='超时退出战斗（单位秒）, 0代表不退出')


class NetherWorldConfig(BaseModel):
    enable_task: bool = Field(default=True, description='是否开启阴界任务')
    enable: bool = Field(default=False, description='是否启用御魂切换')
    preset_enable: bool = Field(default=False, description='preset_enable_help')
    switch_group_team: str = Field(default='-1,-1', description='switch_group_team_help')

    # 是否开启绿标
    green_enable: bool = Field(default=False, description='green_enable_help')
    # 选哪一个绿标
    green_mark: GreenMarkType = Field(default=GreenMarkType.GREEN_LEFT1, description='green_mark_help')

    # 超时退出战斗
    exit_battle_second: int = Field(default=0, description='超时退出战斗（单位秒）, 0代表不退出')


class Hunt(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    kirin_config: KirinConfig = Field(default_factory=KirinConfig)
    nether_world_config: NetherWorldConfig = Field(default_factory=NetherWorldConfig)
