import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from module.config.config import Config
from module.config.config_model import ConfigModel
from tasks.Component.config_base import Time
from tasks.KekkaiUtilize.config import (
    KekkaiUtilize,
    NoTakeoverConfig,
    PrewarmConfig,
    kekkai_prewarm_dispatch_at,
    no_takeover_resume_at,
)


class NoTakeoverWindowTest(unittest.TestCase):
    def test_same_start_and_end_disables_window(self):
        config = NoTakeoverConfig(enable=True)
        self.assertIsNone(no_takeover_resume_at(config, datetime(2026, 8, 10, 12, 0)))

    def test_normal_daily_window(self):
        config = NoTakeoverConfig(
            enable=True,
            start_time_1=Time(12, 0),
            end_time_1=Time(14, 0),
        )
        self.assertEqual(
            no_takeover_resume_at(config, datetime(2026, 8, 10, 13, 30)),
            datetime(2026, 8, 10, 14, 0),
        )
        self.assertIsNone(no_takeover_resume_at(config, datetime(2026, 8, 10, 14, 0)))

    def test_overnight_window(self):
        config = NoTakeoverConfig(
            enable=True,
            start_time_1=Time(23, 0),
            end_time_1=Time(7, 0),
        )
        expected = datetime(2026, 8, 11, 7, 0)
        self.assertEqual(no_takeover_resume_at(config, datetime(2026, 8, 10, 23, 30)), expected)
        self.assertEqual(
            no_takeover_resume_at(config, datetime(2026, 8, 11, 6, 59)), expected
        )
        self.assertIsNone(no_takeover_resume_at(config, expected))

    def test_overlapping_windows_resume_after_both_end(self):
        config = NoTakeoverConfig(
            enable=True,
            start_time_1=Time(12, 0),
            end_time_1=Time(14, 0),
            start_time_2=Time(13, 30),
            end_time_2=Time(15, 0),
        )
        self.assertEqual(
            no_takeover_resume_at(config, datetime(2026, 8, 10, 13, 0)),
            datetime(2026, 8, 10, 15, 0),
        )

    def test_kekkai_utilize_owns_guard_with_safe_defaults(self):
        config = KekkaiUtilize()
        self.assertIsInstance(config.no_takeover_config, NoTakeoverConfig)
        self.assertFalse(config.no_takeover_config.enable)
        self.assertIsInstance(config.prewarm_config, PrewarmConfig)
        self.assertFalse(config.prewarm_config.enable)

    def test_prewarm_keeps_original_due_time(self):
        config = KekkaiUtilize(
            prewarm_config=PrewarmConfig(enable=True, lead_seconds=60)
        )
        due_at = datetime(2026, 8, 10, 12, 0)

        dispatch_at = kekkai_prewarm_dispatch_at(
            config, due_at, datetime(2026, 8, 10, 11, 59, 30)
        )

        self.assertEqual(dispatch_at, datetime(2026, 8, 10, 11, 59))
        self.assertEqual(due_at, datetime(2026, 8, 10, 12, 0))

    def test_prewarm_does_not_enter_no_takeover_window(self):
        config = KekkaiUtilize(
            prewarm_config=PrewarmConfig(enable=True, lead_seconds=60),
            no_takeover_config=NoTakeoverConfig(
                enable=True,
                start_time_1=Time(11, 0),
                end_time_1=Time(13, 0),
            ),
        )

        self.assertIsNone(kekkai_prewarm_dispatch_at(
            config,
            datetime(2026, 8, 10, 12, 0),
            datetime(2026, 8, 10, 11, 59, 30),
        ))

    def test_scheduler_dispatches_prewarm_without_changing_actual_due(self):
        model = ConfigModel()
        for _, task_config in model:
            if hasattr(task_config, 'scheduler'):
                task_config.scheduler.enable = False
        now = datetime.now().replace(microsecond=0)
        due_at = now + timedelta(seconds=30)
        model.kekkai_utilize.scheduler.enable = True
        model.kekkai_utilize.scheduler.next_run = due_at
        model.kekkai_utilize.prewarm_config = PrewarmConfig(enable=True, lead_seconds=60)

        config = object.__new__(Config)
        config.model = model
        config._model_dict_cache = model.dict()
        config.task = None

        config.update_scheduler()

        self.assertEqual([task.command for task in config.pending_task], ['KekkaiUtilize'])
        self.assertEqual(
            model.kekkai_utilize.scheduler.next_run,
            due_at,
        )

    def test_prewarm_does_not_overtake_an_earlier_task(self):
        model = ConfigModel()
        for _, task_config in model:
            if hasattr(task_config, 'scheduler'):
                task_config.scheduler.enable = False
        now = datetime.now().replace(microsecond=0)
        model.kekkai_utilize.scheduler.enable = True
        model.kekkai_utilize.scheduler.next_run = now + timedelta(seconds=30)
        model.kekkai_utilize.prewarm_config = PrewarmConfig(enable=True, lead_seconds=60)
        model.area_boss.scheduler.enable = True
        model.area_boss.scheduler.next_run = now + timedelta(seconds=10)

        config = object.__new__(Config)
        config.model = model
        config._model_dict_cache = model.dict()
        config.task = None

        config.update_scheduler()

        self.assertEqual(config.pending_task, [])
        self.assertEqual(config.waiting_task[0].command, 'AreaBoss')

    def test_scheduler_delays_only_kekkai_utilize(self):
        fixed_now = datetime(2026, 8, 10, 13, 0)

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 8, 10, 13, 0)

        model = ConfigModel()
        model.kekkai_utilize.scheduler.enable = True
        model.kekkai_utilize.no_takeover_config = NoTakeoverConfig(
            enable=True,
            start_time_1=Time(12, 0),
            end_time_1=Time(14, 0),
        )
        model.area_boss.scheduler.enable = True

        cache = model.dict()
        cache['kekkai_utilize']['scheduler']['next_run'] = '2026-08-10 12:00:00'
        cache['area_boss']['scheduler']['next_run'] = '2026-08-10 12:00:00'

        config = object.__new__(Config)
        config.model = model
        config._model_dict_cache = cache
        config.task = None

        with patch('module.config.config.datetime', FixedDateTime), \
                patch('tasks.KekkaiUtilize.config.datetime', FixedDateTime):
            config.update_scheduler()

        self.assertIn('AreaBoss', [task.command for task in config.pending_task])
        delayed = next(task for task in config.waiting_task if task.command == 'KekkaiUtilize')
        self.assertEqual(delayed.next_run, fixed_now.replace(hour=14))


if __name__ == '__main__':
    unittest.main()
