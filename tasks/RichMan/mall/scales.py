# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time

from module.logger import logger
from tasks.Component.Buy.buy import Buy
from tasks.RichMan.config import Scales as ScalesConfig
from tasks.RichMan.mall.navbar import MallNavbar
from tasks.Utils.config_enum import DemonClass


class Scales(Buy, MallNavbar):

    def execute_scales(self, con: ScalesConfig = None):
        logger.hr('蛇皮商店', 2)
        if not con:
            con = self.config.rich_man.scales
        if not con.enable:
            logger.info('鳞丸未启用')
            return
        self._enter_scales()

        # 朴素的御魂
        if con.orochi_scales:
            self._scales_orochi()
        # 潮汐御魂
        if con.picture_book_scrap:
            self._scales_sea()
        self.save_image()

    def _scales_buy_confirm(self, start_click):
        count_click = 0
        while 1:
            self.screenshot()
            if count_click > 3:
                logger.warning(f"{start_click},无兑换次数，退出")
                return False
            if self.appear(self.I_SCA_SELECT_1):
                return True
            if self.appear(self.I_BUY_PLUS):
                break
            if self.appear_then_click(start_click, interval=1):
                count_click += 1
                continue
        # 设置购买的数量
        self.appear_then_click(self.I_BUY_PLUS, interval=0.4)
        time.sleep(1)
        self.appear_then_click(self.I_BUY_PLUS, interval=0.4)
        return True

    def _scales_buy_more(self, start_click):
        # 重写
        if not self._scales_buy_confirm(start_click):
            return False
        # 购买确认
        while 1:
            self.screenshot()
            if self.appear(self.I_SCA_SIX_STAR) or self.appear(self.I_SCA_REWARD):
                logger.info('鳞丸购买成功')
                time.sleep(1)
                while 1:
                    self.screenshot()
                    if not self.appear(self.I_SCA_SIX_STAR) and self.appear(start_click):
                        break
                    if self.click(self.C_SCA_SOULS_GET_1, interval=1):
                        continue
                # 收获购买的东西
                logger.info('鳞丸获取成功')
                break

            if self.click(self.C_BUY_MORE, interval=5):
                continue

    def _scales_buy_sea_more(self, start_click):
        if not self._scales_buy_confirm(start_click):
            return False
        while 1:
            self.screenshot()
            if not self.appear(self.I_BUY_PLUS):
                break
            if self.appear_then_click(self.I_BUY_SEA, interval=3):
                time.sleep(3)
                continue
        while 1:
            self.screenshot()
            if self.appear(self.I_SCA_PICTURE_BOOK):
                break
            if self.click(self.C_SCA_SOULS_GET_1, interval=3):
                continue
        return True

    def _scales_orochi(self):
        logger.hr('朴素的御魂', 2)
        # 检查是否出现了购买按钮
        if not self.wait_until_appear(self.I_SCA_OROCHI_SCALES, wait_time=3):
            logger.warning('朴素御魂未出现')
            self.save_image(wait_time=0, image_type=True, push_flag=True, content="未发现紫色蛇皮")
            return
        self._scales_buy_more(self.I_SCA_OROCHI_SCALES)

    def _scales_sea(self):
        logger.hr('潮汐御魂', 2)
        # 检查是否出现了购买按钮
        if not self.wait_until_appear(self.I_SCA_PICTURE_BOOK, wait_time=3):
            logger.warning('潮汐御魂未出现')
            self.save_image(wait_time=0, image_type=True, push_flag=True, content="未发现潮汐御魂")
            return
        buy_sea_count = 0
        while 1:
            if not self._scales_buy_sea_more(self.I_SCA_PICTURE_BOOK):
                break
            time.sleep(0.5)
            buy_sea_count += 1
            if buy_sea_count > 3:
                logger.warning('无兑换次数，退出')
                break


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('mi')
    t = Scales(c)

    t.execute_scales()

    # 朴素的御魂
    # con = c.rich_man.scales
    # t._scales_orochi(con.orochi_scales)
    # t._scales_sea(buy_number=30)
