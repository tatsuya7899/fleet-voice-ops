# 応答可能な質問リスト(機械生成)

生成: 2026-10-13 07:14:48 / scripts/data_probe.py
**このファイルは公開物のため集計値のみ。title/working_directory等のemit禁止フィールド・セッション内容・個別session_idは出力しない。**

## データ源の実在(集計)

| 源 | 実測 |
|---|---|
| devin list(FVO_DEVIN_DIR) | 50 セッション |
| session_locks(生存PID) | 4 本 |
| transcripts/*.json | 87 本 |
| 3源の和集合(観測可能範囲) | 116 本 — 艦隊の分母は`devin list`∪生存lock(=50本・歴史lockは除外) |

## 3値分布(現時点)

- active: 4 / stalled_suspect: 0 / dead: 112

## emit許可フィールドの非欠損率(transcripts母集団)

| フィールド | 非欠損 |
|---|---|
| last_tool_name | 86/87 (98%) |
| has_error | 7/87 (8%) |
| step_count | 87/87 (100%) |
| total_prompt_tokens | 87/87 (100%) |
| total_completion_tokens | 87/87 (100%) |
| total_cached_tokens | 87/87 (100%) |

## 応答可能な質問(→公開ツールの正当化根拠)

以下は実データが応えられる質問。これらに対応するツールのみ公開される。

| 質問 | ツール | 根拠 |
|---|---|---|
| 「艦隊全体の状態は?」 | fleet_status | devin list+locksの統合が実在 |
| 「何か詰まってる?」 | whats_stuck | PID生存×last_activity閾値でstalled_suspectを定義可能 |
| 「なぜ詰まったと思う?」 | analyze_stall | last_tool_name/has_error/step_count/tokensが非欠損で抽出可 |
| 「落ちたエージェントを再開して」 | request_resume | dead状態の識別可・`devin --resume`が終了済みで機能(実測) |
| 「トークン量は?」 | fleet_status(tokens) | final_metricsのtotal_*_tokensが非欠損 |

**リスト外の質問(例:「会話の中身は?」「エラーの全文は?」「コストのUSDは?」)は
emit禁止・切る順序・データ不在のいずれかで非対応 = ツール化しない。**
