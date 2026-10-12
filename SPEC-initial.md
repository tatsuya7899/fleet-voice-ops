# SPEC-initial: fleet-voice-ops(v2・R1差し戻し対応版)

Created: 2026-10-13 / Revised: 2026-10-13(review-spec-r1.md の差し戻し6件+受入条件12項を反映)
※本SPECは公開版。前提整理・事業検証・レビュー記録は内部管理側にあり公開物には含めない

## 何を作るか

「アレクサ、どのエージェントが詰まってる?」— 複数並行稼働するコーディングエージェント(自分のDevin CLIセッション群)の状態を、音声/Alexa+経路で聞けるMCPサーバー。**voice observability**(把握の音声化) — 先行の voice control 系(fleetline・herdr-voice-mcp・quietvoice)は「操作の音声化」であり、本案は「動かさず状態を受け取る」重心の違いを名指しする(空位主張は撤回済)。

**構成要素(4つ)**:
1. **fleetリーダー(新規・2データ源統合)**:
   - **生死・最終活動の正**=`devin list --format json`(`last_activity_at`=epoch・`--format json`必須) + `~/.local/share/devin/cli/session_locks/<id>.lock`(中身=PID・`os.kill(pid,0)`で生存判定)。実測済: lock 286本中生存4本=**今まさに動く艦隊**。艦隊の頭数=生存PID数(「87本」は累積履歴であり提出文・デモに使わない)
   - **詳細信号**=`~/.local/share/devin/cli/transcripts/*.json`(ATIF-v1.7・`.claude.jsonl`と`~/.claude/projects/`は対象外)。`source=="system"` stepは読み捨て。transcriptのmtimeは実活動より最大24分古い実測があるため**停滞判定の正に使わない**
   - **読み取り対象外**: `sessions.db`(SQLite 4.3GB+WAL=容量・ロック事故面を先に閉じる)・`.claude.jsonl`・`~/.claude/projects/`
2. **MCPサーバー**: Python `mcp` SDK(Streamable HTTP対応・**pip install時に実バージョンでspec適合を突合**)。公開ツールは「応答可能な質問リスト」の機械生成出力に限定(下記・実在チェック手順)
3. **書き込み1本**: `devin --resume <session_id> --print "<prompt>"`(実在確認済・`devin --help`)。承認=`confirm=true`必須(Human-in-the-loop)。**序数でなくセッション名を復唱して確認を取る**(序数読み替え事故の防止)
4. **preflight検査器(付属品)**: 実装は切る順序2位で**切り済み前提** — READMEに文書引用+手動チェック表+バッジは「手動検査」と明記。デモには出さない。尺配分=音声体験2分30秒/残り30秒(数値固定・事後変更不可)

## agenticの実体(受入条件・事前固定・R2b E4ゲート)

**1動作を名指し**: `analyze_stall(session_id)` ツール — 入力=そのセッションの構造信号のみ(elapsed_s / last_tool_name / has_error / step_count / token totals)。動作=LLMが**停滞原因の仮説を複数(2〜3個)立て、各仮説に確度と根拠信号を対応付け、次の一手を1つ推奨**する。
- **出力スキーマ固定**: `{"session_id": str, "hypotheses": [{"cause": str, "confidence": str(3段), "evidence_signals": [第1層許可キーの名のみ]}], "recommended_action": str}`
- これがSPECに無い状態で実装に入らない(R2bの明文ゲート)。閾値判定だけならcron+通知で足りる批判への回答は、この推論層が本体であること

## 音声でしか成立しない動作(受入条件・事前固定・R2b J1ゲート)

**固定する動作**: 「『何かあった?』と音声で聞く → 停滞セッションの**名前を音声で復唱**される → 音声で承認を返す → 再開指示が発射される」往復。**画面を一度も見ず・手を一度も使わずに、停滞の発見から介入承認までが完結する**。この動作はAlexa+実機に依存しない(汎用MCPクライアント+音声I/Oでも成立する形) — 実機経路を切ってもこの受入条件は消えない
- 固定できないならR2b J1どおり自分のファネル死因(A-05・ラッパー型)と同じ判定を自分に下し、この案を降格する

## 停滞の定義(受入条件・実測反映版)

- **生死**: `session_locks/<id>.lock`のPIDに対して`os.kill(pid,0)` — 生存=alive / 不在・死亡=dead(PID再利用による偽陽性はlock_age併用で緩和・頻度低いが注記)
- **活動性**: `devin list --format json`の`last_activity_at`との差分
- **3値化**: `active`(PID生存 かつ last_activityが閾値600秒以内)/ **`stalled_suspect`**(PID生存 かつ last_activityが閾値超 =「生きているのに進んでいない」=看板の問いへの本当の答え)/ `dead`(PID不在)
- 生死判定は実装30分の既知作業へ降格済み(レビュー実測F1〜F3)。キルラインの「生死照合経路」項目は閉じる

## プライバシー境界(emit許可リスト・2層)

「読まない」は実装不能(ツール名保持オブジェクトにパス同梱・error信号は本文解析が必須)のため**emit境界**へ反転:

1. プロセス内では対象ファイルを読む。`source=="system"` stepは読み捨て(会社情報は注入AGENTS.md経由で**全セッション100%混入**=除外リスト方式は機能しないため)
2. **第1層(データ層・事実)**: emit許可キー=`session_id` / `last_update`(ISO8601) / `elapsed_s` / `last_tool_name` / `has_error`(bool) / `step_count` / `total_*_tokens`。**emit禁止の名指し**: `title`(会話内容由来) / `working_directory`・`working_directory_display`(絶対パス) — 音声読み上げもしない
3. **第2層(推論層・analyze_stall出力のみ)**: キー=固定スキーマ(上記agentic節)。自由文は`cause`/`recommended_action`の2フィールドのみで、第1層の値だけを入力として生成=本文漏洩経路なし
4. **受入条件(機械テスト2本)**: ①「第1層ツールの応答JSONキー集合が許可リストと完全一致」②「analyze_stall出力のキー集合が固定スキーマと完全一致 かつ evidence_signals[]の各要素が第1層許可キーのいずれか」
5. **公開物grepゲート**: 対象=git追跡ファイル全件+submit/+fixture。禁止語=会社固有名詞(語そのものが社内情報のためローカル設定ファイル `~/.config/fleet-voice-ops/forbidden_terms.txt` に外部化)。`scripts/ready.py`の加重検査項目に追加・ヒット1件で提出ブロック

## 対象ユーザー・デモ舞台(受入条件)

- 主: 自分(N=1)。語り上の受け手: 「家にいる間も走り続ける仕事を持つ人」
- **デモ第1幕の舞台を固定**: キッチン等・画面が視界に無い状態。根拠は画面(Echo Show想定の表示)に提示。台本レビューはこの条件の通過判定で行う

## 作業順序(逆転・機械強制) ※実働10/13-22想定・工数見積は下端で上限超過のため**切り済み前提で着手**

1. **Day1-2(10/13-14)**: `submit/demo-script.md`の全節を埋める(現在見出しのみ・空)+ fixtureデータでの音声1往復。問いと応答を一字一句固定: Q=「何かあった?」→ A=「4本のうち1本が30分前から入力待ちで止まっています」型(生存PID数=4に合わせる)
2. **S3 到達性(10/15-16)**: トンネル公開+認証最小構成+汎用MCPクライアントからの呼出。Alexa+実機経路は切る順序4位=目標外
3. その後: fleetリーダー(2データ源)→実データ差替え→動画撮影→提出物
4. **切る順序(事前名指し・上から捨てる)**: ①USD換算(トークン量のみ) ②preflight実装(README手動チェック表へ退避済) ③実データ(fixture退避=事前許容) ④Alexa+実機経路(汎用クライアント+「Alexa+対応は要件適合まで」と明示) ⑤analyze_stall仮説数3→2。**S1台本・S4リーダー・S5推論層・S6書き込み・S7 emit境界は切らない**
5. **機械強制**: `scripts/ready.py`に「demo-script.md各節が空でない」「fixture音声1往復テストが通る」「社内名詞grepヒット0」を加重検査項目として追加し、実データ実装より先に緑になる順序を可視化

## スコープ外

- 書き込みは再開指示1本のみ / 視覚ダッシュボード再実装 / 複数プロバイダ統合
- コスト: トークン量は実在(`final_metrics`・87/87本)で追加実装ほぼ0=答える。USD換算のみ切る順序1位(価格表が別途要るため)

## データ実在チェック(手順・成果物・合格条件)

- 実行物: `scripts/data_probe.py` — **`devin list --format json`・`session_locks/`・`transcripts/*.json`の3源を走査**し「応答可能な質問リスト」を機械生成(`docs/answerable_questions.md`出力)
- 合格条件: 生成リストに無い質問をMCPツールとして公開しない(=リスト外の質問がツールに居たら検査失敗)

## 完了条件(MSC)

- 外部証拠3点: 公開repo実在(MCP実呼出コード)+Devpost提出確認+デモ実演完走(音声Q&A→画面ドリル→承認つき再開の実演)
- **品質ゲート**: 提出3日前に4軸(Technical/Design/Impact/Idea)を自己採点+独立再採点。**閾値=13/20**。未満なら構成変更。**この数値は提出まで変更しない**

## 3日間手計測(拘束条件7・起点是正)

- **起点: 今日(10/13)から3日間**。対象=「画面から離れていてfleet状態を知りたくなった回数」(音声で聞いた実用場面ではなく欲求の回数 — 構築後にしか発火しない計器への変質を是正)
- 記録先: 内部管理側の計測ファイル(公開物には含めない)
- **判定**: 3日で2回未満なら価値主張を「頻度」から「不在時の安心」へ書き換え(fermiのARPU等も連動して修正)

## キルライン(2段に分割)

- **10/14(30分・判定済み)**: 一次データ源の実在 — `devin list --format json`の`last_activity_at`+`session_locks`のPID生存 → **レビュー実測で合格済**(F1〜F3・生存PID 4本)
- **10/17(二値)**: 到達性のみ — トンネル経由で実MCPクライアントから認証を通して**fixtureデータ**が返る(実データ到達を条件にしない=切る順序3位の対象)
- **`devin --resume`の稼働中割込み**: 生存PID実在中に30分で検証(10/17を待たない)
- 主キルライン: 週次純増(自分以外がこのサーバーに問い合わせた実行数/週)0が4週連続でPause審議(起点=repo公開日)
