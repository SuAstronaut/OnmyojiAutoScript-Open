"""百鬼棋局局内页面的退出与结算返回流程。"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from module.exception import GameWaitTooLongError
from module.logger import logger
from tasks.Component.GeneralBattle.assets import GeneralBattleAssets

if TYPE_CHECKING:
    # 仅供类型检查：声明 mixin 最终会被 ScriptTask 混入的能力来源，
    # 使编辑器能解析 self.appear/self.device/self.I_* 等引用。
    from tasks.Chess.assets import ChessAssets
    from tasks.Chess.runtime.settings import ChessRuntimeSettings
    from tasks.GameUi.game_ui import GameUi

    class _ChessTaskBase(GameUi, ChessRuntimeSettings, ChessAssets):
        ...
else:
    _ChessTaskBase = object


class ChessBattleNavigationMixin(_ChessTaskBase):
    """局内退出与结算返回；仅供 ``ScriptTask`` 使用。"""

    CHESS_EXIT_TIMEOUT = 60.0
    CHESS_EXIT_SCREENSHOT_INTERVAL = 0.35

    def chess_result_flow_visible(self) -> bool:
        """检测百鬼棋局大厅或任一结算页面。"""
        return (
            self.appear(self.I_CHECK_CHESS)
            or self.appear(self.I_CHESS_EXIT_TO_LOBBY)
            or self.appear(self.I_CHESS_EXIT_TO_LOBBY_2)
            or self.appear(self.I_CHESS_SHARE)
            or self.appear(self.I_CHECK_CHESS_RANK)
            or self.appear(self.I_CHESS_RANK_GOTO_LOBBY)
        )

    def return_to_chess_lobby(self) -> bool:
        """完成返回按钮、分享页与排名页流程，最终回到棋局大厅。"""
        logger.debug('百鬼棋局结算流程: 返回大厅')
        deadline = time.monotonic() + self.CHESS_EXIT_TIMEOUT
        share_seen = False
        exit_clicked = False
        safe_clicks = 0
        rank_recovery_started = False
        fallback_exit_at = time.monotonic() + 1.5

        while time.monotonic() < deadline:
            self.device.stuck_record_clear()
            self.screenshot()

            if rank_recovery_started and self.appear(self.I_CHECK_CHESS):
                logger.debug('百鬼棋局结算流程: 已从排名页回到大厅')
                return True

            rank_page = self.appear(self.I_CHECK_CHESS_RANK)
            rank_button = self.appear(self.I_CHESS_RANK_GOTO_LOBBY)
            if (rank_page or rank_button) and not exit_clicked:
                rank_recovery_started = True
                if rank_button:
                    self.appear_then_click(
                        self.I_CHESS_RANK_GOTO_LOBBY,
                        interval=1.5,
                    )
                time.sleep(self.CHESS_EXIT_SCREENSHOT_INTERVAL)
                continue

            if not exit_clicked:
                if self.appear(self.I_CHESS_EXIT_TO_LOBBY):
                    self.appear_then_click(
                        self.I_CHESS_EXIT_TO_LOBBY,
                        interval=1.5,
                    )
                    exit_clicked = True
                    time.sleep(self.CHESS_EXIT_SCREENSHOT_INTERVAL)
                    continue
                if self.appear(self.I_CHESS_EXIT_TO_LOBBY_2):
                    self.appear_then_click(
                        self.I_CHESS_EXIT_TO_LOBBY_2,
                        interval=1.5,
                    )
                    exit_clicked = True
                    time.sleep(self.CHESS_EXIT_SCREENSHOT_INTERVAL)
                    continue
                if self.appear(self.I_CHESS_SHARE):
                    exit_clicked = True
                    share_seen = True
                    continue
                if time.monotonic() >= fallback_exit_at:
                    logger.warning(
                        '百鬼棋局结算流程: 未识别到返回按钮, 点击固定返回区域'
                    )
                    self.click(self.I_CHESS_EXIT_TO_LOBBY)
                    exit_clicked = True
                    time.sleep(self.CHESS_EXIT_SCREENSHOT_INTERVAL)
                    continue
                time.sleep(self.CHESS_EXIT_SCREENSHOT_INTERVAL)
                continue

            if not share_seen and self.appear(self.I_CHESS_SHARE):
                share_seen = True

            if not share_seen:
                time.sleep(self.CHESS_EXIT_SCREENSHOT_INTERVAL)
                continue

            if rank_page or rank_button:
                rank_recovery_started = True
                if rank_button:
                    self.appear_then_click(
                        self.I_CHESS_RANK_GOTO_LOBBY,
                        interval=1.5,
                    )
                time.sleep(self.CHESS_EXIT_SCREENSHOT_INTERVAL)
                continue

            if self.appear(self.I_CHECK_CHESS):
                logger.debug(
                    '百鬼棋局结算流程: 分享页后已回到大厅, '
                    f'安全点击次数={safe_clicks}'
                )
                return True

            safe_clicks += 1
            self.click(GeneralBattleAssets.C_REWARD_LEFT)
            time.sleep(self.CHESS_EXIT_SCREENSHOT_INTERVAL)

        raise GameWaitTooLongError('Global Chess: failed to return to lobby after result')

    def exit_chess_battle(self) -> bool:
        """主动退出当前百鬼棋局并完成返回大厅流程。"""
        logger.warning('百鬼棋局页面处理: 退出中断的对局')
        deadline = time.monotonic() + self.CHESS_EXIT_TIMEOUT
        next_exit_click_at = 0.0
        next_confirm_click_at = 0.0
        dialog_seen = False
        confirm_clicked = False

        while time.monotonic() < deadline:
            self.device.stuck_record_clear()
            self.screenshot()

            confirm_visible = self.appear(self.I_CHESS_EXIT_CONFIRM)
            cancel_visible = self.appear(self.I_CHESS_EXIT_CANCEL)
            if confirm_visible or cancel_visible:
                dialog_seen = True

            if dialog_seen and confirm_clicked and not confirm_visible:
                logger.debug('百鬼棋局页面处理: 退出已确认')
                return self.return_to_chess_lobby()

            now = time.monotonic()
            if dialog_seen:
                if confirm_visible and now >= next_confirm_click_at:
                    self.click(self.I_CHESS_EXIT_CONFIRM)
                    confirm_clicked = True
                    next_confirm_click_at = now + 2.0
                time.sleep(self.CHESS_EXIT_SCREENSHOT_INTERVAL)
                continue

            if now >= next_exit_click_at:
                if self.appear(self.I_CHESS_EXIT):
                    self.click(self.I_CHESS_EXIT)
                next_exit_click_at = now + 2.0
            time.sleep(self.CHESS_EXIT_SCREENSHOT_INTERVAL)

        logger.warning(
            '百鬼棋局页面处理超时: '
            f'已见弹窗={dialog_seen}, 已点确认={confirm_clicked}'
        )
        return False
