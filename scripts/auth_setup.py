#!/usr/bin/env python3
"""One-time OAuth2 setup for MCP servers requiring authorization_code flow.

Opens a browser for authorization, captures the callback, exchanges for tokens,
and (by default) POSTs the freshly-minted refresh_token to the backend's admin
re-key endpoint so it lands directly in Redis.

Usage:
    # Default — POST to admin endpoint:
    COMPARAG_ADMIN_URL=https://comparag-backend.up.railway.app \\
    ADMIN_STATUS_TOKEN=<railway-secret> \\
    uv run python scripts/auth_setup.py clarifeye

    # Fallback — print the refresh_token to stdout:
    uv run python scripts/auth_setup.py clarifeye --print
"""

import asyncio
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlparse

# Make `backend.tool_arena.*` importable when this script is run directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402

from backend.tool_arena.config import MCPServerConfig  # noqa: E402,F401
from backend.tool_arena.registry import registry  # noqa: E402

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


def _post_to_admin_seed(
    admin_url: str,
    admin_token: str,
    server_id: str,
    refresh_token: str,
    access_token: str | None,
    expires_in: int | None,
) -> None:
    url = admin_url.rstrip("/") + "/admin/tool-arena/oauth/seed"
    payload = {
        "server_id": server_id,
        "refresh_token": refresh_token,
    }
    if access_token:
        payload["access_token"] = access_token
    if expires_in is not None:
        payload["expires_in"] = expires_in
    headers = {"Authorization": f"Bearer {admin_token}"}
    print(f"\nPOSTing seed to {url} ...")
    resp = httpx.post(url, json=payload, headers=headers, timeout=30.0)
    if resp.status_code >= 400:
        print(f"Seed failed: HTTP {resp.status_code} — {resp.text}")
        sys.exit(2)
    body = resp.json()
    readiness = body.get("readiness", {})
    print(f"Seed accepted. Readiness: {readiness.get('status')!r}")
    if readiness.get("last_error"):
        print(f"  last_error: {readiness['last_error']}")
    print(f"  seeded_at:  {body.get('seeded_at')}")


async def run_setup(tool_id: str, print_only: bool) -> None:
    from mcp import ClientSession
    from mcp.client.auth import OAuthClientProvider
    from mcp.client.streamable_http import streamablehttp_client
    from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata

    from backend.tool_arena.auth import FileTokenStorage
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

    tokens = await storage.get_tokens()
    if not tokens or not tokens.refresh_token:
        print("\nWarning: No refresh_token obtained. The server may not support offline_access.")
        sys.exit(2)

    admin_url = os.environ.get("COMPARAG_ADMIN_URL", "").strip()
    admin_token = os.environ.get("ADMIN_STATUS_TOKEN", "").strip()

    if not print_only and admin_url and admin_token:
        _post_to_admin_seed(
            admin_url=admin_url,
            admin_token=admin_token,
            server_id=server.id,
            refresh_token=tokens.refresh_token,
            access_token=tokens.access_token or None,
            expires_in=tokens.expires_in,
        )
        return

    # Fallback: print the token to stdout for manual handling.
    print(f"\n{'='*60}")
    print("Refresh token (POST to /admin/tool-arena/oauth/seed):")
    print(f"  server_id     = {server.id}")
    print(f"  refresh_token = {tokens.refresh_token}")
    print(f"{'='*60}")


def main():
    args = [a for a in sys.argv[1:] if a]
    print_only = "--print" in args
    args = [a for a in args if a != "--print"]

    if len(args) != 1:
        print("Usage: uv run python scripts/auth_setup.py <tool_id> [--print]")
        print("Example: uv run python scripts/auth_setup.py clarifeye")
        sys.exit(1)

    asyncio.run(run_setup(args[0], print_only=print_only))


if __name__ == "__main__":
    main()
