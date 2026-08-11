# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

from datetime import datetime
from time import sleep

from module.base.timer import Timer
from module.exception import GameStuckError
from module.exception import TaskEnd
from module.logger import logger
from tasks.Component.GeneralBuff.general_buff import GeneralBuff
from tasks.Component.LoginHarvest.login_base import LoginBase
from tasks.Component.SwitchAccount.assets import SwitchAccountAssets
from tasks.GameUi.assets import GameUiAssets
from tasks.Restart.assets import RestartAssets
from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_main
from tasks.WantedQuests.assets import WantedQuestsAssets


class LoginHandler(LoginBase, RestartAssets, GameUiAssets, GeneralBuff):
    character: str

    def __init__(self, *wargs, **kwargs):
        super().__init__(*wargs, **kwargs)
        self.character = self.config.restart.login_character_config.character
        self.O_LOGIN_SPECIFIC_SERVE.keyword = self.character
        self.mail_harvested = 0  # 添加执行标记

    def app_handle_login(self) -> bool:
        self.device.stuck_record_clear()
        self.device.click_record_clear()
        self._app_handle_login()
        # if self.config.restart.harvest_config.enable:
        # self.check_login(self.config.global_game.costume_config)
        self.harvest(self.config.restart.harvest_config.enable_mail)
        if self.config.restart.harvest_config.enable_courtyard_affairs:
            GameUi(self.config).ui_goto_page(page_main)
            self.courtyard_affairs()
        return True

    def courtyard_affairs(self):
        """
        庭院事务
        """
        notes_button = [self.I_COURTYARD_AFFAIRS_NOTES, self.I_COURTYARD_AFFAIRS_NOTES1]
        if not self.ui_click(notes_button, self.I_COURTYARD_AFFAIRS_PAGE, timeout=2):
            logger.warning('进入庭院事务超时！')
            return False
        while 1:
            self.screenshot()
            if self.appear(self.I_NO_TASKS_COMPLETE):
                logger.warning('⚠️ 暂无可完成事务！')
                return True
            if self.appear(self.I_SUCCESS_CLAIMED):
                logger.info('✅ 庭院事务领取成功！')
                return True
            # 点击确认
            if self.appear_then_click(self.I_UI_CONFIRM, interval=1):
                continue
            # 点击取消
            # if self.appear(self.I_LOGIN_CANCEL_BATTLE):
            #     self.ui_click_until_disappear(self.I_LOGIN_CANCEL_BATTLE)
            #     return True
            if self.appear_then_click(self.I_COMPLETE_WITH_ONE_CLICK, interval=1):
                continue
            if self.appear_then_click(self.I_DAILY, interval=1):
                continue

    def _app_handle_login(self):
        """
        最终是在庭院界面
        :return:
        """
        logger.hr('应用登录')
        self.device.stuck_record_add(timeout=600)
        while 1:
            self.screenshot()
            # 渠道服登陆页面
            if self.appear(SwitchAccountAssets.I_QD_READ_AND_AGREED):
                self.set_next_run()
                raise TaskEnd

            if self.appear([WantedQuestsAssets.I_WQ_DONE, WantedQuestsAssets.I_WQ_SEAL]):
                logger.info('✅ 识别到悬赏封印，登录成功')
                break

            # 登录成功
            if self.appear(self.I_LOGIN_SCROOLL_OPEN, interval=1):
                logger.info('✅ 登录成功')
                break
            # 确认进入庭院
            if self.appear_then_click(self.I_LOGIN_SCROOLL_CLOSE, interval=2, threshold=0.9):
                logger.info('打开庭院卷轴')
                continue

            # 4399登录会遇到活动-点击叉号
            if self.appear_then_click(self.I_LOGIN_CLOSE, interval=1):
                logger.info('4399登录会遇到活动-点击叉号')
                continue
            if self.appear_then_click(SwitchAccountAssets.I_ACCEPT_AGREEMENT, interval=1):
                logger.info('接受协议')
                continue

            # 点击取消
            if self.appear_then_click(self.I_CANCEL, interval=0.6):
                logger.info('点击取消按钮')
                continue
            # 右上角的红色的关闭
            if self.appear_then_click(self.I_BACK_RED, interval=0.6):
                logger.info('关闭红色关闭按钮')
                continue
            # 左上角的黄色关闭
            if self.appear_then_click(self.I_BACK_YELLOW, interval=0.6):
                logger.info('关闭黄色关闭按钮')
                continue
            # 点击屏幕进入游戏
            if self.appear(self.I_LOGIN_SPECIFIC_SERVE, interval=0.6) and self.ocr_appear_click(self.O_LOGIN_SPECIFIC_SERVE, interval=0.6):
                logger.info(f'多角色区服选择成功: {self.O_LOGIN_SPECIFIC_SERVE.keyword}')
                while True:
                    self.screenshot()
                    if self.appear(self.I_LOGIN_SPECIFIC_SERVE):
                        self.click(self.C_LOGIN_ENSURE_LOGIN_CHARACTER_IN_SAME_SVR, interval=2)
                        continue
                    break
                logger.info('登录指定用户')
                continue

            # 创建角色, 误入新区直接重启
            if self.appear(self.I_CREATE_ACCOUNT):
                logger.warning('创建角色, 误入新区直接重启')
                raise GameStuckError('出现创建角色界面')
            # 点击’进入游戏‘
            if not self.appear(self.I_LOGIN_8):
                continue
            if self.appear(self.I_CHARACTARS, interval=1):
                # https://github.com/runhey/OnmyojiAutoScript/issues/585
                self.device.click(x=246, y=535)
            self._wait_kekkai_prewarm_at_enter_game()
            if self.ocr_appear_click(self.O_LOGIN_ENTER_GAME, interval=3):
                self.wait_until_appear(self.I_LOGIN_SPECIFIC_SERVE, True, wait_time=5)
                continue

    def _wait_kekkai_prewarm_at_enter_game(self) -> bool:
        """预热启动时停在“进入游戏”页，到原定寄养时间再放行。"""
        task = getattr(self.config, 'task', None)
        kekkai = getattr(self.config, 'kekkai_utilize', None)
        if task is None or getattr(task, 'command', None) != 'KekkaiUtilize' or kekkai is None:
            return False
        prewarm = kekkai.prewarm_config
        if not prewarm.enable:
            return False

        due_at = kekkai.scheduler.next_run
        remaining = (due_at - datetime.now()).total_seconds()
        # 只处理由提前唤起窗口触发的任务，避免手动运行时意外等待很久。
        max_expected_wait = max(30, min(300, int(prewarm.lead_seconds))) + 15
        if remaining <= 0 or remaining > max_expected_wait:
            return False

        logger.info(
            '结界寄养预热完成，停在“进入游戏”界面等待；原定时间: %s，剩余 %.1f 秒',
            due_at, remaining,
        )
        while True:
            remaining = (due_at - datetime.now()).total_seconds()
            if remaining <= 0:
                break
            # 等待本身是预期行为，持续清理卡住记录，不能触发掉线重启。
            self.device.stuck_record_clear()
            sleep(min(0.5, remaining))
        logger.info('结界寄养时间已到，立即点击“进入游戏”')
        return True

    def harvest(self, enable_mail=False):
        """
        获得奖励
        :return: 如果没有发现任何奖励后退出
        """
        logger.hr('收取奖励')
        timer_harvest = Timer(2)  # 如果连续2秒没有发现任何奖励，退出
        while 1:
            self.screenshot()

            # 是否启用插画？-点击取消
            if self.appear_then_click(self.I_CANCEL):
                logger.info('是否启用插画？-点击取消')
                continue
            # 红色的关闭
            if self.appear_then_click(self.I_BACK_RED, interval=1):
                timer_harvest.reset()
                continue
            # 点击'获得奖励'
            if self.ui_reward_appear_click():
                timer_harvest.reset()
                continue
            # 获得奖励
            if self.appear_then_click(self.I_REWARD, interval=0.2):
                timer_harvest.reset()
                continue
            # 偶尔会打开到聊天频道
            if self.appear_then_click(self.I_HARVEST_CHAT_CLOSE, interval=1):
                timer_harvest.reset()
                continue
            # 偶尔会进入其他页面
            # 左上角的黄色关闭
            if self.appear_then_click(self.I_BACK_YELLOW, interval=0.6):
                timer_harvest.reset()
                logger.info('关闭黄色关闭按钮')
                continue
            # 关闭宠物小屋
            if self.appear_then_click(self.I_HARVEST_BACK_PET_HOUSE, interval=0.6):
                timer_harvest.reset()
                logger.info('关闭黄色关闭按钮')
                continue
            if self.appear_then_click(self.I_LIAO_MESSAGE, interval=1):
                timer_harvest.reset()
                logger.info('关闭寮消息通知')
                continue
            # 关闭阴阳师精灵提示
            if self.appear_then_click(self.I_LOGIN_LOGIN_ONMYOJI_GENIE):
                logger.info("关闭阴阳师精灵提示")
                continue
            # 各种邀请框
            self.reject_invite()

            # # 勾玉
            # if self.appear_then_click(self.I_HARVEST_JADE, interval=1.5):
            #     timer_harvest.reset()
            #     continue
            # # 签到
            # if self.appear_then_click(self.I_HARVEST_SIGN, interval=1.5):
            #     self.wait_until_appear(self.I_HARVEST_SIGN_2, wait_time=2)
            #     timer_harvest.reset()
            #     continue
            # # 某些活动的特殊签到，有空看到就删掉
            # if self.appear_then_click(self.I_HARVEST_SIGN_3, interval=0.7):
            #     timer_harvest.reset()
            #     continue
            # if self.appear_then_click(self.I_HARVEST_SIGN_4, interval=1):
            #     timer_harvest.reset()
            #     continue
            # if self.appear_then_click(self.I_HARVEST_SIGN_2, interval=1.5):
            #     self.wait_until_appear(self.I_LOGIN_RED_CLOSE, wait_time=2)
            #     timer_harvest.reset()
            #     continue
            # # 999天的签到福袋
            # if self.appear_then_click(self.I_HARVEST_SIGN_999, interval=1.5):
            #     timer_harvest.reset()
            #     continue
            # # 体力
            # if self.appear_then_click(self.I_HARVEST_AP, interval=1, threshold=0.7):
            #     timer_harvest.reset()
            #     continue
            # # 御魂觉醒加成
            # if self.appear_then_click(self.I_HARVEST_SOUL, interval=1):
            #     timer_harvest.reset()
            #     continue
            # # 寮包
            # if self.appear_then_click(self.I_HARVEST_GUILD_REWARD, interval=2):
            #     timer_harvest.reset()
            #     continue
            # 自选御魂
            # if self.appear(self.I_HARVEST_SOUL_1):
            #     logger.info('Select soul 1')
            #     self.ui_click(self.I_HARVEST_SOUL_1, stop=self.I_HARVEST_SOUL_2)
            #     self.ui_click(self.I_HARVEST_SOUL_2, stop=self.I_HARVEST_SOUL_3, interval=3)
            #     self.ui_click_until_disappear(click=self.I_HARVEST_SOUL_3)
            #     timer_harvest.reset()
            #     continue

            # 判断是否勾选了收取邮件（不收取邮件可以查看每日收获）
            if enable_mail:
                # 只执行一次邮件收取
                if self.mail_harvested < 3:
                    if self.appear(self.I_MAIL_RED_DOTS, interval=1) and self.appear_then_click(
                            self.I_HARVEST_MAIL_TOP_RIGHT, interval=1):
                        if self.wait_until_appear(self.I_HARVEST_MAIL_TITLE, wait_time=2):
                            while 1:
                                self.screenshot()
                                # 如果没有出现 ‘收取全部’ 也没有出现 ‘还未读的邮件’ 那就可以退出了
                                if not self.appear(self.I_HARVEST_MAIL_ALL) and not self.appear(
                                        self.I_HARVEST_MAIL_OPEN) and not self.appear(self.I_CANCEL):
                                    logger.info('邮件已全部收取')
                                    break
                                if self.appear_then_click(self.I_CANCEL, interval=1):
                                    continue
                                if self.appear_then_click(self.I_HARVEST_MAIL_ALL, interval=1):
                                    self.wait_until_appear_then_click(self.I_HARVEST_MAIL_CONFIRM, wait_time=2)
                                    continue
                                if self.appear_then_click(self.I_HARVEST_MAIL_OPEN, interval=1):
                                    continue
                        timer_harvest.reset()
                        self.mail_harvested += 1  # 设置标记为已执行
                        continue

            # 3秒内没有发现任何奖励，退出
            if not timer_harvest.started():
                timer_harvest.start()
            else:
                if timer_harvest.reached():
                    logger.info('没有更多奖励')
                    return

    def set_specific_usr(self, character: str):
        self.character = character
        self.O_LOGIN_SPECIFIC_SERVE.keyword = character

# if __name__ == '__main__':
#     from module.config.config import Config
#     c = Config('wy')
#     t = LoginHandler(c)
#     t.app_handle_login()
