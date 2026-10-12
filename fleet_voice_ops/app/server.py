"""MCPサーバー(Streamable HTTP対応・mcp SDK v2 / MCPServer)。

公開ツールは「応答可能な質問リスト」(SPEC §データ実在チェック)に限定した4本のみ:
fleet_status / whats_stuck / analyze_stall / request_resume

S3「到達性」(SPEC-initial.md): 最小Bearer認証(`fleet_voice_ops.app.auth`)を
ASGIレベルで被せてから起動する。
"""
from __future__ import annotations

import os

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from fleet_voice_ops.app import tools
from fleet_voice_ops.app.auth import resolve_auth_token, wrap_with_auth

server = MCPServer(name="fleet-voice-ops")


@server.tool()
def fleet_status() -> list[dict]:
    """List all fleet sessions with their 3-value status (active/stalled_suspect/dead)."""
    return tools.fleet_status()


@server.tool()
def whats_stuck() -> list[dict]:
    """List sessions currently stalled_suspect (alive but no recent progress)."""
    return tools.whats_stuck()


@server.tool()
def analyze_stall(session_id: str) -> dict:
    """Generate stall-cause hypotheses and a recommended action for one session."""
    return tools.analyze_stall(session_id)


@server.tool()
def request_resume(session_id: str, confirm: bool = False) -> dict:
    """Ask for confirmation (confirm=false) or issue a dry-run resume command (confirm=true)."""
    return tools.request_resume(session_id, confirm=confirm)


def _transport_security() -> TransportSecuritySettings | None:
    """トンネル越しの到達性検証向け(SPEC S3)。

    `FVO_ALLOWED_HOSTS`(カンマ区切り、例: ngrokの一時ホスト名)が設定されて
    いる場合のみDNSリバインディング保護のホスト許可リストに追加する。未設定
    ならSDK既定(localhostのみ許可)のまま。
    """
    allowed = os.environ.get("FVO_ALLOWED_HOSTS", "")
    if not allowed:
        return None
    hosts = [h.strip() for h in allowed.split(",") if h.strip()]
    return TransportSecuritySettings(allowed_hosts=hosts, allowed_origins=["*"])


def build_app():
    """認証ミドルウェアで包んだASGIアプリを返す(テスト・手動検証用)。"""
    token = resolve_auth_token()
    starlette_app = server.streamable_http_app(transport_security=_transport_security())
    return wrap_with_auth(starlette_app, token=token)


async def _serve() -> None:
    import uvicorn

    port = int(os.environ.get("FVO_PORT", "8765"))
    host = os.environ.get("FVO_HOST", "127.0.0.1")
    app = build_app()
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    await uvicorn.Server(config).serve()


def main() -> None:
    import asyncio

    asyncio.run(_serve())


if __name__ == "__main__":
    main()
