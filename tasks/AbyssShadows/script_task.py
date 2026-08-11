# This Python file uses the following encoding: utf-8
# @brief    Ryou Dokan Toppa (阴阳竂道馆突破功能)
# @author   jackyhwei
# @note     draft version without full test
# github    https://github.com/roarhill/oas

from time import sleep

from cached_property import cached_property
from datetime import datetime
from enum import Enum
from module.base.timer import Timer
from module.exception import TaskEnd
from module.logger import logger
from pathlib import Path
from tasks.AbyssShadows.assets import AbyssShadowsAssets
from tasks.AbyssShadows.config import AbyssShadows
from tasks.AbyssShadows.config import BattleOrder, BattleLevel
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.GameUi.page import page_guild


# 单个敌人最大战斗次数(防止同一敌人无限重试)
MAX_BATTLE_COUNT = 2


class AreaType:
    """ 暗域类型 """
    DRAGON = AbyssShadowsAssets.I_ABYSS_DRAGON  # 神龙暗域
    PEACOCK = AbyssShadowsAssets.I_ABYSS_PEACOCK  # 孔雀暗域
    FOX = AbyssShadowsAssets.I_ABYSS_FOX  # 白藏主暗域
    LEOPARD = AbyssShadowsAssets.I_ABYSS_LEOPARD  # 黑豹暗域

    @cached_property
    def name(self) -> str:
        """

        :return:
        """
        return Path(self.file).stem.upper()

    def __str__(self):
        return self.name

    __repr__ = __str__


class EmemyType(Enum):
    """ 敌人类型 """
    BOSS = 1  # 首领
    GENERAL = 2  # 副将
    ELITE = 3  # 精英


class CilckArea:
    """ 点击区域 """
    GENERAL_1 = AbyssShadowsAssets.C_GENERAL_1_CLICK_AREA
    GENERAL_2 = AbyssShadowsAssets.C_GENERAL_2_CLICK_AREA
    ELITE_1 = AbyssShadowsAssets.C_ELITE_1_CLICK_AREA
    ELITE_2 = AbyssShadowsAssets.C_ELITE_2_CLICK_AREA
    ELITE_3 = AbyssShadowsAssets.C_ELITE_3_CLICK_AREA
    BOSS = AbyssShadowsAssets.C_BOSS_CLICK_AREA

    @cached_property
    def name(self) -> str:
        """

        :return:
        """
        return Path(self.file).stem.upper()

    def __str__(self):
        return self.name

    __repr__ = __str__


class ScriptTask(GeneralBattle, SwitchSoul, AbyssShadowsAssets):
    """ 狭间暗域 """
    boss_fight_count = 0  # 首领战斗次数
    general_fight_count = 0  # 副将战斗次数
    elite_fight_count = 0  # 精英战斗次数
    error_count = 0
    area_fight_count = 0
    goto_count = 0
    each_limit_second = 0
    # =========新增：记录当前区域已经击败的怪物，防止重复点击=========
    killed_targets = set()

    def get_selected_areas(self):
        boss_type_list = []
        cfg: AbyssShadows = self.config.abyss_shadows
        dragon = cfg.abyss_shadows_boss_type.dragon
        peacock = cfg.abyss_shadows_boss_type.peacock
        fox = cfg.abyss_shadows_boss_type.fox
        leopard = cfg.abyss_shadows_boss_type.leopard
        if dragon:
            boss_type_list.append(AreaType.DRAGON)
        if peacock:
            boss_type_list.append(AreaType.PEACOCK)
        if fox:
            boss_type_list.append(AreaType.FOX)
        if leopard:
            boss_type_list.append(AreaType.LEOPARD)
        return boss_type_list

    def run(self):
        """ 狭间暗域主函数

        :return:
        """

        today = datetime.now().weekday()
        if today not in [4, 5, 6]:
            self.push_notify(f"今天不是狭间暗域开放日，退出")
            self.set_next_run(task='AbyssShadows', finish=True, server=True, success=True)
            raise TaskEnd

        cfg: AbyssShadows = self.config.abyss_shadows

        if cfg.elite_switch_soul_config.enable:
            self.run_switch_soul(cfg.elite_switch_soul_config.switch_group_team)
        if cfg.elite_switch_soul_config.enable_switch_by_name:
            self.run_switch_soul_by_name(cfg.elite_switch_soul_config.group_name, cfg.elite_switch_soul_config.team_name)

        if cfg.general_switch_soul_config.enable:
            self.run_switch_soul(cfg.general_switch_soul_config.switch_group_team)
        if cfg.general_switch_soul_config.enable_switch_by_name:
            self.run_switch_soul_by_name(cfg.general_switch_soul_config.group_name, cfg.general_switch_soul_config.team_name)

        if cfg.boss_switch_soul_config.enable:
            self.run_switch_soul(cfg.boss_switch_soul_config.switch_group_team)
        if cfg.boss_switch_soul_config.enable_switch_by_name:
            self.run_switch_soul_by_name(cfg.boss_switch_soul_config.group_name, cfg.boss_switch_soul_config.team_name)

        # 进入狭间
        self.goto_abyss_shadows()

        boss_type_list = self.get_selected_areas()
        logger.info(f"战斗区域列表(按顺序): {boss_type_list}")

        # 循环遍历【每一个区域】：区域1完整打完 → 区域2完整打完 → 区域3完整打完
        while self.area_fight_count < len(boss_type_list):
            target_area = boss_type_list[self.area_fight_count]
            logger.info(f"=====开始处理区域 {target_area.name}=====")
            # 切换至当前目标区域
            while 1:
                if cfg.abyss_shadows_boss_type.open:
                    self.open_abyss_shadows()
                if self.select_boss(target_area):
                    break
                else:
                    self.device.click_record_clear()
                    self.error_count += 1
                    wait_time = 30
                    logger.warning(f"进入{target_area.name}失败, 等待{wait_time}秒")
                    sleep(wait_time)
                    if self.error_count >= 6:
                        self.save_image(content='未能进入狭间暗域区域', wait_time=0, push_flag=True, image_type=True)
                        self.set_next_run(task='AbyssShadows', finish=True, server=True, success=True)
                        raise TaskEnd

            # 等待可进攻
            self.device.stuck_record_add('BATTLE_STATUS_S')
            logger.info(f"{target_area.name} 集结中,等待可进攻时间")
            self.wait_until_appear(self.I_BATTLE_TO_START)
            self.device.stuck_record_clear()

            # 获取配置攻击顺序
            order_mapping = {
                BattleOrder.ELITE_GENERAL_BOSS: [EmemyType.ELITE, EmemyType.GENERAL, EmemyType.BOSS],
                BattleOrder.ELITE_BOSS_GENERAL: [EmemyType.ELITE, EmemyType.BOSS, EmemyType.GENERAL],
                BattleOrder.GENERAL_ELITE_BOSS: [EmemyType.GENERAL, EmemyType.ELITE, EmemyType.BOSS],
                BattleOrder.GENERAL_BOSS_ELITE: [EmemyType.GENERAL, EmemyType.BOSS, EmemyType.ELITE],
                BattleOrder.BOSS_ELITE_GENERAL: [EmemyType.BOSS, EmemyType.ELITE, EmemyType.GENERAL],
                BattleOrder.BOSS_GENERAL_ELITE: [EmemyType.BOSS, EmemyType.GENERAL, EmemyType.ELITE],
            }
            attack_sequence = order_mapping[self.config.abyss_shadows.abyss_shadows_boss_type.attack_order]

            # 【重置当前区域击杀清单和战斗计数器】
            # 每次切换暗域都归零，确保新区域拥有完整的攻击配额
            self.killed_targets.clear()
            self.boss_fight_count = 0
            self.general_fight_count = 0
            self.elite_fight_count = 0
            self.error_count = 0
            # 按顺序击杀当前区域全部敌人
            for enemy_type in attack_sequence:
                self.find_enemy(enemy_type)

            logger.info(f"区域 {target_area.name} 全部怪物遍历完成")
            logger.info(f"击杀统计 - 首领: {self.boss_fight_count}, 副将: {self.general_fight_count}, 精英: {self.elite_fight_count}")

            # 准备下一个区域
            self.area_fight_count += 1
            if self.area_fight_count < len(boss_type_list):
                next_area = boss_type_list[self.area_fight_count]
                self.change_area(next_area)

        # 所有区域全部打完
        logger.info(f"✅ 全部选择区域执行完毕: {boss_type_list}")
        while 1:
            self.screenshot()
            if self.appear(self.I_ABYSS_MAP):
                self.save_image(content='所有区域战斗全部完成', push_flag=True, image_type=True)
                break
            if self.appear_then_click(self.I_ABYSS_NAVIGATION, interval=1):
                continue

        self.next_run()

    def next_run(self):
        today = datetime.today()
        current_weekday = today.weekday()  # 周一为0，周日为6
        next_run_weekday = 5
        if current_weekday == 6:
            msg = f"设置下周{next_run_weekday}执行"
            logger.warning(msg)
            self.next_run_week(next_run_weekday)
            raise TaskEnd
        else:
            self.set_next_run(task='AbyssShadows', finish=True, server=True, success=True)
            raise TaskEnd

    def check_current_area(self):
        """ 获取当前区域
        :return AreaType
        """
        while 1:
            self.screenshot()
            if self.appear(self.I_PEACOCK_AREA):
                return AreaType.PEACOCK
            elif self.appear(self.I_DRAGON_AREA):
                return AreaType.DRAGON
            elif self.appear(self.I_FOX_AREA):
                return AreaType.FOX
            elif self.appear(self.I_LEOPARD_AREA):
                return AreaType.LEOPARD
            else:
                continue

    def change_area(self, area_name: AreaType) -> bool:
        """ 切换到下个区域
        :return
        """
        logger.info(f"切换到 {area_name.name} 区域")
        while 1:
            self.screenshot()
            # 先关闭地图界面，避免遮挡切换区域按钮
            if self.appear(self.I_ABYSS_MAP):
                self.click(self.I_ABYSS_MAP_EXIT, interval=2)
                continue
            # 判断当前区域是否正确
            current_area = self.check_current_area()
            if current_area == area_name:
                logger.info(f"当前区域 {current_area.name} 正确")
                break
            # 切换区域界面
            if self.appear(self.I_ABYSS_DRAGON_OVER):
                self.select_boss(area_name)
                logger.info(f"选择 {area_name.name}")
                continue
            # 点击切换区域按钮
            if self.appear_then_click(self.I_CHANGE_AREA, interval=4):
                continue

        return True

    def goto_abyss_shadows(self) -> bool:
        """ 进入狭间
        :return bool
        """
        logger.info("准备进入狭间暗域")
        self.ui_goto_page(page_guild)

        while 1:
            self.screenshot()
            # 进入神社
            if self.appear_then_click(self.I_RYOU_SHENSHE, interval=1):
                logger.info("进入神社")
                continue
            # 查找狭间
            if not self.appear(self.I_ABYSS_SHADOWS, threshold=0.8):
                self.swipe(self.S_TO_ABBSY_SHADOWS, interval=3)
                continue
            # 进入狭间
            if self.appear(self.I_ABYSS_SHADOWS):
                logger.info("识别到寮-狭间暗域")
                break
        while 1:
            self.screenshot()
            if self.appear_then_click(self.I_ABYSS_SHADOWS):
                logger.info("点击进入狭间暗域")
                continue
            if self.appear(self.I_ABYSS_SHADOWS_SURE):
                logger.info("已经在狭间暗域主界面")
                return True

    def open_abyss_shadows(self) -> bool:
        logger.info("准备开启狭间")
        if not self.appear(self.I_OPEN_ABYSS_SHADOWS, interval=1):
            logger.info("未找到开启狭间入口, 说明狭间已开启")
            return True

        # 根据配置选择难度
        cfg: AbyssShadows = self.config.abyss_shadows
        battle_level = cfg.abyss_shadows_boss_type.battle_level
        level_map = {
            BattleLevel.EASY: (self.I_BATTLE_LEVEL_EASY, self.I_BATTLE_LEVEL_EASY_SURE),
            BattleLevel.NORMAL: (self.I_BATTLE_LEVEL_NORMAL, self.I_BATTLE_LEVEL_NORMAL_SURE),
            BattleLevel.HARD: (self.I_BATTLE_LEVEL_HARD, self.I_BATTLE_LEVEL_HARD_SURE),
        }
        level_img, level_sure_img = level_map[battle_level]
        logger.info(f"选择难度: {battle_level.value}")

        while 1:
            self.screenshot()
            if self.appear(level_sure_img, interval=1):
                break
            if self.appear_then_click(level_img, interval=1):
                continue
            if self.appear_then_click(self.I_CHANGE_BATTLE_LEVEL, interval=1):
                continue
        while 1:
            self.screenshot()
            if self.appear_then_click(self.I_OPEN_ABYSS_SHADOWS, interval=1):
                continue
            if self.appear(self.I_UI_SURE, interval=1):
                self.ui_click_until_disappear(self.I_UI_SURE)
                break

    def select_boss(self, area_name: AreaType) -> bool:
        """ 选择暗域类型
        :return
        """
        logger.info(f"开始选择暗域类型: {area_name.name}")
        click_times = 0
        while 1:
            self.screenshot()
            # 区域图片与入口图片不一致，使用点击进去

            if self.appear(self.I_ABYSS_DRAGON_OVER) or self.appear(self.I_ABYSS_DRAGON):
                match area_name:
                    case AreaType.DRAGON:
                        is_click = self.click(self.C_ABYSS_DRAGON, interval=2)
                    case AreaType.PEACOCK:
                        is_click = self.click(self.C_ABYSS_PEACOCK, interval=2)
                    case AreaType.FOX:
                        is_click = self.click(self.C_ABYSS_FOX, interval=2)
                    case AreaType.LEOPARD:
                        is_click = self.click(self.C_ABYSS_LEOPARD, interval=2)
                if is_click:
                    click_times += 1
                    logger.info(f"点击区域 {area_name.name} {click_times} 次")
                if click_times >= 3:
                    logger.info(f"选择首领: {area_name.name} 失败")
                    return False
                continue
            if self.appear(self.I_ABYSS_NAVIGATION):
                break
        return True

    def find_enemy(self, enemy_type: EmemyType) -> bool:
        """ 寻找敌人,并开始寻路进入战斗
        :return 是否找到敌人，若目标已死亡则返回False，否则返回True
        True 找到敌人，并已经战斗完成
        """
        logger.info(f"寻找敌人类型: {enemy_type.name}")
        while 1:
            self.screenshot()
            # 点击战报按钮
            if self.appear(self.I_ABYSS_MAP):
                break
            if self.appear_then_click(self.I_ABYSS_NAVIGATION, interval=1):
                continue

        match enemy_type:
            case EmemyType.BOSS:
                success = self.run_boss_fight()
            case EmemyType.GENERAL:
                success = self.run_general_fight()
            case EmemyType.ELITE:
                success = self.run_elite_fight()
            case _:
                success = False
        return success

    def run_boss_fight(self) -> bool:
        """ 首领战斗  """
        cfg: AbyssShadows = self.config.abyss_shadows
        # 顺位寮模式: 每个boss只攻击一次; 非顺位寮模式: 咬到死(MAX_BATTLE_COUNT次)
        max_count = 1 if cfg.abyss_shadows_boss_type.sequential_mode else MAX_BATTLE_COUNT
        target = CilckArea.BOSS
        # 已确认击杀直接跳过
        if target in self.killed_targets:
            logger.info(f"{target.name} 已击杀，跳过")
            return True

        success = False
        # 咬到死模式: 循环攻击直到怪物死亡或次数上限
        while self.boss_fight_count < max_count:
            if self.click_emeny_area(target):
                success = True
                logger.info(f"攻击首领 {target.name} 第 {self.boss_fight_count + 1}/{max_count} 次")
                self.battle_fight("boss")
                self.boss_fight_count += 1
                # 顺位寮模式：打一次就标记已击杀，不再重试
                if cfg.abyss_shadows_boss_type.sequential_mode:
                    self.killed_targets.add(target)
                    break
                # 咬到死模式：不标记击杀，继续循环尝试下一次攻击
            else:
                logger.warning(f"{target.name} 无法挑战，判定已被击杀")
                self.killed_targets.add(target)
                while 1:
                    self.screenshot()
                    if not self.appear(self.I_ABYSS_MAP):
                        break
                    self.appear_then_click(self.I_BACK_RED, interval=1)
                break

        if success:
            logger.info(f'首领战斗完成，已攻击 {self.boss_fight_count} 次')
        return success

    def run_general_fight(self) -> bool:
        """ 副将战斗  """
        cfg: AbyssShadows = self.config.abyss_shadows
        # 顺位寮模式: 每个敌人只攻击一次; 非顺位寮模式: 咬到死(MAX_BATTLE_COUNT次)
        max_count = 1 if cfg.abyss_shadows_boss_type.sequential_mode else MAX_BATTLE_COUNT
        general_list = [CilckArea.GENERAL_2, CilckArea.GENERAL_1]
        logger.info(f"开始副将战斗{'(顺位寮模式)' if cfg.abyss_shadows_boss_type.sequential_mode else '(咬到死模式)'}")
        for general in general_list:
            # 已确认击杀直接跳过
            if general in self.killed_targets:
                logger.info(f"{general.name} 已击杀，跳过")
                continue

            attempts = 0
            # 咬到死模式: 循环攻击同一只副将直到死亡或次数上限
            while attempts < max_count:
                if self.click_emeny_area(general):
                    attempts += 1
                    logger.info(f"攻击副将 {general.name} 第 {attempts}/{max_count} 次")
                    self.battle_fight("general")
                    self.general_fight_count += 1
                    # 顺位寮模式：打一次就标记已击杀，不再重试
                    if cfg.abyss_shadows_boss_type.sequential_mode:
                        self.killed_targets.add(general)
                        break
                    # 咬到死模式：不标记击杀，继续循环尝试下一次攻击
                else:
                    logger.warning(f"{general.name} 无法挑战，判定已击杀")
                    self.killed_targets.add(general)
                    break
        return True

    def run_elite_fight(self) -> bool:
        """ 精英战斗  """
        cfg: AbyssShadows = self.config.abyss_shadows
        # 顺位寮模式: 每个敌人只攻击一次; 非顺位寮模式: 咬到死(MAX_BATTLE_COUNT次)
        max_count = 1 if cfg.abyss_shadows_boss_type.sequential_mode else MAX_BATTLE_COUNT
        elite_list = [CilckArea.ELITE_1, CilckArea.ELITE_2, CilckArea.ELITE_3]
        logger.info(f"开始精英战斗{'(顺位寮模式)' if cfg.abyss_shadows_boss_type.sequential_mode else '(咬到死模式)'}")
        for elite in elite_list:
            # 已确认击杀直接跳过
            if elite in self.killed_targets:
                logger.info(f"{elite.name} 已击杀，跳过")
                continue

            attempts = 0
            # 咬到死模式: 循环攻击同一只精英直到死亡或次数上限
            while attempts < max_count:
                if self.click_emeny_area(elite):
                    attempts += 1
                    logger.info(f"攻击精英 {elite.name} 第 {attempts}/{max_count} 次")
                    self.battle_fight("elite")
                    self.elite_fight_count += 1
                    # 顺位寮模式：打一次就标记已击杀，不再重试
                    if cfg.abyss_shadows_boss_type.sequential_mode:
                        self.killed_targets.add(elite)
                        break
                    # 咬到死模式：不标记击杀，继续循环尝试下一次攻击
                else:
                    logger.warning(f"{elite.name} 无法挑战，判定已击杀")
                    self.killed_targets.add(elite)
                    break
        return True

    def goto_fire(self, click_area: CilckArea):
        logger.info(f"开始前往 战斗地点: {click_area.name}")
        timer = Timer(15)
        timer.start()

        # 点击战报进入地图界面
        while 1:
            if timer.reached():
                logger.info(f"前往战斗地点 {click_area.name} 超时，返回重试")
                return "重试"
            self.screenshot()
            if self.appear_then_click(self.I_ABYSS_NAVIGATION, interval=1.5):
                logger.info(f"点击战报")
                continue
            if self.appear(self.I_ABYSS_MAP):
                logger.info(f"找到狭间地图，退出")
                break

        # 点击攻打区域
        click_times = 0
        while 1:
            if timer.reached():
                logger.info(f"前往战斗地点 {click_area.name} 超时，返回重试")
                return "重试"
            self.screenshot()
            # =========核心修复：连续2次点击无法打开 → 判断怪物已击杀，返回False=========
            if click_times >= 2:
                logger.warning(f"多次点击未进入 {click_area.name},怪物已击破，跳过")
                return False
            # 出现前往按钮就退出
            if self.appear(self.I_ABYSS_GOTO_ENEMY):
                break
            if self.appear(self.I_ABYSS_FIRE):
                break
            if self.click(click_area, interval=1.5):
                click_times += 1
                continue
            if self.appear_then_click(self.I_UI_SURE, interval=1):
                continue
        # 点击前往按钮
        while 1:
            if timer.reached():
                logger.info(f"前往战斗地点 {click_area.name} 超时，返回重试")
                return "重试"
            self.screenshot()
            if self.appear_then_click(self.I_ABYSS_GOTO_ENEMY, interval=1):
                logger.info(f"点击前往按钮")
                # 点击敌人后，如果是不同区域会确认框，点击确认
                if self.appear_then_click(self.I_UI_SURE, interval=1):
                    logger.info(f"点击确认框")

                sleep(3)  # 跑动画比较花时间
                continue
            if self.appear(self.I_ABYSS_FIRE):
                break

        return True

    def click_emeny_area(self, click_area: CilckArea) -> bool:
        """ 点击敌人区域  """
        self.goto_count = 0
        while self.goto_count < 3:
            result = self.goto_fire(click_area)
            logger.info(f"前往战斗地点 {click_area.name} 结果: {result}")
            if not result:
                return False
            if result == "重试":
                self.goto_count += 1
            else:
                break
        else:
            logger.info(f"前往战斗地点 {click_area.name} 超出最大重试次数仍未成功")
            return False

        # 点击战斗按钮
        self.wait_until_appear(self.I_ABYSS_FIRE)
        while 1:
            self.screenshot()
            if self.appear_then_click(self.I_ABYSS_FIRE, interval=1):
                logger.info(f"点击挑战按钮")
                # 挑战敌人后，如果是奖励次数上限，会出现确认框
                self.appear_then_click(self.I_UI_SURE, interval=1)
                continue
            if self.appear(self.I_PREPARE_HIGHLIGHT):
                break

        return True

    def battle_fight(self, battle_type) -> bool:
        """
        狭间暗域的准备和战斗
        """
        logger.hr(f"准备战斗", 2)
        cfg: AbyssShadows = self.config.abyss_shadows

        if battle_type == "elite":
            # 每场战斗限制秒数
            config = cfg.elite_general_battle_config
            self.each_limit_second = cfg.battle_limit_second.elite_limit_second
        elif battle_type == "general":
            config = cfg.general_general_battle_config
            self.each_limit_second = cfg.battle_limit_second.general_limit_second
        elif battle_type == "boss":
            config = cfg.boss_general_battle_config
            self.each_limit_second = cfg.battle_limit_second.boss_limit_second
        else:
            self.each_limit_second = 0

        run_timer = Timer(self.each_limit_second)
        if self.each_limit_second > 0:
            run_timer.start()

        # 切换预设的队伍上阵， 要求是在不锁定队伍时的情况下
        self.switch_preset_team(config.preset_enable, config.preset_group, config.preset_team)
        logger.info(f"开始战斗")
        self.current_count += 1
        logger.info(f'当前次数: {self.current_count}')
        while 1:
            self.screenshot()
            if run_timer.started() and run_timer.reached():
                logger.info(f'已到本场战斗时间{self.each_limit_second}秒, 退出')
                self.exit_battle()
                run_timer.reset()
                continue
            if self.appear_then_click(self.I_PREPARE_HIGHLIGHT, interval=1):
                self.device.stuck_record_add('BATTLE_STATUS_S')
                continue
            if self.appear_then_click(self.I_WIN, interval=1):
                continue
            if self.appear_then_click(self.I_REWARD, interval=1):
                continue
            if self.appear(self.I_ABYSS_NAVIGATION):
                return True


if __name__ == "__main__":
    from module.config.config import Config

    config = Config('du')
    t = ScriptTask(config)
    t.run()

    # t.battle_fight()