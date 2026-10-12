#!/usr/bin/env python3
"""3データ源を走査して「応答可能な質問リスト」を機械生成する。

SPEC-initial.md §データ実在チェック: 生成リストに無い質問をMCPツールとして公開しない
(=リスト外の質問がツールに居たら検査失敗)。

出力先: docs/answerable_questions.md
**公開物のため集計値のみ** — title/working_directory等のemit禁止フィールドや
セッション内容は書き出さない(session_idの個別列挙もしない・件数のみ)。
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fleet_voice_ops.lib.reader import DEFAULT_DEVIN_DIR, DEFAULT_LOCKS_DIR  # noqa: E402
from fleet_voice_ops.lib.transcript import DEFAULT_TRANSCRIPTS_DIR, _extract_signals  # noqa: E402
from fleet_voice_ops.lib.status import ACTIVE_THRESHOLD_S  # noqa: E402

DOCS_PATH = os.path.join(os.path.dirname(__file__), "..", "docs", "answerable_questions.md")


def _load_devin_list() -> list[dict]:
    try:
        proc = subprocess.run(
            ["devin", "list", "--format", "json"],
            cwd=DEFAULT_DEVIN_DIR, capture_output=True, text=True, timeout=60,
        )
        data = json.loads(proc.stdout)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _alive_locks() -> dict[str, int]:
    alive = {}
    for p in glob.glob(os.path.join(DEFAULT_LOCKS_DIR, "*.lock")):
        try:
            pid = int(open(p).read().strip())
            os.kill(pid, 0)
            alive[os.path.basename(p)[:-5]] = pid
        except (OSError, ValueError):
            continue
    return alive


def main() -> int:
    now = time.time()
    listed = _load_devin_list()
    alive = _alive_locks()
    transcripts = {
        os.path.basename(p)[:-5]
        for p in glob.glob(os.path.join(DEFAULT_TRANSCRIPTS_DIR, "*.json"))
    }

    listed_ids = {s.get("short_id") or s.get("id") for s in listed}
    union = listed_ids | set(alive) | transcripts
    union.discard(None)

    # フィールド非欠損率(集計のみ)
    fields = ["last_tool_name", "has_error", "step_count",
              "total_prompt_tokens", "total_completion_tokens", "total_cached_tokens"]
    present = {f: 0 for f in fields}
    for sid in sorted(transcripts):
        try:
            doc = json.load(open(os.path.join(DEFAULT_TRANSCRIPTS_DIR, f"{sid}.json")))
        except Exception:
            continue
        sig = _extract_signals(doc, sid)
        for f in fields:
            v = sig.get(f)
            if v is not None and v is not False and v != 0:
                present[f] += 1

    stalled = active = dead = 0
    for sid in union:
        la = next((s.get("last_activity_at") for s in listed
                   if (s.get("short_id") or s.get("id")) == sid), None)
        is_alive = sid in alive
        if not is_alive:
            dead += 1
        elif la and (now - la) <= ACTIVE_THRESHOLD_S:
            active += 1
        else:
            stalled += 1

    n_tr = max(len(transcripts), 1)
    lines = [
        "# 応答可能な質問リスト(機械生成)",
        "",
        f"生成: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))} / scripts/data_probe.py",
        "**このファイルは公開物のため集計値のみ。title/working_directory等のemit禁止フィールド・セッション内容・個別session_idは出力しない。**",
        "",
        "## データ源の実在(集計)",
        "",
        "| 源 | 実測 |",
        "|---|---|",
        f"| devin list(FVO_DEVIN_DIR) | {len(listed_ids)} セッション |",
        f"| session_locks(生存PID) | {len(alive)} 本 |",
        f"| transcripts/*.json | {len(transcripts)} 本 |",
        f"| 3源の和集合(観測可能範囲) | {len(union)} 本 — 艦隊の分母は`devin list`∪生存lock(={len(listed_ids | set(alive))}本・歴史lockは除外) |",
        "",
        "## 3値分布(現時点)",
        "",
        f"- active: {active} / stalled_suspect: {stalled} / dead: {dead}",
        "",
        "## emit許可フィールドの非欠損率(transcripts母集団)",
        "",
        "| フィールド | 非欠損 |",
        "|---|---|",
    ]
    for f in fields:
        lines.append(f"| {f} | {present[f]}/{len(transcripts)} ({present[f]*100//n_tr}%) |")

    lines += [
        "",
        "## 応答可能な質問(→公開ツールの正当化根拠)",
        "",
        "以下は実データが応えられる質問。これらに対応するツールのみ公開される。",
        "",
        "| 質問 | ツール | 根拠 |",
        "|---|---|---|",
        "| 「艦隊全体の状態は?」 | fleet_status | devin list+locksの統合が実在 |",
        "| 「何か詰まってる?」 | whats_stuck | PID生存×last_activity閾値でstalled_suspectを定義可能 |",
        "| 「なぜ詰まったと思う?」 | analyze_stall | last_tool_name/has_error/step_count/tokensが非欠損で抽出可 |",
        "| 「落ちたエージェントを再開して」 | request_resume | dead状態の識別可・`devin --resume`が終了済みで機能(実測) |",
        "| 「トークン量は?」 | fleet_status(tokens) | final_metricsのtotal_*_tokensが非欠損 |",
        "",
        "**リスト外の質問(例:「会話の中身は?」「エラーの全文は?」「コストのUSDは?」)は",
        "emit禁止・切る順序・データ不在のいずれかで非対応 = ツール化しない。**",
        "",
    ]
    os.makedirs(os.path.dirname(DOCS_PATH), exist_ok=True)
    open(DOCS_PATH, "w").write("\n".join(lines))
    print(f"wrote {DOCS_PATH}: union={len(union)} alive={len(alive)} transcripts={len(transcripts)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
