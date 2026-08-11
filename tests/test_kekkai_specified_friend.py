import unittest
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np

from tasks.KekkaiUtilize.config import SelectFriendList
from tasks.KekkaiUtilize.script_task import ScriptTask


class KekkaiSpecifiedFriendTest(unittest.TestCase):
    def test_unpublished_red_tag_is_detected(self):
        image = np.zeros((720, 1280, 3), dtype=np.uint8)
        x1, y1, x2, y2 = ScriptTask.FRIEND_UNPUBLISHED_ROI
        image[y1:y2, x1:x2] = (180, 30, 30)

        ratio = ScriptTask._friend_unpublished_red_ratio(image)

        self.assertGreaterEqual(ratio, ScriptTask.FRIEND_UNPUBLISHED_RED_RATIO)

    def test_public_realm_has_no_unpublished_red_tag(self):
        image = np.full((720, 1280, 3), (180, 150, 110), dtype=np.uint8)

        ratio = ScriptTask._friend_unpublished_red_ratio(image)

        self.assertLess(ratio, ScriptTask.FRIEND_UNPUBLISHED_RED_RATIO)

    def test_unique_long_name_tolerates_partial_ocr(self):
        self.assertTrue(
            ScriptTask._single_friend_result_matches('柴可拖拉机', '[abl可拉机')
        )

    def test_unique_long_name_rejects_unrelated_friend(self):
        self.assertFalse(
            ScriptTask._single_friend_result_matches('柴可拖拉机', '偷弟')
        )

    def test_multiple_searches_restore_input_method_only_once(self):
        task = object.__new__(ScriptTask)
        with patch.object(ScriptTask, '_current_input_method', return_value='original.ime') as current, \
                patch.object(ScriptTask, '_select_specified_friend_with_active_ime', return_value=True), \
                patch.object(ScriptTask, '_restore_input_method') as restore:
            result = task._select_specified_friend(
                '偷弟,柴可拖拉机', '', '', SelectFriendList.SAME_SERVER
            )

        self.assertTrue(result)
        current.assert_called_once_with()
        restore.assert_called_once_with('original.ime')

    def test_last_best_friend_skips_duplicate_search(self):
        task = object.__new__(ScriptTask)
        with patch.object(ScriptTask, 'device', new_callable=PropertyMock, return_value=MagicMock()), \
                patch.object(ScriptTask, 'switch_friend_list'), \
                patch.object(ScriptTask, '_search_friend_name', return_value=True) as search, \
                patch.object(ScriptTask, 'screenshot'), \
                patch.object(ScriptTask, '_find_exact_friend_result', return_value=(420, 267)), \
                patch.object(
                    ScriptTask,
                    '_specified_friend_card_info',
                    side_effect=[('斗鱼', 101, 101.0), ('斗鱼', 143, 143.0)],
                ), \
                patch('tasks.KekkaiUtilize.script_task.time.sleep'):
            result = task._select_specified_friend_with_active_ime(
                '偷弟,柴可拖拉机', '', '', SelectFriendList.SAME_SERVER
            )

        self.assertTrue(result)
        self.assertEqual(search.call_count, 2)
        search.assert_any_call('偷弟', restore_input_method=False)
        search.assert_any_call('柴可拖拉机', restore_input_method=False)


if __name__ == '__main__':
    unittest.main()
