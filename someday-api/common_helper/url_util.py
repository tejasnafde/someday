"""URL safety utilities - SSRF protection for outbound HTTP calls.

validate_url() is a cheap static pre-check. SSRFSafeTransport is the real
enforcement: it runs on every request, so each redirect hop is re-checked, and
it pins the connection to a vetted IP so DNS cannot change between the check
and the connect. Never fetch a user-supplied URL with a bare httpx.get() - use
safe_client() or get_capped().
"""

import ipaddress
import socket

import httpx

# Well-known metadata endpoints that should never be reachable from the app server.
BLOCKED_HOSTS = {
    "169.254.169.254",        # AWS / GCP / Azure instance metadata (link-local)
    "169.254.170.2",          # ECS task metadata
    "metadata.google.internal",
    "metadata.internal",
}

MAX_REDIRECTS = 5
# Bounds one decoded chunk, so a gzip bomb cannot materialise megabytes between
# two cap checks (a single raw read decompresses up to ~1000x).
CHUNK_BYTES = 65536


class BlockedURLError(ValueError):
    """Target failed SSRF vetting. Subclasses ValueError so callers that catch
    ValueError (oversized bodies, bad DNS) still catch it, while alerting can
    tell a blocked target from a routine one."""


def vet_target(url: httpx.URL) -> str | None:
    """Raise BlockedURLError if the target is unsafe. Return the hostname that
    still needs a DNS pin, or None when the target is a vetted IP literal.

    Single source of the static policy: validate_url and the transport both
    call it, so a new rule cannot land in one and miss the other."""
    if url.scheme not in ("http", "https"):
        raise BlockedURLError(f"Unsupported URL scheme: {url.scheme!r}")
    host = (url.host or "").lower()
    if not host:
        raise BlockedURLError("URL has no host")
    if host in BLOCKED_HOSTS:
        raise BlockedURLError(f"Blocked host: {host!r}")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return host
    if not ip.is_global:
        raise BlockedURLError(f"Non-routable IP address: {host!r}")
    return None


def validate_url(url: str) -> None:
    """Raise ValueError if url is not a safe external HTTP/S URL.

    Static checks only. Hostnames pass without DNS resolution here - resolution,
    per-hop re-validation and IP pinning happen in SSRFSafeTransport, which any
    code actually fetching the URL must use (via safe_client() or get_capped())."""
    try:
        parsed = httpx.URL(url)
    except httpx.InvalidURL as exc:
        # InvalidURL is not a ValueError; callers catch ValueError only.
        raise BlockedURLError(f"Malformed URL: {exc}") from exc
    vet_target(parsed)


def resolve_pinned_ip(host: str) -> str:
    """Resolve host and return one vetted IP to pin the connection to.

    Every address the resolver returns must be globally routable - one private
    record among public ones is exactly the rebinding/split-horizon shape this
    exists to stop. Prefers IPv4 (present on effectively every target and
    avoids v6-egress variance)."""
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise BlockedURLError(f"DNS resolution failed for {host!r}: {exc}") from exc
    if not infos:
        raise BlockedURLError(f"DNS resolution returned no addresses for {host!r}")
    addresses = []
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise BlockedURLError(f"Host {host!r} resolves to non-routable address {ip}")
        addresses.append(ip)
    v4 = [ip for ip in addresses if ip.version == 4]
    return str(v4[0] if v4 else addresses[0])


class SSRFSafeTransport(httpx.BaseTransport):
    """httpx transport that vets and pins the destination of every request.

    Because it sits at the transport layer it sees every redirect hop. Hostname
    targets are resolved, every resolved address is vetted, and the request is
    rewritten to connect to that pinned IP. The Host header and the sni_hostname
    extension keep the original hostname, so virtual hosting and certificate
    verification still work."""

    def __init__(self, inner: httpx.BaseTransport | None = None):
        # No keep-alive: httpcore keys the pool on the pinned IP, so a reused
        # connection could serve a second hostname over a session whose
        # certificate was verified for the first one.
        self.inner = inner or httpx.HTTPTransport(
            limits=httpx.Limits(max_keepalive_connections=0)
        )

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        host = vet_target(request.url)
        if host:
            # New Request, not in-place mutation: the client resolves relative
            # redirects against ITS request object, which must keep the hostname.
            request = httpx.Request(
                method=request.method,
                url=request.url.copy_with(host=resolve_pinned_ip(host)),
                headers=request.headers,
                stream=request.stream,
                extensions={**request.extensions, "sni_hostname": host},
            )
        return self.inner.handle_request(request)

    def close(self) -> None:
        self.inner.close()


def safe_client(**kwargs) -> httpx.Client:
    """httpx.Client wired for untrusted URLs: SSRF-safe transport and a bounded
    redirect chain. Raises BlockedURLError from inside send() on a bad hop."""
    kwargs.setdefault("transport", SSRFSafeTransport())
    kwargs.setdefault("follow_redirects", True)
    kwargs.setdefault("max_redirects", MAX_REDIRECTS)
    return httpx.Client(**kwargs)


def get_capped(
    url: str,
    max_bytes: int,
    headers: dict | None = None,
    timeout: float = 10.0,
    transport: httpx.BaseTransport | None = None,
) -> httpx.Response:
    """GET an untrusted URL through the SSRF-safe transport, streaming the body
    with a hard byte cap, and return a Response holding the capped body.

    The cap is enforced while streaming, so an oversized or endless body is
    abandoned instead of being downloaded and then rejected. Raises
    BlockedURLError on a blocked hop, ValueError past the cap, and
    httpx.HTTPError on transport or status failures. The transport argument is
    the seam for tests; it is wrapped, so the SSRF layer always applies."""
    # Up front, so a malformed URL becomes BlockedURLError here rather than
    # httpx.InvalidURL (NOT a ValueError) out of the client's own URL building.
    validate_url(url)
    extra = {"transport": SSRFSafeTransport(transport)} if transport else {}
    with safe_client(timeout=timeout, **extra) as client:
        with client.stream("GET", url, headers=headers) as resp:
            resp.raise_for_status()
            declared = resp.headers.get("content-length", "")
            if declared.isdigit() and int(declared) > max_bytes:
                raise ValueError(f"Response declares {declared} bytes, cap is {max_bytes}")
            chunks: list[bytes] = []
            total = 0
            for chunk in resp.iter_bytes(chunk_size=CHUNK_BYTES):
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError(f"Response body exceeded the {max_bytes} byte cap")
                chunks.append(chunk)
            # Drop the hop headers: the body is already decoded and re-sized, and
            # a stale content-encoding makes httpx try to decompress it again.
            kept = [(k, v) for k, v in resp.headers.raw
                    if k.lower() not in (b"content-encoding", b"content-length")]
            return httpx.Response(
                resp.status_code,
                headers=httpx.Headers(kept),
                content=b"".join(chunks),
                request=resp.request,
            )
