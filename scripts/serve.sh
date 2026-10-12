#!/usr/bin/env bash
# MCPサーバー(Streamable HTTP + 最小Bearer認証)の起動スクリプト。
# SPEC-initial.md S3「到達性」向け。
#
# 環境変数:
#   FVO_AUTH_TOKEN  Bearerトークン(未設定なら起動時にデモ用トークンを自動生成し、
#                    標準エラーへ出力される。ファイル・ログには残らない)
#   FVO_HOST        既定 127.0.0.1
#   FVO_PORT        既定 8765
#
# 使い方:
#   FVO_AUTH_TOKEN=my-secret ./scripts/serve.sh
set -euo pipefail
cd "$(dirname "$0")/.."
python -m fleet_voice_ops.app.server
