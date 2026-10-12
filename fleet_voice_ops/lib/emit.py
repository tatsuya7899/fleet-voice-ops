"""emit境界(SPEC-initial.md §プライバシー境界)。

第1層(データ層・事実)のemit許可キー:
  session_id / last_update / elapsed_s / last_tool_name / has_error / step_count / total_*_tokens
加えて、fleet_status/whats_stuckが返す3値(`status`)は本タスク委任文(B節)で
明示的に要求されているデータ層の事実であり、title/working_directoryと同じ
機微クラスではないため許可キーに含める。

emit禁止として名指しされているキー: title / working_directory / working_directory_display
"""
from __future__ import annotations

import re

TOKEN_KEY_PATTERN = re.compile(r"^total_.*_tokens$")

# リテラルで固定されたemit許可キー(status含む・上記docstring参照)
ALLOWED_LAYER1_LITERAL_KEYS = frozenset(
    {
        "session_id",
        "last_update",
        "elapsed_s",
        "last_tool_name",
        "has_error",
        "step_count",
        "status",
    }
)

# emit禁止として名指しされているキー(フィルタで必ず落とす)
FORBIDDEN_KEYS = frozenset({"title", "working_directory", "working_directory_display"})


def is_allowed_layer1_key(key: str) -> bool:
    """キー名が第1層のemit許可リストに合致するか(total_*_tokens はパターン一致)。"""
    if key in ALLOWED_LAYER1_LITERAL_KEYS:
        return True
    return bool(TOKEN_KEY_PATTERN.match(key))


def filter_layer1(raw: dict) -> dict:
    """生レコードから許可キーのみを残す(禁止キーは必ず除外)。"""
    return {k: v for k, v in raw.items() if is_allowed_layer1_key(k) and k not in FORBIDDEN_KEYS}


# 第2層(推論層・analyze_stall出力)の固定スキーマ
LAYER2_TOP_KEYS = frozenset({"session_id", "hypotheses", "recommended_action"})
LAYER2_HYPOTHESIS_KEYS = frozenset({"cause", "confidence", "evidence_signals"})
