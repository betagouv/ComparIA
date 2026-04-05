"""CORS origin list builder — extracted for testability."""
import os


def build_origins(base: list[str], extra_env: str = "") -> list[str]:
    """Return base origins extended by comma-separated values in extra_env."""
    extras = [o.strip() for o in extra_env.split(",") if o.strip()]
    return base + extras


_BASE_ORIGINS = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:8000",
    "http://localhost:8001",
]


def get_origins() -> list[str]:
    """Return the effective origins list, extended from ALLOWED_ORIGINS env var."""
    return build_origins(_BASE_ORIGINS, os.getenv("ALLOWED_ORIGINS", ""))
