import re
from module.logger import logger
from tasks.SixRealms.moon_sea.skills import MoonSeaSkills
from tasks.GameUi.assets import GameUiAssets


class MoonSeaMap(MoonSeaSkills):

    def enter_island(self):
        self.screenshot()
        if self.appear_then_click_and_wait(GameUiAssets.I_CANCEL, wait_time=1):
            return True
        if self.appear_then_click_and_wait(self.I_SHENMI, wait_time=1):
            return True
        if self.appear_then_click_and_wait(self.I_HUNDUN, wait_time=1):
            return True
        if self.appear_then_click_and_wait(self.I_ZHAN, wait_time=1):
            return True
        if self.appear_then_click_and_wait(self.I_XING, wait_time=1):
            return True
        if self.appear_then_click_and_wait(self.I_NINGXI, wait_time=1):
            return True
        return None

    def activate_store(self) -> bool:
        """
        最后打boss前面激活一次商店买东西
        @return: 有钱够就是True
        """
        if self.cnt_skill101 >= 5:
            # 如果柔风满级就不召唤
            return False
        if self.cnt_coin < 600:
            return False
        self.screenshot()
        if not self.appear(self.I_M_STORE_ACTIVITY):
            return False
        if not self.appear_rgb(self.I_M_STORE_ACTIVITY):
            return False
        remaining_number = self.ocr_result(self.O_REMAINING_NUMBER)
        if '回合' not in remaining_number:
            return False
        match = re.search(r'-?\d+', remaining_number)
        number = int(match.group()) if match else None
        if number is None or number > 3 or number == 0:
            return False

        cnt_act = 0
        logger.info('召唤宁息岛屿')
        while 1:
            self.screenshot()
            if self.appear(self.I_UI_CONFIRM):
                self.ui_click_until_disappear(self.I_UI_CONFIRM, interval=2)
                break
            if cnt_act >= 3:
                logger.warning('商店未激活')
                return False
            if self.appear_then_click(self.I_M_STORE_ACTIVITY, interval=1.5):
                cnt_act += 1
                continue
        self.ui_click(self.I_NINGXI, self.I_STORE_EXIT)
        logger.info('成功进入宁息岛屿')
        return True


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('du')
    t = MoonSeaMap(c)
    # t.screenshot()
    # t.device.image = load_image(r'C:\Users\Ryland\Desktop\Desktop\34.png')
    # match = re.search(r'\d{1,2}', '<17回合后迎战月读')
    # if match:
    #     isl_num = int(match.group())
    #     print(isl_num)

