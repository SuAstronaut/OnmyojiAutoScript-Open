# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from pydantic import BaseModel, Field
from tasks.Component.config_base import ConfigBase
from tasks.Component.config_scheduler import Scheduler
from tasks.Utils.config_enum import DemonClass


class ThousandThings(BaseModel):
    # 千物宝箱
    enable: bool = Field(default=False)
    mystery_amulet: bool = Field(default=False)
    black_daruma_fragment: bool = Field(default=False)
    ap: bool = Field(default=False, description='ap_help')


class Shrine(BaseModel):
    # 神龛
    enable: bool = Field(default=False)
    black_daruma: bool = Field(default=False)
    white_daruma_five: bool = Field(default=False)
    white_daruma_four: bool = Field(default=False)


class GuildStore(BaseModel):
    # 功勋商店
    enable: bool = Field(default=False)
    guild_libao: bool = Field(title='功勋礼包', default=False)
    guild_fl: bool = Field(title='风铃', default=False)
    guild_exp: bool = Field(title='经验御札', default=False)
    guild_yuhun: bool = Field(title='随机六星御魂', default=False)

    mystery_amulet: bool = Field(default=False)
    black_daruma_scrap: bool = Field(default=False)
    skin_ticket: int = Field(default=0, description='skin_ticket_help')


class GuildProcurement(BaseModel):
    # 寮内采办
    enable: bool = Field(default=False)
    buy_lottery_box: bool = Field(title='同心奖箱', default=False)


class Consignment(BaseModel):
    # 寄售屋
    enable: bool = Field(default=False)
    buy_sale_ticket: bool = Field(default=False, description='buy_sale_ticket_help')


class Scales(BaseModel):
    # 密卷屋 蛇皮
    enable: bool = Field(default=False)
    orochi_scales: bool = Field(default=True)
    picture_book_scrap: bool = Field(default=True)


class Bondlings(BaseModel):
    # 契灵商店 契忆
    enable: bool = Field(default=False)
    random_soul: int = Field(default=0, description='random_soul_help')
    bondling_stone: int = Field(default=0, description='bondling_stone_help')
    high_bondling_discs: int = Field(default=0, description='high_bondling_discs_help')
    medium_bondling_discs: int = Field(default=0, description='medium_bondling_discs_help')


class SpecialRoom(BaseModel):
    # 杂货铺 特殊购买
    enable: bool = Field(default=False)
    check_money: bool = Field(default=False, title='是否检查购买金额足够')
    totem_pass: bool = Field(default=False)
    medium_bondling_discs: int = Field(default=0, description='medium_bondling_discs_special')
    low_bondling_discs: int = Field(default=0, description='low_bondling_discs_special')


class HonorRoom(BaseModel):
    # 杂货铺 荣誉购买
    enable: bool = Field(default=False)
    check_money: bool = Field(default=False, title='是否检查购买金额')
    mystery_amulet: bool = Field(default=False, description='mystery_amulet_help_honor')
    black_daruma_scrap: bool = Field(default=False, description='black_daruma_scrap_help_honor')


class FriendshipPoints(BaseModel):
    # 杂货铺 友情点
    enable: bool = Field(default=False)
    check_money: bool = Field(default=False, title='是否检查购买金额')
    white_daruma: bool = Field(default=False)
    red_daruma: int = Field(default=0)
    broken_amulet: int = Field(default=0)


class MedalRoom(BaseModel):
    # 杂货铺 勋章购买
    enable: bool = Field(default=False)
    check_money: bool = Field(default=False, title='是否检查购买金额')
    black_daruma: bool = Field(default=False)
    mystery_amulet: bool = Field(default=False)
    ap_100: bool = Field(default=False)
    random_soul: bool = Field(default=False)
    white_daruma: bool = Field(default=False)
    # 挑战券
    challenge_pass: int = Field(default=0, description='challenge_pass_help')
    red_daruma: int = Field(default=0)
    broken_amulet: int = Field(default=0)


class Charisma(BaseModel):
    # 杂货铺 魅力购买
    enable: bool = Field(default=False)
    check_money: bool = Field(default=False, title='是否检查购买金额')
    black_daruma_scrap: bool = Field(default=False)
    mystery_amulet: bool = Field(default=False)


class PushNotify(BaseModel):
    enable: bool = Field(title='Enable', default=True, description='大富翁是否消息通知')


class RichMan(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    push_notify: PushNotify = Field(default_factory=PushNotify)
    # 千物宝箱
    thousand_things: ThousandThings = Field(default_factory=ThousandThings)
    # 神龛
    shrine: Shrine = Field(default_factory=Shrine)
    # 功勋商店
    guild_store: GuildStore = Field(default_factory=GuildStore)
    # 寮内采办
    guild_procurement: GuildProcurement = Field(default_factory=GuildProcurement, title='寮内采办')
    # 寄售屋
    consignment: Consignment = Field(default_factory=Consignment)
    # 密卷屋 蛇皮
    scales: Scales = Field(default_factory=Scales)
    # 契灵商店 契忆
    bondlings: Bondlings = Field(default_factory=Bondlings)
    # 杂货铺
    special_room: SpecialRoom = Field(default_factory=SpecialRoom)
    honor_room: HonorRoom = Field(default_factory=HonorRoom)
    friendship_points: FriendshipPoints = Field(default_factory=FriendshipPoints)
    medal_room: MedalRoom = Field(default_factory=MedalRoom)
    charisma: Charisma = Field(default_factory=Charisma)
