from fastapi import Request


def get_ip(request: Request) -> str:
    """
    Extract user's real IP address from Gradio request headers.

    Handles proxy chains and cloud protection services by checking multiple headers.
    Priority order: cloud-protector-client-ip > x-original-forwarded-for > x-forwarded-for > request.client.host

    Args:
        request: Gradio Request object with headers

    Returns:
        str: User's IP address (first IP if multiple comma-separated values)
    """
    # Try cloud protection provider IP first (OVH, etc.)
    if "cloud-protector-client-ip" in request.headers:
        ip = request.headers["cloud-protector-client-ip"]
    # Try original forwarded IP (before multiple proxies)
    elif "x-original-forwarded-for" in request.headers:
        ip = request.headers["x-original-forwarded-for"]
    # Try standard forwarded-for header
    elif "x-forwarded-for" in request.headers:
        ip = request.headers["x-forwarded-for"]
    # Fall back to direct client IP
    elif request.client and request.client.host:
        ip = request.client.host
    else:
        ip = ""

    # Multiple IPs can be returned as comma-separated string; take the first (client IP)
    if "," in ip:
        ip = ip.split(",")[0].strip()

    return ip
