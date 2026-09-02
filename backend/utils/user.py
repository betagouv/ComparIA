from logging import getLogger

from fastapi import Request

from backend.config import settings

logger = getLogger("languia")


def get_ip(request: Request) -> str:
    """
    Resolve the client IP, reading X-Forwarded-For only behind trusted proxies.

    Args:
        request: incoming request, with its headers and socket peer

    Returns:
        str: client IP, empty when nothing identifies the caller
    """
    direct_ip = request.client.host if request.client and request.client.host else ""

    hops = settings.COMPARIA_TRUSTED_PROXY_COUNT
    if hops <= 0:
        return direct_ip

    # Anybody can send X-Forwarded-For, and a spoofed value would defeat every
    # rate limit keyed on the IP. Only the entries our own proxies appended can
    # be believed: the outermost trusted one wrote the value at -hops, whatever
    # the client put before it.
    chain = [
        part.strip()
        for part in request.headers.get("x-forwarded-for", "").split(",")
        if part.strip()
    ]
    if len(chain) < hops:
        return direct_ip

    return chain[-hops]


def get_matomo_tracker_from_cookies(cookies: dict[str, str]) -> str | None:
    """
    Extract Matomo/Piwik visitor ID from cookies.

    Used for anonymous visitor tracking (if enabled by user).

    Args:
        cookies: Request cookies dict

    Returns:
        str: Matomo visitor ID, or None if not found
    """
    # Matomo cookies start with "_pk_id."
    for key, value in cookies.items():
        if key.startswith("_pk_id."):
            logger.debug(f"Found matomo cookie: {key}: {value}")
            return value

    return None
