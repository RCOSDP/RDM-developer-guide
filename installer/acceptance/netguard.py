"""Loopback-only network guard of the acceptance suite (SPEC-04 §3.4, ADR-02 §3.5).

Pure functions on URLs, importable without Playwright or pytest so that `installer/tests/` can unit
test them. The fixtures in conftest.py use them for browser routes, WebSocket routes, and the
wrapper around Playwright's APIRequestContext.
"""
from __future__ import annotations

from urllib.parse import urljoin, urlsplit

LOOPBACK_HOST = "127.0.0.1"
# Redirects of API calls are never delegated to Playwright (max_redirects is forced to 0); the wrapper
# follows at most this many hops itself and checks every Location against the loopback origin.
MAX_REDIRECT_HOPS = 5
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
# 307/308 keep the verb and the body; the others are re-issued as GET without a body (RFC 9110 §15.4).
METHOD_PRESERVING_STATUSES = frozenset({307, 308})
BODY_KWARGS = ("data", "form", "multipart")
WEBSOCKET_ROUTE_REQUIREMENT = (
    "BrowserContext.route_web_socket is unavailable: the loopback guard cannot intercept WebSockets. "
    "Playwright >= 1.48 (pytest-playwright >= 0.6) is required; run: pip install -e \"installer[accept]\" "
    "&& PLAYWRIGHT_BROWSERS_PATH=.venv/.playwright playwright install chromium"
)
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


def forced_redirect_kwargs(kwargs: dict) -> dict:
    """`kwargs` with `max_redirects` forced to 0. A caller asking for automatic redirects is a
    programming error (ValueError): Playwright would follow them before any origin check."""
    requested = kwargs.get("max_redirects", 0)
    if requested not in (0, None):
        raise ValueError(f"max_redirects={requested!r} is not allowed: the guard follows redirects itself (SPEC-04 §3.4)")
    return {**kwargs, "max_redirects": 0}


def redirect_target(url: str, status: int, headers: dict | None) -> str | None:
    """Absolute URL of the Location header for a 3xx answer to `url`, or None when the response is
    not a redirect. Relative Locations resolve against the answered URL (ADR-02 §3.5 keeps the check
    on the resolved value, never on the raw header)."""
    if status not in REDIRECT_STATUSES or not headers:
        return None
    location = None
    for k, v in headers.items():
        if isinstance(k, str) and k.lower() == "location":
            location = v
            break
    if not location:
        return None
    return urljoin(url, location.strip())


def redirect_follow_up(verb: str, status: int, kwargs: dict) -> tuple[str, dict]:
    """(verb, kwargs) to use for the next hop: 307/308 keep both, every other 3xx becomes a GET without
    a body."""
    if status in METHOD_PRESERVING_STATUSES:
        return verb, dict(kwargs)
    return "get", {k: v for k, v in kwargs.items() if k not in BODY_KWARGS}
