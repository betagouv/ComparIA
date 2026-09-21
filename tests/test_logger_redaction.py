"""The access log must not keep invite tokens.

Run with pytest, or directly:
    uv run python tests/test_logger_redaction.py
"""

import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")

from backend.logger import _RedactInviteToken  # noqa: E402


def access_record(path):
    # Same shape as uvicorn's access log: the path is one of the args.
    return logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        0,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:1", "GET", path, "1.1", 200),
        None,
    )


def test_the_invite_token_is_redacted_from_access_logs():
    record = access_record("/api/auth/invite/Sup3rS3cretT0ken?x=1")
    assert _RedactInviteToken().filter(record)
    assert record.getMessage() == (
        '127.0.0.1:1 - "GET /api/auth/invite/<redacted>?x=1 HTTP/1.1" 200'
    )


def test_other_paths_are_left_alone():
    record = access_record("/api/auth/invite/accept")
    _RedactInviteToken().filter(record)
    assert "/api/auth/invite/accept" in record.getMessage()
    record = access_record("/api/auth/me")
    _RedactInviteToken().filter(record)
    assert "/api/auth/me" in record.getMessage()


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-q"]))
