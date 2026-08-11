"""State primitives for paired Orochi and Realm Raid tasks.

This module deliberately contains no screenshot, click or task-scheduling code. It
only provides a locked, atomic state file which two OAS configuration processes can
use as a small rendezvous point.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Optional

from filelock import FileLock

from module.config.atomicwrites import atomic_write


STATE_VERSION = 1
CONFIG_NAME_PATTERN = re.compile(r"^[^/\\]+$")


class PairSyncError(RuntimeError):
    """Raised when paired state is invalid or an update is stale."""


class PairPhase(str, Enum):
    IDLE = "idle"
    WAITING_OROCHI = "waiting_orochi"
    OROCHI_RUNNING = "orochi_running"
    READY_FOR_RAID = "ready_for_raid"
    RAID_RUNNING = "raid_running"
    RAID_DONE = "raid_done"
    RECOVERY_REQUIRED = "recovery_required"
    RECONNECTING = "reconnecting"
    RECOVERING = "recovering"
    READY_TO_REGROUP = "ready_to_regroup"
    PAUSED_ERROR = "paused_error"


@dataclass(frozen=True)
class PairValidationResult:
    enabled: bool
    valid: bool
    errors: tuple[str, ...] = ()
    teammate: str = ""


def normalize_config_name(name: str) -> str:
    """Return a safe config stem used for comparisons and state keys."""
    value = str(name or "").strip()
    if value.lower().endswith(".json"):
        value = value[:-5].strip()
    if not value or not CONFIG_NAME_PATTERN.fullmatch(value) or value in {".", ".."}:
        raise PairSyncError(f"无效的配置名称: {name!r}")
    return value


def _member_key(name: str) -> str:
    return normalize_config_name(name).casefold()


def pair_id(first: str, second: str) -> str:
    names = sorted((_member_key(first), _member_key(second)))
    if names[0] == names[1]:
        raise PairSyncError("队友配置不能选择当前配置自身")
    return hashlib.sha256("\0".join(names).encode("utf-8")).hexdigest()[:24]


class PairSyncState:
    """Locked JSON state shared by exactly two OAS configurations."""

    def __init__(
        self,
        current_config: str,
        teammate_config: str,
        state_dir: Optional[os.PathLike[str] | str] = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.current_config = normalize_config_name(current_config)
        self.teammate_config = normalize_config_name(teammate_config)
        self.current_key = _member_key(self.current_config)
        self.teammate_key = _member_key(self.teammate_config)
        self.pair_id = pair_id(self.current_config, self.teammate_config)
        self.state_dir = Path(state_dir) if state_dir else Path.cwd() / "tmp" / "team_link"
        self.state_file = self.state_dir / f"orochi_realm_raid_{self.pair_id}.json"
        self.lock_file = Path(f"{self.state_file}.lock")
        self.clock = clock

    def _empty_state(self) -> Dict[str, Any]:
        now = self.clock()
        members: Dict[str, Dict[str, Any]] = {}
        for display_name in (self.current_config, self.teammate_config):
            members[_member_key(display_name)] = {
                "display_name": display_name,
                "phase": PairPhase.IDLE.value,
                "heartbeat_at": 0.0,
                "cycle_id": 0,
                "recovery_id": 0,
                "last_error": "",
            }
        return {
            "version": STATE_VERSION,
            "pair_id": self.pair_id,
            "created_at": now,
            "updated_at": now,
            "cycle_id": 0,
            "recovery_id": 0,
            "recovery": {
                "active": False,
                "reason": "",
                "detected_by": "",
                "started_at": 0.0,
            },
            "campaign": {
                "active": False,
                "start_cycle_id": 0,
                "max_cycles": 1,
                "started_at": 0.0,
            },
            "members": members,
        }

    def _read_unlocked(self) -> Dict[str, Any]:
        if not self.state_file.exists():
            return self._empty_state()
        with self.state_file.open("r", encoding="utf-8") as file:
            state = json.load(file)
        self._validate_state(state)
        state.setdefault("campaign", {
            "active": False,
            "start_cycle_id": int(state.get("cycle_id", 0)),
            "max_cycles": 1,
            "started_at": 0.0,
        })
        return state

    def _write_unlocked(self, state: Dict[str, Any]) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = self.clock()
        with atomic_write(
            str(self.state_file), overwrite=True, encoding="utf-8", newline=""
        ) as file:
            json.dump(state, file, ensure_ascii=False, indent=2, sort_keys=False)

    def _validate_state(self, state: Dict[str, Any]) -> None:
        if state.get("version") != STATE_VERSION or state.get("pair_id") != self.pair_id:
            raise PairSyncError("联动状态文件版本或队伍标识不匹配")
        if set(state.get("members", {})) != {self.current_key, self.teammate_key}:
            raise PairSyncError("联动状态文件中的队伍成员不匹配")

    def _mutate(self, callback: Callable[[Dict[str, Any]], Any]) -> Any:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with FileLock(str(self.lock_file)):
            state = self._read_unlocked()
            result = callback(state)
            self._write_unlocked(state)
            return result

    def initialize(self) -> Dict[str, Any]:
        """Create the state file if needed and return a detached snapshot."""
        return self._mutate(lambda state: json.loads(json.dumps(state)))

    def snapshot(self) -> Dict[str, Any]:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        with FileLock(str(self.lock_file)):
            return json.loads(json.dumps(self._read_unlocked()))

    def heartbeat(
        self,
        phase: PairPhase | str,
        *,
        last_error: str = "",
        expected_cycle_id: Optional[int] = None,
        expected_recovery_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        phase_value = PairPhase(phase).value

        def update(state: Dict[str, Any]) -> Dict[str, Any]:
            if expected_cycle_id is not None and state["cycle_id"] != expected_cycle_id:
                raise PairSyncError("联动轮次已变化，拒绝写入过期状态")
            if expected_recovery_id is not None and state["recovery_id"] != expected_recovery_id:
                raise PairSyncError("恢复轮次已变化，拒绝写入过期状态")
            member = state["members"][self.current_key]
            member.update({
                "phase": phase_value,
                "heartbeat_at": self.clock(),
                "cycle_id": state["cycle_id"],
                "recovery_id": state["recovery_id"],
                "last_error": str(last_error or ""),
            })
            return json.loads(json.dumps(member))

        return self._mutate(update)

    def peer_unresponsive(self, timeout_seconds: float, now: Optional[float] = None) -> bool:
        state = self.snapshot()
        heartbeat_at = float(state["members"][self.teammate_key]["heartbeat_at"])
        current_time = self.clock() if now is None else now
        return heartbeat_at <= 0 or current_time - heartbeat_at > timeout_seconds

    def both_in_phase(self, phases: PairPhase | str | Iterable[PairPhase | str]) -> bool:
        if isinstance(phases, (PairPhase, str)):
            accepted = {PairPhase(phases).value}
        else:
            accepted = {PairPhase(phase).value for phase in phases}
        state = self.snapshot()
        cycle_id = state["cycle_id"]
        return all(
            member["phase"] in accepted and member["cycle_id"] == cycle_id
            for member in state["members"].values()
        )

    def advance_cycle(self, expected_cycle_id: int) -> int:
        def update(state: Dict[str, Any]) -> int:
            if state["cycle_id"] != expected_cycle_id:
                raise PairSyncError("联动轮次已被另一端推进")
            state["cycle_id"] += 1
            for member in state["members"].values():
                member.update({
                    "phase": PairPhase.IDLE.value,
                    "heartbeat_at": 0.0,
                    "cycle_id": state["cycle_id"],
                    "last_error": "",
                })
            return state["cycle_id"]

        return self._mutate(update)

    def begin_campaign(self, max_cycles: int, *, starts_with_raid: bool = False) -> Dict[str, Any]:
        """Create one finite/infinite linked run without resetting an active run."""
        max_cycles = int(max_cycles)
        if max_cycles < 0:
            raise PairSyncError("联动轮数不能小于 0")

        def update(state: Dict[str, Any]) -> Dict[str, Any]:
            campaign = state["campaign"]
            if not campaign["active"]:
                campaign.update({
                    "active": True,
                    # A standalone RealmRaid is a prelude; it should still wake Orochi.
                    "start_cycle_id": state["cycle_id"] + (1 if starts_with_raid else 0),
                    "max_cycles": max_cycles,
                    "started_at": self.clock(),
                })
            elif int(campaign["max_cycles"]) != max_cycles:
                raise PairSyncError("两端设置的联动轮数不一致")
            return json.loads(json.dumps(campaign))

        return self._mutate(update)

    def release_completed_cycle(self, expected_cycle_id: int) -> tuple[int, bool]:
        """Advance once and atomically decide whether another Orochi cycle is due."""
        def update(state: Dict[str, Any]) -> tuple[int, bool]:
            if state["cycle_id"] != expected_cycle_id:
                raise PairSyncError("联动轮次已被另一端推进")
            state["cycle_id"] += 1
            for member in state["members"].values():
                member.update({
                    "phase": PairPhase.IDLE.value,
                    "heartbeat_at": 0.0,
                    "cycle_id": state["cycle_id"],
                    "last_error": "",
                })
            campaign = state["campaign"]
            max_cycles = int(campaign["max_cycles"])
            completed_cycles = state["cycle_id"] - int(campaign["start_cycle_id"])
            should_continue = bool(campaign["active"]) and (
                max_cycles == 0 or completed_cycles < max_cycles
            )
            if not should_continue:
                campaign["active"] = False
            return state["cycle_id"], should_continue

        return self._mutate(update)

    def start_recovery(self, reason: str) -> int:
        """Start one idempotent recovery generation and notify the peer via state."""
        reason = str(reason or "unknown")

        def update(state: Dict[str, Any]) -> int:
            recovery = state["recovery"]
            if not recovery["active"]:
                state["recovery_id"] += 1
                recovery.update({
                    "active": True,
                    "reason": reason,
                    "detected_by": self.current_config,
                    "started_at": self.clock(),
                })
            member = state["members"][self.current_key]
            member.update({
                "phase": PairPhase.RECOVERY_REQUIRED.value,
                "heartbeat_at": self.clock(),
                "cycle_id": state["cycle_id"],
                "recovery_id": state["recovery_id"],
            })
            return state["recovery_id"]

        return self._mutate(update)

    def finish_recovery(self, expected_recovery_id: int) -> None:
        def update(state: Dict[str, Any]) -> None:
            if state["recovery_id"] != expected_recovery_id:
                raise PairSyncError("恢复轮次已变化，拒绝结束过期恢复")
            if not all(
                member["recovery_id"] == expected_recovery_id
                and member["phase"] == PairPhase.READY_TO_REGROUP.value
                for member in state["members"].values()
            ):
                raise PairSyncError("双方尚未完成恢复，不能重新组队")
            state["recovery"].update({
                "active": False,
                "reason": "",
                "detected_by": "",
                "started_at": 0.0,
            })

        self._mutate(update)


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise PairSyncError(f"配置文件不是 JSON 对象: {path.name}")
    return value


def _pair_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    return config.get("orochi", {}).get("pair_sync_config", {})


def _pair_enabled(settings: Dict[str, Any]) -> bool:
    return bool(settings.get("link_enabled", settings.get("enable", False)))


def _role(config: Dict[str, Any]) -> str:
    return str(config.get("orochi", {}).get("orochi_config", {}).get("user_status", ""))


def _find_config(config_dir: Path, name: str) -> Optional[Path]:
    expected = _member_key(name)
    for path in config_dir.glob("*.json"):
        if path.stem.casefold() == expected and "template" not in path.stem.casefold():
            return path
    return None


def validate_pair_configuration(
    current_config: str,
    config_dir: os.PathLike[str] | str = "config",
) -> PairValidationResult:
    """Validate reciprocal teammate selection and leader/member roles."""
    directory = Path(config_dir)
    try:
        current_name = normalize_config_name(current_config)
        current_path = _find_config(directory, current_name)
        if current_path is None:
            return PairValidationResult(True, False, ("当前配置文件不存在",))
        current = _read_json(current_path)
        settings = _pair_settings(current)
        if not _pair_enabled(settings):
            return PairValidationResult(False, True)
        teammate = normalize_config_name(settings.get("teammate_config", ""))
        if _member_key(teammate) == _member_key(current_name):
            return PairValidationResult(True, False, ("队友配置不能选择自己",), teammate)
        teammate_path = _find_config(directory, teammate)
        if teammate_path is None:
            return PairValidationResult(True, False, ("队友配置文件不存在",), teammate)
        peer = _read_json(teammate_path)
        peer_settings = _pair_settings(peer)
        errors = []
        if not _pair_enabled(peer_settings):
            errors.append("队友没有打开联动总开关")
        try:
            points_back = _member_key(peer_settings.get("teammate_config", ""))
        except PairSyncError:
            points_back = ""
        if points_back != _member_key(current_name):
            errors.append("队友配置没有反向选择当前配置")
        roles = {_role(current), _role(peer)}
        if roles != {"leader", "member"}:
            errors.append("两端身份必须恰好为一个队长和一个队员")
        if int(settings.get("cycle_count", 1)) != int(peer_settings.get("cycle_count", 1)):
            errors.append("两端设置的联动轮数不一致")
        return PairValidationResult(True, not errors, tuple(errors), teammate)
    except (OSError, ValueError, json.JSONDecodeError, PairSyncError) as exc:
        return PairValidationResult(True, False, (str(exc),))
