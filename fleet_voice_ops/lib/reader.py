"""実fleet読み取り層(2データ源統合 + transcript併合)。

データ源(SPEC-initial.md §fleetリーダー):
- 生死: `~/.local/share/devin/cli/session_locks/<id>.lock`(中身=PID)に対して
  `os.kill(pid, 0)` で生存判定。PID再利用の偽陽性はlock_age併用で緩和(注記のみ)
- 活動: `devin list --format json`(cwd=FVO_DEVIN_DIR・既定 ~/Developer)の
  `last_activity_at`(epoch)を正とする。transcriptのmtimeは最大24分古い実測のため使わない
- 詳細: transcripts/<id>.json から transcript.py 経由で併合(存在するもののみ)

対象外: sessions.db / *.claude.jsonl / ~/.claude/projects/

退化動作: `devin list` が失敗・空・非JSONでも落とさず、
lockベースの生死のみで組み立てる(elapsed_sはlock mtimeから近似)。
emitキー集合は固定(欠損は None/0/False で埋める)。
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import time
from typing import Any

from fleet_voice_ops.lib.transcript import DEFAULT_TRANSCRIPTS_DIR, read_session_signals

DEFAULT_DEVIN_DIR = os.path.expanduser("~/Developer")
DEFAULT_LOCKS_DIR = os.path.expanduser("~/.local/share/devin/cli/session_locks")
DEVIN_LIST_TIMEOUT_S = 60


def _devin_list(devin_dir: str) -> list[dict[str, Any]]:
    """`devin list --format json` を実行してセッション一覧を返す。失敗時は []。"""
    try:
        proc = subprocess.run(
            ["devin", "list", "--format", "json"],
            cwd=devin_dir,
            capture_output=True,
            text=True,
            timeout=DEVIN_LIST_TIMEOUT_S,
        )
        if proc.returncode != 0:
            return []
        data = json.loads(proc.stdout)
        return data if isinstance(data, list) else []
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return []


def _lock_pids(locks_dir: str) -> dict[str, tuple[int, float]]:
    """{session_id: (pid, lock_mtime_epoch)}。読めないlockは無視。"""
    out: dict[str, tuple[int, float]] = {}
    for path in glob.glob(os.path.join(locks_dir, "*.lock")):
        sid = os.path.basename(path)[: -len(".lock")]
        try:
            pid = int(open(path).read().strip())
            out[sid] = (pid, os.path.getmtime(path))
        except (OSError, ValueError):
            continue
    return out


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def read_fleet_sessions(
    devin_dir: str | None = None,
    locks_dir: str = DEFAULT_LOCKS_DIR,
    transcripts_dir: str = DEFAULT_TRANSCRIPTS_DIR,
    now: float | None = None,
) -> list[dict[str, Any]]:
    """実fleetのRawSession相当dict一覧を返す(emit前・pid_alive含む内部形)。"""
    devin_dir = devin_dir or os.environ.get("FVO_DEVIN_DIR") or DEFAULT_DEVIN_DIR
    now = now if now is not None else time.time()

    listed = _devin_list(devin_dir)
    locks = _lock_pids(locks_dir)

    by_id: dict[str, dict[str, Any]] = {}
    for s in listed:
        sid = s.get("short_id") or s.get("id")
        if not sid:
            continue
        by_id[sid] = {"last_activity_at": s.get("last_activity_at")}

    # 艦隊の分母 = devin listに載るセッション ∪ 生存PIDのlock。
    # 死んだlockは歴史lock(数百本)であり艦隊ではないため含めない。
    alive_ids = {sid for sid, (pid, _) in locks.items() if _pid_alive(pid)}
    sessions: list[dict[str, Any]] = []
    for sid in sorted(set(by_id) | alive_ids):
        pid, lock_mtime = locks.get(sid, (None, None))
        alive = _pid_alive(pid) if pid is not None else False

        last_activity = by_id.get(sid, {}).get("last_activity_at")
        if last_activity is None and lock_mtime is not None:
            last_activity = lock_mtime  # devin listに無いがlockがあればmtimeで近似
        elapsed_s = max(0, int(now - last_activity)) if last_activity else None

        record: dict[str, Any] = {
            "session_id": sid,
            "last_update": (
                time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(last_activity))
                if last_activity
                else None
            ),
            "elapsed_s": elapsed_s if elapsed_s is not None else 0,
            "pid_alive": alive,
            # 詳細信号(欠損は固定値 — emitキー集合を一定に保つ)
            "last_tool_name": None,
            "has_error": False,
            "step_count": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_cached_tokens": 0,
        }

        signals = read_session_signals(sid, transcripts_dir)
        if signals:
            record.update({k: v for k, v in signals.items() if k != "session_id"})
        sessions.append(record)

    return sessions
