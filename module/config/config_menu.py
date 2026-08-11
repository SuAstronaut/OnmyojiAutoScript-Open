# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

from cached_property import cached_property

from module.config.utils import *


class ConfigMenu:
    # 手动的代码配置菜单
    def __init__(self) -> None:
        self.menu = {}
        # 总览
        self.menu["Overview"] = []
        self.menu['TaskList'] = []
        # 脚本设置
        self.menu['Config'] = ['Script', 'Restart', 'GlobalGame']
        # 开发工具
        self.menu["Tools"] = ['Image Rule', 'Ocr Rule', 'Click Rule', 'Long Click Rule', 'Swipe Rule', 'List Rule']

        # 日常的任务
        self.menu["Daily Task"] = ['Nian', 'GoldYoukai', 'ExperienceYoukai', 'Pets', 'DailyTrifles', 'WantedQuests',
                                   'AreaBoss', 'DemonEncounter', 'SoulsTidy', 'CollectiveMissions', 'Delegation', 'TalismanPass', ]
        # 刷御魂
        self.menu["Dungeon Task"] = ["Exploration", 'MemoryScrolls', 'Sougenbi', 'Orochi', "EvoZone", "BondlingFairyland",
                                     "GoryouRealm", 'FallenSun', ]

        # 阴阳寮
        self.menu["Guild Task"] = ['KekkaiUtilize', 'KekkaiActivation', 'RyouToppa', 'RealmRaid', 'Dokan',
                                   "GuildBanquet", 'Hunt', 'AbyssShadows', "DemonRetreat", ]
        # 每周任务
        self.menu["Weekly Task"] = ['Duel', 'RichMan', 'WeeklyTrifles', 'Secret', 'EternitySea', 'SixRealms', 'Netherworld',
                                    'TrueOrochi']
        # 活动的任务
        self.menu["Version Activity"] = ['ActivityCommon', 'ActivityCommon2', 'ActivitySimple', 'FrogBoss',
                                         'FloatParade', 'NianTrue', 'LBS', "HeroTest", ]

        # 账号切换
        self.menu["Permission Task"] = ["SwitchAccountMany"]

        self.menu["other"] = ["Hyakkiyakou", "Chess"]

    @cached_property
    def gui_menu(self) -> str:
        """
        生成的是json字符串
        :return:
        """
        return json.dumps(self.menu, ensure_ascii=False, sort_keys=False, default=str)

    @cached_property
    def gui_menu_list(self) -> dict:
        del self.menu['TaskList']
        del self.menu['Tools']
        return self.menu


if __name__ == "__main__":
    try:
        m = ConfigMenu()
        print(m.gui_menu)
    except:
        print('weih')
