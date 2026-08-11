# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

from time import sleep

import inflection
import re

from module.config.utils import *
from module.logger import logger
from pathlib import Path
from pydantic import BaseModel, ValidationError, Field
# 导入配置的Python文件
from tasks.Component.config_base import ConfigBase, TimeDelta
# 这一部分是活动的配置-----------------------------------------------------------------------------------------------------
from tasks.AbyssShadows.config import AbyssShadows
from tasks.ActivityCommon.config import ActivityCommon
from tasks.ActivityCommon2.config import ActivityCommon2
from tasks.ActivitySimple.config import ActivitySimple
from tasks.AreaBoss.config import AreaBoss
from tasks.AutoCake.config import AutoCake
# 肝帝专属---------------------------------------------------------------------------------------------------------------
from tasks.BondlingFairyland.config import BondlingFairyland
from tasks.Chess.config import Chess
from tasks.CollectiveMissions.config import CollectiveMissions
# 每日任务-----------------------------------------------------------------------------------------------------
from tasks.DailyTrifles.config import DailyTrifles
from tasks.Delegation.config import Delegation
from tasks.DemonEncounter.config import DemonEncounter
from tasks.DemonRetreat.config import DemonRetreat
from tasks.Dokan.config import Dokan
from tasks.Duel.config import Duel
from tasks.EternitySea.config import EternitySea
from tasks.EvoZone.config import EvoZone
from tasks.ExperienceYoukai.config import ExperienceYoukai
from tasks.Exploration.config import Exploration
from tasks.FallenSun.config import FallenSun
from tasks.FloatParade.config import FloatParade
from tasks.FrogBoss.config import FrogBoss
from tasks.GlobalGame.config import GlobalGame
from tasks.GoldYoukai.config import GoldYoukai
from tasks.GoryouRealm.config import GoryouRealm
from tasks.GuildBanquet.config import GuildBanquet
from tasks.HeroTest.config import HeroTest
from tasks.Hunt.config import Hunt
from tasks.Hyakkiyakou.config import Hyakkiyakou
from tasks.KekkaiActivation.config import KekkaiActivation
from tasks.KekkaiUtilize.config import KekkaiUtilize
from tasks.KittyShop.config import KittyShop
from tasks.LBS.config import LBS
from tasks.MainStory.config import MainStory
from tasks.MemoryScrolls.config import MemoryScrolls
from tasks.MetaDemon.config import MetaDemon
from tasks.MysteryShop.config import MysteryShop
from tasks.Nian.config import Nian
from tasks.NianTrue.config import NianTrue
# 阴阳寮----------------------------------------------------------------------------------------------------------------------
from tasks.Orochi.config import Orochi
from tasks.Pets.config import Pets
from tasks.Quiz.config import Quiz
from tasks.RealmRaid.config import RealmRaid
from tasks.Restart.config import Restart
from tasks.RichMan.config import RichMan
from tasks.RyouToppa.config import RyouToppa
from tasks.Script.config import Script
from tasks.Secret.config import Secret
from tasks.SixRealms.config import SixRealms
from tasks.Sougenbi.config import Sougenbi
from tasks.SoulsTidy.config import SoulsTidy
from tasks.SwitchAccountConfig.config import SwitchAccountConfig
from tasks.SwitchAccountLoop.config import SwitchAccountLoop
from tasks.SwitchAccountOnce.config import SwitchAccountOnce
from tasks.SwitchAccountMany.config import SwitchAccountMany
from tasks.Tako.config import Tako
from tasks.TalismanPass.config import TalismanPass
# 每周任务---------------------------------------------------------------------------------------------------------------
from tasks.TrueOrochi.config import TrueOrochi
from tasks.WantedQuests.config import WantedQuests
from tasks.WeeklyTrifles.config import WeeklyTrifles
from tasks.Netherworld.config import Netherworld
# ----------------------------------------------------------------------------------------------------------------------


class ConfigModel(ConfigBase):
    config_name: str = "yys"
    running_task: str = ""

    script: Script = Field(default_factory=Script)
    restart: Restart = Field(default_factory=Restart)
    global_game: GlobalGame = Field(default_factory=GlobalGame)

    # 这些是每日任务的
    area_boss: AreaBoss = Field(default_factory=AreaBoss)
    experience_youkai: ExperienceYoukai = Field(default_factory=ExperienceYoukai)
    gold_youkai: GoldYoukai = Field(default_factory=GoldYoukai)
    nian: Nian = Field(default_factory=Nian)
    realm_raid: RealmRaid = Field(default_factory=RealmRaid)
    ryou_toppa: RyouToppa = Field(default_factory=RyouToppa)
    kekkai_utilize: KekkaiUtilize = Field(default_factory=KekkaiUtilize)
    kekkai_activation: KekkaiActivation = Field(default_factory=KekkaiActivation)
    demon_encounter: DemonEncounter = Field(default_factory=DemonEncounter)
    daily_trifles: DailyTrifles = Field(default_factory=DailyTrifles)
    talisman_pass: TalismanPass = Field(default_factory=TalismanPass)
    pets: Pets = Field(default_factory=Pets)
    souls_tidy: SoulsTidy = Field(default_factory=SoulsTidy)
    delegation: Delegation = Field(default_factory=Delegation)
    exploration: Exploration = Field(default_factory=Exploration)
    wanted_quests: WantedQuests = Field(default_factory=WantedQuests)
    tako: Tako = Field(default_factory=Tako)

    # 这些是刷御魂的
    orochi: Orochi = Field(default_factory=Orochi)
    sougenbi: Sougenbi = Field(default_factory=Sougenbi)
    fallen_sun: FallenSun = Field(default_factory=FallenSun)
    eternity_sea: EternitySea = Field(default_factory=EternitySea)
    six_realms: SixRealms = Field(default_factory=SixRealms)

    # 这些是活动的
    activity_simple: ActivitySimple = Field(default_factory=ActivitySimple)
    activity_common: ActivityCommon = Field(default_factory=ActivityCommon)
    activity_common_2: ActivityCommon2 = Field(default_factory=ActivityCommon2)
    auto_cake: AutoCake = Field(default_factory=AutoCake)
    meta_demon: MetaDemon = Field(default_factory=MetaDemon)
    frog_boss: FrogBoss = Field(default_factory=FrogBoss)
    float_parade: FloatParade = Field(default_factory=FloatParade)
    quiz: Quiz = Field(default_factory=Quiz)
    kitty_shop: KittyShop = Field(default_factory=KittyShop)
    nian_true: NianTrue = Field(default_factory=NianTrue)
    main_story: MainStory = Field(default_factory=MainStory)
    lbs: LBS = Field(default_factory=LBS)
    switch_account_config: SwitchAccountConfig = Field(default_factory=SwitchAccountConfig)
    switch_account_once: SwitchAccountOnce = Field(default_factory=SwitchAccountOnce)
    switch_account_many: SwitchAccountMany = Field(default_factory=SwitchAccountMany)
    switch_account_loop: SwitchAccountLoop = Field(default_factory=SwitchAccountLoop)

    # 这些是肝帝专属
    bondling_fairyland: BondlingFairyland = Field(default_factory=BondlingFairyland)
    evo_zone: EvoZone = Field(default_factory=EvoZone)
    goryou_realm: GoryouRealm = Field(default_factory=GoryouRealm)
    hyakkiyakou: Hyakkiyakou = Field(default_factory=Hyakkiyakou)
    chess: Chess = Field(default_factory=Chess)
    hero_test: HeroTest = Field(default_factory=HeroTest)
    memory_scrolls: MemoryScrolls = Field(default_factory=MemoryScrolls)

    # 这些是每周任务
    true_orochi: TrueOrochi = Field(default_factory=TrueOrochi)
    rich_man: RichMan = Field(default_factory=RichMan)
    secret: Secret = Field(default_factory=Secret)
    weekly_trifles: WeeklyTrifles = Field(default_factory=WeeklyTrifles)
    mystery_shop: MysteryShop = Field(default_factory=MysteryShop)
    duel: Duel = Field(default_factory=Duel)
    netherworld: Netherworld = Field(default_factory=Netherworld)

    # 阴阳寮
    collective_missions: CollectiveMissions = Field(default_factory=CollectiveMissions)
    hunt: Hunt = Field(default_factory=Hunt)
    dokan: Dokan = Field(default_factory=Dokan)
    abyss_shadows: AbyssShadows = Field(default_factory=AbyssShadows)
    demon_retreat: DemonRetreat = Field(default_factory=DemonRetreat)
    guild_banquet: GuildBanquet = Field(default_factory=GuildBanquet)

    # @validator('script')
    # def script_validator(cls, v):
    #     if v is None:
    #         return Script()

    def __init__(self, config_name: str=None) -> None:
        """

        :param config_name:
        """
        if not config_name:
            super().__init__()
            return
        if config_name == "template":
            logger.warning(f"排除{config_name}模板")
            return

        data = self.read_json(config_name)
        data["config_name"] = config_name

        # 首先尝试直接初始化模型
        try:
            super().__init__(**data)
        except ValidationError as e:
            logger.warning(f"[{config_name}] 配置模型初始化失败: {e}")
            try:
                from module.config.config_validator import _fix_by_model_field_type
                # 尝试使用模型类型信息进行更精确的修复
                data = _fix_by_model_field_type(config_name, data, self.__class__)
                
                logger.info(f"[{config_name}] 配置数据已修复，正在保存到文件...")
                self.write_json(config_name, data)
                    
                # 用修复后的数据重新初始化
                super().__init__(**data)
            except ImportError:
                # 如果导入失败，跳过修复
                logger.warning("无法导入配置修复函数，跳过配置修复步骤")
                raise  # 重新抛出原始异常
            except Exception as fix_e:
                logger.error(f"修复配置数据时发生错误: {fix_e}")
                raise  # 重新抛出原始异常
        
    def __setattr__(self, key, value):
        """
        只要修改属性就会触发这个函数 自动保存
        :param key:
        :param value:
        :return:
        """
        super().__setattr__(key, value)
        # logger.info(f"auto save config `{key}` to {value}")
        self.save()

    @staticmethod
    def read_json(config_name: str) -> dict:
        """
        读文件 没有额外操作
        :param config_name:  不带后缀
        :return:
        """
        filepath = Path.cwd() / "config" / f"{config_name}.json"
        return read_file(filepath)

    @staticmethod
    def write_json(config_name: str, data) -> None:
        """

        :param config_name: 不带后缀
        :param data:  字典而不是字符串
        :return:
        """
        filepath = Path.cwd() / "config" / f"{config_name}.json"

        max_retries = 3
        retry_delay = 1
        for attempt in range(max_retries):
            try:
                write_file(filepath, data)
                return
            except PermissionError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"保存配置文件权限被拒绝，{retry_delay}秒后重试 (第{attempt + 1}次): {e}")
                    sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
                else:
                    logger.error(f"保存配置文件失败，已重试{max_retries}次仍无法访问: {e}")
                    raise
            except Exception as e:
                logger.error(f"保存配置文件时发生未知错误: {e}")
                raise

    def gui_args(self, task: str) -> str:
        """
        返回提供给gui显示的参数
        :param task: 输入的是任务的名称英文 如'Script' 或者是'script'都是可以的
        :return: 返回的是pydantic给我们结构化的输出的信息, 如果不能获取就返回空的str
        """
        task = convert_to_underscore(task)
        task_gui = getattr(self, task, None)
        if task_gui is None:
            logger.warning(f'{task} is no inexistence')
            return ''

        schema2 = task_gui.schema()
        # https://github.com/pydantic/pydantic/discussions/5687
        if 'definitions' in schema2:
            if 'Scheduler' in schema2['definitions']:
                if 'properties' in schema2['definitions']['Scheduler']:
                    properties = schema2['definitions']['Scheduler']['properties']
                    if 'success_interval' in properties:
                        properties['success_interval']['type'] = 'string'
                    if 'failure_interval' in properties:
                        properties['failure_interval']['type'] = 'string'
        return json.dumps(schema2)

    def gui_task(self, task: str) -> str:
        """
        返回提供给gui显示的参数
        :param task:
        :return:
        """
        task_name = convert_to_underscore(task)
        task = getattr(self, task_name, None)
        if task is None:
            logger.warning(f'{task_name} is no inexistence')
            return ''
        return task.json()

    def save(self) -> None:
        """
        :return:
        """
        self.write_json(self.config_name, self.dict())

    @staticmethod
    def type(key: str) -> str:
        """
        输入模型的键值，获取这个字段对象的类型 比如输入是orochi输出是Orochi
        :param key:
        :return:
        """
        field_type: str = str(ConfigModel.__annotations__[key])
        # return field_type
        if '.' in field_type:
            classname = field_type.split('.')[-1][:-2]
            return classname
        else:
            classname = re.findall(r"'([^']*)'", field_type)[0]
            return classname

    # @root_validator
    # def on_on_property_change(cls, values):
    #     """
    #     当属性改变时保存
    #     :param values:
    #     :return:
    #     """
    #     logger.info(f'property change auto save')
    #     cls.save()

    @staticmethod
    def deep_get(obj, keys: str, default=None):
        """
        递归获取模型的值
        :param obj:
        :param keys:
        :param default:
        :return:
        """
        if not isinstance(keys, list):
            keys = keys.split('.')
        value = obj
        try:
            for key in keys:
                value = getattr(value, key)
        except AttributeError:
            return default
        return value

    @staticmethod
    def deep_set(obj, keys: str, value) -> bool:
        if not isinstance(keys, list):
            keys = keys.split('.')
        current_obj = obj
        try:
            for key in keys[:-1]:
                current_obj = getattr(current_obj, key)
            setattr(current_obj, keys[-1], value)
            return True
        except (AttributeError, KeyError):
            return False

    # ----------------------------------- fastapi -----------------------------------
    def script_task(self, task: str) -> dict:
        """
        配置返回前端OASX
        :param task: 同gui_args函数
        :return:
        """
        task = convert_to_underscore(task)
        task = getattr(self, task, None)
        if task is None:
            logger.warning(f'{task} is no inexistence')
            return {}

        def properties_groups(sch) -> dict:
            properties = {}
            for key, value in sch["properties"].items():
                if value.get("hidden") is True:
                    continue
                # 处理有 $ref 的字段（嵌套的 Config）
                if '$ref' in value:
                    properties[key] = re.search(r"/([^/]+)$", value['$ref']).group(1)
                elif 'allOf' in value and len(value['allOf']) > 0 and '$ref' in value['allOf'][0]:
                    # 处理 allOf 形式的引用
                    properties[key] = re.search(r"/([^/]+)$", value['allOf'][0]['$ref']).group(1)
            return properties

        def extract_groups(sch):
            # 从schema 中提取未解析的group的数据
            properties = properties_groups(sch)

            result = {}
            for key, value in properties.items():
                # value 是一个字符串（引用名称），不是字典，所以不能使用 get 方法
                # 需要检查定义本身是否有隐藏属性
                if value in sch["definitions"]:
                    definition = sch["definitions"][value]
                    # 检查定义的 properties 中是否有 hidden 属性
                    if "properties" in definition:
                        visible_properties = {}
                        for prop_key, prop_value in definition["properties"].items():
                            if prop_value.get("hidden") is not True:
                                visible_properties[prop_key] = prop_value
                        if visible_properties:  # 只有当还有可见属性时才添加
                            result[key] = {**definition, "properties": visible_properties}
                    else:
                        # 如果定义中没有 properties，直接添加
                        result[key] = definition
            return result

        def merge_value(groups, jsons, definitions) -> list[dict]:
            # 将 groups的参数，同导出的json一起合并, 用于前端显示
            result = []
            for key, value in groups["properties"].items():
                item = {}
                item["name"] = key
                if value.get("hidden") is True:
                    continue

                # 检查 title 是否是 Pydantic 自动生成的
                underscore_key = inflection.underscore(key)
                auto_generated_title = inflection.titleize(underscore_key)
                field_title = value.get("title", auto_generated_title)

                # 如果是自动生成的 title，使用下划线格式的字段名
                item["title"] = underscore_key if field_title == auto_generated_title else field_title

                if "description" in value:
                    item["description"] = value["description"]
                item["default"] = value["default"]
                item["value"] = jsons[key] if key in jsons else value["default"]
                item["type"] = value["type"] if "type" in value else "enum"
                if "headline" in value:
                    item["headline"] = value["headline"]
                if value.get("dynamic_options") == "script_files":
                    # 配置文件会动态增删，不能在 Pydantic Enum 中写死。
                    # 空字符串表示尚未选择队友；同时排除当前配置自身。
                    from module.server.config_manager import ConfigManager
                    current_name = self.config_name.casefold()
                    options = [
                        name for name in ConfigManager.all_script_files()
                        if name.casefold() != current_name
                    ]
                    item["type"] = "enum"
                    item["enumEnum"] = [""] + options
                if 'allOf' in value:
                    # list
                    enum_key = re.search(r"/([^/]+)$", value['allOf'][0]['$ref']).group(1)
                    item["enumEnum"] = definitions[enum_key]["enum"]
                # TODO: 最大值最小值
                result.append(item)
            return result

        schema = task.schema()
        groups = extract_groups(schema)

        result: dict[str, list] = {}
        task_dict = task.dict()
        # 过滤掉隐藏的键
        filtered_task_dict = {}
        for key, value in task_dict.items():
            # 检查这个key是否在原始schema的properties中，并且是否有hidden标记
            if key in schema["properties"] and schema["properties"][key].get("hidden") is True:
                continue  # 跳过隐藏的键
            if key in groups:  # 只处理在groups中存在的键
                filtered_task_dict[key] = value

        for key, value in filtered_task_dict.items():
            result[key] = merge_value(groups[key], value, schema["definitions"])

        return result

    def script_set_arg(self, task: str, group: str, argument: str, value) -> bool:
        # 验证参数
        task = convert_to_underscore(task)
        group = convert_to_underscore(group)
        argument = convert_to_underscore(argument)

        # pandtic验证
        if isinstance(value, str) and len(value) == 8:
            try:
                value = datetime.strptime(value, '%H:%M:%S').time()
            except ValueError:
                pass
        if isinstance(value, str) and len(value) == 11:
            try:
                date_time = datetime.strptime(value, '%d %H:%M:%S')
                value = TimeDelta(days=date_time.day, hours=date_time.hour, minutes=date_time.minute, seconds=date_time.second)
            except ValueError:
                pass
        if isinstance(value, str) and len(value) == 19:
            try:
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
        if isinstance(value, str) and value == 'true':
            value = True
        if isinstance(value, str) and value == 'false':
            value = False

        task_object = getattr(self, task, None)
        group_object = getattr(task_object, group, None)
        argument_object = getattr(group_object, argument, None)
        # print(group_object)
        # print(argument_object)

        if argument_object is None:
            logger.error(f'Set arg {task}.{group}.{argument}.{value} failed')
            return False

        # 设置参数
        try:
            setattr(group_object, argument, value)
            logger.info(f'Set arg {self.config_name}.{task}.{group}.{argument}.{value}')
            self.save()  # 我是没有想到什么方法可以使得属性改变自动保存的
            return True
        except ValidationError as e:
            logger.error(e)
            return False

    def copy_script_task(self, task_name: str, source_task: BaseModel) -> bool:
        model_task_name = convert_to_underscore(task_name)
        try:
            setattr(self, model_task_name, source_task)
            self.save()
            logger.info(f'Copy task {model_task_name} success')
            return True
        except ValidationError as e:
            logger.error(e)
            return False

    def copy_task_group(self, task_name: str, group_name: str, source_task: BaseModel) -> bool:
        model_task_name = convert_to_underscore(task_name)
        model_group_name = convert_to_underscore(group_name)
        task_object = getattr(self, model_task_name, None)
        if not task_object:
            return False
        source_group_obj = getattr(source_task, model_group_name, None)
        if not source_group_obj:
            return False
        try:
            setattr(task_object, model_group_name, source_group_obj)
            self.save()
            logger.info(f'复制配置组 {model_task_name}.{model_group_name} 成功')
            return True
        except ValidationError as e:
            logger.error(e)
            return False


if __name__ == "__main__":
    try:
        c = ConfigModel("4399")
    except ValidationError as e:
        print(e)
        c = ConfigModel()

    c.save()
    print(c.script_task('Duel'))
