# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from enum import Enum
from pydantic import BaseModel, Field
from tasks.Component.config_base import ConfigBase, Time
from tasks.Component.config_scheduler import Scheduler


class ActiveType(str, Enum):
    battle = 'A-爬塔'
    battle2 = 'A-首领'
    delegate = '委派'
    huanjing = '狭间幻境'
    lingran = '灵染试炼'
    yanwu = '逢魔演武'
    gua = '呱呱画室'
    guabattle = '青蛙瓷器挑战'


class ModeType(str, Enum):
    DigitCounter = 'DigitCounter'
    Digit = 'Digit'


class NumberType(str, Enum):
    Ticket = '门票数量（数值递减）'
    Battle = '战斗次数（数值递增）'


class ActivityCommonConfig(BaseModel):
    # 活动类型选择
    active_type: ActiveType = Field(default=ActiveType.battle)
    # goto_challenge_path: str = Field(default='', description='只有‘A-版本活动’才生效\n前往挑战页面文字，用逗号间隔， 比如（版本活动,梦魔挑战）')

    enable: bool = Field(default=False, description='是否限制次数和时间')
    # 限制次数
    limit_count: int = Field(default=200)
    # 限制时间
    limit_time: Time = Field(default=Time(minute=30))

    each_limit_second: int = Field(default=0, title='每场战斗限制秒数（0秒代表不限制)')
    # 结束后激活 御魂清理
    active_souls_clean: bool = Field(default=False, description='active_souls_clean_help')
    enable_check_first_priority_task: bool = Field(default=False, description='有更高优先级任务就结束本任务，执行更高优先级任务\n'
                                                                              '适合爬塔中途去蹭卡，蹭卡结束也会继续爬塔，但是任务次数等都会重新开始')


class CheckBattleConfig(ConfigBase):
    enable: bool = Field(default=False, description='是否启用 OCR 战斗次数检测')
    ocr_number_mode: ModeType = Field(default=ModeType.DigitCounter, title='OCR 战斗次数检测类型')
    ocr_number_roi: str = Field(default='', title='OCR 坐标（例如：1136,113,31,52）')
    limit_ocr_number: int = Field(default=-1, title='限制战斗次数')
    number_type: NumberType = Field(default=NumberType.Battle, title='限制战斗次数类型')


class SwitchSoulConfig(BaseModel):
    enable: bool = Field(default=False, description='是否启用 御魂切换')
    # 是否启动 预设队伍
    preset_enable: bool = Field(default=False, description='preset_enable_help')
    switch_group_team: str = Field(default='-1,-1', description='switch_group_team_help')
    enable_switch_by_name: bool = Field(default=False, description='enable_switch_by_name_help')
    group_name: str = Field(default='')
    team_name: str = Field(default='')


class ActivityCommon(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    activity_common_config: ActivityCommonConfig = Field(default_factory=ActivityCommonConfig, title='活动通用配置')
    check_battle_config: CheckBattleConfig = Field(default_factory=CheckBattleConfig, title='战斗检测配置')
    switch_soul_config: SwitchSoulConfig = Field(default_factory=SwitchSoulConfig)
