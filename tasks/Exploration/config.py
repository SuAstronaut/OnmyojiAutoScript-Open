from enum import Enum
from pydantic import BaseModel, Field
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.Component.GeneralInvite.config_invite import FindMode
from tasks.Component.SwitchSoul.switch_soul_config import SwitchSoulConfig
from tasks.Component.config_base import ConfigBase, Time
from tasks.Component.config_scheduler import Scheduler


class ExplorationLevel(str, Enum):
    EXPLORATION_1 = '第一章'
    EXPLORATION_2 = '第二章'
    EXPLORATION_3 = '第三章'
    EXPLORATION_4 = '第四章'
    EXPLORATION_5 = '第五章'
    EXPLORATION_6 = '第六章'
    EXPLORATION_7 = '第七章'
    EXPLORATION_8 = '第八章'
    EXPLORATION_9 = '第九章'
    EXPLORATION_10 = '第十章'
    EXPLORATION_11 = '第十一章'
    EXPLORATION_12 = '第十二章'
    EXPLORATION_13 = '第十三章'
    EXPLORATION_14 = '第十四章'
    EXPLORATION_15 = '第十五章'
    EXPLORATION_16 = '第十六章'
    EXPLORATION_17 = '第十七章'
    EXPLORATION_18 = '第十八章'
    EXPLORATION_19 = '第十九章'
    EXPLORATION_20 = '第二十章'
    EXPLORATION_21 = '第二十一章'
    EXPLORATION_22 = '第二十二章'
    EXPLORATION_23 = '第二十三章'
    EXPLORATION_24 = '第二十四章'
    EXPLORATION_25 = '第二十五章'
    EXPLORATION_26 = '第二十六章'
    EXPLORATION_27 = '第二十七章'
    EXPLORATION_28 = '第二十八章'


class AttackNumber(str, Enum):
    SEVEN = '7'
    ALL = 'all'


class UpType(str, Enum):
    ALL = 'up_all'  # 全部
    EXP = 'up_exp'  # 经验
    COIN = 'up_coin'  # 金币
    DARUMAA = 'up_daruma'  # 达摩


class UserStatus(str, Enum):
    LEADER = 'leader'
    MEMBER = 'member'
    ALONE = 'alone'


# 是否自动添加候补式神
class AutoRotate(str, Enum):
    no = '不'
    yes = '是'


class ChooseRarity(str, Enum):
    N = 'N卡'
    S = '素材'


class InviteConfig(BaseModel):
    friend_1: str = Field(default='', description='friend_name_help')
    find_mode: FindMode = Field(default=FindMode.AUTO_FIND, description='find_mode_help')
    wait_time: Time = Field(default=Time(minute=2), description='wait_time_help')


class Scrolls(BaseModel):
    # 绘卷模式
    scrolls_enable: bool = Field(title='', default=False, description='开启绘卷模式时,下面的时间、次数、章节限制失效\n'
                                                                      '会一直探索到突破券>26时，结束探索任务，调起突破任务')
    # scrolls_cd: Time = Field(title='间隔时间', default=Time(hour=0, minute=1, second=0), description='本次探索任务结束到下次探索任务的时间（如果要持续循环探索突破就设置一个较小的时间）')
    # scrolls_threshold: int = Field(title='突破票数量', default=25, description='超过设定的票数就结束探索任务，调起突破任务（需要开启突破任务）')
    check_boss_num: bool = Field(title='超鬼王掉落检查', default=False, description='满50结束探索任务（超鬼王期间使用）', hidden=True)


class ExplorationConfig(BaseModel):
    buff_gold_50_click: bool = Field(default=False)
    buff_gold_100_click: bool = Field(default=False)
    buff_exp_50_click: bool = Field(default=False)
    buff_exp_100_click: bool = Field(default=False)
    # 是否开启自动轮换
    atuo_rotate_on: bool = Field(default=True)
    # enable_hard_mode: bool = Field(default=True, description='是否困难模式')

    user_status: UserStatus = Field(default=UserStatus.ALONE, description='user_status_help')
    # current_exploration_count: int = Field(title='探索次数', default='7', description='默认探索7次')
    limit_time: Time = Field(default=Time(minute=30))
    minions_cnt: int = Field(title='战斗次数', default=30)
    min_boss_cnt: int = Field(title='战斗章数', default=4, description='打 X 章后结束任务（打完一次boss才算一章）')

    exploration_level: ExplorationLevel = Field(title='选择探索章节', default=ExplorationLevel.EXPLORATION_28)
    auto_rotate: AutoRotate = Field(title='自动添加候补式神', default=AutoRotate.no)
    choose_rarity: ChooseRarity = Field(title='选择狗粮稀有度', default=ChooseRarity.N)
    up_type: UpType = Field(default=UpType.ALL)


class Exploration(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    scrolls: Scrolls = Field(default_factory=Scrolls)
    invite_config: InviteConfig = Field(default_factory=InviteConfig)
    exploration_config: ExplorationConfig = Field(default_factory=ExplorationConfig)
    # general_battle_config: GeneralBattleConfig = Field(default_factory=GeneralBattleConfig)
    switch_soul_config: SwitchSoulConfig = Field(default_factory=SwitchSoulConfig)
