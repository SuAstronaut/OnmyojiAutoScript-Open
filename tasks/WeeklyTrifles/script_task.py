# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time

from module.base.timer import Timer
from module.exception import TaskEnd
from module.logger import logger
from tasks.DailyTrifles.script_task import ScriptTask as DailyTriflesTask
from tasks.GameUi.page import page_collection, page_area_boss, page_secret_zones
from tasks.WeeklyTrifles.assets import WeeklyTriflesAssets

""" 每周任务 """


class ScriptTask(DailyTriflesTask, WeeklyTriflesAssets):
    def run(self):
        con = self.config.weekly_trifles.trifles
        if con.share_collect:
            self._share_collect()
        if con.share_area_boss:
            self._share_area_boss()
        if con.share_secret:
            self._share_secret()
        if con.broken_amulet:
            self._broken_amulet(con.broken_amulet)

        # self.set_next_run(task='WeeklyTrifles', success=True, finish=False)
        # 设置下一次运行时间是周一
        self.next_run_week(1)
        raise TaskEnd('WeeklyTrifles')

    def click_share(self, wechat) -> bool:
        """
        点击分享
        :param wechat:
        :return:
        """
        # 点击分享
        # self.ui_click(wechat, self.I_WT_QR_CODE)
        while 1:
            self.screenshot()
            if self.appear(self.I_WT_QR_CODE):
                break
            if self.appear_then_click(wechat, interval=2.5):
                continue
        logger.info('点击分享')
        get_timer = Timer(7)
        get_timer.start()
        while 1:
            self.screenshot()
            if self.ui_reward_appear_click():
                logger.info('领取奖励')
                return True
            if self.appear_then_click(self.I_WT_QR_CODE, self.C_WT_WECHAT, interval=4.8):
                self.save_image()
                continue
            if get_timer.reached():
                logger.warning('Share timeout. The reward may have been obtained')
                return False

    def _share_collect(self):
        """
        图鉴分享
        :return:
        """
        logger.hr('分享收集')
        self.ui_goto_page(page_collection)
        # 点击分享
        while 1:
            self.screenshot()
            if self.appear(self.I_WT_QR_CODE):
                break
            if self.appear_then_click(self.I_CANCEL, interval=3):
                continue
            if self.appear_then_click(self.I_WT_SHIKIAGMI, interval=3):
                continue
            if self.appear_then_click(self.I_WT_COLLECT_WECHAT, interval=3):
                continue
            if self.appear_then_click(self.I_COLLECT_WT_SHARE, interval=5):
                continue
        logger.info('点击分享')
        get_timer = Timer(3)
        get_timer.start()
        while 1:
            self.screenshot()

            if self.ui_reward_appear_click():
                logger.info('领取奖励')
                break

            if self.appear_then_click(self.I_WT_QR_CODE, self.C_WT_WECHAT, interval=0.8):
                self.save_image()
                continue
            if get_timer.reached():
                logger.warning('Share timeout. The reward may have been obtained')
                break
        # 返回
        while 1:
            self.screenshot()
            if self.appear(self.I_WT_SHIKIAGMI):
                break
            if self.appear_then_click(self.I_BACK_RED, interval=1):
                continue
            if self.appear_then_click(self.I_BACK_BLUE, interval=1):
                continue
            if self.appear_then_click(self.I_BACK_YELLOW, interval=1):
                continue

    def _share_area_boss(self):
        """
        地鬼分享
        :return:
        """
        logger.hr('分享地域鬼王')
        self.ui_goto_page(page_area_boss)

        # 一路进去
        obtained = False
        while 1:
            self.screenshot()
            if self.appear(self.I_WT_AB_WECHAT):
                break
            if self.appear(self.I_WT_NO_DAY):
                obtained = True
                break
            if self.click(self.C_WT_AB_CLICK, interval=3):
                continue
            if self.appear_then_click(self.I_WT_DAY_BATTLE, interval=3):
                continue
            if self.appear_then_click(self.I_WT_SHARE_AB, interval=3):
                continue
        # 再次检查一次这周有没有领取
        time.sleep(1)
        self.screenshot()
        if not self.appear(self.I_WT_AB_JADE):
            logger.warning('本周已获得')
            obtained = True
        if not obtained:
            # 点击分享
            self.click_share(self.I_WT_AB_WECHAT)

    def _share_secret(self):
        """
        秘闻分享
        :return:
        """
        logger.hr('分享秘闻')
        self.ui_goto_page(page_secret_zones)
        # 一路进去
        while 1:
            self.screenshot()
            if self.appear(self.I_WT_SE_WECHAT):
                break
            if self.appear_then_click(self.I_WT_ENTER_SE, interval=3):
                continue
            if self.appear_then_click(self.I_WT_SE_SHARE, interval=3):
                continue
        logger.info('进入秘闻')
        # 判断是否已经领取
        self.screenshot()
        if self.appear(self.I_WT_SE_WECHAT):
            # 点击分享
            self.click_share(self.I_WT_SE_WECHAT)


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('mi')
    t = ScriptTask(c)
    t.screenshot()
    t._share_collect()

    # t._share_secret()
    # t.click_share(t.I_WT_SE_WECHAT)
