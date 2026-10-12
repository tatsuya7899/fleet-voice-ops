# `devin --resume` 割込み可否の実測(2026-10-13)

SPECキルラインの検証項目「`devin --resume`が稼働中セッションへ機能するか」の実測記録。
対象は使い捨てセッション(`chatter-charger`・`devin --print "sleep 240 …"`で起動)。

## 実測結果

| 条件 | 操作 | 結果 |
|---|---|---|
| 稼働中(`sleep 240`実行中・lock PID=61957生存) | `devin --resume chatter-charger --print "INTERRUPT_TEST…"` | **失敗**: `Error: failed to start ACP agent session`。元セッションは生存・処理継続(4分後にSLEEP_DONEで正常完走) |
| 終了後(lock残存・PID死) | 同上(`RESUME_WORKS`要求) | **成功**: 応答 `RESUME_WORKS` |

## 意味(実測確定)

- `--resume` は**稼働中(ACPセッション張り付き中)への割込みには使えない**。ロック中のセッションに2つ目のACPエージェントはアタッチできない
- `--resume` は**終了済み(PID死)セッションでは機能する**
- 書き込み1本 `request_resume` の対象は **`dead` かつ未完の作業を持つセッション**に限定する。`stalled_suspect`(PID生存)へresumeを打つと上記エラーで失敗するため、ツール側で対象の3値を検査してから発射するか、エラーをそのまま返す設計が必要
- デモシナリオの落とし所: 「停滞」でなく「**落ちたエージェントの再開**」(音声承認→dead状態セッションにresume発射)が実演として安全に成立する形

