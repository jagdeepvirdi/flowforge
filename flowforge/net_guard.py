"""SSRF guard for outbound requests to editor-configurable URLs (e.g. webhooks).

Pipeline/notification config (webhook_url, etc.) is entered by whoever can edit
pipelines and is then fetched server-side. Without a check, that lets an editor
point FlowForge at internal-only services: link-local/RFC1918 addresses, the
cloud metadata endpoint (169.254.169.254), or loopback — none of which should
ever be reachable from a webhook URL typed into a form.
"""
import ipaddress
import socket
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


def assert_public_url(url: str) -> None:
    """Raise UnsafeUrlError if url is not a well-formed http(s) URL resolving to a public IP.

    Note: this checks the IP(s) resolved at call time, immediately before use — it
    does not protect against DNS-rebinding (a TOCTOU where the same hostname
    resolves to a different IP a moment later). That residual risk is accepted here;
    the goal is to block obviously-misconfigured or malicious static targets.
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
