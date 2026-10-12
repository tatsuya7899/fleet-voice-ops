"""fleetリーダー(2データ源)とtranscript抽出のテスト — 合成fixtureのみ使用。

実transcript・devin listの生データはテストから読まない(内部情報を含むため)。
"""
from __future__ import annotations

import json
import os

from fleet_voice_ops.lib import reader, transcript
from fleet_voice_ops.lib.status import classify


def _write_json(path: str, doc: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(doc, f)


def _synthetic_transcript(with_metrics: bool = True) -> dict:
    return {
        "schema_version": "ATIF-v1.7",
        "session_id": "unit-test-sid",
        "steps": [
            {"source": "system", "message": {"content": "SECRET_SYSTEM_CONTEXT"}, "tool_calls": []},
            {
                "source": "agent",
                "tool_calls": [{"function_name": "exec", "arguments": {"command": "ls /secret/path"}}],
                "observation": {"results": [{"content": "ok"}]},
            },
            {
                "source": "agent",
                "tool_calls": [{"function_name": "AskUserQuestion", "arguments": {}}],
                "observation": {"results": [{"content": "Error: tool failed with exception"}]},
            },
        ],
        "final_metrics": {
            "total_steps": 3,
            "total_prompt_tokens": 100,
            "total_completion_tokens": 50,
            "total_cached_tokens": 10,
        },
    } if with_metrics else {
        "steps": [{"source": "agent", "tool_calls": [{"function_name": "exec"}], "observation": {"results": [{"content": "done"}]}}],
        "final_metrics": {},
    }


def test_transcript_extracts_signals_and_drops_system(tmp_path):
    tdir = str(tmp_path)
    _write_json(os.path.join(tdir, "unit-test-sid.json"), _synthetic_transcript())

    sig = transcript.read_session_signals("unit-test-sid", tdir)
    assert sig is not None
    assert sig["session_id"] == "unit-test-sid"
    assert sig["last_tool_name"] == "AskUserQuestion"  # 最終tool_callsの関数名
    assert sig["has_error"] is True  # 最終resultのエラー文言を検出
    assert sig["step_count"] == 3  # final_metrics.total_steps
    assert sig["total_prompt_tokens"] == 100
    # systemステップ由来の値・内部フィールドは出さない
    assert "SECRET_SYSTEM_CONTEXT" not in json.dumps(sig)
    assert "arguments" not in sig and "observation" not in sig


def test_transcript_missing_returns_none(tmp_path):
    assert transcript.read_session_signals("no-such", str(tmp_path)) is None


def test_transcript_missing_metrics_falls_back(tmp_path):
    tdir = str(tmp_path)
    _write_json(os.path.join(tdir, "unit-test-sid.json"), _synthetic_transcript(with_metrics=False))
    sig = transcript.read_session_signals("unit-test-sid", tdir)
    assert sig["step_count"] == 1  # len(steps)へフォールバック
    assert sig["has_error"] is False


def test_classify_three_values():
    assert classify(True, 100) == "active"
    assert classify(True, 601) == "stalled_suspect"
    assert classify(False, 601) == "dead"


def test_reader_merges_locks_and_transcripts(tmp_path, monkeypatch):
    locks = str(tmp_path / "locks")
    tdir = str(tmp_path / "transcripts")
    os.makedirs(locks)
    os.makedirs(tdir)

    me = os.getpid()  # 生存PIDとして自分を使う
    dead_pid = 2**22  # 存在しないPID(再利用性を考えて十分大きい値)
    with open(os.path.join(locks, "live-sid.lock"), "w") as f:
        f.write(str(me))
    with open(os.path.join(locks, "dead-sid.lock"), "w") as f:
        f.write(str(dead_pid))

    _write_json(os.path.join(tdir, "live-sid.json"), _synthetic_transcript())
    # dead-sidはdevin listに載る(=艦隊の分母に入る)がlock PIDは死んでいる
    monkeypatch.setattr(reader, "_devin_list", lambda d: [
        {"short_id": "dead-sid", "last_activity_at": 1_000_000},
        {"short_id": "stale-lock-sid", "last_activity_at": 1_000_000},
    ])
    monkeypatch.setenv("FVO_DEVIN_DIR", str(tmp_path))

    sessions = {s["session_id"]: s for s in reader.read_fleet_sessions(
        devin_dir=str(tmp_path), locks_dir=locks, transcripts_dir=tdir)}

    assert sessions["live-sid"]["pid_alive"] is True
    assert sessions["live-sid"]["last_tool_name"] == "AskUserQuestion"  # transcript併合
    assert sessions["dead-sid"]["pid_alive"] is False
    assert sessions["dead-sid"]["last_tool_name"] is None  # transcript不在・固定キーで欠損
    # 死んだlockでdevin listにも無い履歴は艦隊に含めない — この環境に dead-lock だけの
    # 「lock-only dead」は無いので、代わりにstale-lock-sidが分母に入ることを確認
    assert "stale-lock-sid" in sessions and sessions["stale-lock-sid"]["pid_alive"] is False
    # emitキー集合が揃っている(欠損はNone/0/False)
    for key in ("session_id", "last_update", "elapsed_s", "last_tool_name",
                "has_error", "step_count", "total_prompt_tokens"):
        assert key in sessions["dead-sid"]


def test_reader_survives_devin_list_failure(tmp_path, monkeypatch):
    locks = str(tmp_path / "locks")
    tdir = str(tmp_path / "transcripts")
    os.makedirs(locks)
    os.makedirs(tdir)
    with open(os.path.join(locks, "live-sid.lock"), "w") as f:
        f.write(str(os.getpid()))
    monkeypatch.setattr(reader, "_devin_list", lambda d: [])
    sessions = reader.read_fleet_sessions(
        devin_dir=str(tmp_path), locks_dir=locks, transcripts_dir=tdir)
    assert len(sessions) == 1 and sessions[0]["pid_alive"] is True
