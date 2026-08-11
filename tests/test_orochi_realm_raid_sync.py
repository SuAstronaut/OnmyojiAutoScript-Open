import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from module.team_link.orochi_realm_raid_sync import (
    PairPhase,
    PairSyncError,
    PairSyncState,
    validate_pair_configuration,
)
from module.team_link.runtime import PairSyncRuntime


class FakeClock:
    def __init__(self, value=100.0):
        self.value = value

    def __call__(self):
        return self.value


class PairSyncStateTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.clock = FakeClock()
        self.first = PairSyncState("窗口5", "窗口6.json", self.temp_dir.name, self.clock)
        self.second = PairSyncState("窗口6", "窗口5", self.temp_dir.name, self.clock)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_both_sides_share_one_state_file_and_barrier(self):
        self.assertEqual(self.first.state_file, self.second.state_file)
        self.first.heartbeat(PairPhase.RAID_DONE)
        self.assertFalse(self.first.both_in_phase(PairPhase.RAID_DONE))
        self.second.heartbeat(PairPhase.RAID_DONE)
        self.assertTrue(self.first.both_in_phase(PairPhase.RAID_DONE))

    def test_peer_timeout_uses_heartbeat_age(self):
        self.second.heartbeat(PairPhase.WAITING_OROCHI)
        self.clock.value += 4.9
        self.assertFalse(self.first.peer_unresponsive(5))
        self.clock.value += 0.2
        self.assertTrue(self.first.peer_unresponsive(5))

    def test_recovery_is_idempotent_and_requires_both_ready(self):
        recovery_id = self.first.start_recovery("account_kicked")
        self.assertEqual(recovery_id, self.second.start_recovery("peer_notified"))
        self.first.heartbeat(PairPhase.READY_TO_REGROUP, expected_recovery_id=recovery_id)
        with self.assertRaises(PairSyncError):
            self.first.finish_recovery(recovery_id)
        self.second.heartbeat(PairPhase.READY_TO_REGROUP, expected_recovery_id=recovery_id)
        self.first.finish_recovery(recovery_id)
        self.assertFalse(self.first.snapshot()["recovery"]["active"])

    def test_stale_cycle_update_is_rejected(self):
        self.first.initialize()
        self.assertEqual(1, self.first.advance_cycle(0))
        with self.assertRaises(PairSyncError):
            self.second.heartbeat(PairPhase.RAID_RUNNING, expected_cycle_id=0)


class PairConfigurationValidationTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_config(self, name, teammate, role, enable=True, cycle_count=1):
        data = {
            "orochi": {
                "pair_sync_config": {
                    "link_enabled": enable,
                    "teammate_config": teammate,
                    "cycle_count": cycle_count,
                },
                "orochi_config": {"user_status": role},
            }
        }
        (self.config_dir / f"{name}.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )

    def test_valid_reciprocal_pair(self):
        self.write_config("窗口5", "窗口6", "leader")
        self.write_config("窗口6", "窗口5", "member")
        result = validate_pair_configuration("窗口5", self.config_dir)
        self.assertTrue(result.enabled)
        self.assertTrue(result.valid)

    def test_rejects_non_reciprocal_pair_and_same_roles(self):
        self.write_config("窗口5", "窗口6", "leader")
        self.write_config("窗口6", "别的配置", "leader")
        result = validate_pair_configuration("窗口5", self.config_dir)
        self.assertFalse(result.valid)
        self.assertIn("队友配置没有反向选择当前配置", result.errors)
        self.assertIn("两端身份必须恰好为一个队长和一个队员", result.errors)

    def test_disabled_mode_keeps_original_behavior(self):
        self.write_config("窗口5", "", "leader", enable=False)
        result = validate_pair_configuration("窗口5", self.config_dir)
        self.assertFalse(result.enabled)
        self.assertTrue(result.valid)

    def test_rejects_different_cycle_counts(self):
        self.write_config("窗口5", "窗口6", "leader", cycle_count=1)
        self.write_config("窗口6", "窗口5", "member", cycle_count=2)
        result = validate_pair_configuration("窗口5", self.config_dir)
        self.assertFalse(result.valid)
        self.assertIn("两端设置的联动轮数不一致", result.errors)


class PairSyncRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.config_dir = self.root / "config"
        self.state_dir = self.root / "state"
        self.config_dir.mkdir()
        self.clock = FakeClock()

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_config(self, name, teammate, role, enable=True, cycle_count=1, raid_opt_in=True):
        data = {
            "orochi": {
                "pair_sync_config": {
                    "link_enabled": enable,
                    "teammate_config": teammate,
                    "cycle_count": cycle_count,
                },
                "orochi_config": {"user_status": role},
            }
        }
        (self.config_dir / f"{name}.json").write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
        pair_settings = SimpleNamespace(
            link_enabled=enable,
            teammate_config=teammate,
            cycle_count=cycle_count,
            heartbeat_interval_seconds=1,
            peer_unresponsive_seconds=5,
        )
        return SimpleNamespace(
            config_name=name,
            orochi=SimpleNamespace(
                pair_sync_config=pair_settings,
                orochi_config=SimpleNamespace(user_status=role),
            ),
            realm_raid=SimpleNamespace(
                scheduler=SimpleNamespace(enable=True),
                orochi_link_config=SimpleNamespace(
                    continue_orochi_after_raid=raid_opt_in,
                ),
            ),
        )

    def test_disabled_runtime_has_no_state_or_side_effect(self):
        config = self.make_config("窗口5", "", "leader", enable=False)
        runtime = PairSyncRuntime(
            config,
            state_dir=self.state_dir,
            config_dir=self.config_dir,
            clock=self.clock,
        )
        runtime.set_phase(PairPhase.RAID_RUNNING)
        self.assertFalse(runtime.enabled)
        self.assertIsNone(runtime.state)
        self.assertFalse(self.state_dir.exists())

    def test_leader_releases_only_after_both_raids_are_done(self):
        leader_config = self.make_config("窗口5", "窗口6", "leader")
        member_config = self.make_config("窗口6", "窗口5", "member")
        leader = PairSyncRuntime(
            leader_config,
            state_dir=self.state_dir,
            config_dir=self.config_dir,
            clock=self.clock,
        )
        member = PairSyncRuntime(
            member_config,
            state_dir=self.state_dir,
            config_dir=self.config_dir,
            clock=self.clock,
        )
        leader.begin_campaign(starts_with_raid=False)
        member.begin_campaign(starts_with_raid=False)
        member.set_phase(PairPhase.RAID_DONE)
        self.assertFalse(leader.wait_for_raid_release(sleep=lambda _: None))
        self.assertFalse(member.wait_for_raid_release(sleep=lambda _: None))
        self.assertEqual(1, leader.cycle_id)
        self.assertEqual(1, member.cycle_id)

    def test_standalone_raid_opt_in_wakes_one_full_orochi_cycle(self):
        leader_config = self.make_config("窗口5", "窗口6", "leader")
        member_config = self.make_config("窗口6", "窗口5", "member")
        leader = PairSyncRuntime(
            leader_config, state_dir=self.state_dir, config_dir=self.config_dir,
            require_realm_raid_opt_in=True, clock=self.clock,
        )
        member = PairSyncRuntime(
            member_config, state_dir=self.state_dir, config_dir=self.config_dir,
            require_realm_raid_opt_in=True, clock=self.clock,
        )
        leader.begin_campaign(starts_with_raid=True)
        member.begin_campaign(starts_with_raid=True)
        member.set_phase(PairPhase.RAID_DONE)
        self.assertTrue(leader.wait_for_raid_release(sleep=lambda _: None))
        self.assertTrue(member.wait_for_raid_release(sleep=lambda _: None))
        # The standalone raid was only the prelude. One configured full
        # Orochi->RealmRaid round is still allowed, then the campaign stops.
        member.set_phase(PairPhase.RAID_DONE)
        self.assertFalse(leader.wait_for_raid_release(sleep=lambda _: None))
        self.assertFalse(member.wait_for_raid_release(sleep=lambda _: None))

    def test_realm_raid_without_its_own_switch_does_not_join_link(self):
        self.make_config("窗口5", "窗口6", "leader", raid_opt_in=False)
        self.make_config("窗口6", "窗口5", "member")
        config = self.make_config("窗口5", "窗口6", "leader", raid_opt_in=False)
        runtime = PairSyncRuntime(
            config, state_dir=self.state_dir, config_dir=self.config_dir,
            require_realm_raid_opt_in=True, clock=self.clock,
        )
        self.assertFalse(runtime.enabled)
        self.assertIsNone(runtime.state)


if __name__ == "__main__":
    unittest.main()
