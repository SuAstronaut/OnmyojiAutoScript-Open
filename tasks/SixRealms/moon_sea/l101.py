import re
from module.base.timer import Timer
from module.logger import logger
from tasks.SixRealms.moon_sea.skills import MoonSeaSkills
from tasks.GameUi.assets import GameUiAssets

class MoonSeaL101(MoonSeaSkills):

    def buy_skill_101(self) -> bool:
        logger.info('开始购买')
        self.wait_until_appear(self.I_STORE_STABLE_FLAG)
        buy_try: int = 0
        while 1:
            self.screenshot()
            if self.appear_then_click(self.I_UI_CONFIRM, interval=1.5):
                break
            if self.appear(self.I_UI_SURE):
                break
            if buy_try >= 4:
                logger.warning(f'购买柔风失败')
                return False
            if self.appear(self.I_STORE_SKILL_101, interval=3):
                x, y = self.I_STORE_SKILL_101.front_center()
                x -= 60
                self.device.click(x=x, y=y)
                buy_try += 1
        self.ui_click_until_disappear(self.I_UI_SURE)
        self.wait_until_appear(self.I_STORE_EXIT)
        self.cnt_skill101 += 1
        logger.info(f'柔风等级: {self.cnt_skill101}')
        return True

    def refresh_store(self) -> bool:
        # 刷新宁溪
        # 只会点击一次
        logger.info('刷新商店')
        text = self.O_STORE_REFRESH_TIME.ocr(self.device.image)
        matches = re.search(f"剩\d+次", text)
        if matches:
            refresh_time = int(matches.group()[1])
            logger.info(f'刷新次数: {refresh_time}')
            if refresh_time <= 0:
                return False
        self.appear_then_click(self.I_STORE_REFRESH, interval=1.5)
        self.wait_until_stable(self.I_UI_SURE, timeout=Timer(2, count=10))
        logger.info('刷新商店完成')
        return True

    def run_l101(self):
        logger.hr('宁息之屿')
        if self.cnt_skill101 >= 5:
            logger.info('柔风已经满级, 退出')
            while 1:
                self.screenshot()
                if self.in_main():
                    break
                if self.appear_then_click(self.I_UI_SURE, interval=1):
                    continue
                if self.appear_then_click(self.I_STORE_EXIT, interval=1):
                    continue
            return

        logger.info('持续购买技能直到金钱耗尽')
        self.wait_until_appear(self.I_STORE_EXIT)
        self.wait_animate_stable(self.C_STORE_ANIMATE_KEEP, timeout=2)
        if self.appear(GameUiAssets.I_CANCEL):
            # 有时候点击进入商店太快了，就进入会选随机的一个
            self.ui_click_until_disappear(GameUiAssets.I_CANCEL, interval=1)
        while 1:
            self.screenshot()
            self.cnt_coin = self.O_COIN_NUM.ocr(self.device.image)
            if self.cnt_coin < 300:
                logger.info('金币不足')
                break

            if self.appear(self.I_UI_SURE):
                self.ui_click_until_disappear(self.I_UI_SURE, interval=1)
            if self.appear(self.I_STORE_SKILL_101):
                self.buy_skill_101()
            elif self.cnt_coin < 400:
                break
            elif not self.refresh_store():
                break

        logger.info('Finish purchase skill 101')
        while 1:
            self.screenshot()
            if self.in_main():
                break
            if self.appear_then_click(self.I_UI_SURE, interval=1):
                continue
            if self.appear_then_click(self.I_STORE_EXIT, interval=1):
                continue


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('du')
    t = MoonSeaL101(c)
    t.screenshot()

    t.run_l101()
