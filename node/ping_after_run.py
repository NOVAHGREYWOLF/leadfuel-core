#!/usr/bin/env python3
"""NODE oss-4: run a cron job, then ping the local Healthchecks about how it went.

    ping_after_run.py --check NAME -- <command> [args...]

Healthchecks is a dead-man's switch: a job that stops pinging is a job that stopped running. This wrapper
runs the command, passes its output and exit code through untouched, and then sends one ping.

  * exit 0           -> POST <base>/ping/<uuid>        (success)
  * exit non-zero    -> POST <base>/ping/<uuid>/fail   (the job ran and failed)
  * cannot start     -> POST .../fail, exit 127

Rules, all refusals rather than fall-throughs:
  * OFF by default. With no HC_PING_BASE the wrapper only runs the command and says so on stderr
    ("ping_after_run: off"). Turning it on is the owner's step once the compose is up.
  * The base URL must be http and its host must be loopback, RFC 1918, or tailnet (100.64/10), checked on
    every address the name resolves to. A hosted URL (hc-ping.com, healthchecks.io, any public name) is
    refused, the ping is not sent, and the job still runs. No outside alert channel exists here (Law 9).
  * A ping failure never changes the job's exit code, and never hides it. The wrapper reports the ping as
    `sent`, `skipped` or `failed` on stderr; a job whose ping failed is still the job's exit code.
  * Check UUIDs come from a private map (HC_CHECKS_FILE, json {"name": "uuid"}), never from this repo.
    An unknown name skips the ping with a message; it does not guess.
  * Output of the job is not sent to Healthchecks: the ping body is the exit code only.

Stdlib only. Tests: tests/test_ping_after_run.py.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import socket
import subprocess
import sys
import urllib.parse
import urllib.request

TAILNET = ipaddress.ip_network("100.64.0.0/10")


def _allowed_ip(ip: str) -> bool:
    a = ipaddress.ip_address(ip)
    return a.is_loopback or a.is_private or a in TAILNET


def check_base(base: str, resolve=socket.getaddrinfo) -> tuple[bool, str]:
    """(ok, reason). The base must be http on a local address; anything unresolvable is refused."""
    u = urllib.parse.urlsplit(base or "")
    if u.scheme != "http" or not u.hostname:
        return False, "base must be http://host[:port] on the local network"
    try:
        ips = {r[4][0] for r in resolve(u.hostname, u.port or 80, type=socket.SOCK_STREAM)}
    except OSError:
        return False, "base host did not resolve"
    if not ips:
        return False, "base host did not resolve"
    bad = sorted(i for i in ips if not _allowed_ip(i))
    if bad:
        return False, "base host is not loopback, private or tailnet"
    return True, ""


def load_uuid(name: str, path: str | None) -> str | None:
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f).get(name)
    except (OSError, ValueError, AttributeError):
        return None


def send_ping(base: str, uuid: str, code: int, opener=None) -> str:
    suffix = "" if code == 0 else "/fail"
    url = f"{base.rstrip('/')}/ping/{urllib.parse.quote(uuid, safe='')}{suffix}"
    req = urllib.request.Request(url, data=str(code).encode(), method="POST")
    try:
        (opener or urllib.request.urlopen)(req, timeout=10).close()
    except Exception:
        return "failed"
    return "sent"


def ping_after(name: str, code: int, env=None, resolve=socket.getaddrinfo, opener=None) -> str:
    env = os.environ if env is None else env
    base = env.get("HC_PING_BASE", "")
    if not base:
        return "off"
    ok, why = check_base(base, resolve)
    if not ok:
        return "skipped (" + why + ")"
    uuid = load_uuid(name, env.get("HC_CHECKS_FILE"))
    if not uuid:
        return "skipped (no check uuid for this name)"
    return send_ping(base, uuid, code, opener)


def main(argv=None, env=None, run=subprocess.call, **ping_kw) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--check", required=True, help="name of the check in the private uuid map")
    p.add_argument("cmd", nargs=argparse.REMAINDER)
    a = p.parse_args(argv)
    cmd = a.cmd[1:] if a.cmd[:1] == ["--"] else a.cmd
    if not cmd:
        p.error("no command given")
    try:
        code = run(cmd)
    except OSError:
        code = 127
    status = ping_after(a.check, code, env=env, **ping_kw)
    print(f"ping_after_run: {a.check}: exit {code}, ping {status}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
