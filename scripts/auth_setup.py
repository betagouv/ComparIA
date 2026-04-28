#!/usr/bin/env python3
"""One-time OAuth2 setup for MCP servers requiring authorization_code flow.

Opens a browser for authorization, captures the callback, exchanges for tokens,
and prints the refresh_token to set as a Railway env var.

Usage:
    uv run python scripts/auth_setup.py clarifeye
"""

import asyncio
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlparse

from backend.tool_arena.config import MCPServerConfig
from backend.tool_arena.registry import registry

CALLBACK_PORT = 9876
_auth_result: dict[str, str | None] = {"code": None, "state": None}
_server_ref: list[HTTPServer] = []


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        _auth_result["code"] = params.get("code", [None])[0]
        _auth_result["state"] = params.get("state", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h1>Authorization complete!</h1><p>You can close this tab.</p>")
        if _server_ref:
            Thread(target=_server_ref[0].shutdown).start()

    def log_message(self, format, *args):
        pass


async def redirect_handler(url: str) -> None:
    print(f"\nOpening browser for authorization...\n{url}\n")
    webbrowser.open(url)


async def callback_handler() -> tuple[str, str | None]:
    server = HTTPServer(("localhost", CALLBACK_PORT), CallbackHandler)
    _server_ref.append(server)
    print(f"Waiting for callback on http://localhost:{CALLBACK_PORT}/callback ...")
    server.serve_forever()
    code = _auth_result["code"]
    if not code:
        raise RuntimeError("No authorization code received")
    return code, _auth_result["state"]


async def run_setup(tool_id: str) -> None:
    from mcp import ClientSession
    from mcp.client.auth import OAuthClientProvider
    from mcp.client.streamable_http import streamablehttp_client
    from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata

    import os
    from backend.tool_arena.auth import TOKENS_DIR, FileTokenStorage
    from backend.tool_arena.config import OAuth2Auth

    server = registry.get_server(tool_id)
    if server is None:
        print(f"Error: tool '{tool_id}' not found in mcp_servers.json")
        sys.exit(1)

    if server.auth is None or server.auth.type != "oauth2":
        print(f"Error: tool '{tool_id}' does not use OAuth2 auth")
        sys.exit(1)

    auth: OAuth2Auth = server.auth  # type: ignore[assignment]
    client_secret = os.environ.get(auth.client_secret_env, "")
    if not client_secret:
        print(f"Error: {auth.client_secret_env} env var not set")
        sys.exit(1)

    storage = FileTokenStorage(server.id)

    client_info = OAuthClientInformationFull(
        client_id=auth.client_id,
        client_secret=client_secret,
        redirect_uris=[f"http://localhost:{CALLBACK_PORT}/callback"],
    )

    client_metadata = OAuthClientMetadata(
        redirect_uris=[f"http://localhost:{CALLBACK_PORT}/callback"],
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        client_name="CompaRAG Tool Arena",
        scope="claudeai openid offline_access",
        token_endpoint_auth_method="client_secret_post",
    )

    # Pre-seed client info
    p = storage._dir / "client_info.json"
    p.write_text(client_info.model_dump_json(indent=2))

    provider = OAuthClientProvider(
        server_url=str(server.endpoint),
        client_metadata=client_metadata,
        storage=storage,
        redirect_handler=redirect_handler,
        callback_handler=callback_handler,
    )

    print(f"Connecting to {server.name} ({server.endpoint})...")

    async with streamablehttp_client(
        str(server.endpoint),
        auth=provider,
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"\nSuccess! Connected and found {len(tools.tools)} tools:")
            for t in tools.tools:
                print(f"  - {t.name}")

    # Read stored tokens
    tokens = await storage.get_tokens()
    if tokens and tokens.refresh_token:
        print(f"\n{'='*60}")
        print(f"Set this env var on Railway:")
        print(f"  {server.id.upper()}_REFRESH_TOKEN={tokens.refresh_token}")
        print(f"{'='*60}")
    else:
        print("\nWarning: No refresh_token obtained. The server may not support offline_access.")


def main():
    if len(sys.argv) != 2:
        print("Usage: uv run python scripts/auth_setup.py <tool_id>")
        print("Example: uv run python scripts/auth_setup.py clarifeye")
        sys.exit(1)

    asyncio.run(run_setup(sys.argv[1]))


if __name__ == "__main__":
    main()
