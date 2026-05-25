"""Service-to-service auth — the PRODUCER half of the two-way mesh.

Every app validates inbound calls from other apps the same way: a shared secret in
the ``X-Service-Token`` header, checked constant-time against the ``LEADFUEL_SERVICE_TOKEN``
env. The API stays OFF until that env is set, so nothing opens a hole by default.

Framework-agnostic: the check takes a plain headers mapping (anything with ``.get``),
so Flask's ``request.headers``, a dict, or any WSGI/ASGI headers object all work.

    from leadfuel_core import service_auth as SA

    if not SA.is_enabled():
        return 503  # token unset → API disabled
    if not SA.header_authed(request.headers):
        return 403  # missing / wrong token
"""
from __future__ import annotations

import hmac
import os

TOKEN_ENV = "LEADFUEL_SERVICE_TOKEN"
TOKEN_HEADER = "X-Service-Token"


def service_token(env: str = TOKEN_ENV) -> str:
    """The configured shared secret (empty string if unset)."""
    return (os.environ.get(env) or "").strip()


def is_enabled(env: str = TOKEN_ENV) -> bool:
    """True iff a token is configured. When False, the API should answer 503."""
    return bool(service_token(env))


def token_matches(sent: str | None, env: str = TOKEN_ENV) -> bool:
    """Constant-time compare of a presented token against the configured one.
    False if no token is configured or the presented one is empty/wrong."""
    tok = service_token(env)
    if not tok:
        return False
    sent = (sent or "").strip()
    return bool(sent) and hmac.compare_digest(sent, tok)


def header_authed(headers, header: str = TOKEN_HEADER, env: str = TOKEN_ENV) -> bool:
    """True iff the headers mapping carries the correct service token."""
    try:
        sent = headers.get(header)
    except AttributeError:  # not a mapping
        sent = None
    return token_matches(sent, env)
