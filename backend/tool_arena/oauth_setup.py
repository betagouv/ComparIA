"""One-time OAuth2 setup for MCP servers requiring authorization_code flow.

Usage:
    uv run python -m backend.tool_arena.oauth_setup clarifeye

Opens a browser for login, captures the callback, and stores tokens to disk.
Subsequent MCP calls use the refresh token automatically.
"""

import asyncio
import logging
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlparse

from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.auth import OAuthClientMetadata
from mcp.types import TextContent

from backend.tool_arena.auth import FileTokenStorage, get_oauth_provider
from backend.tool_arena.config import load_mcp_servers

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

CALLBACK_PORT = 9876
_auth_response: dict[str, str] = {}


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        if "code" in qs:
            _auth_response["code"] = qs["code"][0]
            _auth_response["state"] = qs.get("state", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Authorized! You can close this tab.</h1>")
        else:
            _auth_response["error"] = qs.get("error", ["unknown"])[0]
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h1>Authorization failed</h1>")

    def log_message(self, format, *args):
        pass


async def setup_oauth(server_id: str) -> None:
    servers = load_mcp_servers()
    server = next((s for s in servers if s.id == server_id), None)
    if not server:
        logger.error(f"Server '{server_id}' not found in mcp_servers.json")
        sys.exit(1)
    if not server.auth or server.auth.type != "oauth2":
        logger.error(f"Server '{server_id}' does not use OAuth2 auth")
        sys.exit(1)

    logger.info(f"Setting up OAuth for: {server.name} ({server.endpoint})")

    # Start callback server
    httpd = HTTPServer(("localhost", CALLBACK_PORT), CallbackHandler)
    thread = Thread(target=httpd.handle_request, daemon=True)
    thread.start()

    storage = FileTokenStorage(server_id)

    async def redirect_handler(auth_url: str) -> None:
        logger.info(f"\nOpening browser for authorization...")
        logger.info(f"URL: {auth_url}\n")
        webbrowser.open(auth_url)

    async def callback_handler() -> tuple[str, str | None]:
        logger.info("Waiting for callback on http://localhost:9876/callback ...")
        thread.join(timeout=300)
        if "code" not in _auth_response:
            raise RuntimeError(f"Auth failed: {_auth_response.get('error', 'timeout')}")
        return _auth_response["code"], _auth_response.get("state")

    provider = get_oauth_provider(server)
    provider.context.redirect_handler = redirect_handler
    provider.context.callback_handler = callback_handler

    logger.info("Connecting to MCP server with OAuth...")
    try:
        async with streamablehttp_client(
            str(server.endpoint),
            auth=provider,
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                logger.info(f"\nSuccess! Found {len(tools.tools)} tool(s):")
                for t in tools.tools:
                    logger.info(f"  - {t.name}: {t.description[:80] if t.description else '(no description)'}")

                tokens = await storage.get_tokens()
                if tokens:
                    logger.info(f"\nTokens stored to disk. Refresh token: {'yes' if tokens.refresh_token else 'no'}")
                else:
                    logger.info("\nWarning: no tokens stored — auth may need repeating")
    except Exception as e:
        logger.error(f"\nFailed: {e}")
        sys.exit(1)
    finally:
        httpd.server_close()

    logger.info("\nDone. The backend will use stored tokens automatically.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run python -m backend.tool_arena.oauth_setup <server_id>")
        sys.exit(1)
    asyncio.run(setup_oauth(sys.argv[1]))
