"""Loopback-only network guard of the acceptance suite (SPEC-04 §3.4, ADR-02 §3.5).

Pure functions on URLs, importable without Playwright or pytest so that `installer/tests/` can unit
test them. The fixtures in conftest.py use them for browser routes, WebSocket routes, and the
wrapper around Playwright's APIRequestContext.
"""
from __future__ import annotations

from urllib.parse import urlsplit

LOOPBACK_HOST = "127.0.0.1"
HTTP_SCHEMES: tuple[str, ...] = ("http",)
WS_SCHEMES: tuple[str, ...] = ("ws",)
ALL_SCHEMES: tuple[str, ...] = HTTP_SCHEMES + WS_SCHEMES
DEFAULT_PORTS = {"http": 80, "ws": 80}


def origin_of(url: str, schemes: tuple[str, ...] = ALL_SCHEMES) -> tuple[str, str, int] | None:
    """(scheme, host, port) of `url`, or None when the URL is not a plain, credential-free URL
    with one of `schemes`. The netloc must be exactly `host` or `host:port`."""
    try:
        u = urlsplit(url)
        port = u.port  # raises ValueError on a non-numeric or out-of-range port
    except (ValueError, AttributeError, TypeError):
        return None
    if u.scheme not in schemes or not u.hostname:
        return None
    if u.username is not None or u.password is not None:
        return None
    host = u.hostname
    expected = host if port is None else f"{host}:{port}"
    if u.netloc.lower() != expected:
        return None
    return u.scheme, host, port if port is not None else DEFAULT_PORTS.get(u.scheme, 0)


def is_loopback_origin(url: str, schemes: tuple[str, ...] = HTTP_SCHEMES) -> bool:
    """True only for `http://127.0.0.1[:port]/...` (or the scheme(s) given), parsed exactly.

    Rejects https, `localhost`, `[::1]`, `127.0.0.1.evil.test`, `127.0.0.1.`, credentials in the
    netloc, and anything urlsplit cannot parse. Lookalikes never pass a string-prefix check here.
    """
    origin = origin_of(url, schemes)
    return origin is not None and origin[1] == LOOPBACK_HOST


def same_origin(url: str, other: str, schemes: tuple[str, ...] = ALL_SCHEMES) -> bool:
    """Exact (scheme, host, port) equality; False if either URL does not parse to an origin."""
    a = origin_of(url, schemes)
    b = origin_of(other, schemes)
    return a is not None and a == b


def offending_urls(urls: list[str], schemes: tuple[str, ...] = ALL_SCHEMES) -> list[str]:
    """The subset of `urls` that would leave the machine."""
    return [u for u in urls if not is_loopback_origin(u, schemes)]
