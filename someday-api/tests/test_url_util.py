"""SSRF protection tests - static validation, DNS pinning, per-hop checks, byte cap."""

import gzip
import socket

import httpx
import pytest

from common_helper import url_util
from common_helper.url_util import (
    BlockedURLError,
    SSRFSafeTransport,
    get_capped,
    resolve_pinned_ip,
    safe_client,
    validate_url,
)

PUBLIC_V4 = "93.184.216.34"
PUBLIC_V6 = "2606:2800:220:1:248:1893:25c8:1946"


def addrinfo(*addresses):
    """Build a socket.getaddrinfo-shaped result for the given IP strings."""
    out = []
    for a in addresses:
        family = socket.AF_INET6 if ":" in a else socket.AF_INET
        sockaddr = (a, 0, 0, 0) if ":" in a else (a, 0)
        out.append((family, socket.SOCK_STREAM, 6, "", sockaddr))
    return out


# ---------------------------------------------------------------- validate_url

class TestValidateUrl:

    @pytest.mark.parametrize("url", [
        "https://example.com/page",
        "http://example.com",
        f"https://{PUBLIC_V4}/img.png",
    ])
    def test_accepts_safe_urls(self, url):
        validate_url(url)  # must not raise

    @pytest.mark.parametrize("url", [
        "file:///etc/passwd",
        "ftp://example.com/x",
        "gopher://example.com",
        "https://",
        "https://169.254.169.254/latest/meta-data/",
        "https://metadata.google.internal/computeMetadata/v1/",
        "http://127.0.0.1:8080/admin",
        "http://10.0.0.5/internal",
        "http://192.168.1.1/",
        "http://[::1]/",
    ])
    def test_rejects_unsafe_urls(self, url):
        with pytest.raises(ValueError):
            validate_url(url)

    @pytest.mark.parametrize("url", [
        "http://[::1",                  # unclosed bracket
        "http://example.com:port/x",    # non-numeric port
        "https://\u200bexample.com/",   # zero-width char, common in pasted links
    ])
    def test_malformed_urls_raise_value_error_not_invalid_url(self, url):
        """httpx.InvalidURL does NOT subclass ValueError. Callers catch
        ValueError only, so letting it escape turns a bad paste into a 500."""
        with pytest.raises(ValueError):
            validate_url(url)


# ----------------------------------------------------------- resolve_pinned_ip

class TestResolvePinnedIp:

    def test_returns_public_v4(self, monkeypatch):
        monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: addrinfo(PUBLIC_V4))
        assert resolve_pinned_ip("example.com") == PUBLIC_V4

    def test_prefers_v4_over_v6(self, monkeypatch):
        monkeypatch.setattr(
            socket, "getaddrinfo", lambda *a, **k: addrinfo(PUBLIC_V6, PUBLIC_V4)
        )
        assert resolve_pinned_ip("example.com") == PUBLIC_V4

    def test_v6_only_returns_v6(self, monkeypatch):
        monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: addrinfo(PUBLIC_V6))
        assert resolve_pinned_ip("example.com") == PUBLIC_V6

    def test_private_address_rejected(self, monkeypatch):
        monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: addrinfo("10.1.2.3"))
        with pytest.raises(ValueError, match="non-routable"):
            resolve_pinned_ip("rebind.attacker.example")

    def test_one_private_among_public_rejects_all(self, monkeypatch):
        # Split-horizon / rebinding shape: never pick the public one and proceed.
        monkeypatch.setattr(
            socket, "getaddrinfo", lambda *a, **k: addrinfo(PUBLIC_V4, "192.168.0.10")
        )
        with pytest.raises(ValueError, match="non-routable"):
            resolve_pinned_ip("rebind.attacker.example")

    def test_dns_failure_raises_value_error(self, monkeypatch):
        def boom(*a, **k):
            raise socket.gaierror("NXDOMAIN")
        monkeypatch.setattr(socket, "getaddrinfo", boom)
        with pytest.raises(ValueError, match="DNS resolution failed"):
            resolve_pinned_ip("nope.invalid")


# ---------------------------------------------------------- SSRFSafeTransport

class TestSSRFSafeTransport:

    def test_pins_hostname_to_resolved_ip(self, monkeypatch):
        monkeypatch.setattr(url_util, "resolve_pinned_ip", lambda host: PUBLIC_V4)
        seen = {}

        def handler(request):
            seen["url"] = str(request.url)
            seen["host_header"] = request.headers["host"]
            seen["sni"] = request.extensions.get("sni_hostname")
            return httpx.Response(200, text="ok")

        transport = SSRFSafeTransport(inner=httpx.MockTransport(handler))
        with httpx.Client(transport=transport) as client:
            resp = client.get("https://example.com/page?x=1")

        assert resp.status_code == 200
        assert seen["url"] == f"https://{PUBLIC_V4}/page?x=1"
        assert seen["host_header"] == "example.com"  # virtual hosting intact
        assert seen["sni"] == "example.com"          # cert verified against hostname

    def test_public_ip_literal_passes_untouched(self):
        def handler(request):
            assert request.url.host == PUBLIC_V4
            assert "sni_hostname" not in request.extensions
            return httpx.Response(200)

        transport = SSRFSafeTransport(inner=httpx.MockTransport(handler))
        with httpx.Client(transport=transport) as client:
            assert client.get(f"http://{PUBLIC_V4}/x").status_code == 200

    @pytest.mark.parametrize("url", [
        "http://127.0.0.1/",
        "http://169.254.169.254/latest/",
        "http://metadata.google.internal/",
        "http://192.168.1.1/router",
    ])
    def test_blocks_bad_targets_before_connecting(self, url):
        def handler(request):
            raise AssertionError("must never reach the network")

        transport = SSRFSafeTransport(inner=httpx.MockTransport(handler))
        with httpx.Client(transport=transport) as client:
            with pytest.raises(ValueError):
                client.get(url)

    def test_redirect_hop_to_private_ip_is_blocked(self):
        """The transport sees every hop - a public origin cannot bounce the
        client into the internal network via a redirect."""
        def handler(request):
            return httpx.Response(
                302, headers={"location": "http://169.254.169.254/latest/meta-data/"}
            )

        transport = SSRFSafeTransport(inner=httpx.MockTransport(handler))
        with httpx.Client(transport=transport, follow_redirects=True) as client:
            with pytest.raises(ValueError, match="Blocked host"):
                client.get(f"http://{PUBLIC_V4}/open-redirect")

    def test_relative_redirect_resolves_against_hostname(self, monkeypatch):
        """The pin must not leak into redirect resolution: a relative Location
        goes back to the hostname, not to the pinned IP."""
        monkeypatch.setattr(url_util, "resolve_pinned_ip", lambda host: PUBLIC_V4)
        hops = []

        def handler(request):
            hops.append(request.headers["host"])
            if len(hops) == 1:
                return httpx.Response(302, headers={"location": "/moved"})
            return httpx.Response(200, text="ok")

        transport = SSRFSafeTransport(inner=httpx.MockTransport(handler))
        with httpx.Client(transport=transport, follow_redirects=True) as client:
            resp = client.get("https://example.com/start")

        assert resp.status_code == 200
        assert hops == ["example.com", "example.com"]


# -------------------------------------------------------------------- get_capped

class ChunkStream(httpx.SyncByteStream):
    """Response stream with no content-length header."""

    def __init__(self, chunks):
        self.chunks = chunks

    def __iter__(self):
        yield from self.chunks


def capped(handler, url=f"http://{PUBLIC_V4}/x", max_bytes=1000):
    """get_capped against a mock origin. The transport seam is wrapped by
    SSRFSafeTransport inside get_capped, so the vetting still runs."""
    return get_capped(url, max_bytes=max_bytes, transport=httpx.MockTransport(handler))


class TestGetCapped:

    def test_returns_body_under_cap(self):
        resp = capped(lambda request: httpx.Response(200, content=b"x" * 100))
        assert resp.status_code == 200
        assert resp.content == b"x" * 100

    def test_rejects_on_declared_content_length(self):
        with pytest.raises(ValueError, match="declares"):
            capped(lambda request: httpx.Response(200, content=b"x" * 2000))

    def test_rejects_streamed_body_over_cap(self):
        # No content-length header - the cap must trip during iteration.
        def handler(request):
            return httpx.Response(200, stream=ChunkStream([b"x" * 600, b"y" * 600]))

        with pytest.raises(ValueError, match="exceeded"):
            capped(handler)

    def test_gzip_bomb_cannot_materialise_past_the_cap(self):
        """iter_bytes must slice the DECODED stream: one raw read of a bomb
        decompresses ~1000x, so an unsliced chunk blows the cap in memory
        before the check runs."""
        bomb = gzip.compress(b"a" * 20_000_000)

        def handler(request):
            return httpx.Response(200, headers={"content-encoding": "gzip"}, content=bomb)

        with pytest.raises(ValueError, match="exceeded"):
            capped(handler, max_bytes=1_000_000)

    def test_decodes_gzip_once(self):
        """The returned Response carries the already-decoded body, so the
        content-encoding header must not survive - httpx would inflate again."""
        def handler(request):
            return httpx.Response(
                200,
                headers={"content-encoding": "gzip", "content-type": "text/html"},
                content=gzip.compress(b"<title>hi</title>"),
            )

        resp = capped(handler)
        assert resp.content == b"<title>hi</title>"
        assert "content-encoding" not in resp.headers

    def test_text_uses_declared_charset(self):
        """Quoted charset labels are RFC-legal; httpx.Response.text handles
        them, which is why this code does not hand-roll charset parsing."""
        def handler(request):
            return httpx.Response(
                200,
                headers={"content-type": 'text/html; charset="shift_jis"'},
                content="\u3053\u3093\u306b\u3061\u306f".encode("shift_jis"),
            )

        assert capped(handler).text == "\u3053\u3093\u306b\u3061\u306f"

    def test_blocked_hop_raises_blocked_url_error(self):
        def handler(request):
            return httpx.Response(302, headers={"location": "http://127.0.0.1/admin"})

        with pytest.raises(BlockedURLError):
            capped(handler)

    def test_malformed_url_raises_blocked_not_invalid_url(self):
        """httpx builds the URL itself inside client.stream(), so get_capped
        must reject a malformed one before that raises the non-ValueError."""
        with pytest.raises(BlockedURLError):
            capped(lambda request: httpx.Response(200), url="http://[::1")

    def test_http_error_propagates(self):
        with pytest.raises(httpx.HTTPStatusError):
            capped(lambda request: httpx.Response(404))


# ------------------------------------------------------------------ safe_client

class TestSafeClient:

    def test_defaults(self):
        with safe_client() as client:
            assert client.follow_redirects is True
            assert client.max_redirects == url_util.MAX_REDIRECTS
