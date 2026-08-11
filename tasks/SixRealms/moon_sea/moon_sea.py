from module.logger import logger
from tasks.SixRealms.common import MoonSeaType
from tasks.SixRealms.moon_sea.l101 import MoonSeaL101
from tasks.SixRealms.moon_sea.l102 import MoonSeaL102
from tasks.SixRealms.moon_sea.l103 import MoonSeaL103
from tasks.SixRealms.moon_sea.l104 import MoonSeaL104
from tasks.SixRealms.moon_sea.l105 import MoonSeaL105
from tasks.SixRealms.moon_sea.map import MoonSeaMap
from tasks.GameUi.assets import GameUiAssets

class MoonSea(MoonSeaMap, MoonSeaL101, MoonSeaL102, MoonSeaL103, MoonSeaL104, MoonSeaL105):

    @property
    def _conf(self):
        return self.config.six_realms.six_realms_gate

    def one(self):
        self.cnt_skill101 = 1
        if not self._start():
            return False
        while 1:
            self.screenshot()

            if self.appear([self.I_BOSS_OVER, self.I_BOSS_SHUTU, self.I_BOSS_SHUTU_2]):
                self.ui_click([self.I_BOSS_OVER, self.I_BOSS_SHUTU, self.I_BOSS_SHUTU_2], stop=self.I_MSTART)
                return True

            if self.appear(self.I_BOSS_BATTLE_GIVEUP, interval=1):
                while 1:
                    self.screenshot()
                    if self.appear([self.I_BOSS_OVER, self.I_BOSS_SHUTU, self.I_BOSS_SHUTU_2]):
                        self.save_image(task_name='六道椒图失败', push_flag=True, image_type=True, wait_time=0, content=f'⚠️ 六道椒图失败 柔风等级：{self.cnt_skill101}')
                        self.ui_click([self.I_BOSS_OVER, self.I_BOSS_SHUTU, self.I_BOSS_SHUTU_2], stop=self.I_MSTART)
                        return True
                    if self.appear_then_click(self.I_BOSS_BATTLE_GIVEUP, interval=1):
                        continue
                    if self.appear_then_click(self.I_UI_CONFIRM, interval=1):
                        continue

            if self.activate_store():
                continue

            # 如果是boss
            if self.appear(self.I_BOSS_FIRE):
                logger.info(f'柔风等级: {self.cnt_skill101}, 剩余金币: {self.cnt_coin}')
                # if self.cnt_skill101 < 4:
                #     self.push_notify(f'⚠️ 柔风等级: {self.cnt_skill101}, 剩余金币: {self.cnt_coin}')
                self.boss_team_lock()
                if self.boss_battle():
                    continue

            if self.appear_then_click(self.I_COIN, action=self.C_UI_REWARD, interval=1):
                continue

            if self.select_skill(refresh=True):
                continue

            if self.enter_island():
                continue
            isl_type = self.island_name()
            if not isl_type:
                continue
            match isl_type:
                case MoonSeaType.island101: self.run_l101()
                case MoonSeaType.island102: self.run_l102()
                case MoonSeaType.island103: self.run_l103()
                case MoonSeaType.island104: self.run_l104()
                case MoonSeaType.island105: self.run_l105()

    def _start(self):
        logger.hr('六道椒图', 1)
        while 1:
            self.screenshot()
            if self.appear(self.I_MSTART,interval=1):
                if self._conf.number_enable:
                    cu = self.O_SIXREALMS_NUMBER.ocr(self.device.image)
                    logger.info(f"六道门票数量：{cu}")
                    if not cu > 0:
                        self.push_notify("六道门票数量不足, 退出！")
                        return False
                break
            if self.appear_then_click(self.I_MENTER, interval=1):
                continue
            if self.appear(self.I_MCONINUE):
                # 继续上一把的
                self.ui_click_until_disappear(self.I_MCONINUE)
                return True
        while 1:
            self.screenshot()
            if self.appear(self.I_MSHOUZU):
                break
            if self.appear_then_click(self.I_MSHUTEN, interval=3):
                continue
            if self.appear_then_click(self.I_MSHOUZU_SELECT, interval=1):
                continue
        while 1:
            self.screenshot()
            if self.appear(self.I_PREPARE_BATTLE):
                break
            if self.appear_then_click(self.I_MSTART_UNCHECK, interval=0.6):
                continue
            if self.appear_then_click(self.I_UI_SURE, interval=1):
                continue
            if self.appear_then_click(self.I_UI_CONFIRM, interval=1):
                continue
            if self.appear_then_click(self.I_MSKIP, interval=1):
                continue
            if self.appear_then_click(self.I_MSTART, interval=1):
                continue
            if self.appear_then_click(self.I_MSTART_CONFIRM, interval=1):
                continue
            if self.appear_then_click(self.I_MSTART_CONFIRM2, interval=1):
                continue
            if self.appear_then_click(self.I_MCONINUE, interval=1):
                continue
        while 1:
            self.screenshot()
            if self.appear(self.I_M_STORE):
                break
            if self.appear_then_click(self.I_MFIRST_SKILL, interval=1):
                continue
        # 选中第一个柔风
        logger.info("选择第一个技能柔风")
        return True

    def island_name(self):
        while 1:
            self.screenshot()
            text = self.O_ISLAND_NAME.ocr(self.device.image)
            if '星之屿' in text:
                return MoonSeaType.island105
            if '鏖战之屿' in text:
                return MoonSeaType.island104
            if '混沌之屿' in text:
                return MoonSeaType.island103
            if '神秘之屿' in text:
                return MoonSeaType.island102
            if '宁息之屿' in text:
                return MoonSeaType.island101
            else:
                return False

    def boss_team_lock(self):
        while 1:
            self.screenshot()
            if self.appear(self.I_BOSS_TEAM_LOCK):
                break
            if self.appear_then_click(self.I_BOSS_TEAM_UNLOCK, interval=2):
                logger.info('点击锁定Boss队伍')
                continue

    def boss_battle(self) -> bool:
        logger.hr('Boss战斗')
        while 1:
            self.screenshot()
            if self.appear(self.I_BOSS_SHARE):
                break
            if self.appear(self.I_BOSS_BATTLE_GIVEUP):
                break
            if self.appear_then_click(self.I_BOSS_FIRE, interval=1):
                self.device.stuck_record_clear()
                self.device.stuck_record_add('BATTLE_STATUS_S')
                continue
            if self.appear(self.I_BOSS_USE_DOUBLE, interval=1):
                # 双倍奖励
                logger.info('双倍奖励')
                self.ui_get_reward(self.I_BOSS_USE_DOUBLE)
            if self.ui_reward_appear_click():
                continue
            if self.appear_then_click(self.I_BOSS_GET_EXP, interval=1):
                logger.info('获取经验')
                continue
            if self.appear_then_click(self.I_UI_CONFIRM, interval=1):
                continue
            if self.appear_then_click(GameUiAssets.I_CANCEL, interval=1):
                # 取消购买 万相赐福
                continue
            if self.appear_then_click(self.I_BOSS_SKIP, interval=1):
                # 第二个boss
                self.device.stuck_record_clear()
                self.device.stuck_record_add('BATTLE_STATUS_S')
                continue
        logger.info('Boss战斗结束')
        return True


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('百鬼-16480')
    t = MoonSea(c)
    t.one()
    # t.select_skill()
