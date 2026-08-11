import traceback
from module.atom.image import RuleImageGroup

from tasks.Component.Costume.assets import CostumeAssets as C
from tasks.Component.CostumeBattle.assets import CostumeBattleAssets

from tasks.Component.GeneralBattle.assets import GeneralBattleAssets
from tasks.GameUi.assets import GameUiAssets as G
from tasks.KekkaiUtilize.assets import KekkaiUtilizeAssets
from tasks.Restart.assets import RestartAssets
from tasks.RyouToppa.assets import RyouToppaAssets
from tasks.WantedQuests.assets import WantedQuestsAssets


class PageRegistry:
    _registry = dict()

    @classmethod
    def add(cls, page):
        """注册指定页面"""
        cls._registry[page.name] = page

    @classmethod
    def remove(cls, page):
        """从注册表中移除指定页面"""
        cls._registry.pop(page.name, None)

    @classmethod
    def all(cls):
        return list(cls._registry.values())


class Page:
    def __init__(self, check_button, links=None, chinese_name=None):
        if links is None:
            links = {}
        self.check_button = check_button
        # 修改数据结构为 {destination: [button1, button2, ...]}
        self.links = {dest: [btn] if not isinstance(btn, list) else btn
                      for dest, btn in links.items()} if links else {}
        self.additional: list = None  # 附加按钮或者是ocr检测按钮
        (filename, line_number, function_name, text) = traceback.extract_stack()[-2]
        self.name = text[:text.find('=')].strip()
        # 设置中文名称，如果未提供则使用变量名
        self.chinese_name = chinese_name if chinese_name else self.name
        PageRegistry.add(self)

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.chinese_name

    def link(self, button, destination):
        # 统一转成列表（支持传 1 个 或 多个）
        button_list = button if isinstance(button, (list, tuple)) else [button]

        if destination not in self.links:
            self.links[destination] = []

        # 关键：把多个按钮分别存进去，变成扁平列表！
        if button_list not in self.links[destination]:
            self.links[destination].append(button_list)

# ===================== 【公共工具方法】 =====================

# 默认倒序
def get_reversed_attr_list(module, prefix, reverse=True):
    # 排序规则：支持数字 1/13/4_1 等格式，倒序
    def sort_key(key):
        return tuple(int(n) for n in key.replace(prefix, "").split("_"))

    # 筛选 + 排序
    attrs = sorted(
        [k for k in dir(module) if k.startswith(prefix)],
        key=sort_key,
        reverse=reverse
    )
    # 组装最终列表
    return [getattr(module, k) for k in attrs]

# 庭院相关
main_goto_summon_list = [G.I_MAIN_GOTO_SUMMON] + get_reversed_attr_list(C, "I_MAIN_GOTO_SUMMON_")
main_goto_exploration_list = [G.I_MAIN_GOTO_EXPLORATION] + get_reversed_attr_list(C, "I_MAIN_GOTO_EXPLORATION_")
main_goto_town_list = [G.I_MAIN_GOTO_TOWN] + get_reversed_attr_list(C, "I_MAIN_GOTO_TOWN_")
main_goto_pet_list = [G.I_PET_HOUSE] + get_reversed_attr_list(C, "I_PET_HOUSE_")

# 战斗相关
exit_list = [GeneralBattleAssets.I_EXIT] + get_reversed_attr_list(CostumeBattleAssets, "I_EXIT_", reverse=False)
friends_list = [GeneralBattleAssets.I_FRIENDS] + get_reversed_attr_list(CostumeBattleAssets, "I_FRIENDS_", reverse=False)

win_list = RuleImageGroup([GeneralBattleAssets.I_WIN] + get_reversed_attr_list(G, "I_WIN_", reverse=False))
false_list = RuleImageGroup([GeneralBattleAssets.I_FALSE] + get_reversed_attr_list(G, "I_FALSE_", reverse=False))

prepare_highlight_list = RuleImageGroup([GeneralBattleAssets.I_PREPARE_HIGHLIGHT_1, GeneralBattleAssets.I_PREPARE_HIGHLIGHT_2])


# 登录login
page_login = Page(G.I_CHECK_LOGIN_FORM, chinese_name='登录界面')
# Main Home 主页
page_main = Page([
    G.I_PAGE_MAIN_RELAX,
    WantedQuestsAssets.I_WQ_DONE,
    WantedQuestsAssets.I_WQ_SEAL,
    RestartAssets.I_LOGIN_SCROOLL_OPEN,
    RestartAssets.I_LOGIN_SCROOLL_CLOSE,
], chinese_name='庭院')
page_login.link(button=RestartAssets.O_LOGIN_ENTER_GAME, destination=page_main)
page_main.additional = [G.I_BACK_RED, RestartAssets.I_LOGIN_SCROOLL_CLOSE]
# 町中town
page_town = Page(G.I_CHECK_TOWN, chinese_name='町中')
page_town.link(button=G.I_TOWN_GOTO_MAIN, destination=page_main)
page_main.link(button=main_goto_town_list, destination=page_town)
# 召唤summon
page_summon = Page(G.I_CHECK_SUMMON, chinese_name='召唤')
page_summon.link(button=G.I_BACK_YELLOW, destination=page_main)
page_main.link(button=main_goto_summon_list, destination=page_summon)
# 探索exploration
page_exploration = Page(G.I_CHECK_EXPLORATION, chinese_name='探索')
page_exploration.link(button=G.I_BACK_YELLOW, destination=page_main)
page_main.link(button=main_goto_exploration_list, destination=page_exploration)
page_main.link(button=G.I_EXPLORATION_EXPAND, destination=page_exploration)
# 宠物屋 pet
page_pet = Page(G.I_PET_CLAW, chinese_name='宠物屋')
page_pet.link(button=GeneralBattleAssets.I_EXIT_OLD, destination=page_main)
page_main.link(button=main_goto_pet_list, destination=page_pet)

# ************************************* 探索部分 *****************************************#
# 觉醒 awake zones
page_awake_zones = Page(G.I_CHECK_AWAKE, chinese_name='觉醒副本')
page_awake_zones.link(button=G.I_BACK_YELLOW, destination=page_exploration)
page_exploration.link(button=G.I_EXPLORATION_GOTO_AWAKE_ZONE, destination=page_awake_zones)
# 御魂 soul zones
page_soul_zones = Page(G.I_CHECK_SOUL_ZONES, chinese_name='御魂副本')
page_soul_zones.link(button=G.I_BACK_YELLOW, destination=page_exploration)
page_exploration.link(button=G.I_EXPLORATION_GOTO_SOUL_ZONE, destination=page_soul_zones)
# 结界突破 realm raid
page_realm_raid = Page(G.I_CHECK_REALM_RAID, chinese_name='结界突破')
page_realm_raid.link(button=G.I_BACK_RED, destination=page_exploration)
page_exploration.link(button=G.I_EXPLORATION_GOTO_REALM_RAID, destination=page_realm_raid)
# 寮突破 击破奖励
page_kekkai_toppa = Page(RyouToppaAssets.I_RYOU_REWARD, chinese_name='寮突破')
page_kekkai_toppa.link(button=G.I_BACK_RED, destination=page_exploration)
page_kekkai_toppa.link(button=G.I_RYOUTOPPA_GOTO_REALMRAID, destination=page_realm_raid)
page_realm_raid.link(button=RyouToppaAssets.I_RYOU_TOPPA, destination=page_kekkai_toppa)
# 御灵 goryou realm
page_goryou_realm = Page(G.I_CHECK_GORYOU, chinese_name='御灵副本')
page_goryou_realm.link(button=G.I_BACK_YELLOW, destination=page_exploration)
page_exploration.link(button=G.I_EXPLORATION_GOTO_GORYOU_REALM, destination=page_goryou_realm)
# 委派 delegation
page_delegation = Page(G.I_CHECK_DELEGATION, chinese_name='委派')
page_delegation.link(button=G.I_BACK_YELLOW, destination=page_exploration)
page_exploration.link(button=G.I_EXPLORATION_GOTO_DELEGATION, destination=page_delegation)
# 秘闻副本 SECRET zones
page_secret_zones = Page(G.I_CHECK_SECRET_ZONES, chinese_name='秘闻副本')
page_secret_zones.link(button=G.I_BACK_YELLOW, destination=page_exploration)
page_exploration.link(button=G.I_EXPLORATION_GOTO_SECRET_ZONES, destination=page_secret_zones)
# 地域鬼王 area boss
page_area_boss = Page(G.I_CHECK_AREA_BOSS, chinese_name='地域鬼王')
page_area_boss.link(button=G.I_BACK_YELLOW, destination=page_exploration)
page_exploration.link(button=G.I_EXPLORATION_GOTO_AREA_BOSS, destination=page_area_boss)
# 平安奇谭 heian kitan
page_heian_kitan = Page(G.I_CHECK_HEIAN_KITAN, chinese_name='平安奇谭')
page_heian_kitan.link(button=G.I_CHECK_HEIAN_KITAN, destination=page_exploration)
page_exploration.link(button=G.I_EXPLORATION_GOTO_HEIAN_KITAN, destination=page_heian_kitan)
# 六道之门 椒图
page_six_gates = Page(G.I_CHECK_SIX_GATES, chinese_name='六道之门-椒图')
page_six_gates.link(button=G.I_BACK_BLUE, destination=page_exploration)
page_exploration.link(button=G.I_EXPLORATION_GOTO_SIX_GATES, destination=page_six_gates)
# 六道之门 觉
page_six_gates_jue = Page(G.I_CHECK_SIX_GATES_JUE, chinese_name='六道之门-觉')
page_six_gates_jue.link(button=G.I_BACK_BLUE, destination=page_exploration)
page_exploration.link(button=G.I_EXPLORATION_GOTO_SIX_GATES_JUE, destination=page_six_gates_jue)
# 契灵之境 bondling fairyland
page_bondling_fairyland = Page(G.I_CHECK_BONDLING_FAIRYLAND, chinese_name='契灵之境')
page_bondling_fairyland.link(button=G.I_BACK_YELLOW, destination=page_exploration)
page_exploration.link(button=G.I_EXPLORATION_GOTO_BONDLING_FAIRYLAND, destination=page_bondling_fairyland)
# 英杰试炼 hero test
page_hero_test = Page(G.I_CHECK_HERO_TEST, chinese_name='英杰试炼')
page_hero_test.link(button=G.I_BACK_YELLOW, destination=page_exploration)
page_exploration.link(button=G.I_EXPLORATION_GOTO_HERO_TEST, destination=page_hero_test)

# ************************************* 町中部分 *****************************************#
# 斗技 duel
page_duel = Page(G.I_CHECK_DUEL, chinese_name='斗技')
page_duel.link(button=G.I_BACK_YELLOW, destination=page_town)
page_town.link(button=G.I_TOWN_GOTO_DUEL, destination=page_duel)
# 逢魔之时 demon_encounter
page_demon_encounter = Page(G.I_CHECK_DEMON_ENCOUNTER, chinese_name='逢魔之时')
page_demon_encounter.link(button=G.I_BACK_YELLOW, destination=page_town)
page_town.link(button=G.I_TOWN_GOTO_DEMON_ENCOUNTER, destination=page_demon_encounter)
# 麒麟 kirin
page_kirin = Page(G.I_CHECK_KIRIN, chinese_name='麒麟')
page_kirin.link(button=G.I_BACK_YELLOW, destination=page_town)
page_town.link(button=G.I_TOWN_GOTO_HUNT, destination=page_kirin)
# 阴界之门 netherworld
page_netherworld = Page(G.I_CHECK_NETHERWORLD, chinese_name='阴界之门')
page_netherworld.link(button=G.I_BACK_YELLOW, destination=page_town)
page_town.link(button=G.I_TOWN_GOTO_HUNT, destination=page_netherworld)
# 协同斗技 draft_duel
page_draft_duel = Page(G.I_CHECK_DRAFT_DUEL, chinese_name='协同斗技')
page_draft_duel.link(button=G.I_BACK_YELLOW, destination=page_town)
page_town.link(button=G.I_TOWN_GOTO_DRAFT_DUEL, destination=page_draft_duel)
# 百鬼弈 hyakkisen
page_hyakkisen = Page(G.I_CHECK_HYAKKISEN, chinese_name='百鬼弈')
page_hyakkisen.link(button=G.I_BACK_YELLOW, destination=page_town)
page_town.link(button=G.I_TOWN_GOTO_HYAKKISEN, destination=page_hyakkisen)
# 百鬼夜行
page_hyakkiyakou = Page(G.I_CHECK_KYAKKIYAKOU, chinese_name='百鬼夜行')
page_hyakkiyakou.link(button=G.I_BACK_RED, destination=page_town)
page_town.link(button=[G.I_TOWN_GOTO_HYAKKIYAKOU, G.I_TOWN_GOTO_HYAKKIYAKOU_2], destination=page_hyakkiyakou)
# 鼬乐园 entertainment
page_entertainment = Page(G.I_CHECK_ENTERTAINMENT, chinese_name='鼬乐园')
page_entertainment.link(button=G.I_BACK_YELLOW, destination=page_town)
page_town.link(button=G.I_TOWN_GOTO_ENTERTAINMENT, destination=page_entertainment)
# 百鬼棋局 chess
page_chess = Page(G.I_CHECK_CHESS, chinese_name='百鬼棋局')
page_chess.link(button=G.I_BACK_YELLOW, destination=page_entertainment)
page_entertainment.link(button=G.I_ENTERTAINMENT_GOTO_CHESS, destination=page_chess)

# ************************************* 庭院部分 *****************************************#
# 式神录 shikigami_records
page_shikigami_records = Page(G.I_CHECK_RECORDS, chinese_name='式神录')
page_shikigami_records.additional = [G.I_BACK_RED]
page_shikigami_records.link(button=G.I_BACK_YELLOW, destination=page_main)
page_main.link(button=G.I_MAIN_GOTO_SHIKIGAMI_RECORDS, destination=page_shikigami_records)
# 阴阳术 onmyodo
page_onmyodo = Page(G.I_CHECK_ONMYODO, chinese_name='阴阳术')
page_onmyodo.link(button=G.I_BACK_YELLOW, destination=page_main)
page_main.link(button=G.I_MAIN_GOTO_ONMYODO, destination=page_onmyodo)
# 好友 friends
page_friends = Page(G.I_CHECK_FRIENDS, chinese_name='好友')
page_friends.link(button=G.I_BACK_YELLOW, destination=page_main)
page_main.link(button=G.I_MAIN_GOTO_FRIENDS, destination=page_friends)
# 商店 mall
page_mall = Page(check_button=[G.I_CHECK_MALL, G.I_CHECK_MALL_2], chinese_name='商店')
page_mall.additional = [G.I_BACK_RED, G.I_CANCEL]
page_mall.link(button=G.I_BACK_YELLOW, destination=page_main)
page_main.link(button=G.I_MAIN_GOTO_MALL, destination=page_mall)
# 阴阳寮 guild
page_guild = Page(G.I_CHECK_GUILD, chinese_name='阴阳寮')
page_guild.additional = [KekkaiUtilizeAssets.I_PLANT_TREE_CLOSE]
page_guild.link(button=G.I_BACK_YELLOW, destination=page_main)
page_main.link(button=G.I_MAIN_GOTO_GUILD, destination=page_guild)
# 结界
page_realm = Page(G.I_CHECK_REALM_SHIN, chinese_name='结界')
page_realm.additional = [KekkaiUtilizeAssets.I_PLANT_TREE_CLOSE]
page_realm.link(button=G.I_BACK_YELLOW, destination=page_guild)
page_guild.link(button=G.I_CHECK_GUILD, destination=page_realm)
# 组队 team
page_team = Page(G.I_CHECK_TEAM, chinese_name='组队')
page_team.link(button=G.I_BACK_YELLOW, destination=page_main)
page_main.link(button=G.I_MAIN_GOTO_TEAM, destination=page_team)
# 收集 collection
page_collection = Page(G.I_CHECK_COLLECTION, chinese_name='收集')
page_collection.link(button=G.I_BACK_YELLOW, destination=page_main)
page_main.link(button=G.I_MAIN_GOTO_COLLECTION, destination=page_collection)
# 珍旅居
page_travel = Page(G.I_CHECK_TRAVEL, chinese_name='珍旅居')
page_travel.link(button=G.I_BACK_YELLOW, destination=page_main)
page_main.link(button=G.I_MAIN_GOTO_TRAVEL, destination=page_travel)

# 活动总览
page_all_active = Page(G.I_PAGE_ALL_ACTIVE, chinese_name='活动总览')
page_all_active.link(button=G.I_BACK_YELLOW, destination=page_main)
page_main.link(button=G.I_PAGE_MAIN_GOTO_PAGE_ALL_ACTIVE, destination=page_all_active)


