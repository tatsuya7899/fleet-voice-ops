# デモ動画台本

注意: 証拠の境界を見せるカットを最初に置く(できないこと・未検証の範囲を隠さない)。
台本は英語デモ用(Devpost提出規定=3分制限)。審査員は冒頭20秒で見せ場(音声往復)を見る前提で構成する。

## 尺・構成

- 総尺: 3分00秒(厳守・事後変更不可)
- **音声体験: 2分30秒**(固定・数値は事後変更しない)
- **残り: 30秒**(タイトルカード+証拠の境界+クレジット。preflight検査器はここに含めない=デモに出さない)
- 第1幕の舞台: キッチン等、**画面が視界に無い状態**で音声のみのやり取りを撮る。根拠(session_id/elapsed_s/last_tool_name等)はEcho Show相当の画面カットで別途提示する(音声往復そのものには映さない)

## シーン一覧

| # | 秒数 | 画 | 音声/字幕(英語) | 備考 |
|---|------|----|-------------------|------|
| 1 | 0:00-0:20 | キッチン等、画面なし。人物がAlexa+相当のデバイスに話しかける | Q: "Anything going on with my agents?" → A: "Out of 4 sessions, one is waiting for input (30 min) and one died with an error." | **冒頭20秒に音声往復を置く(審査員の見せ場)**。日本語の固定一字一句はSPEC §作業順序どおり Q=「何かあった?」→ A=「4本のうち1本が30分前から入力待ちで止まっています・1本がエラーで落ちています」型。英語訳はこの対応を保つ(台数=生存PID数4に一致させる・「入力待ち」と「落ちた」は区別して言う=resume可否が違うため) |
| 2 | 0:20-0:45 | 画面カット(Echo Show相当のUI)。fleet_statusの3値一覧を提示 | ナレーション: "fleet-voice-ops reads session liveness from PID checks and recent activity — not what's inside the conversation." | 根拠の提示(音声では見せない情報をここで裏付ける) |
| 3 | 0:45-1:30 | 画面: analyze_stallの出力(hypotheses + recommended_action) | ナレーション: "It doesn't just detect a stall — it proposes hypotheses with confidence and evidence, then recommends one action." | agentic実体(SPEC §agenticの実体)の提示 |
| 4 | 1:30-2:30 | 再びキッチン等、画面なし。音声で承認し再開が発射される | Q(approve): "Yes, go ahead." → A: "Resuming demo-driftwood now." | **音声でしか成立しない動作の後半**(承認→再開指示)。対象は`dead`(PID死・エラー付きで終了)セッション — 実測で稼働中へのresumeは失敗するため(根拠: docs/interrupt-test-evidence.md)。序数でなくセッション名を復唱していることを字幕で強調 |
| 5 | 2:30-2:50 | 画面: 証拠の境界カード | テキスト: "What this demo does NOT do yet: read real transcripts live, run on an actual Alexa+ device, execute a real resume (dry-run only)." | 未検証範囲を隠さない(本タスク冒頭の注意の実行) |
| 6 | 2:50-3:00 | タイトルカード+リポジトリURL+クレジット | — | — |

## 撮影・生成手順

1. `source venv/bin/activate && python scripts/voice_demo.py` を対話モードで起動し、シーン1・4のセリフをそのまま入力して応答を確認する(本番撮影前に台本どおりの応答が出ることをリハーサルで確認する)
2. シーン1・4は画面を映さず、マイク入力(人の声)→スピーカー出力(`say`または実機)の往復を録画する
3. シーン2・3は `python -c` や簡易CLIで `fleet_status()` / `analyze_stall("demo-birch")` の出力をターミナル or 簡易UIに表示して録画する
4. 英語字幕を焼き込む(日本語の一字一句はこの台本内の対応表を正とする)
5. 編集時に総尺3分・音声体験2分30秒の配分を超えないことをタイムラインで確認してから書き出す

