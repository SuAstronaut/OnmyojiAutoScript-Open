# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from enum import Enum
from pydantic import Field
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.Component.SwitchSoul.switch_soul_config import SwitchSoulConfig
from tasks.Component.config_base import ConfigBase, Time
from tasks.Component.config_scheduler import Scheduler


class SougenbiClass(str, Enum):
    GREED = '贪之阵'
    Anger = '嗔之阵'
    Foolery = '痴之阵'


class SougenbiConfig(ConfigBase):
    sougenbi_class: SougenbiClass = Field(default=SougenbiClass.Foolery)
    # 限制时间
    limit_time: Time = Field(default=Time(minute=30))
    # 限制次数
    limit_count: int = Field(default=30)
    # 加成
    buff_enable: bool = Field(default=False)
    # 是否点击金币50buff
    buff_gold_50_click: bool = Field(default=False, description='')
    # 是否点击金币100buff
    buff_gold_100_click: bool = Field(default=False, description='')
    # 是否点击经验50buff
    buff_exp_50_click: bool = Field(default=False, description='')
    # 是否点击经验100buff
    buff_exp_100_click: bool = Field(default=False, description='')


class Sougenbi(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    sougenbi_config: SougenbiConfig = Field(default_factory=SougenbiConfig)
    general_battle_config: GeneralBattleConfig = Field(default_factory=GeneralBattleConfig)
    switch_soul_config: SwitchSoulConfig = Field(default_factory=SwitchSoulConfig)

