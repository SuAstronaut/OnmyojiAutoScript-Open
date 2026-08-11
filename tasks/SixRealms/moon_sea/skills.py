import re
from cached_property import cached_property
from module.base.timer import Timer
from module.logger import logger
from tasks.SixRealms.assets import SixRealmsAssets
from tasks.base_task import BaseTask


class MoonSeaSkills(BaseTask, SixRealmsAssets):

    cnt_skill101 = 0
    cnt_coin = 0

    def in_main(self, screenshot: bool = False):
        if screenshot:
            self.screenshot()
        if self.appear(self.I_M_STORE):
            return True
        if self.appear(self.I_M_STORE_ACTIVITY):
            return True
        if self.appear(self.I_BOSS_FIRE):
            return True
        return False

    def battle_lock_team(self):
        self.ui_click(self.I_BATTLE_TEAM_UNLOCK, self.I_BATTLE_TEAM_LOCK)
        return

    def island_battle(self):
        # 小怪战斗
        self.screenshot()
        while 1:
            self.screenshot()
            if self.appear(self.I_SKILL_REFRESH):
                break
            if self.appear(self.I_COIN):
                break
            if self.appear(self.I_BOSS_BATTLE_GIVEUP):
                break
            if self.appear_then_click(self.I_NPC_FIRE, interval=1):
                self.device.stuck_record_add('BATTLE_STATUS_S')
                continue
        self.device.stuck_record_clear()

    @cached_property
    def selects_button(self):
        return [
            self.I_SELECT_0,
            self.I_SELECT_1,
            self.I_SELECT_2,
            self.I_SELECT_3,
        ]

    def _select_skill(self) -> int:
        self.wait_until_stable(self.I_SELECT_3)
        select = 3  # 从0开始计数
        button = None
        # 只选柔风
        self.screenshot()
        if not button and self.appear(self.I_SKILL101):
            self.cnt_skill101 += 1
            logger.info(f'柔风等级: {self.cnt_skill101}')
            button = self.I_SKILL101
        elif not button and self.appear(self.I_SKILL105):
            button = self.I_SKILL105
        if button:
            x, y = button.front_center()
            if x < 360:
                select = 0
            elif 360 <= x < 640:
                select = 1
            elif 640 <= x < 960:
                select = 2
            else:
                select = 3
        logger.info(f'选择位置: {select}')
        return select

    def select_skill(self, refresh: bool = False):
        def check_coin_skill() -> bool:
            self.cnt_coin = self.O_COIN_NUM.ocr(self.device.image)
            return self.cnt_coin > 50

        def check_refresh() -> bool:
            # 检测是否有钱刷新技能
            text = self.O_SKILL_REFRESH.ocr(self.device.image)
            matches = re.search(f"剩\d+次", text)
            if matches:
                refresh_time = int(matches.group()[1])
                logger.info(f'刷新次数: {refresh_time}')
                if refresh_time <= 0:
                        return False
                else:
                    return True
            return False

        if self.appear(self.I_UI_SURE):
            self.ui_click_until_disappear(self.I_UI_SURE)
            return True

        if self.cnt_skill101 >= 5:
            self.appear_then_click(self.selects_button[3])
            # logger.info('柔风已经满级, 退出')
            return False

        if self.appear(self.I_SKILL_REFRESH) and self.appear(self.I_SELECT_3) and not self.appear(self.I_COIN2):
            # 战斗结束后选技能
            logger.info('开始选择技能')
            select = self._select_skill()
            # 如果没有柔风并且钱够并且还有刷新次数
            if refresh and select == 3 and check_coin_skill() and check_refresh() and self.cnt_skill101 < 5:
                self.appear_then_click(self.I_SKILL_REFRESH)
                return True

            if self.appear_then_click(self.selects_button[select]):
                return True

        return None


