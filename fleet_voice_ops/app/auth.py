"""最小Bearer認証ミドルウェア(SPEC-initial.md S3「到達性」向け)。

Alexa+の実測要件(review-spec-r1.md / Amazon文書): 未認証リクエストは
401を返すが、`WWW-Authenticate` ヘッダは付けない(RFC 9728の一般的な
推奨とは逆向き。正式なOAuth 2.1+PKCE/PRMは切る順序4位のため対象外)。

トークンは環境変数 `FVO_AUTH_TOKEN` から読む。未設定なら起動時に
ランダム生成し、標準エラー出力へ警告を出す(デモ用途・ファイル/ログへの
永続化はしない)。
"""
from __future__ import annotations

import os
import secrets
import sys

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send


def resolve_auth_token() -> str:
    """環境変数 FVO_AUTH_TOKEN を優先し、無ければデモ用に都度生成する。

    生成したトークンはファイル・ログへは書き込まない(標準エラーへの
    警告表示のみ)。
    """
    token = os.environ.get("FVO_AUTH_TOKEN")
    if token:
        return token
    generated = secrets.token_urlsafe(32)
    print(
        "[fleet-voice-ops] WARNING: FVO_AUTH_TOKEN not set. "
        "Generated a demo-only token for this process lifetime. "
        "Set FVO_AUTH_TOKEN explicitly for anything beyond local demos.",
        file=sys.stderr,
    )
    return generated


class BearerAuthMiddleware:
    """ASGIミドルウェア: `Authorization: Bearer <token>` のみ通す。

    - 未認証(ヘッダ無し/形式不正)・誤トークンは 401 を返す。
    - `WWW-Authenticate` ヘッダは意図的に付けない(Alexa+実測要件)。
    - 認証済みならアプリへ透過する。
    """

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self._token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        auth_header = request.headers.get("authorization", "")
        prefix = "Bearer "
        is_authorized = auth_header.startswith(prefix) and secrets.compare_digest(
            auth_header[len(prefix):], self._token
        )

        if not is_authorized:
            response = Response(status_code=401, content="Unauthorized")
            # 意図的に WWW-Authenticate を付けない(Alexa+実測要件・上部docstring参照)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)


def wrap_with_auth(app: ASGIApp, token: str) -> ASGIApp:
    """与えられたASGIアプリをBearer認証ミドルウェアで包む。"""
    return BearerAuthMiddleware(app, token=token)
