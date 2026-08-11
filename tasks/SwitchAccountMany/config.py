# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from pydantic import BaseModel, Field
from enum import Enum
from tasks.Component.config_base import ConfigBase, Time
from tasks.Component.config_scheduler import Scheduler


class AccountsType(str, Enum):
    IOS = 'ios'
    ANDROID = 'android'

class ManyConfig(BaseModel):
    switch_accounts_type: AccountsType = Field(default=AccountsType.IOS, title='切换账号类型')
    accounts_number: int = Field(default=1, title='需要切换账号数量')
    current_number: int = Field(default=0, title='当前切换到第几个账号', description='无需修改自动计数')
    # enable_notify: bool = Field(default=False, description='消息通知')
    # enable_save_img: bool = Field(default=False, description='截图保存')


class SwitchAccountMany(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    many_config: ManyConfig = Field(default_factory=ManyConfig, title='此任务适用于小号轮换做日常，需要额外开通权限')
