"""MCPツールの本体実装(app層。lib層のみに依存・一方向)。"""
from __future__ import annotations

import os
import time

from fleet_voice_ops.lib.emit import filter_layer1
from fleet_voice_ops.lib.fixtures import get_fixture_sessions
from fleet_voice_ops.lib.reader import read_fleet_sessions
from fleet_voice_ops.lib.resume import request_resume as _request_resume
from fleet_voice_ops.lib.stall_analysis import analyze_stall as _analyze_stall
from fleet_voice_ops.lib.status import classify

_REAL_CACHE: dict[str, object] = {"at": 0.0, "sessions": []}
_REAL_CACHE_TTL_S = 30


def _use_real() -> bool:
    return os.environ.get("FVO_DATA_SOURCE") == "real"


def _raw_sessions() -> list[dict]:
    """データ源切替(FVO_DATA_SOURCE=fixture|real・既定fixture)。
    realは30秒キャッシュ(devin list subprocessの頻発を抑える)。"""
    if not _use_real():
        return get_fixture_sessions()
    if time.time() - _REAL_CACHE["at"] > _REAL_CACHE_TTL_S:
        _REAL_CACHE["sessions"] = read_fleet_sessions()
        _REAL_CACHE["at"] = time.time()
    return list(_REAL_CACHE["sessions"])


def _raw_session(session_id: str) -> dict | None:
    for s in _raw_sessions():
        if s.get("session_id") == session_id:
            return s
    return None


def _emit_session(raw: dict) -> dict:
    status = classify(raw["pid_alive"], raw["elapsed_s"])
    enriched = dict(raw)
    enriched["status"] = status
    return filter_layer1(enriched)


def fleet_status() -> list[dict]:
    """全セッションの3値一覧(active/stalled_suspect/dead)。"""
    return [_emit_session(raw) for raw in _raw_sessions()]


def whats_stuck() -> list[dict]:
    """stalled_suspectのセッション名+経過秒+last_tool_nameのみ。"""
    return [s for s in fleet_status() if s["status"] == "stalled_suspect"]


def analyze_stall(session_id: str) -> dict:
    """agentic実体: 構造信号から停滞原因の仮説を立てて返す。"""
    raw = _raw_session(session_id)
    if raw is None:
        raise ValueError(f"unknown session_id: {session_id}")
    signals = filter_layer1(raw)
    return _analyze_stall(session_id, signals)


def request_resume(session_id: str, confirm: bool = False) -> dict:
    """承認(confirm=true)付きの再開指示。confirm=falseはセッション名の復唱確認。
    稼働中セッションへの発射は実測で失敗するため lib 層で拒否する。"""
    raw = _raw_session(session_id)
    return _request_resume(session_id, confirm=confirm, session_alive=(raw or {}).get("pid_alive"))
