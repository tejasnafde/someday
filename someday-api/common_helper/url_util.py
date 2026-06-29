"""URL safety utilities - SSRF protection for outbound HTTP calls."""

import ipaddress
from urllib.parse import urlparse

# Well-known metadata endpoints that should never be reachable from the app server.
BLOCKED_HOSTS = {
    "169.254.169.254",        # AWS / GCP / Azure instance metadata (link-local)
    "169.254.170.2",          # ECS task metadata
    "metadata.google.internal",
    "metadata.internal",
}


def validate_url(url: str) -> None:
    """Raise ValueError if url is not a safe external HTTP/S URL.

    Guards against:
    - Non-HTTP/S schemes (file://, ftp://, etc.)
    - IP literals in private / loopback / link-local ranges
    - Known cloud metadata hostnames

    Limitation: hostname-based DNS rebinding (attacker controls DNS) requires
    infra-level egress controls to fully prevent and is out of scope here."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme!r}")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError("URL has no host")
    if host in BLOCKED_HOSTS:
        raise ValueError(f"Blocked host: {host!r}")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return  # Not an IP literal - hostname, accepted (DNS rebinding is infra's problem)
    if not ip.is_global:
        raise ValueError(f"Non-routable IP address: {host!r}")
