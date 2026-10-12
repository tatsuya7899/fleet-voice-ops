# 到達性の実測記録(SPEC-initial.md S3「10/17キルライン」)

対象: トンネル経由で実MCPクライアントから認証を通してfixtureデータが返ること。

## 構成

- サーバー: `python -m fleet_voice_ops.app.server`(Streamable HTTP + 最小Bearer認証、`FVO_PORT=8765`)
- トンネル: `ngrok http 8765`(無料枠・一時URL。**このURLはセッション限定で既に失効している**)
  - 取得した公開URL(当時のみ有効): `https://diactinic-taisha-unpunctated.ngrok-free.dev`
- クライアント: `scripts/mcp_client_check.py`(mcp SDK ClientSessionによるStreamable HTTP接続)
- トークン: 環境変数 `FVO_AUTH_TOKEN` に設定(本ドキュメントには値を書かない。以降は `Authorization: Bearer <redacted>` と表記)

## 遭遇した問題と対処

1. **mcp SDK 2.3.0の`streamable_http_client`は2値タプルを返す**(read_stream, write_stream)。3値(get_session_idを含む)を期待する古い実装例があったため合わせて修正。
2. **`CallToolResult`のフィールド名はsnake_case**(`is_error` / `structured_content`)。`isError`/`structuredContent`(TS SDK由来の命名)ではないため修正。
3. **ngrok経由だとDNSリバインディング保護で`421 Invalid Host header`**: mcp SDKの`TransportSecuritySettings`は既定でlocalhostしか許可しない。`FVO_ALLOWED_HOSTS`環境変数(カンマ区切り)を新設し、ngrokの一時ホスト名を明示的に許可リストへ追加することで解消。

## ローカル(localhost)での結果

```
$ FVO_SERVER_URL="http://127.0.0.1:8765/mcp" FVO_AUTH_TOKEN=<redacted> python scripts/mcp_client_check.py
Connecting to http://127.0.0.1:8765/mcp ...
OK: tools/list returned expected 4 tools: ['analyze_stall', 'fleet_status', 'request_resume', 'whats_stuck']
OK: whats_stuck returned fixture data: [{'session_id': 'demo-birch', 'last_update': '2026-10-13T09:29:00Z', 'elapsed_s': 1800, 'last_tool_name': 'AskUserQuestion', 'has_error': False, 'step_count': 41, 'total_input_tokens': 48000, 'total_output_tokens': 9100, 'status': 'stalled_suspect'}]
PASS
local exit=0
```

## ngrokトンネル経由での結果

```
$ FVO_SERVER_URL="https://diactinic-taisha-unpunctated.ngrok-free.dev/mcp" FVO_AUTH_TOKEN=<redacted> python scripts/mcp_client_check.py
Connecting to https://diactinic-taisha-unpunctated.ngrok-free.dev/mcp ...
OK: tools/list returned expected 4 tools: ['analyze_stall', 'fleet_status', 'request_resume', 'whats_stuck']
OK: whats_stuck returned fixture data: [{'session_id': 'demo-birch', 'last_update': '2026-10-13T09:29:00Z', 'elapsed_s': 1800, 'last_tool_name': 'AskUserQuestion', 'has_error': False, 'step_count': 41, 'total_input_tokens': 48000, 'total_output_tokens': 9100, 'status': 'stalled_suspect'}]
PASS
tunnel exit=0
```

## curlでの401/200(ヘッダ確認・トンネル経由)

```
$ curl -sS -i https://diactinic-taisha-unpunctated.ngrok-free.dev/mcp -H "Accept: application/json, text/event-stream"
HTTP/2 401
content-length: 12
# www-authenticate ヘッダなし(Alexa+実測要件どおり)

$ curl -sS -i -H "Authorization: Bearer wrong" -H "Accept: application/json, text/event-stream" https://diactinic-taisha-unpunctated.ngrok-free.dev/mcp
HTTP/2 401
content-length: 12
# www-authenticate ヘッダなし

$ curl -sS -i -H "Authorization: Bearer <redacted>" -H "Accept: application/json, text/event-stream" -H "Content-Type: application/json" -X POST https://diactinic-taisha-unpunctated.ngrok-free.dev/mcp -d '{}'
HTTP/2 400
content-length: 2012
# 正トークンは認証層を通過。400はMCPプロトコル層のJSONバリデーション(空ボディ)によるもので認証エラーではない
```

## 結論

- トンネル経由で実MCPクライアントから認証を通してfixtureデータ(4セッション中1件stalled_suspect)が返ることを実測で確認した。**10/17キルラインは合格**。
- ngrok無料枠の範囲内(新規課金・アカウント作成なし)で完結した。
- 使用した公開URLはセッション限定の一時URLであり、本記録作成後に失効している。
