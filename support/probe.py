#!/usr/bin/env python3
"""SUPPORT K07: the reachability probe. Can a person reach us, and can we prove it?

The founding rule of the support desk: a silent inbox and a working-but-unused inbox must not render the same.
"Nobody asked" is not "nobody could reach us". So this probe answers one question, in three words:

    OK       a message sent to the address was found in the inbox within the wait
    FAIL     the message was sent and did not arrive (or the surface answered with an error)
    UNKNOWN  the probe could not run or could not see its subject (no sender wired, send raised, the inbox could not
             be read, the surface did not answer). UNKNOWN is never reported as FAIL and never as OK.

Two parts, both without side effects of their own:

  * ``check_surface(url)`` is one GET against a LOOPBACK or TAILNET address (127.0.0.0/8, ::1, 100.64.0.0/10 and
    names ending `.ts.net`). Any other host is refused before a socket opens: this tool does not reach the internet.
  * ``self_test(send, find, ...)`` takes the sender and the finder as arguments. There is NO default sender: sending
    a message is a send and goes through the door, so the wiring (and the owner's yes) comes later. The tests use a
    fake inbox. With no sender the CLI says UNKNOWN and names why.

``inbox_state(probe, tickets)`` is the sentence a status page may print. A ticket count of zero is only "nobody has
written" when the probe said OK; with any other probe result it says unknown, never "no tickets".

Nothing here starts a container, reads a secret, sends mail or opens a customer surface.
"""
from __future__ import annotations

import argparse
import ipaddress
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Callable, NamedTuple

OK, FAIL, UNKNOWN = "OK", "FAIL", "UNKNOWN"


class Result(NamedTuple):
    state: str
    detail: str


def host_allowed(host: str) -> bool:
    """True only for loopback, tailnet (CGNAT 100.64/10) and *.ts.net. Anything else, including a failed parse, is no."""
    host = (host or "").strip().strip("[]").lower()
    if not host:
        return False
    if host == "localhost" or host.endswith(".ts.net"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_loopback or (ip.version == 4 and ip in ipaddress.ip_network("100.64.0.0/10"))


def _default_fetch(url: str, timeout: float) -> int:
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(url, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def check_surface(url: str, fetch: Callable[[str, float], int] = _default_fetch, timeout: float = 5.0) -> Result:
    """One GET on the inbox's own address. A redirect is reported, not followed."""
    p = urllib.parse.urlsplit(url)
    if p.scheme not in ("http", "https") or not host_allowed(p.hostname or ""):
        return Result(UNKNOWN, f"refused to probe {p.hostname or url!r}: only loopback and tailnet addresses are allowed")
    try:
        code = fetch(url, timeout)
    except Exception as e:                      # timeout, refused, DNS: the surface did not answer, which is not "down"
        return Result(UNKNOWN, f"the surface did not answer ({type(e).__name__}); not the same as down")
    if 200 <= code < 300:
        return Result(OK, f"HTTP {code}")
    if code in (301, 302, 303, 307, 308):
        return Result(UNKNOWN, f"HTTP {code} redirect, not followed")
    return Result(FAIL, f"HTTP {code}")


def self_test(send: Callable[[str, str], None] | None, find: Callable[[str], bool], address: str, *,
              wait_s: float = 60.0, poll_s: float = 5.0, sleep: Callable[[float], None] = time.sleep,
              clock: Callable[[], float] = time.monotonic, token: str | None = None) -> Result:
    """Send one message carrying a fresh token to `address` and look for the token in the inbox."""
    if send is None:
        return Result(UNKNOWN, "no sender is wired; sending is a door act and waits for the owner's yes")
    token = token or f"probe-{uuid.uuid4().hex[:12]}"
    try:
        send(address, token)
    except Exception as e:
        return Result(UNKNOWN, f"the probe could not send ({type(e).__name__}); nothing was proven")
    deadline = clock() + wait_s
    while True:
        try:
            if find(token):
                return Result(OK, f"token {token} found in the inbox")
        except Exception as e:
            return Result(UNKNOWN, f"the inbox could not be read ({type(e).__name__}); the message may have landed")
        if clock() >= deadline:
            return Result(FAIL, f"token {token} sent and not found within {wait_s:g}s")
        sleep(poll_s)


def inbox_state(probe: Result, tickets: int | None) -> str:
    """The one sentence a status page may print. Zero tickets never reads as 'no tickets' unless the probe says OK."""
    if probe.state != OK:
        return f"unknown: the inbox could not be proven reachable ({probe.state}: {probe.detail})"
    if tickets is None:
        return "reachable; ticket count unknown"
    if tickets == 0:
        return "reachable; nobody has written yet"
    return f"reachable; {tickets} ticket(s)"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="SUPPORT K07 reachability probe (read-only, loopback and tailnet only)")
    ap.add_argument("--url", default="http://127.0.0.1:3000/api", help="the inbox's own address")
    ap.add_argument("--self-test", action="store_true", help="needs a wired sender; today this reports UNKNOWN")
    a = ap.parse_args(argv)
    res = self_test(None, lambda t: False, "") if a.self_test else check_surface(a.url)
    print(f"{res.state} | {res.detail}")
    return {OK: 0, FAIL: 1, UNKNOWN: 2}[res.state]


if __name__ == "__main__":
    raise SystemExit(main())
