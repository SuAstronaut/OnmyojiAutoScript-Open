# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time

import numpy as np
import random
from cached_property import cached_property
from datetime import timedelta, datetime
from enum import Enum
from module.atom.click import RuleClick
from module.exception import TaskEnd
from module.logger import logger
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.GeneralInvite.general_invite import GeneralInvite
from tasks.Component.GeneralRoom.general_room import GeneralRoom
from tasks.Component.ReplaceShikigami.replace_shikigami import ReplaceShikigami
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.Exploration.assets import ExplorationAssets
from tasks.Exploration.config import ChooseRarity, UpType
from tasks.Exploration.config import ExplorationLevel
from tasks.GameUi.page import page_exploration, page_main
from tasks.Restart.assets import RestartAssets
from tasks.Utils.config_enum import ShikigamiClass
from tasks.Component.GeneralBuff.config_buff import BuffClass


class Scene(Enum):
    UNKNOWN = 0  #
    WORLD = 1  # 探索大世界
    ENTRANCE = 2  # 入口弹窗
    MAIN = 3  # 探索里面
    BATTLE_PREPARE = 4  # 战斗准备
    BATTLE_FIGHTING = 5  # 战斗中
    TEAM = 6  # 组队


class BaseExploration(GeneralBattle, GeneralRoom, GeneralInvite, ReplaceShikigami, SwitchSoul, ExplorationAssets):
    last_scene_log = None  # 新增：用于缓存上一次的日志内容
    current_boss_cnt = 0
    min_boss_cnt = 0

    def __init__(self, config):
        super().__init__(config)

    @cached_property
    def _config(self):
        # self.config.exploration.general_battle_config.lock_team_enable = True
        limit_time = self.config.exploration.exploration_config.limit_time
        self.limit_time: timedelta = timedelta(
            hours=limit_time.hour,
            minutes=limit_time.minute,
            seconds=limit_time.second
        )
        return self.config.model.exploration

    def get_current_scene(self, reuse_screenshot: bool = True) -> Scene:
        if not reuse_screenshot:
            self.screenshot()

        # 初始化 scene 变量
        scene = Scene.UNKNOWN
        if self.appear(self.I_E_EXPLORATION_CLICK):
            scene = Scene.ENTRANCE
            log_message = "在探索入口弹窗中"
        elif self.appear([self.I_E_SETTINGS_BUTTON, self.I_E_AUTO_ROTATE_ON, self.I_E_AUTO_ROTATE_OFF, self.I_LOCK_ON, self.I_LOCK_OFF]):
            scene = Scene.MAIN
            log_message = "在探索里面"
        elif self.is_in_prepare():
            scene = Scene.BATTLE_PREPARE
            log_message = "在战斗准备"
        elif self.is_in_battle():
            scene = Scene.BATTLE_FIGHTING
            log_message = "在战斗中"
        elif self.is_in_room() or self.appear(self.I_CREATE_ENSURE):
            scene = Scene.TEAM
            log_message = "在组队界面中"
        elif self.appear(self.I_CHECK_EXPLORATION) and not self.appear([self.I_E_SETTINGS_BUTTON, self.I_E_AUTO_ROTATE_ON, self.I_E_AUTO_ROTATE_OFF]):
            scene = Scene.WORLD
            log_message = "在探索大世界中"
        elif self.appear([RestartAssets.I_LOGIN_SCROOLL_OPEN, RestartAssets.I_LOGIN_SCROOLL_CLOSE]):
            scene = Scene.UNKNOWN
            log_message = "在庭院中"
            # 探索页面
            self.ui_goto_page(page_exploration)
        else:
            log_message = "未知场景"

        # 新增：判断日志是否重复，避免重复打印
        if log_message != self.last_scene_log:
            logger.info(f"当前场景: {log_message}")
            self.last_scene_log = log_message

        return scene

    def pre_process(self):
        explorationConfig = self._config
        if explorationConfig.switch_soul_config.enable:
            self.run_switch_soul(explorationConfig.switch_soul_config.switch_group_team)

        if explorationConfig.switch_soul_config.enable_switch_by_name:
            self.run_switch_soul_by_name(explorationConfig.switch_soul_config.group_name,
                                         explorationConfig.switch_soul_config.team_name)

        # 开启加成
        con = self.config.exploration.exploration_config
        if con.buff_gold_50_click or con.buff_gold_100_click or con.buff_exp_50_click or con.buff_exp_100_click:
            buff = []
            if con.buff_gold_50_click:
                buff.append(BuffClass.GOLD_50)
            if con.buff_gold_100_click:
                buff.append(BuffClass.GOLD_100)
            if con.buff_exp_50_click:
                buff.append(BuffClass.EXP_50)
            if con.buff_exp_100_click:
                buff.append(BuffClass.EXP_100)
            self.check_buff(buff)

    def post_process(self):
        con = self._config.exploration_config
        if con.buff_gold_50_click or con.buff_gold_100_click or con.buff_exp_50_click or con.buff_exp_100_click:
            buff = [BuffClass.GOLD_50_CLOSE, BuffClass.GOLD_100_CLOSE, BuffClass.EXP_50_CLOSE, BuffClass.EXP_100_CLOSE]
            self.check_buff(buff)
        self.set_next_run(task='Exploration', success=True, finish=False)
        raise TaskEnd

    # 打开指定的章节：
    def open_expect_level(self, goal_level):
        swipeCount = 0
        target_box = ()  # 保存目标章节的位置
        
        while 1:
            # 判断有无目标章节
            self.screenshot()

            # 获取当前章节名和位置
            results = self._detect_visible_chapters()
            text1 = [result.ocr_text for result in results]
            logger.info(f"当前章节: {text1}")
            
            if not text1:
                self.ui_click_until_disappear(self.I_BACK_RED)
                continue
            logger.info(f"目标章节: {goal_level}")

            # 判断当前章节有无目标章节
            result = set(text1).intersection({goal_level})

            # 有则保存位置并跳出
            if result and len(result) > 0:
                # 找到目标章节,保存其位置
                for res in results:
                    if goal_level == res.ocr_text:
                        target_box = res.after_box  # [x, y, w, h]
                        logger.info(f"已找到目标章节: {goal_level} 位置: {target_box}")
                        break

            # 选中对应章节 - 直接使用之前保存的位置
            if target_box:
                # 点击章节名称下方(按钮位置)
                CLICK_TMP = RuleClick(roi_front=target_box, roi_back=target_box, name="CLICK_TMP")
                self.click(CLICK_TMP)
                if not self.wait_until_appear(self.I_E_EXPLORATION_CLICK, wait_time=5):
                    continue

            # 检查是否进入章节
            if self.appear(self.I_E_EXPLORATION_CLICK):
                break
            else:
                self.device.click_record_clear()
                # 判断目标章节与当前章节的相对位置
                should_swipe_up = self._should_swipe_up(text1, goal_level)
                # 根据判断结果决定滑动方向
                if should_swipe_up:
                    self.swipe(self.S_SWIPE_LEVEL_UP)
                else:
                    self.swipe(self.S_SWIPE_LEVEL_DOWN)

                swipeCount += 1
                if swipeCount >= 15:
                    return False

        while 1:
            self.screenshot()
            if self.appear_then_click(self.I_UI_SURE, interval=1):
                continue
            if self.appear_then_click(self.I_UI_CONFIRM, interval=1):
                continue
            if self.appear(self.I_E_EXPLORATION_CLICK):
                break
            if self.is_in_room():
                break

        return True

    def _detect_visible_chapters(self):
        """
        检测当前可见章节
        使用OCR识别章节区域,并进行图像预处理增强透明文字识别
        :return: OCR识别结果列表[BoxedResult]
        """
        # 获取OCR区域

        # 使用基类的预处理方法
        processed_image = self.O_E_EXPLORATION_LEVEL_NUMBER.preprocess_ocr_image(self.device.image)
        
        # 使用处理后的图像进行OCR
        results = self.O_E_EXPLORATION_LEVEL_NUMBER.detect_and_ocr(processed_image)
        return results

    # 候补：
    def enter_settings_and_do_operations(self):
        # 打开设置
        while 1:
            self.screenshot()
            if self.appear(self.I_E_OPEN_SETTINGS):
                logger.info("打开设置")
                break
            if self.is_in_battle():
                logger.warning('因战斗中打开设置失败')
                return
            if self.click(self.C_CLICK_SETTINGS, interval=2):
                continue

        # 候补出战数量识别
        self.screenshot()
        if not self.appear(self.I_E_OPEN_SETTINGS):
            logger.warning('因战斗中打开设置失败')
            return
        cu, res, total = self.O_E_ALTERNATE_NUMBER.ocr(self.device.image)
        if cu >= 20:
            logger.info(f"当前狗粮数量：{cu}, 大于20，无需补充")
            self.ui_click_until_disappear(self.I_E_SURE_BUTTON)
            return
        else:
            logger.info(f"当前狗粮数量：{cu}, 小于20，补充狗粮")
            self.add_shiki()

    # 添加式神
    def add_shiki(self, screenshot=True):
        if screenshot:
            self.screenshot()
            if not self.appear(self.I_E_OPEN_SETTINGS):
                logger.warning('因战斗中打开设置失败')
                return
        choose_rarity = self._config.exploration_config.choose_rarity
        rarity = ShikigamiClass.N if choose_rarity == ChooseRarity.N else ShikigamiClass.MATERIAL
        self.switch_shikigami_class(rarity)

        self.click(self.C_CLICK_STANDBY_TEAM)
        # 移动至未候补的狗粮
        while 1:
            # 慢一点
            time.sleep(0.5)
            self.screenshot()
            if not self.appear(self.I_E_OPEN_SETTINGS):
                logger.warning('因战斗中打开设置失败')
                return
            if self.appear(self.I_E_RATATE_EXSIT):
                self.swipe(self.S_SWIPE_SHIKI_TO_LEFT)
            else:
                break
        while 1:
            # 候补出战数量识别
            self.screenshot()
            if not self.appear(self.I_E_OPEN_SETTINGS):
                logger.warning('因战斗中打开设置失败')
                return
            cu, res, total = self.O_E_ALTERNATE_NUMBER.ocr(self.device.image)
            if cu >= 40:
                logger.info(f"当前狗粮数量：{cu}, 大于40，补充完毕")
                break
            self.swipe(self.S_SWIPE_SHIKI_TO_LEFT_ONE)
            # 慢一点
            time.sleep(0.5)
            self.screenshot()
            self.click(self.L_ROTATE_1)
            self.device.click_record_clear()

        self.appear_then_click(self.I_E_SURE_BUTTON)

    # 找up按钮
    def search_up_fight(self, up_type: UpType = None):
        if up_type is None:
            up_type = self._config.exploration_config.up_type
        if up_type != UpType.ALL:
            match up_type:
                case UpType.EXP:
                    find_flag = self.I_UP_EXP
                case UpType.COIN:
                    find_flag = self.I_UP_COIN
                case UpType.DARUMAA:
                    find_flag = self.I_UP_DARUMA
                case _:
                    find_flag = self.I_UP_EXP
            appear = self.appear(find_flag)
            if not appear:
                return None
            # logger.info(f'找到UP类型: {up_type} 位置 {find_flag.roi_front}')
            x, y, _, _ = find_flag.roi_front
            x_center, y_center = find_flag.front_center()
            roi_back_y = max(0, y - 300)
            roi_back_h = y - 20 - roi_back_y
            roi_back_x = max(0, x - 160)
            roi_back_w = min(1280, x + 200) - roi_back_x
            # self.I_NORMAL_BATTLE_BUTTON.roi_back = [roi_back_x, roi_back_y, roi_back_w, roi_back_h]
            # logger.info(f'将在以下区域搜索普通战斗按钮: {roi_back_x, roi_back_y, roi_back_w, roi_back_h}')
            matches = self.I_NORMAL_BATTLE_BUTTON.match_all(
                image=self.device.image,
                threshold=0.9,
                roi=[roi_back_x, roi_back_y, roi_back_w, roi_back_h]
            )
            if not matches:
                return None
            distances = []
            for match in matches:
                x_match, y_match = match[1], match[2]
                distance = np.linalg.norm(
                    np.array([x_center, y_center]) - np.array([x_match, y_match])
                )
                distances.append((distance, match))
            distances.sort(key=lambda x: x[0], reverse=False)
            match = distances[0][1]
            roi_front = list(match[1:])  # x,y,w,h
            self.I_NORMAL_BATTLE_BUTTON.roi_front = roi_front
            # logger.info(f"在 {roi_front} 找到普通战斗按钮")
            return self.I_NORMAL_BATTLE_BUTTON
        if self.appear(self.I_NORMAL_BATTLE_BUTTON):
            return self.I_NORMAL_BATTLE_BUTTON
        return None

    def check_boss_number(self, con_scrolls):
        if con_scrolls.check_boss_num:
            cu, res, total = self.O_CHECK_BOSS_NUM.ocr(self.device.image)
            message = f"当前鬼王掉落数量: {cu} / {total} 剩余: {res}"
            logger.info(message)
            if cu + res == total and cu == 50 and total == 50:
                self.push_notify(message)
                self.set_next_run()
                raise TaskEnd

    def activate_realm_raid(self, con_scrolls, con) -> None:
        # 判断是否开启突破票检测
        if not con_scrolls.scrolls_enable:
            return
        self.screenshot()
        if self.appear([self.I_E_EXPLORATION_CLICK, self.I_EXP_CREATE_TEAM]):
            cu, res, total = self.O_REALM_RAID_NUMBER1.ocr(self.device.image)
        else:
            cu, res, total = self.O_REALM_RAID_NUMBER.ocr(self.device.image)

        # 判断突破票数量

        # 添加校验：只有当总值等于30时才认为是突破券数量
        if total != 30:
            logger.warning(f"识别到的总值{total}不是30，可能不是突破券，跳过此次识别")
            return  
    
        if cu < 27:
            return
        logger.info(f"突破票数量:{cu}, 结束探索任务")
        # 关闭加成
        if self.appear(self.I_RED_CLOSE):
            self.ui_click_until_disappear(self.I_RED_CLOSE)
        if self.appear(self.I_CANCEL):
            self.ui_click_until_disappear(self.I_CANCEL)
        if self.appear(self.I_CANCEL):
            self.ui_click_until_disappear(self.I_CANCEL)
        if con.buff_gold_50_click or con.buff_gold_100_click or con.buff_exp_50_click or con.buff_exp_100_click:
            buff = [BuffClass.GOLD_50_CLOSE, BuffClass.GOLD_100_CLOSE, BuffClass.EXP_50_CLOSE, BuffClass.EXP_100_CLOSE]
            self.check_buff(buff)

        # 设置下次执行行时间
        # cd = con_scrolls.scrolls_cd
        # timedelta_cd = timedelta(hours=cd.hour, minutes=cd.minute, seconds=cd.second)
        # datetime_now = datetime.now()
        # self.set_next_run(task='Exploration', target=datetime_now + timedelta_cd)

        datetime_now = datetime.now()
        self.set_next_run(task='Exploration', target=datetime_now + timedelta(minutes=1))
        # 绘卷捐赠
        self.set_next_run(task='MemoryScrolls', target=datetime_now)
        # 个突
        self.set_next_run(task='RealmRaid', target=datetime_now)
        if not self.config.realm_raid.scheduler.enable:
            self.config.realm_raid.scheduler.enable = True
            self.config.save()
        raise TaskEnd

    def quit_explore(self):
        logger.info('退出本次探索')
        while 1:
            self.screenshot()
            if self.appear(self.I_BACK_RED) and self.appear(self.I_E_EXPLORATION_CLICK):
                break
            if self.appear(self.I_CHECK_EXPLORATION) and not self.appear([self.I_E_SETTINGS_BUTTON, self.I_E_AUTO_ROTATE_ON, self.I_E_AUTO_ROTATE_OFF]):
                break
            if self.appear(self.I_BUFF_1):
                break
            if self.appear_then_click(self.I_E_EXIT_CONFIRM, interval=0.8):
                continue
            if self.appear_then_click(self.I_BACK_YELLOW, interval=1.5):
                continue

    def fire(self, button, boss_battle: bool = False) -> bool:
        self.ui_click_until_disappear(button, interval=1)
        if self.appear([self.I_E_SETTINGS_BUTTON, self.I_E_AUTO_ROTATE_ON, self.I_E_AUTO_ROTATE_OFF]):
            # 如果还在探索说明，这个是显示滑动导致挑战按钮不在范围内
            logger.warning('挑战按钮消失，但仍在探索中')
            return False
        if boss_battle:
            self.current_boss_cnt += 1
        self.run_general_battle_e()
        return True

    def get_box(self):
        if self.appear_then_click(self.I_TREASURE_BOX_CLICK, interval=1):
            # 宝箱
            logger.info('出现宝箱，点击获取。')
            return True
        return False

    def _should_swipe_up(self, current_levels, target_level):
        """
        判断是否需要向上滑动
        小章节在上面，大章节在下面
        """
        # 获取所有章节列表
        exploration_levels = list(ExplorationLevel)

        # 找到目标章节在枚举中的索引
        target_index = -1
        for i, level in enumerate(exploration_levels):
            if level.value == target_level:
                target_index = i
                break

        if target_index == -1:
            return True  # 无法找到目标章节，默认向上滑动

        # 检查当前显示的章节
        for current_level in current_levels:
            # 找到当前章节在枚举中的索引
            for i, level in enumerate(exploration_levels):
                if level.value == current_level:
                    # 如果当前显示的章节索引大于目标章节索引
                    # 说明目标章节在上方，需要向上滑动
                    if i > target_index:
                        return True
                    break

        # 默认向下滑动（目标章节在下方）
        return False

    def run_general_battle_e(self) -> bool:
        """
        运行脚本
        :return:
        """
        # 本人选择的策略是只要进来了就算一次，不管是不是打完了
        self.current_count += 1

        # 绘卷模式
        if self._config.scrolls.scrolls_enable:
            logger.hr("探索 （绘卷模式）", 2)
            logger.info(f'当前次数: {self.current_count}')
        else:
            logger.hr("探索 （普通模式）", 2)
            logger.info(f'当前次数: {self.current_count} / {self.limit_count}')
            logger.info(f'完成章节: {self.current_boss_cnt} / {self.min_boss_cnt}')
            task_run_time = datetime.now() - self.start_time
            # 格式化时间，只保留整数部分的秒
            task_run_time_seconds = timedelta(seconds=int(task_run_time.total_seconds()))
            logger.info(f'运行时间: {task_run_time_seconds} / {self.limit_time}')

        self.device.click_record_clear()
        click_list = [self.I_E_REWARD_STATISTICS, self.I_WIN, self.I_FALSE, self.I_REWARD, self.I_REWARD_GOLD]
        while 1:
            self.screenshot()

            if self.appear([self.I_E_SETTINGS_BUTTON, self.I_E_AUTO_ROTATE_ON, self.I_E_AUTO_ROTATE_OFF, self.I_LOCK_ON, self.I_LOCK_OFF]):
                break

            # 处理战斗类元素
            action_click = self.get_random_reward_action([self.C_REWARD_LEFT, self.C_REWARD_RIGHT])
            if any(self.appear_then_click(item, action=action_click, interval=1) for item in click_list):
                continue
            # 误点聊天频道会自动关闭
            if self.appear_then_click(RestartAssets.I_HARVEST_CHAT_CLOSE):
                continue
        return True


if __name__ == "__main__":
    from module.config.config import Config

    config = Config('yys1')
    t = BaseExploration(config)
    t.screenshot()

    # IMAGE_FILE = r"C:\Users\萌萌哒\Desktop\QQ20240818-163854.png"
    # image = load_image(IMAGE_FILE)
    # t.device.image = image
    while 1:
    # print(t.search_up_fight(UpType.EXP))
        t.screenshot()
        print(t.I_UP_DARUMA.match(t.device.image))
        time.sleep(0.2)
    # Image.fromarray(t.device.image.astype(np.uint8)).show()

