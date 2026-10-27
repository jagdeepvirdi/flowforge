"""SSRF guard for outbound requests to editor-configurable URLs (e.g. webhooks).

Pipeline/notification config (webhook_url, etc.) is entered by whoever can edit
pipelines and is then fetched server-side. Without a check, that lets an editor
point FlowForge at internal-only services: link-local/RFC1918 addresses, the
cloud metadata endpoint (169.254.169.254), or loopback — none of which should
ever be reachable from a webhook URL typed into a form.
"""
import http.client
import ipaddress
import socket
import urllib.request
from urllib.parse import urlparse

_ALLOWED_SCHEMES = frozenset({'http', 'https'})


class UnsafeUrlError(ValueError):
    """Raised when a configured URL resolves to a non-public address."""


def _is_unsafe_ip(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def resolve_public_ips(url: str) -> list[str]:
    """Return the public IPs url resolves to; raise UnsafeUrlError if it is not a well-formed
    http(s) URL or if ANY resolved address is non-public.

    This alone does not stop DNS rebinding (the name can resolve differently when the
    request is later made) — use safe_urlopen(), which connects to the exact IP validated here.
    """
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES or not parsed.hostname:
        raise UnsafeUrlError(f"Invalid URL {url!r}: must be an http(s) URL with a hostname")

    hostname = parsed.hostname
    try:
        addr = ipaddress.ip_address(hostname)
        resolved_ips = [addr]
    except ValueError:
        try:
            infos = socket.getaddrinfo(hostname, None)
        except socket.gaierror as e:
            raise UnsafeUrlError(f"Could not resolve host {hostname!r}: {e}") from e
        resolved_ips = [ipaddress.ip_address(info[4][0]) for info in infos]

    if not resolved_ips:
        raise UnsafeUrlError(f"Could not resolve host {hostname!r}")

    unsafe = [str(ip) for ip in resolved_ips if _is_unsafe_ip(ip)]
    if unsafe:
        raise UnsafeUrlError(
            f"Refusing to fetch {url!r}: host {hostname!r} resolves to a non-public "
            f"address ({', '.join(unsafe)}). Internal/link-local/loopback targets "
            "are not allowed."
        )
    return [str(ip) for ip in resolved_ips]


def assert_public_url(url: str) -> None:
    """Raise UnsafeUrlError if url is not a well-formed http(s) URL resolving to a public IP.

    Check-only form (does a DNS lookup). Prefer safe_urlopen() for the actual request:
    validating here and then fetching by name leaves a DNS-rebinding window.
    """
    resolve_public_ips(url)


def check_url_syntax(url: str) -> None:
    """Cheap, DNS-free validation for save time: http(s) scheme, a hostname, and — when the
    host is a literal IP — a public one. Hostnames are NOT resolved here (that happens at
    send time in safe_urlopen); this just rejects obviously-bad config early with a clear 400.
    """
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES or not parsed.hostname:
        raise UnsafeUrlError(f"Invalid URL {url!r}: must be an http(s) URL with a hostname")
    try:
        addr = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        return
    if _is_unsafe_ip(addr):
        raise UnsafeUrlError(
            f"Refusing {url!r}: {parsed.hostname!r} is a non-public address. "
            "Internal/link-local/loopback targets are not allowed."
        )


# ── safe outbound requests ────────────────────────────────────────────────────

class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Never follow redirects: a public URL must not be able to bounce the request to an
    internal address after the guard has approved it. The 3xx surfaces as an HTTPError."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


class _PinnedHTTPConnection(http.client.HTTPConnection):
    """Connects to a pre-validated IP regardless of what the hostname resolves to now."""

    def __init__(self, *args, pinned_ip: str, **kwargs):
        super().__init__(*args, **kwargs)
        self._pinned_ip = pinned_ip

    def connect(self):
        self.sock = socket.create_connection(
            (self._pinned_ip, self.port), self.timeout, self.source_address
        )


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """As above for TLS; certificate/SNI verification still uses the original hostname."""

    def __init__(self, *args, pinned_ip: str, **kwargs):
        super().__init__(*args, **kwargs)
        self._pinned_ip = pinned_ip

    def connect(self):
        sock = socket.create_connection(
            (self._pinned_ip, self.port), self.timeout, self.source_address
        )
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


class _PinnedHTTPHandler(urllib.request.HTTPHandler):
    def __init__(self, ip: str):
        super().__init__()
        self._ip = ip

    def http_open(self, req):
        return self.do_open(_PinnedHTTPConnection, req, pinned_ip=self._ip)


class _PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, ip: str):
        super().__init__()
        self._ip = ip

    def https_open(self, req):
        return self.do_open(
            _PinnedHTTPSConnection, req,
            pinned_ip=self._ip, context=getattr(self, '_context', None),
        )


def _uses_proxy(url: str) -> bool:
    parsed = urlparse(url)
    if not urllib.request.getproxies().get(parsed.scheme):
        return False
    return not urllib.request.proxy_bypass(parsed.hostname or '')


def safe_urlopen(req: 'urllib.request.Request | str', timeout: float = 10):
    """urlopen for editor-configurable URLs. Validates the target, does not follow redirects,
    and connects to the validated IP (closing the DNS-rebinding window).

    Raises UnsafeUrlError for unsafe targets; HTTPError for HTTP errors including 3xx.
    When an HTTP(S) proxy is configured for the target, the proxy performs resolution and
    IP pinning is skipped (the target is still validated and redirects still refused) —
    in proxied deployments, enforce destination policy at the proxy as well.
    """
    url = req if isinstance(req, str) else req.full_url
    ips = resolve_public_ips(url)
    handlers: list = [_NoRedirectHandler()]
    if not _uses_proxy(url):
        handlers += [_PinnedHTTPHandler(ips[0]), _PinnedHTTPSHandler(ips[0])]
    return urllib.request.build_opener(*handlers).open(req, timeout=timeout)  # nosec B310 - scheme validated above
