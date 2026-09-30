"""
A fake model provider speaking the OpenAI compatible streaming protocol over a
local socket.

Tests point a model endpoint at it, so a request goes through the real HTTP
call of LiteLLM and nothing here depends on which LiteLLM function makes it.
The behaviour is set on the instance and read for every request: how fast the
tokens come, how long the first byte takes, how many answers are a 429 first.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeProvider:
    def __init__(self) -> None:
        self.tokens: list[str] = ["Bonjour", " le", " monde"]
        self.reasoning_tokens: list[str] = []
        # Seconds between two tokens, and before the first byte of the answer.
        self.token_delay = 0.0
        self.first_byte_delay = 0.0
        # The next requests to answer with a 429, before succeeding.
        self.rate_limited_first = 0
        # "stop" for a complete answer, "length" for one cut at the token limit.
        self.finish_reason = "stop"
        # Token count reported in the last chunk, None to report nothing.
        self.reported_tokens: int | None = None
        self.requests: list[dict] = []
        self._lock = threading.Lock()
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_port}/v1"

    def start(self) -> "FakeProvider":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    def _handler(self):
        provider = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args) -> None:
                pass

            def do_POST(self) -> None:
                body = json.loads(
                    self.rfile.read(int(self.headers.get("Content-Length", 0)))
                )
                with provider._lock:
                    provider.requests.append(body)
                    refuse = provider.rate_limited_first > 0
                    if refuse:
                        provider.rate_limited_first -= 1
                if refuse:
                    self._send_json(
                        429,
                        {"error": {"message": "rate limited", "type": "rate_limit"}},
                        {"Retry-After": "0"},
                    )
                else:
                    self._stream(body)

            def _send_json(self, status: int, payload: dict, headers=None) -> None:
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                for name, value in (headers or {}).items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(data)

            def _event(self, delta: dict, finish=None, usage=None) -> None:
                chunk = {
                    "id": "chatcmpl-fake",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "fake",
                    "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
                }
                if usage:
                    chunk["usage"] = usage
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
                self.wfile.flush()

            def _stream(self, body: dict) -> None:
                time.sleep(provider.first_byte_delay)
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True

                pieces = [("reasoning_content", t) for t in provider.reasoning_tokens]
                pieces += [("content", t) for t in provider.tokens]
                try:
                    for index, (field, text) in enumerate(pieces):
                        if index:
                            time.sleep(provider.token_delay)
                        delta = {field: text}
                        if not index:
                            delta["role"] = "assistant"
                        self._event(delta)
                    usage = None
                    if provider.reported_tokens is not None:
                        usage = {
                            "prompt_tokens": 5,
                            "completion_tokens": provider.reported_tokens,
                            "total_tokens": 5 + provider.reported_tokens,
                        }
                    self._event({}, finish=provider.finish_reason, usage=usage)
                    self.wfile.write(b"data: [DONE]\n\n")
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    # The client hung up: it is done with this answer.
                    pass

        return Handler
