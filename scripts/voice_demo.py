#!/usr/bin/env python3
"""音声往復の最小ローカルクライアント(SPEC-initial.md §音声でしか成立しない動作)。

ブラウザ・外部APIなしで、テキスト入力→MCPツール呼出→print+macOS `say`読み上げ、
の最小実装。実機(Alexa+)には依存しない(受入条件どおり汎用クライアントでも成立する形)。

使い方:
  python scripts/voice_demo.py                      # 対話モード(標準入力から質問)
  python scripts/voice_demo.py "何かあった?"          # 1問1答モード(デモ撮影用)

音声1往復の固定フロー:
  1. 「何かあった?」 → stalled_suspect(入力待ち)とdead(落ちた)を区別して読み上げ、
     dead側へ「再開しますか?」を提案(実測: 稼働中へのresumeは失敗するため)
  2. 「お願い」「resume」等の承認発話 → deadセッションへ request_resume(confirm=True)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fleet_voice_ops.app.tools import fleet_status, request_resume, whats_stuck  # noqa: E402

STUCK_TRIGGERS = ("何かあった", "stuck", "anything stuck", "fleet status")
APPROVE_TRIGGERS = ("お願い", "resume", "approve", "yes", "承認")


def _speak(text: str) -> None:
    print(f"[voice-out] {text}")
    try:
        subprocess.run(["say", text], check=False, timeout=15)
    except FileNotFoundError:
        pass  # mac以外(say未搭載)ではprintのみで続行


def _format_fleet_reply(total: int, stuck: list[dict], dead: list[dict]) -> str:
    """実測どおり「停滞」と「落ちた」を区別して言う(再開可否が違うため)。"""
    parts: list[str] = []
    if stuck:
        s = stuck[0]
        minutes = s["elapsed_s"] // 60
        parts.append(f"1本({s['session_id']})が{minutes}分前から{s['last_tool_name']}待ちで止まっています")
    if dead:
        d = dead[0]
        parts.append(f"1本({d['session_id']})がエラーで落ちています")
    if not parts:
        return f"{total}本のセッションは全て順調に進んでいます。"
    return f"{total}本のうち、" + "・".join(parts) + "。"


def handle_question(text: str, last_stuck_session_id: str | None) -> tuple[str, str | None]:
    """1問を処理し、(応答テキスト, 次ターンに持ち越すセッションID) を返す。

    承認の宛先は「落ちた(dead)」セッション — 実測で稼働中へのresumeは失敗するため
    (docs/interrupt-test-evidence.md)。停滞中セッションは報告のみで再開対象にしない。
    """
    lowered = text.lower()

    if any(t in text or t in lowered for t in APPROVE_TRIGGERS) and last_stuck_session_id:
        result = request_resume(last_stuck_session_id, confirm=True)
        return result["message"], None

    if any(t in text or t in lowered for t in STUCK_TRIGGERS):
        all_sessions = fleet_status()
        stuck = [s for s in all_sessions if s["status"] == "stalled_suspect"]
        dead = [s for s in all_sessions if s["status"] == "dead"]
        reply = _format_fleet_reply(len(all_sessions), stuck, dead)
        if dead:
            reply += f"{dead[0]['session_id']}を再開しますか?"
        next_session = dead[0]["session_id"] if dead else None
        return reply, next_session

    return "すみません、聞き取れませんでした。「何かあった?」と聞いてみてください。", last_stuck_session_id


def run_one_shot(question: str) -> None:
    reply, next_session = handle_question(question, None)
    _speak(reply)
    if next_session:
        approve_reply, _ = handle_question("お願い", next_session)
        _speak(approve_reply)


def run_interactive() -> None:
    last_stuck_session_id: str | None = None
    print("音声デモ(テキスト入力で代替)。Ctrl-Dで終了。")
    try:
        while True:
            question = input("[voice-in] > ")
            reply, last_stuck_session_id = handle_question(question, last_stuck_session_id)
            _speak(reply)
    except EOFError:
        print()


def main(argv: list[str]) -> int:
    if argv:
        run_one_shot(" ".join(argv))
    else:
        run_interactive()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
