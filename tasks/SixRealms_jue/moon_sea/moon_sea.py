from module.logger import logger
from tasks.SixRealms.common import MoonSeaType
from tasks.SixRealms_jue.moon_sea.l101 import MoonSeaL101
from tasks.SixRealms_jue.moon_sea.l102 import MoonSeaL102
from tasks.SixRealms_jue.moon_sea.l103 import MoonSeaL103
from tasks.SixRealms_jue.moon_sea.l104 import MoonSeaL104
from tasks.SixRealms_jue.moon_sea.l105 import MoonSeaL105
from tasks.SixRealms_jue.moon_sea.map import MoonSeaMap
from tasks.GameUi.assets import GameUiAssets

class MoonSea(MoonSeaMap, MoonSeaL101, MoonSeaL102, MoonSeaL103, MoonSeaL104, MoonSeaL105):

    @property
    def _conf(self):
        return self.config.model.six_realms.six_realms_gate

    def one(self):
        # 每轮开始初始化轰雷和力量等级
        logger.info('初始化轰雷和力量等级')
        self.cnt_skill101 = 0
        self.cnt_skillpower = 0
        self.cnt_zhanfang = 0

        if not self._start():
            return False
        logger.hr('开始觉副本', 2)
        while 1:
            self.screenshot()            
                
            if self.select_skill(refresh=True):
                continue

            if self.enter_island():
                continue
            isl_type = self.island_name()
            if not isl_type:
                continue
            logger.info(f'选择岛屿 [轰雷等级：{self.cnt_skill101}, 力量等级：{self.cnt_skillpower}]')
            match isl_type:
                case MoonSeaType.island101: self.run_l101()
                case MoonSeaType.island102: self.run_l102()
                case MoonSeaType.island103: self.run_103()
                case MoonSeaType.island104: self.run_l104()
                case MoonSeaType.island105: self.run_l105()
                case MoonSeaType.island106:
                    logger.info('是Boss岛屿')
                    self.boss_team_lock()
                    if self.boss_battle():
                        return True
                    else:
                        continue
            self.wait_animate_stable(self.C_MAIN_ANIMATE_KEEP, timeout=3)
            continue

    def _start(self):
        logger.hr('六道觉', 1)
        while 1:
            self.screenshot()
            if self.appear(self.I_MSTART,interval=1):
                logger.info('第一次开启re')
                break
            if self.appear_then_click(self.I_MENTER, interval=1):
                continue
            if self.appear(self.I_MCONINUE):
                logger.info("继续执行re")
                # 继续上一把的
                self.ui_click(self.I_MCONINUE, [self.I_M_STORE_ACTIVITY], timeout=5)
                return True
        logger.info("确认选择")
        while 1:
            self.screenshot()
            if self.appear(self.I_MSHOUZU):
                break
            if self.appear_then_click(self.I_MSHUTEN, interval=3):
                continue
            if self.appear_then_click(self.I_MSHOUZU_SELECT, interval=1):
                continue
        logger.info("已确认选择")
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
            if self.appear_then_click(self.I_MPEACOCK_SKILL_1, interval=1):
                continue
        self.ui_click(self.I_MFIRST_SKILL, self.I_M_STORE, interval=1)
        # 选中第一个极道轰炸
        logger.info("选择第一个技能极道轰炸")
        return True

    def island_name(self):
        while 1:
            self.screenshot()
            text = self.O_ISLAND_NAME.ocr(self.device.image)
            if '绽放' in text:
                return MoonSeaType.island105
            if '战之' in text:
                return MoonSeaType.island104
            if '混' in text:
                return MoonSeaType.island103
            if '神秘' in text:
                return MoonSeaType.island102
            if '宁息' in text:
                return MoonSeaType.island101
            if '恋色' in text:
                return MoonSeaType.island106
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
        self.ui_click_until_disappear(self.I_BOSS_FIRE, interval=1)
        self.device.stuck_record_clear()
        self.device.stuck_record_add('BATTLE_STATUS_S')
        while 1:
            self.screenshot()
            if self.appear(self.I_BOSS_SHARE):
                break
            if self.appear(self.I_BOSS_BATTLE_GIVEUP):
                # 打boss失败了
                logger.warning('Boss战斗放弃')
                self.ui_click_until_disappear(self.I_BOSS_BATTLE_GIVEUP, interval=1)
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
            if self.appear_then_click(GameUiAssets.I_CANCEL, interval=1):
                # 取消购买 万相赐福
                continue
            if self.appear_then_click(self.I_UI_CONFIRM, interval=1):
                continue
            if self.appear(self.I_BOSS_SKIP, interval=30):
                # 第二个boss
                self.device.stuck_record_clear()
                self.device.stuck_record_add('BATTLE_STATUS_S')
                continue
        logger.info('Boss战斗结束')
        if self.wait_until_appear(self.I_BOSS_SHUTU, wait_time=3):
            self.ui_click(self.I_BOSS_SHUTU, stop=self.I_MSTART)
        else:
            self.save_image(task_name='六道觉失败', push_flag=True, image_type=True, wait_time=0, content=f'⚠️ 六道觉失败 轰雷等级：{self.cnt_skill101}, 力量等级：{self.cnt_skillpower}')
            self.ui_click(self.I_BOSS_OVER, stop=self.I_MSTART)
        return True


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('du')
    t = MoonSea(c)
    t.one()
    # t.select_skill()
