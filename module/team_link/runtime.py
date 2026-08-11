"""Runtime adapter between OAS tasks and the paired state primitives."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Callable, Optional

from module.logger import logger
from module.team_link.orochi_realm_raid_sync import (
    PairPhase,
    PairSyncError,
    PairSyncState,
    validate_pair_configuration,
)


class PairSyncRuntime:
    """A throttled per-task view of one paired synchronization state."""

    def __init__(
        self,
        config,
        *,
        state_dir=None,
        config_dir="config",
        require_realm_raid_opt_in: bool = False,
        clock: Callable[[], float] = time.time,
    ):
        self.config = config
        self.clock = clock
        settings = config.orochi.pair_sync_config
        master_enabled = bool(getattr(settings, "link_enabled", False))
        realm_raid_enabled = bool(
            self.config.realm_raid.orochi_link_config.continue_orochi_after_raid
        )
        self.enabled = master_enabled and (
            realm_raid_enabled if require_realm_raid_opt_in else True
        )
        self.state: Optional[PairSyncState] = None
        self.phase = PairPhase.IDLE
        self.cycle_id = 0
        self.recovery_id = 0
        self.heartbeat_interval = max(1, int(settings.heartbeat_interval_seconds))
        self.peer_unresponsive_seconds = max(3, int(settings.peer_unresponsive_seconds))
        self._next_heartbeat_at = 0.0
        self.max_cycles = max(0, int(settings.cycle_count))

        if not self.enabled:
            return

        validation = validate_pair_configuration(config.config_name, config_dir=config_dir)
        if not validation.valid:
            details = "；".join(validation.errors) or "未知配置错误"
            raise PairSyncError(f"双配置联动校验失败：{details}")

        self.state = PairSyncState(
            config.config_name,
            validation.teammate,
            state_dir=state_dir,
            clock=clock,
        )
        snapshot = self.state.initialize()
        self.cycle_id = int(snapshot["cycle_id"])
        self.recovery_id = int(snapshot["recovery_id"])

    def begin_campaign(self, *, starts_with_raid: bool) -> None:
        if self.enabled and self.state is not None:
            self.state.begin_campaign(self.max_cycles, starts_with_raid=starts_with_raid)

    @property
    def is_leader(self) -> bool:
        role = self.config.orochi.orochi_config.user_status
        return getattr(role, "value", role) == "leader"

    def set_phase(self, phase: PairPhase, *, last_error: str = "") -> None:
        if not self.enabled or self.state is None:
            return
        self.phase = PairPhase(phase)
        member = self.state.heartbeat(
            self.phase,
            last_error=last_error,
            expected_cycle_id=self.cycle_id,
            expected_recovery_id=self.recovery_id,
        )
        self.recovery_id = int(member["recovery_id"])
        self._next_heartbeat_at = self.clock() + self.heartbeat_interval

    def heartbeat_if_due(self, *, force: bool = False) -> None:
        if not self.enabled or self.state is None:
            return
        if force or self.clock() >= self._next_heartbeat_at:
            self.set_phase(self.phase)

    def mark_error(self, message: str) -> None:
        self.set_phase(PairPhase.PAUSED_ERROR, last_error=message)

    def ensure_realm_raid_enabled(self) -> None:
        """Enable RealmRaid only when paired mode actually needs to schedule it."""
        if not self.enabled or self.config.realm_raid.scheduler.enable:
            return

        def update_config():
            self.config.realm_raid.scheduler.enable = True

        self.config.safe_save(update_config)

    def wait_for_raid_release(
        self,
        *,
        sleep: Callable[[float], None] = time.sleep,
    ) -> bool:
        """Wait without game input until both raids finish and leader advances cycle."""
        if not self.enabled or self.state is None:
            return False

        completed_cycle = self.cycle_id
        snapshot = self.state.snapshot()
        if int(snapshot["cycle_id"]) > completed_cycle:
            self.cycle_id = int(snapshot["cycle_id"])
            self.recovery_id = int(snapshot["recovery_id"])
            self.phase = PairPhase.IDLE
            return bool(snapshot["campaign"]["active"])
        try:
            self.set_phase(PairPhase.RAID_DONE)
        except PairSyncError:
            # The leader can advance immediately after this member reports done.
            snapshot = self.state.snapshot()
            if int(snapshot["cycle_id"]) > completed_cycle:
                self.cycle_id = int(snapshot["cycle_id"])
                self.recovery_id = int(snapshot["recovery_id"])
                self.phase = PairPhase.IDLE
                return bool(snapshot["campaign"]["active"])
            raise
        warned_unresponsive = False

        while True:
            snapshot = self.state.snapshot()
            current_cycle = int(snapshot["cycle_id"])
            if current_cycle > completed_cycle:
                self.cycle_id = current_cycle
                self.recovery_id = int(snapshot["recovery_id"])
                self.phase = PairPhase.IDLE
                return bool(snapshot["campaign"]["active"])

            if self.is_leader and self.state.both_in_phase(PairPhase.RAID_DONE):
                try:
                    self.cycle_id, should_continue = self.state.release_completed_cycle(completed_cycle)
                    self.phase = PairPhase.IDLE
                    logger.info(f"双端个人突破均已完成，联动轮次推进至 {self.cycle_id}")
                    return should_continue
                except PairSyncError:
                    # The peer may have observed an already advanced generation.
                    continue

            self.heartbeat_if_due()
            if self.state.peer_unresponsive(self.peer_unresponsive_seconds):
                if not warned_unresponsive:
                    logger.warning(
                        f"队友超过 {self.peer_unresponsive_seconds} 秒无联动心跳，"
                        "保持无加成等待，不启动御魂"
                    )
                    warned_unresponsive = True
            elif warned_unresponsive:
                logger.info("队友联动心跳已恢复，继续等待个人突破完成")
                warned_unresponsive = False
            sleep(self.heartbeat_interval)

    def schedule_orochi_now(self, task) -> None:
        if self.enabled:
            task.set_next_run(task="Orochi", target=datetime.now())
