# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from cached_property import cached_property
from datetime import datetime
from module.base.timer import Timer
from module.exception import TaskEnd
from module.logger import logger
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.Component.GeneralInvite.config_invite import InviteConfig, InviteNumber
from tasks.Exploration.base import BaseExploration, Scene
from tasks.Exploration.config import AutoRotate, UserStatus
from tasks.Exploration.config import ExplorationLevel
from tasks.GameUi.page import page_exploration


class SoloExploration(BaseExploration):
    INVITE_FLAG_OFF = (157, 109, 83)
    INVITE_FLAG_ON = (227, 193, 153)
    goal_level = ""
    is_first = True

    @cached_property
    def _invite_config(self) -> InviteConfig:
        return InviteConfig(
            invite_number=InviteNumber.ONE,
            friend_1=self._config.invite_config.friend_1,
            friend_2='',
            find_mode=self._config.invite_config.find_mode,
            wait_time=self._config.invite_config.wait_time,
            default_invite=False
        )

    @cached_property
    def _general_battle_config(self):
        gbc = GeneralBattleConfig()
        return gbc

    def run_solo(self):
        logger.hr('单人模式')
        explore_init = False
        search_fail_cnt = 0
        atuo_rotate_on = self.config.exploration.exploration_config.atuo_rotate_on
        self.goal_level = self.config.exploration.exploration_config.exploration_level
        self.limit_count = self._config.exploration_config.minions_cnt
        self.min_boss_cnt = self._config.exploration_config.min_boss_cnt

        open_expect_level = False
        self.ui_goto_page(page_exploration)
        while 1:
            self.screenshot()

            if self.check_exit(False):
                self.quit_explore()
                break

            scene = self.get_current_scene()

            #
            if scene == Scene.WORLD:
                # self.check_boss_number(self._config.scrolls)
                if self.check_exit():
                    break
                # 打开指定的章节：
                self.open_expect_level(self.goal_level)
                open_expect_level = True
                continue

            elif scene == Scene.ENTRANCE:
                # 判断是否有更高优先级任务，去执行新任务
                self._check_first_priority_task()
                if self.check_exit():
                    break
                if open_expect_level:
                    while 1:
                        self.screenshot()
                        if self.appear(self.I_E_SETTINGS_BUTTON):
                            break
                        if self.appear(self.I_LOCK_ON):
                            break
                        if self.appear(self.I_LOCK_OFF):
                            break
                        if self.appear_then_click(self.I_E_EXPLORATION_CLICK):
                            search_fail_cnt = 0
                            continue
                else:
                    self.appear_then_click(self.I_BACK_YELLOW)
                continue
            #
            elif scene == Scene.MAIN:
                # 是否第一次进
                if not explore_init:
                    if atuo_rotate_on:
                        if self._config.exploration_config.auto_rotate == AutoRotate.yes:
                            self.enter_settings_and_do_operations()
                        logger.info('先锁定阵容，再点击轮换')
                        self.ui_click(self.I_LOCK_ON, stop=self.I_LOCK_OFF)
                        while 1:
                            self.screenshot()
                            if self.appear(self.I_LOCK_ON):
                                break
                            if self.click(self.C_AUTO_TOTATE, interval=1):
                                continue
                        logger.info('自动轮换已开启')
                    else:
                        self.ui_click(self.I_LOCK_ON, stop=self.I_LOCK_OFF)
                        logger.info('阵容已锁定')
                    explore_init = True
                    continue
                # 小纸人
                # if self.appear(self.I_BATTLE_REWARD):
                #     # if self.ui_get_reward(self.I_BATTLE_REWARD):
                #     logger.info('识别到小纸人')
                #     self.quit_explore()
                #     continue
                # boss
                # 出现宝箱
                if self.get_box():
                    continue
                if self.appear(self.I_BOSS_BATTLE_BUTTON):
                    if self.fire(self.I_BOSS_BATTLE_BUTTON, True):
                        logger.info(f'Boss战斗完成{self.current_boss_cnt}次')
                    self.quit_explore()

                    """ 测试代码实现章节依次递增进攻 """
                    # self.next_level()
                    # open_expect_level = False

                    continue
                # 小怪
                fight_button = self.search_up_fight()
                if fight_button is not None:
                    if self.fire(fight_button):
                        logger.info(f'小怪战斗完成')
                    continue
                # 向后拉,寻找怪
                if search_fail_cnt >= 5 or self.appear(self.I_SWIPE_END):
                    self.quit_explore()
                else:
                    if self.swipe(self.S_SWIPE_BACKGROUND_RIGHT, interval=1):
                        search_fail_cnt += 1
            elif scene == Scene.BATTLE_PREPARE or scene == Scene.BATTLE_FIGHTING:
                self.check_take_over_battle(is_screenshot=False, config=self._general_battle_config)

    def run_leader(self):
        logger.hr('队长模式')
        explore_init = False
        search_fail_cnt = 0
        friend_leave_timer = Timer(10)
        atuo_rotate_on = self.config.exploration.exploration_config.atuo_rotate_on

        self.goal_level = self.config.exploration.exploration_config.exploration_level
        self.limit_count = self._config.exploration_config.minions_cnt
        self.min_boss_cnt = self._config.exploration_config.min_boss_cnt

        while 1:
            self.screenshot()
            scene = self.get_current_scene()
            # 探索大世界
            if scene == Scene.WORLD:
                self.wait_until_stable(self.I_CHECK_EXPLORATION)
                if self.check_exit():
                    self.wait_until_stable(self.I_CANCEL, timer=Timer(0.6, 2))
                    if self.appear(self.I_CANCEL):
                        self.ui_click_until_disappear(self.I_CANCEL)
                    break
                if self.appear(self.I_UI_SURE):
                    self.ui_click_until_disappear(self.I_UI_SURE)
                    continue
                self.open_expect_level(self.goal_level)
                self.is_first = True
                continue

            # 邀请好友, 非常有可能是后面邀请好友，然后直接跳到组队了
            elif scene == Scene.ENTRANCE:
                while 1:
                    self.screenshot()
                    if self.is_in_room():
                        break
                    # 继续邀请队友
                    if self.appear_then_click(self.I_UI_SURE, interval=1):
                        continue
                    if self.appear_then_click(self.I_ENSURE_PRIVATE_FALSE, interval=0.5):
                        continue
                    if self.appear_then_click(self.I_ENSURE_PRIVATE_FALSE_2, interval=0.5):
                        continue
                    if self.appear_then_click(self.I_FORM_TEAM, interval=1):
                        continue
                    if self.appear_then_click(self.I_EXP_CREATE_ENSURE, interval=2):
                        continue
            #
            elif scene == Scene.TEAM:
                self.wait_until_stable(self.I_ADD_2, timer=Timer(0.8, 1))
                if self.appear(self.I_FIRE, threshold=0.8) and not self.appear(self.I_ADD_2):
                    self.ui_click_until_disappear(self.I_FIRE, interval=1)
                    continue
                if self.appear(self.I_ADD_2) and self.run_invite(config=self._invite_config, is_first=self.is_first):
                    self.is_first = False
                    continue
                else:
                    logger.warning('邀请失败，退出')
                    while 1:
                        self.screenshot()
                        if self.appear(self.I_CHECK_EXPLORATION):
                            break
                        if self.appear_then_click(self.I_UI_SURE, interval=0.5):
                            continue
                        if self.appear_then_click(self.I_BACK_RED, interval=0.7):
                            continue
                        if self.appear_then_click(self.I_BACK_YELLOW, interval=1):
                            continue
                    break
            ##
            elif scene == Scene.MAIN:
                # 是否第一次进
                if not explore_init:
                    if atuo_rotate_on:
                        if self._config.exploration_config.auto_rotate == AutoRotate.yes:
                            self.enter_settings_and_do_operations()
                        logger.info('先锁定阵容，再点击轮换')
                        self.ui_click(self.I_LOCK_ON, stop=self.I_LOCK_OFF)
                        while 1:
                            self.screenshot()
                            if self.appear(self.I_LOCK_ON):
                                break
                            if self.click(self.C_AUTO_TOTATE, interval=1):
                                continue
                        logger.info('自动轮换已开启')
                    else:
                        self.ui_click(self.I_LOCK_ON, stop=self.I_LOCK_OFF)
                        logger.info('阵容已锁定')
                    friend_leave_timer = Timer(10)
                    explore_init = True
                    continue
                # 出现宝箱
                if self.get_box():
                    continue
                # 小纸人
                if self.appear(self.I_BATTLE_REWARD):
                    if self.ui_get_reward(self.I_BATTLE_REWARD):
                        continue
                # 中途有人跑路
                if not self.appear(self.I_TEAM_EMOJI):
                    if not friend_leave_timer.started():
                        logger.warning('队友离开，启动计时器')
                        friend_leave_timer = Timer(10)
                        friend_leave_timer.start()
                    elif friend_leave_timer.started() and friend_leave_timer.reached():
                        logger.warning('队友离开计时器到达')
                        logger.warning('退出队伍')
                        self.quit_explore()
                        continue
                else:
                    # logger.warning('Team emoji appear again, clear friend_leave_timer')
                    friend_leave_timer = Timer(10)
                # boss
                if self.appear(self.I_BOSS_BATTLE_BUTTON):
                    if self.fire(self.I_BOSS_BATTLE_BUTTON, True):
                        logger.info(f'Boss战斗完成{self.current_boss_cnt}次')
                    self.quit_explore()
                    continue
                # 小怪
                fight_button = self.search_up_fight()
                if fight_button is not None:
                    if self.fire(fight_button):
                        logger.info(f'小怪战斗完成')
                    continue
                # 向后拉,寻找怪
                if search_fail_cnt >= 4:
                    search_fail_cnt = 0
                    if self.appear(self.I_SWIPE_END):
                        self.quit_explore()
                        continue
                    if self.swipe(self.S_SWIPE_BACKGROUND_RIGHT, interval=4.5):
                        continue
                else:
                    search_fail_cnt += 1
            #
            elif scene == Scene.BATTLE_PREPARE or scene == Scene.BATTLE_FIGHTING:
                self.check_take_over_battle(is_screenshot=False, config=self._general_battle_config)
            elif scene == Scene.UNKNOWN:
                continue

    def run_member(self):
        logger.hr('队员模式')
        explore_init = False
        last_scene = Scene.UNKNOWN
        wait_timer = Timer(50)
        wait_timer.start()

        atuo_rotate_on = self.config.exploration.exploration_config.atuo_rotate_on
        self.goal_level = self.config.exploration.exploration_config.exploration_level
        self.limit_count = self._config.exploration_config.minions_cnt
        self.min_boss_cnt = self._config.exploration_config.min_boss_cnt

        while 1:
            self.screenshot()
            scene = self.get_current_scene()

            if wait_timer.reached():
                logger.warning('等待计时器到达')
                break

            if last_scene != scene:
                last_scene = scene
                wait_timer.reset()
            #
            if scene == Scene.WORLD:
                if self.check_exit():
                    break
                self.check_then_accept()
                continue
            #
            elif scene == Scene.ENTRANCE:
                self.check_then_accept()
                continue
            #
            elif scene == Scene.MAIN:
                # 是否第一次进
                if not explore_init:
                    if atuo_rotate_on:
                        if self._config.exploration_config.auto_rotate == AutoRotate.yes:
                            self.enter_settings_and_do_operations()
                        logger.info('先锁定阵容，再点击轮换')
                        self.ui_click(self.I_LOCK_ON, stop=self.I_LOCK_OFF)
                        while 1:
                            self.screenshot()
                            if self.appear(self.I_LOCK_ON):
                                break
                            if self.click(self.C_AUTO_TOTATE, interval=1):
                                continue
                        logger.info('自动轮换已开启')
                    else:
                        self.ui_click(self.I_LOCK_ON, stop=self.I_LOCK_OFF)
                        logger.info('阵容已锁定')
                    explore_init = True
                    continue
                # 出现宝箱
                if self.get_box():
                    continue
                # 小纸人
                if self.appear(self.I_BATTLE_REWARD):
                    self.quit_explore()
            #
            elif scene == Scene.BATTLE_PREPARE or scene == Scene.BATTLE_FIGHTING:
                self.check_take_over_battle(is_screenshot=False, config=self._general_battle_config)

    def get_next_exploration_level(self):
        """
        获取下一个探索章节
        """
        current_level = self.goal_level
        # 获取所有章节列表
        levels = list(ExplorationLevel)

        # 找到当前章节的索引
        current_index = levels.index(current_level)

        # 如果是最后一个章节，则返回None表示结束
        if current_index == len(levels) - 1:
            logger.warning('已经是最后一章，结束任务')
            self.set_next_run(success=True, finish=True)
            raise TaskEnd

        # 返回下一个章节
        next_index = current_index + 1
        if levels[next_index] == "第十三章":
            logger.warning('已经是最后一章，结束任务')
            self.set_next_run(success=True, finish=True)
            raise TaskEnd

        return levels[next_index]

    def next_level(self):
        """
        打开下一个探索章节
        """
        next_level = self.get_next_exploration_level()
        logger.info(f"切换到下一个章节: {next_level.value}")

        # 更新配置中的章节
        self.goal_level = next_level

        # 重置探索次数和时间
        self.current_count = 0
        self.start_time = datetime.now()

    def check_exit(self, check_flag: bool = True) -> bool:
        # 判断是否开启绘卷模式
        if not self._config.scrolls.scrolls_enable:
            # True 表示要退出这个任务
            if self.current_boss_cnt >= self.min_boss_cnt:
                logger.info(f'✅ 探索章数 {self.current_boss_cnt}/{self.min_boss_cnt}, 结束探索任务')
                return True
            if self.current_count >= self.limit_count:
                logger.info(f'✅ 探索次数 {self.current_count}/{self.limit_count}, 结束探索任务')
                return True
            if datetime.now() - self.start_time >= self.limit_time:
                logger.info(f'✅ 探索时间限制已到, 结束探索任务')
                return True
        else:
            if check_flag:
                self.activate_realm_raid(self._config.scrolls, self._config.exploration_config)
        return False


class ScriptTask(SoloExploration):
    def run(self):
        logger.hr('探索')
        # 换御魂
        self.pre_process()
        match self._config.exploration_config.user_status:
            case UserStatus.ALONE: self.run_solo()
            case UserStatus.LEADER: self.run_leader()
            case UserStatus.MEMBER: self.run_member()
            case _: self.run_solo()

        self.post_process()


if __name__ == "__main__":
    from module.config.config import Config

    config = Config('mi')
    t = ScriptTask(config)
    t.run()

