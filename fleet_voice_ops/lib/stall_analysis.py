"""analyze_stall の agentic実体(SPEC-initial.md §agenticの実体)。

入力=構造信号のみ(elapsed_s/last_tool_name/has_error/step_count/token totals)。
出力=固定スキーマ:
  {"session_id": str,
   "hypotheses": [{"cause": str, "confidence": str(3段), "evidence_signals": [...]}],
   "recommended_action": str}

環境変数 FVO_LLM が設定されていなければ、ルールベースの仮説生成にフォールバックする
(デモ用。実LLM呼出しは本タスクのスコープ外=Day3以降)。
"""
from __future__ import annotations

import os

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"

# evidence_signalsに使ってよい値=第1層許可キーの名のみ(SPEC §プライバシー境界4)
_INPUT_SIGNAL_KEYS = ("elapsed_s", "last_tool_name", "has_error", "step_count")


def _rule_based_hypotheses(signals: dict) -> list[dict]:
    hypotheses: list[dict] = []

    if signals.get("last_tool_name") in {"AskUserQuestion", "ExitPlanMode"}:
        hypotheses.append(
            {
                "cause": "waiting_on_human_input",
                "confidence": CONFIDENCE_HIGH,
                "evidence_signals": ["last_tool_name", "elapsed_s"],
            }
        )

    if signals.get("has_error"):
        hypotheses.append(
            {
                "cause": "blocked_by_unresolved_error",
                "confidence": CONFIDENCE_MEDIUM,
                "evidence_signals": ["has_error", "elapsed_s"],
            }
        )

    if signals.get("step_count", 0) > 30 and signals.get("elapsed_s", 0) > 600:
        hypotheses.append(
            {
                "cause": "long_running_task_may_be_stuck_in_loop",
                "confidence": CONFIDENCE_LOW,
                "evidence_signals": ["step_count", "elapsed_s"],
            }
        )

    if not hypotheses:
        hypotheses.append(
            {
                "cause": "unknown_stall_cause",
                "confidence": CONFIDENCE_LOW,
                "evidence_signals": ["elapsed_s"],
            }
        )

    # 2〜3個に収める(SPEC: 複数(2〜3個))
    if len(hypotheses) == 1:
        hypotheses.append(
            {
                "cause": "idle_waiting_for_external_dependency",
                "confidence": CONFIDENCE_LOW,
                "evidence_signals": ["elapsed_s", "last_tool_name"],
            }
        )
    return hypotheses[:3]


def _recommended_action(signals: dict, hypotheses: list[dict]) -> str:
    """推奨アクションを生死と整合させる — 稼働中セッションへのresumeは
    実測で拒否される(interrupt-test-evidence.md)ため指さない。"""
    top_cause = hypotheses[0]["cause"]
    dead = signals.get("status") == "dead"
    if top_cause == "waiting_on_human_input":
        return "respond_to_pending_question"
    if top_cause == "blocked_by_unresolved_error":
        return "resume_with_confirmation" if dead else "inspect_error_before_resume"
    return "resume_with_confirmation" if dead else "monitor_or_send_followup"


def analyze_stall(session_id: str, signals: dict) -> dict:
    """構造信号から仮説を立て、固定スキーマで返す。

    signals は第1層許可キーのみを含む dict を渡すこと(呼び出し側の責務)。
    """
    if os.environ.get("FVO_LLM"):
        # 実LLM呼出しは本タスクのスコープ外(Day3以降)。
        # 将来実装時もsignals以外(title/working_directory等)を入力に混ぜない。
        raise NotImplementedError("FVO_LLM経路は未実装(ルールベースにフォールバックすること)")

    hypotheses = _rule_based_hypotheses(signals)
    return {
        "session_id": session_id,
        "hypotheses": hypotheses,
        "recommended_action": _recommended_action(signals, hypotheses),
    }
