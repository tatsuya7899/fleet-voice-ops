"""SPEC-initial.md §プライバシー境界 受入条件①:
第1層ツールの応答JSONキー集合が許可リストと完全一致すること。
(emit禁止として名指しされた title / working_directory が絶対に出ないこと)
"""
from __future__ import annotations

from fleet_voice_ops.app.tools import fleet_status, whats_stuck
from fleet_voice_ops.lib.emit import FORBIDDEN_KEYS, is_allowed_layer1_key


def test_fleet_status_keys_match_allowlist_exactly():
    sessions = fleet_status()
    assert sessions, "fixtureが空では検証にならない"
    for session in sessions:
        for key in session.keys():
            assert is_allowed_layer1_key(key), f"許可リスト外のキーが含まれている: {key}"
        for forbidden in FORBIDDEN_KEYS:
            assert forbidden not in session


def test_fleet_status_contains_four_sessions_with_one_stalled_suspect():
    sessions = fleet_status()
    assert len(sessions) == 4
    stalled = [s for s in sessions if s["status"] == "stalled_suspect"]
    assert len(stalled) == 1


def test_whats_stuck_returns_only_stalled_suspect_sessions():
    stuck = whats_stuck()
    assert len(stuck) == 1
    for session in stuck:
        assert session["status"] == "stalled_suspect"
        for key in session.keys():
            assert is_allowed_layer1_key(key)
        for forbidden in FORBIDDEN_KEYS:
            assert forbidden not in session
