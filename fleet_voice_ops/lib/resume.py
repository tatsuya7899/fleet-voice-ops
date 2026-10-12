"""request_resume の実体(SPEC-initial.md §構成要素3・書き込み1本)。

書き込みは `devin --resume <session_id> --print "<prompt>"` の1本のみ。
承認(confirm=true)が無ければコマンドは組み立てず、
序数でなくセッション名を復唱する確認応答を返す(序数読み替え事故の防止)。

既定でdry-run(環境変数 FVO_DRY_RUN が "0" のときのみ実実行)。
本タスクのスコープ(fixtureのみ)では実行は想定しないため、
実行系コードパスはあっても呼ばれない前提とする。
"""
from __future__ import annotations

import os
import subprocess

DEFAULT_RESUME_PROMPT = "please continue"


def build_resume_command(session_id: str, prompt: str = DEFAULT_RESUME_PROMPT) -> list[str]:
    return ["devin", "--resume", session_id, "--print", prompt]


def request_resume(session_id: str, confirm: bool = False, session_alive: bool | None = None) -> dict:
    """confirm=False: セッション名を復唱して承認を求める応答。
    confirm=True: dry-runモードならコマンドをechoするだけで実実行しない。

    session_alive=True の場合は発射を拒否する(実測: docs/interrupt-test-evidence.md —
    稼働中セッションへの --resume は「failed to start ACP agent session」で失敗する)。
    対象は終了済み(pid_alive=False)セッションに限定する。
    """
    if session_alive is True:
        return {
            "session_id": session_id,
            "action": "refused",
            "message": f"{session_id} は稼働中のため再開できません(対象は終了済みセッションです)",
        }

    if not confirm:
        return {
            "session_id": session_id,
            "action": "confirmation_required",
            "message": f"{session_id} を再開します。よろしいですか?",
        }

    command = build_resume_command(session_id)
    dry_run = os.environ.get("FVO_DRY_RUN", "1") != "0"

    if dry_run:
        return {
            "session_id": session_id,
            "action": "dry_run",
            "command": command,
            "message": f"[dry-run] {' '.join(command)}",
        }

    proc = subprocess.run(command, capture_output=True, text=True, timeout=30)
    return {
        "session_id": session_id,
        "action": "executed",
        "command": command,
        "returncode": proc.returncode,
    }
