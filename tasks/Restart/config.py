# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

from datetime import time

from pydantic import BaseModel
from pydantic import Field

from tasks.Component.config_base import ConfigBase
from tasks.Component.config_base import Time
from tasks.Component.config_scheduler import Scheduler


class RestartScheduler(Scheduler):
    enable: bool = Field(default=True, description='enable_help')
    priority: int = Field(default=0, description='priority_help')
    server_update: time = Field(default=time(hour=9, minute=5, second=0), description='server_update_help')


class HarvestConfig(BaseModel):
    # 默认启用
    # enable: bool = Field(default=True, description='harvest_enable_help')
    # 永久勾玉卡
    # enable_jade: bool = Field(default=True)
    # 签到
    # enable_sign: bool = Field(default=True)
    # 999天的签到福袋
    # enable_sign_999: bool = Field(default=True)
    # 邮件
    enable_mail: bool = Field(default=True)
    # 御魂加成
    # enable_soul: bool = Field(default=True)
    # 体力
    # enable_ap: bool = Field(default=True)
    # 庭院事务
    enable_courtyard_affairs: bool = Field(default=True)


class TaskConfig(ConfigBase):
    # 出现异常是否重启游戏
    error_restart: bool = Field(default=True)
    error_restart_time: Time = Field(default=Time(second=10), title='异常重启游戏时间', description='遇到报错间隔多久时间重启')
    # 首次重启是否调起 集体任务
    enable_collective_missions: bool = Field(default=False)
    # 首次重启是否调起 大神签到
    enable_big_god_sign_in: bool = Field(default=False)
    # enable_update_repo: bool = Field(default=False, description='首次重启是否调起 更新GitHub协作者权限')
    # github_token: str = Field(default="")
    # 任务完成日期
    task_date: str = Field(default='')


class LoginCharacterConfig(BaseModel):
    # 同账号同服务器多个角色时,需要登录的角色名/服务器名
    character: str = Field(default="")


class Restart(ConfigBase):
    # scheduler: RestartScheduler = Field(default_factory=RestartScheduler)
    harvest_config: HarvestConfig = Field(default_factory=HarvestConfig)
    task_config: TaskConfig = Field(default_factory=TaskConfig)
    login_character_config: LoginCharacterConfig = Field(default_factory=LoginCharacterConfig)
