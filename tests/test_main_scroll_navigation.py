import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_main
from tasks.Restart.assets import RestartAssets


class MainScrollNavigationTest(unittest.TestCase):
    def test_open_and_closed_scroll_both_identify_main_page(self):
        self.assertIn(RestartAssets.I_LOGIN_SCROOLL_OPEN, page_main.check_button)
        self.assertIn(RestartAssets.I_LOGIN_SCROOLL_CLOSE, page_main.check_button)

    def test_scroll_transition_blocks_page_link_until_open(self):
        game = object.__new__(GameUi)
        page = SimpleNamespace(
            additional=[RestartAssets.I_LOGIN_SCROOLL_CLOSE]
        )

        with patch.object(GameUi, 'appear_then_operate', return_value=True), \
                patch.object(GameUi, '_wait_main_scroll_open', return_value=False):
            self.assertFalse(game.run_additional(page, interval=0.6))

    def test_scroll_wait_succeeds_after_open_state_appears(self):
        game = object.__new__(GameUi)

        with patch.object(GameUi, 'screenshot', return_value=None), \
                patch.object(GameUi, 'appear', side_effect=[False, True]), \
                patch('tasks.GameUi.game_ui.sleep', return_value=None):
            self.assertTrue(game._wait_main_scroll_open(timeout=1))


if __name__ == '__main__':
    unittest.main()
