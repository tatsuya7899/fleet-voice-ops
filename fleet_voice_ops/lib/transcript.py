"""単一セッションのtranscript `.json`から詳細信号を抽出する。

対象: `~/.local/share/devin/cli/transcripts/<short_id>.json`(ATIF-v1.7)。
`source=="system"`のstepは構造的に除外する(注入されたシステム文脈が主経路のため)。

返すdictはemit層(filter_layer1)にそのまま通せる許可キーのみで構成する。
内部フィールド(prompts/arguments/observation本文/path)は一切含めない。

注意: transcriptのmtimeは実活動より最大24分古い実測があるため、
停滞判定の正(last_activity)には使わない。詳細信号の供給のみ。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

ERROR_PATTERN = re.compile(r"error|failed|exception|traceback", re.IGNORECASE)

DEFAULT_TRANSCRIPTS_DIR = os.path.expanduser("~/.local/share/devin/cli/transcripts")


def _extract_signals(doc: dict[str, Any], session_id: str) -> dict[str, Any]:
    """transcript文書からemit可能な構造信号だけを取り出す。"""
    steps = [s for s in doc.get("steps", []) if s.get("source") != "system"]

    last_tool_name: str | None = None
    for step in reversed(steps):
        calls = step.get("tool_calls") or []
        if calls:
            last_tool_name = calls[-1].get("function_name")
            break

    has_error = False
    for step in reversed(steps):
        obs = step.get("observation")
        if not isinstance(obs, dict):
            continue
        results = obs.get("results") or []
        if not results:
            continue
        has_error = any(ERROR_PATTERN.search(str(r.get("content", ""))) for r in results)
        break

    metrics = doc.get("final_metrics") or {}
    step_count = metrics.get("total_steps") if metrics.get("total_steps") is not None else len(steps)

    signals: dict[str, Any] = {
        "session_id": session_id,
        "last_tool_name": last_tool_name,
        "has_error": has_error,
        "step_count": step_count,
    }
    for key in ("total_prompt_tokens", "total_completion_tokens", "total_cached_tokens"):
        if metrics.get(key) is not None:
            signals[key] = metrics[key]
    return signals


def read_session_signals(
    session_id: str, transcripts_dir: str = DEFAULT_TRANSCRIPTS_DIR
) -> dict[str, Any] | None:
    """`<session_id>.json` から詳細信号を読む。ファイルが無ければ None。"""
    path = os.path.join(transcripts_dir, f"{session_id}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return _extract_signals(doc, session_id)
