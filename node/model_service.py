#!/usr/bin/env python3
"""The one local model service: one address in one file (queue item fold-c-G03).

Reads node/model_service.json and answers one question: which base URL does this caller use?

  python node/model_service.py resolve [--scheduled]   print the address (exit 2 and a reason if none)
  python node/model_service.py list                    every service, enabled or not
  python node/model_service.py probe <id>              GET <base_url>/models on THAT service only

RULES, each pinned by tests/test_model_service.py:
  * Nothing leaves the private network. A base_url whose host is not loopback, RFC 1918, tailnet or a
    LAN-style name is refused when the file is read, so a typo or a pasted vendor URL cannot sit in it.
  * No fallback to anything. `one` enabled -> it. `one` not enabled -> the first enabled service that
    is allowed for the caller (a scheduled caller never gets a service marked scheduled_ok false).
    Nothing allowed -> NoModelService, never a default address.
  * `probe` is the only code that opens a socket, runs only when asked by name, and only to the
    address already validated above. `resolve` and `list` send nothing.
Stdlib only.
"""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
import sys
import urllib.parse
import urllib.request

DEFAULT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_service.json")
SCHEMA = "model-service-1"
LAN_NETS = [ipaddress.ip_network(n) for n in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10", "127.0.0.0/8", "fd00::/8", "::1/128")]
LAN_SUFFIXES = (".lan", ".local", ".internal", ".home.arpa", ".ts.net")


class ModelServiceError(Exception):
    pass


class NoModelService(ModelServiceError):
    pass


def host_is_private(host: str) -> bool:
    host = (host or "").strip("[]").lower()
    if not host:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # a name: one label ("overlord") or a LAN-style suffix. A dotted public name is refused.
        return host == "localhost" or "." not in host or host.endswith(LAN_SUFFIXES)
    return any(ip.version == n.version and ip in n for n in LAN_NETS)


def check_base_url(url: str) -> str:
    p = urllib.parse.urlparse(url or "")
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ModelServiceError("base_url %r is not an http(s) URL" % (url,))
    if p.username or p.password:
        raise ModelServiceError("base_url must not carry credentials")
    if not host_is_private(p.hostname):
        raise ModelServiceError("base_url host %r is not loopback, private or tailnet" % (p.hostname,))
    return url.rstrip("/")


def load(path: str = DEFAULT_FILE) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        raise ModelServiceError("cannot read %s: %s" % (path, exc))
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ModelServiceError("%s is not a %s file" % (path, SCHEMA))
    services = data.get("services")
    if not isinstance(services, list) or not services:
        raise ModelServiceError("no services listed")
    seen = set()
    for s in services:
        if not isinstance(s, dict) or not s.get("id") or s["id"] in seen:
            raise ModelServiceError("each service needs a unique id")
        seen.add(s["id"])
        s["base_url"] = check_base_url(s.get("base_url"))
    if data.get("one") not in seen:
        raise ModelServiceError("`one` names no listed service")
    return data


def resolve(data: dict, scheduled: bool = False) -> dict:
    by_id = {s["id"]: s for s in data["services"]}

    def allowed(s: dict) -> bool:
        return s.get("enabled") is True and (not scheduled or s.get("scheduled_ok") is True)

    one = by_id[data["one"]]
    if allowed(one):
        return one
    for s in data["services"]:
        if allowed(s):
            return s
    why = "the one service (%s) is %s" % (one["id"], one.get("state", "not enabled"))
    raise NoModelService("no model service for this caller: %s, and no other enabled service is allowed%s"
                         % (why, " for scheduled work" if scheduled else ""))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None            # a 3xx surfaces as an HTTPError; the GET never leaves the validated host


def _default_opener(url, timeout):
    """No redirects and no proxy: the request goes only to the address check_base_url approved."""
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)
    return op.open(url, timeout=timeout)


def probe(service: dict, opener=_default_opener, timeout: float = 5.0) -> list:
    """GET <base_url>/models on one already-validated service. Returns the model ids."""
    url = check_base_url(service["base_url"]) + "/models"
    with opener(url, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return sorted(str(m.get("id")) for m in body.get("data", []) if isinstance(m, dict))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--file", default=DEFAULT_FILE)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("resolve")
    r.add_argument("--scheduled", action="store_true")
    sub.add_parser("list")
    p = sub.add_parser("probe")
    p.add_argument("id")
    a = ap.parse_args(argv)
    try:
        data = load(a.file)
        if a.cmd == "list":
            for s in data["services"]:
                print("%s%s\t%s\t%s\t%s" % ("*" if s["id"] == data["one"] else " ", s["id"], s["base_url"],
                                          "enabled" if s.get("enabled") is True else "off", s.get("state", "")))
            return 0
        if a.cmd == "resolve":
            print(resolve(data, a.scheduled)["base_url"])
            return 0
        svc = next((s for s in data["services"] if s["id"] == a.id), None)
        if svc is None:
            raise ModelServiceError("no service %r" % a.id)
        print("\n".join(probe(svc)) or "(answered, no models listed)")
        return 0
    except ModelServiceError as exc:
        print("model_service: %s" % exc, file=sys.stderr)
        return 2
    except OSError as exc:
        print("model_service: unknown, could not reach it (%s)" % exc, file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
