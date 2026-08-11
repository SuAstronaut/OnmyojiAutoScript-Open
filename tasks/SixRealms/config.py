# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from pydantic import BaseModel, Field
from tasks.Component.config_base import ConfigBase, Time
from tasks.Component.config_scheduler import Scheduler
from enum import Enum



class SixRealmsType(str, Enum):
    JIAOTU = '椒图'
    JUE = '觉'


class SixRealmsGate(BaseModel):
    # 六道之门类型
    six_realms_type: SixRealmsType = Field(title='六道之门类型', default=SixRealmsType.JIAOTU, description='阵容只支持速刷阵容，B站搜索速刷六道\n'
                                                                                                        '椒图：|TA|f5956b15f0382f9bce7390b099662ff6\n'
                                                                                                        'SP铃鹿和椒图瞬势；丑女若水；其余三个强身、红颜、借力')
    # 是否只打门票
    number_enable: bool = Field(default=False, title='是否只打门票', description='门票检查只支持椒图模式')
    # 限制时间
    limit_time: Time = Field(default=Time(minute=30))
    # 限制次数
    limit_count: int = Field(default=1)
    # 保存的任务进度（用于高优先级任务中断后恢复）
    saved_count: int = Field(default=0, title='已保存的运行次数，用于任务中断后恢复')


class SwitchSoulConfig(BaseModel):
    enable: bool = Field(default=False)
    # 换第一行
    one_switch: str = Field(default='-1,-1', title='六道之门御魂', description='switch_group_team_help')


class SixRealms(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    six_realms_gate: SixRealmsGate = Field(default_factory=SixRealmsGate)
    switch_soul_config: SwitchSoulConfig = Field(default_factory=SwitchSoulConfig)













