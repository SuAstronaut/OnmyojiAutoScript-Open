# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from enum import Enum  # type: ignore
from datetime import datetime, time  # type: ignore
from pydantic import BaseModel, Field

from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.Component.config_scheduler import Scheduler
from tasks.Component.config_base import ConfigBase, Time, TimeDelta
from tasks.Component.SwitchSoul.switch_soul_config import SwitchSoulConfig


class Layer(str, Enum):
    YANWU = "源赖光经验副本"
    MIJING = "源赖光技能副本"
    CHUANCHENG = "藤原道长经验副本"
    MENGXU = "藤原道长技能副本"


class SkillMode(str, Enum):
    PVE = 'PVE'
    PVP = 'PVP'


class HeroTestConfig(BaseModel):
    # 副本选择
    layer: Layer = Field(default=Layer.YANWU)
    skill_mode: SkillMode = Field(default=SkillMode.PVE, description="\n===============源赖光阵容===============\n"
                                                                     "1.五只不重复的一星式神（无需御魂，故无阵容码）\n"
                                                                     "2.一只满级茨球or针女（针女最快，容错最高）\n"
                                                                     "3.源赖光满级，御灵满级\n"
                                                                     "源赖光-PVP 祝福选取：剑之垒乘胜、天下布武绝命、血怒、鬼胄诱敌、追击\n"
                                                                     "源赖光-PVE 祝福选取：剑之垒乘胜、八华斩增进、血啸、鬼胄诱敌、追击\n"
                                                                     "\n===============藤原阵容===============\n"
                                                                     "藤原-PVP 祝福选取：泛音，凝啸，韵迟，叩弦，逐空\n"
                                                                     "|TA|ab2ca90ec90888a9c2a9fe8fc86922ec\n"

                                                                     "藤原-PVE 祝福选取：同调，韵迟，弥天，叠辉，敛神\n"
                                                                     "|TA|e5198a1ddfeed30f824b88e4aa0f9dd3\n"
                                  )
    # 限制时间
    limit_time: Time = Field(default=Time(minute=30))
    # 限制次数
    limit_count: int = Field(default=100)
    # 是否开启经验加成
    exp_50_buff_enable_help: bool = Field(default=False, description="打开经验50%加成")
    exp_100_buff_enable_help: bool = Field(
        default=False, description="打开经验100%加成"
    )


class HeroTest(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    herotest: HeroTestConfig = Field(default_factory=HeroTestConfig)
    general_battle: GeneralBattleConfig = Field(default_factory=GeneralBattleConfig)
    switch_soul_config: SwitchSoulConfig = Field(default_factory=SwitchSoulConfig)
