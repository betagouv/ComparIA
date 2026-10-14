import ipaddress

from fastapi import Request

from backend.config import settings


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


def ip_bucket(ip: str) -> str:
    """
    The unit a per-IP limit counts against.

    An IPv6 subscriber is usually handed a whole /64, so counting single
    addresses would give one connection billions of fresh budgets. IPv4 and
    anything unparseable are counted as they are.
    """
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped:
            return str(address.ipv4_mapped)
        return str(ipaddress.ip_network(f"{address}/64", strict=False))
    return ip
