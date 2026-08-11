# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from enum import Enum
from pydantic import Field
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.Component.GeneralInvite.config_invite import InviteConfig
from tasks.Component.SwitchSoul.switch_soul_config import SwitchSoulConfig
from tasks.Component.config_base import ConfigBase, Time
from tasks.Component.config_scheduler import Scheduler


class BondlingMode(str, Enum):
    MODE1 = 'mode_1'
    MODE2 = 'mode_2'
    MODE3 = 'mode_3'
    MODE4 = 'mode_4'


class BondlingClass(str, Enum):
    TOMB_GUARD = '镇墓兽'
    AZURE_BASAN = '火灵'
    SNOWBALL = '茨球'
    LITTLE_KURO = '小黑'
    BONDLING_2_1 = '针女'
    BONDLING_2_2 = '薙魂'
    BONDLING_2_3 = '月魔兔'
    BONDLING_2_4 = '狐火'


class UserStatus(str, Enum):
    LEADER = 'leader'
    MEMBER = 'member'
    ALONE = 'alone'
    handoff1 = 'handoff1'
    handoff2 = 'handoff2'


class BondlingConfig(ConfigBase):
    # 身份
    user_status: UserStatus = Field(default=UserStatus.ALONE, description='user_status_help')
    bondling_mode: BondlingMode = Field(default=BondlingMode.MODE2, description='bondling_mode_help')
    limit_time: Time = Field(default=Time(minute=30))
    limit_count: int = Field(default=30)
    # bondling_stone_enable: bool = Field(default=False, description='bondling_stone_enable_help')
    bondling_stone_class: BondlingClass = Field(default=BondlingClass.TOMB_GUARD, description='bondling_stone_class_help')


class BondlingSwitchSoul(ConfigBase):
    auto_switch_soul: bool = Field(default=False, description='auto_switch_soul_help')
    # 镇墓兽 config
    tomb_guard_switch: str = Field(default='-1,-1', description='tomb_guard_switch_help')
    # 茨球 config
    snowball_switch: str = Field(default='-1,-1', description='snowball_switch_help')
    # 小黑 config
    little_kuro_switch: str = Field(default='-1,-1', description='little_kuro_switch_help')
    # 火灵 config
    azure_basan_switch: str = Field(default='-1,-1', description='azure_basan_switch_help')


class BondlingCheck(ConfigBase):
    check_enable: bool = Field(default=True, title='是否检查契忆数量')
    limit_num: int = Field(default=2000, title='契忆数量限制')


class BondlingFairyland(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    bondling_check: BondlingCheck = Field(default_factory=BondlingCheck, title='契忆检查')
    bondling_config: BondlingConfig = Field(default_factory=BondlingConfig)
    # bondling_switch_soul: BondlingSwitchSoul = Field(default_factory=BondlingSwitchSoul)
    invite_config: InviteConfig = Field(default_factory=InviteConfig)
    # battle_config: GeneralBattleConfig = Field(default_factory=GeneralBattleConfig)
    switch_soul_config: SwitchSoulConfig = Field(default_factory=SwitchSoulConfig)
    bondling_find_switch: SwitchSoulConfig = Field(default_factory=SwitchSoulConfig, title='探查切换御魂')





