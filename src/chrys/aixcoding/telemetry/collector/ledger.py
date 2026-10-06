# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Idempotency ledger: per-session "analysed/reported" state (TS ``ledger.ts``).

Failed runs never advance the ledger (a revision whose report failed is
re-analysed on retry, ADR 0041 decision 5); unreadable/corrupt files are
treated as an empty ledger and archived as ``.corrupt-<ts>`` for diagnosis.
The ledger stores metadata only — never session content.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from chrys.aixcoding.telemetry.collector.locator import safe_file_id

_HEX_64 = re.compile(r"^[0-9a-f]{64}$")
_MAX_TURNS = 100_000


@dataclass(frozen=True, slots=True)
class LedgerTurn:
    turn_id: str
    content_hash: str
    reported_at: str


@dataclass(frozen=True, slots=True)
class CollectorLedger:
    version: int
    session_id: str
    last_revision_hash: str
    last_analyzed_at: str
    analysis_version: int
    # Revision-level single state (D-5): success only when every segment
    # succeeded; failures leave no ledger entry — no 'failed'/'partial' state.
    report_state: str
    turns: list[LedgerTurn] = field(default_factory=list)
    source_path: str = ""


def _validate(ledger: CollectorLedger) -> None:
    if ledger.version != 1:
        msg = "ledger version must be 1"
        raise ValueError(msg)
    if not 1 <= len(ledger.session_id) <= 512:
        msg = "session id out of bounds"
        raise ValueError(msg)
    if not _HEX_64.match(ledger.last_revision_hash):
        msg = "revision hash must be 64 hex chars"
        raise ValueError(msg)
    if ledger.analysis_version <= 0:
        msg = "analysis_version must be positive"
        raise ValueError(msg)
    if ledger.report_state != "reported":
        msg = "report_state must be 'reported'"
        raise ValueError(msg)
    if len(ledger.turns) > _MAX_TURNS:
        msg = "too many turns"
        raise ValueError(msg)
    for turn in ledger.turns:
        if not turn.turn_id or not _HEX_64.match(turn.content_hash) or not turn.reported_at:
            msg = "invalid turn entry"
            raise ValueError(msg)


def _ledger_path(state_dir: str, session_id: str) -> Path:
    return Path(state_dir) / "ledger" / f"{safe_file_id(session_id)}.json"


def load_ledger(state_dir: str, session_id: str) -> CollectorLedger | None:
    """Load the ledger; corrupt files are archived and treated as empty."""
    path = _ledger_path(state_dir, session_id)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = json.loads(raw)
        ledger = CollectorLedger(
            version=data["version"],
            session_id=data["session_id"],
            last_revision_hash=data["last_revision_hash"],
            last_analyzed_at=data["last_analyzed_at"],
            analysis_version=data["analysis_version"],
            report_state=data["report_state"],
            turns=[LedgerTurn(**turn) for turn in data["turns"]],
            source_path=data["source_path"],
        )
        _validate(ledger)
        return ledger
    except KeyError, TypeError, ValueError, json.JSONDecodeError:
        pass  # Corrupt → archive and rebuild.
    with contextlib.suppress(OSError):
        path.rename(f"{path}.corrupt-{int(time.time() * 1000)}")
    return None


def save_ledger(state_dir: str, ledger: CollectorLedger) -> None:
    """Atomically persist the ledger (tmp + rename), owner-only directory."""
    _validate(ledger)
    directory = Path(state_dir) / "ledger"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    ledger_id = safe_file_id(ledger.session_id)
    path = directory / f"{ledger_id}.json"
    temporary = directory / f".{ledger_id}-{os.getpid()}-{time.time_ns()}.tmp"
    payload = asdict(ledger)
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
