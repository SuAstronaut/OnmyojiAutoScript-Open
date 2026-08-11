# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from enum import Enum
from pydantic import BaseModel, Field
from tasks.Component.config_base import ConfigBase
from tasks.Component.config_scheduler import Scheduler


class SummonType(str, Enum):
    default = '普通召唤'
    recall = '今忆召唤'


class DailyTriflesConfig(BaseModel):
    # 日志备份
    enable_backup_log: bool = Field(default=True, title='日志备份')
    # 邮件领取
    enable_mail: bool = Field(default=False)
    # 庭院事务
    enable_courtyard_affairs: bool = Field(default=True)
    # 大神签到
    big_god_sign_in: bool = Field(default=False, title='大神签到')

    # 式神集结
    shikigami_massed: bool = Field(default=True)
    # 铜铃礼包
    copper_box: bool = Field(default=True)
    # 每日一抽
    one_summon: bool = Field(default=False)
    # summon_type: SummonType = Field(default=SummonType.default, description='召唤类型')
    # friend_love: bool = Field(default=False)
    # 吉闻
    luck_msg: bool = Field(default=False)
    # 招募成员
    recruit_members: bool = Field(default=False)
    # 抽奖箱
    lottery_box: bool = Field(default=True)
    # 式神碎片合成
    shikigami_debris: bool = Field(default=False)
    # 商店签到 签到50次得黑蛋的
    store_sign: bool = Field(default=False, description='store_sign_help')
    # 召唤破碎的咒符
    broken_amulet: int = Field(default=0, description='trifles_broken_amulet_help')
    # 每天购买体力数量
    buy_sushi_count: int = Field(default=0)


class DailyTriflesScheduler(Scheduler):
    enable: bool = Field(default=True, description='enable_help')


class DailyTrifles(ConfigBase):
    scheduler: DailyTriflesScheduler = Field(default_factory=DailyTriflesScheduler)
    trifles_config: DailyTriflesConfig = Field(default_factory=DailyTriflesConfig)
