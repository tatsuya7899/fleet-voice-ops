#!/usr/bin/env python3
"""実MCPクライアントによる到達性検証(SPEC-initial.md S3「10/17キルライン」)。

mcp SDK(Python)のStreamable HTTPクライアントで実際にサーバーへ接続し、
`tools/list` で4ツールが見えること、`whats_stuck` を呼んで
fixture応答(4セッション中1件 stalled_suspect)が返ることを確認する。

環境変数:
  FVO_SERVER_URL   例: http://127.0.0.1:8765/mcp (ローカル) / ngrokの公開URL+/mcp (トンネル)
  FVO_AUTH_TOKEN   サーバー起動時に使ったトークンと同じ値

終了コード: 0=PASS / 1=FAIL
"""
from __future__ import annotations

import asyncio
import os
import sys

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

EXPECTED_TOOL_NAMES = {"fleet_status", "whats_stuck", "analyze_stall", "request_resume"}


async def _run(url: str, token: str) -> bool:
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx2.AsyncClient(headers=headers) as http_client:
        async with streamable_http_client(url, http_client=http_client) as (
            read_stream,
            write_stream,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                tools_result = await session.list_tools()
                tool_names = {tool.name for tool in tools_result.tools}
                if tool_names != EXPECTED_TOOL_NAMES:
                    print(
                        f"FAIL: tools/list mismatch. expected={EXPECTED_TOOL_NAMES} "
                        f"actual={tool_names}",
                        file=sys.stderr,
                    )
                    return False
                print(f"OK: tools/list returned expected 4 tools: {sorted(tool_names)}")

                call_result = await session.call_tool("whats_stuck", {})
                if call_result.is_error:
                    print(f"FAIL: whats_stuck returned an error: {call_result}", file=sys.stderr)
                    return False

                structured = call_result.structured_content
                stuck_list = None
                if isinstance(structured, dict) and "result" in structured:
                    stuck_list = structured["result"]
                elif isinstance(structured, list):
                    stuck_list = structured

                if stuck_list is None:
                    print(
                        f"FAIL: could not extract structured list from whats_stuck result: {call_result}",
                        file=sys.stderr,
                    )
                    return False

                if len(stuck_list) != 1:
                    print(
                        f"FAIL: expected exactly 1 stalled_suspect session, got {len(stuck_list)}: {stuck_list}",
                        file=sys.stderr,
                    )
                    return False

                print(f"OK: whats_stuck returned fixture data: {stuck_list}")
                return True


def main() -> int:
    url = os.environ.get("FVO_SERVER_URL", "http://127.0.0.1:8765/mcp")
    token = os.environ.get("FVO_AUTH_TOKEN")
    if not token:
        print("FAIL: FVO_AUTH_TOKEN is not set. It must match the running server's token.", file=sys.stderr)
        return 1

    print(f"Connecting to {url} ...")
    try:
        ok = asyncio.run(_run(url, token))
    except Exception as exc:  # noqa: BLE001 - 検証スクリプトのため広く捕捉して報告
        print(f"FAIL: exception during check: {exc!r}", file=sys.stderr)
        return 1

    if ok:
        print("PASS")
        return 0
    print("FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
