"""fixtureデータ(デモ用・固定値)。

SPEC-initial.md の「作業順序」Day1-2どおり、実transcriptは読まない。
艦隊の頭数=生存PID数(実測4本)に合わせて4セッションを固定する。

このモジュールは「内部で一度読み込んだ生データ」を模す層であり、
title/working_directory などemit禁止の情報も意図的に含める
(SPEC §プライバシー境界: 「読まない」は実装不能なので emit 境界で絞る方式を検証するため)。
"""
from __future__ import annotations

from typing import TypedDict


class RawSession(TypedDict):
    session_id: str
    title: str
    working_directory: str
    last_update: str
    elapsed_s: int
    last_tool_name: str
    has_error: bool
    step_count: int
    total_input_tokens: int
    total_output_tokens: int
    pid_alive: bool


# 架空のセッション名(実在する名前は使わない)。
FIXTURE_SESSIONS: list[RawSession] = [
    {
        "session_id": "demo-amber",
        "title": "Refactor billing module",
        "working_directory": "/Users/demo/projects/billing",
        "last_update": "2026-10-13T09:58:00Z",
        "elapsed_s": 60,
        "last_tool_name": "Bash",
        "has_error": False,
        "step_count": 12,
        "total_input_tokens": 5200,
        "total_output_tokens": 1800,
        "pid_alive": True,
    },
    {
        # stalled_suspect: PID生存・last_activityが30分(1800秒)超過・入力待ち相当のツールで停止
        "session_id": "demo-birch",
        "title": "Investigate flaky integration test",
        "working_directory": "/Users/demo/projects/checkout",
        "last_update": "2026-10-13T09:29:00Z",
        "elapsed_s": 1800,
        "last_tool_name": "AskUserQuestion",
        "has_error": False,
        "step_count": 41,
        "total_input_tokens": 48000,
        "total_output_tokens": 9100,
        "pid_alive": True,
    },
    {
        "session_id": "demo-cedar",
        "title": "Write onboarding docs",
        "working_directory": "/Users/demo/projects/docs-site",
        "last_update": "2026-10-13T09:57:00Z",
        "elapsed_s": 120,
        "last_tool_name": "Write",
        "has_error": False,
        "step_count": 8,
        "total_input_tokens": 3100,
        "total_output_tokens": 900,
        "pid_alive": True,
    },
    {
        # dead: PID不在
        "session_id": "demo-driftwood",
        "title": "Migrate CI pipeline",
        "working_directory": "/Users/demo/projects/infra",
        "last_update": "2026-10-13T06:10:00Z",
        "elapsed_s": 14280,
        "last_tool_name": "Bash",
        "has_error": True,
        "step_count": 77,
        "total_input_tokens": 102000,
        "total_output_tokens": 21000,
        "pid_alive": False,
    },
]


def get_fixture_sessions() -> list[RawSession]:
    """内部データの生レコード一覧を返す(emitフィルタ適用前・テスト/内部処理専用)。"""
    return list(FIXTURE_SESSIONS)


def get_fixture_session(session_id: str) -> RawSession | None:
    for s in FIXTURE_SESSIONS:
        if s["session_id"] == session_id:
            return s
    return None
