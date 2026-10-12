"""SPEC-initial.md S3「到達性」向けの最小Bearer認証の受入条件:

- 未認証(ヘッダ無し)リクエストは 401 を返し、`WWW-Authenticate` ヘッダを
  付けない(Alexa+実測要件。付けるとRFC 9728一般推奨と誤認される)。
- 誤トークンも同様に 401。
- 正トークンならアプリへ透過し、200系が返る。
"""
from __future__ import annotations

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from fleet_voice_ops.app.auth import wrap_with_auth

TOKEN = "test-token-123"


def _build_client() -> TestClient:
    async def ok(request):
        return PlainTextResponse("ok")

    inner_app = Starlette(routes=[Route("/mcp", ok)])
    wrapped = wrap_with_auth(inner_app, token=TOKEN)
    return TestClient(wrapped)


def test_missing_auth_header_returns_401_without_www_authenticate_header():
    client = _build_client()
    response = client.get("/mcp")
    assert response.status_code == 401
    assert "www-authenticate" not in {k.lower() for k in response.headers.keys()}


def test_wrong_token_returns_401():
    client = _build_client()
    response = client.get("/mcp", headers={"Authorization": "Bearer wrong-token"})
    assert response.status_code == 401
    assert "www-authenticate" not in {k.lower() for k in response.headers.keys()}


def test_correct_token_passes_through_to_app():
    client = _build_client()
    response = client.get("/mcp", headers={"Authorization": f"Bearer {TOKEN}"})
    assert response.status_code == 200
    assert response.text == "ok"
