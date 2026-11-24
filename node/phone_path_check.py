"""NODE desks-3-6: is the GREYWOLF end of the iPhone path working?  Read-only; sends nothing but GETs.

Why. On 2026-11-23 the owner's report was "the phone cannot connect (Tailscale)". Measured that day:
Tailscale was Running, the iPhone peer was Online and answered `tailscale ping`, the phone host
answered /api/health directly and through the overlord forward, and every page load since v1.3 had
ended at `GET /api/boot 401` with no `POST /api/pair` after it. So the tunnel was not the blocker:
the phone was not paired. This script puts those readings in one place, so the next "it cannot
connect" is answered from evidence instead of by guessing at the tunnel.

What it can and cannot see. It runs on GREYWOLF. It sees this PC's Tailscale, the phone host and
the forward (one GET /api/health each), and the host's own request log. It cannot see the iPhone's
own request, so it never says "the phone works". The first line is about the GREYWOLF end only:

  GREYWOLF-SIDE-OK    Tailscale is Running here, and the host (and the forward, if one was given)
                      answered /api/health with the host's own body             (exit 0)
  GREYWOLF-SIDE-DOWN  Tailscale is not Running here, or nothing listens on the host's address,
                      or the host answered something else                        (exit 3)
  FORWARD-DOWN        the host is fine but the forward (overlord) refused or answered something
                      that is not the host's health body                          (exit 4)
  UNKNOWN             anything else: a reading could not be taken, or timed out. A timeout under
                      load says UNKNOWN, never DOWN                              (exit 2)

Evidence follows, indented: tailscale, host, forward, phone (peer state and `tailscale ping`),
pairing (what the host log shows), devices (a count: never a label, a digest or a key), and a
`next:` line naming the owner step the evidence points at. Times from the host log are the PC's
local time as logged. The log's identity column (the signed-in account) is never printed.

Usage:
    python phone_path_check.py                         host address from the host log's last start line
    python phone_path_check.py --forward http://OVERLORD-IP:8106
    python phone_path_check.py --no-ping               do not send `tailscale ping` to the phone
    python phone_path_check.py --host http://GREYWOLF-IP:8106 --log PATH --state DIR --tailscale EXE

The forward address can also come from the environment: NOVAHOS_PHONE_FORWARD. No address is
written in this file; the real ones live in the private estate notes.

Stdlib only. Sends nothing outside the tailnet addresses it is given; stops and kills nothing.
"""
import argparse
import datetime as dt
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
from collections import namedtuple
from urllib.parse import urlsplit

OK, DOWN, FORWARD_DOWN, UNKNOWN = "GREYWOLF-SIDE-OK", "GREYWOLF-SIDE-DOWN", "FORWARD-DOWN", "UNKNOWN"
EXIT = {OK: 0, UNKNOWN: 2, DOWN: 3, FORWARD_DOWN: 4}

USER_AGENT = "leadfuel-phone-path-check/1"
LOG_WINDOW_BYTES = 1 << 20          # read at most the last 1 MiB of the host log
DEFAULT_TAILSCALE = r"C:\Program Files\Tailscale\tailscale.exe"

Signal = namedtuple("Signal", "state detail")       # state: ok | down | unknown | skipped
Peer = namedtuple("Peer", "name os online")


# ---------------------------------------------------------------- tailscale (this PC, then the phone)

def classify_tailscale(doc):
    """This PC's own Tailscale, from `tailscale status --json`. Running is ok; a state that needs
    the owner (logged out, stopped) is down; a state in flux or a body it cannot read is unknown."""
    if not isinstance(doc, dict) or not isinstance(doc.get("BackendState"), str):
        return Signal("unknown", "tailscale: status is not readable (no BackendState)")
    state = doc["BackendState"]
    health = [h for h in (doc.get("Health") or []) if isinstance(h, str)]
    extra = ""
    if health:
        extra = "; health warning(s): " + " | ".join(h[:120] for h in health[:3])
    if state == "Running":
        # Self.Online is NOT used: on tailscale 1.104.5 it read false (with LastSeen at year 1) while
        # the backend was Running and `tailscale ping` to the phone passed. The ping is the proof.
        return Signal("ok", "tailscale: Running" + extra)
    if state in ("Starting", "NoState"):
        return Signal("unknown", "tailscale: %s (not settled yet)" % state)
    return Signal("down", "tailscale: backend %s on this PC%s" % (state, extra))


def _phone_nodes(doc, hint=None):
    """The peer entries that are the phone: by name when a hint is given, else every iOS peer."""
    peers = doc.get("Peer") if isinstance(doc, dict) else None
    if not isinstance(peers, dict):
        return []
    out = []
    for p in peers.values():
        if not isinstance(p, dict):
            continue
        if hint:
            if hint.lower() not in (str(p.get("HostName") or "") + " " + str(p.get("DNSName") or "")).lower():
                continue
        elif p.get("OS") != "iOS":
            continue
        out.append(p)
    return out


def find_phone_peers(doc, hint=None):
    """The phone(s) among the peers. Returns (peers, why) where why says what the filter was, so an
    empty list is explained."""
    why = ("name contains %r" % hint) if hint else "OS is iOS"
    if not isinstance(doc, dict) or not isinstance(doc.get("Peer"), dict):
        return [], "no peer list in the status"
    return [Peer(str(p.get("HostName") or p.get("DNSName") or "?"), str(p.get("OS") or "?"),
                 p.get("Online") is True) for p in _phone_nodes(doc, hint)], why


def phone_ips(doc, hint=None):
    """Tailnet IPv4 addresses of the phone peers, for `tailscale ping`."""
    return [ip for p in _phone_nodes(doc, hint) for ip in (p.get("TailscaleIPs") or [])
            if isinstance(ip, str) and "." in ip]


_PONG = re.compile(r"pong from \S+ \([0-9.]+\) via (?P<via>\S+) in (?P<ms>[0-9.]+)ms")


def parse_ping(text):
    """(pongs, routes, ms) from `tailscale ping` output. via is 'DERP(lax)' or 'ip:port'."""
    hits = [m.groupdict() for m in _PONG.finditer(text or "")]
    return len(hits), [h["via"] for h in hits], [float(h["ms"]) for h in hits]


def classify_phone(peers, why, ping=None):
    """What the phone's own end looks like from here. ping is (sent, text) or None when not run.
    This is evidence about the phone, not about GREYWOLF, so it never decides the verdict."""
    if not peers:
        return Signal("unknown", "phone: no peer found (%s)" % why)
    names = ", ".join("%s %s" % (p.name, "Online" if p.online else "Offline") for p in peers)
    online = any(p.online for p in peers)
    if ping is None:
        return Signal("ok" if online else "down", "phone: %s (tailscale ping not run)" % names)
    sent, text = ping
    pongs, routes, ms = parse_ping(text)
    if pongs:
        via = sorted(set(routes))
        return Signal("ok", "phone: %s; tailscale ping %d of %d pong, %s ms, via %s"
                      % (names, pongs, sent, "%d to %d" % (min(ms), max(ms)) if ms else "?", ", ".join(via)))
    return Signal("down", "phone: %s; tailscale ping %d of %d pong (the phone does not answer: Tailscale "
                          "off or asleep on the phone, or the path is cut)" % (names, pongs, sent))


# ---------------------------------------------------------------- health of the host and the forward

HealthResult = Signal


def classify_health(status, body, label):
    """The host's own /api/health body is {"ok": true, "mode": "LOCAL", "model": ...}. A 200 with any
    other body is something else listening (or the forward's own offline page): not the host."""
    if status == 200:
        try:
            doc = json.loads(body.decode("utf-8", "replace"))
        except ValueError:
            doc = None
        if isinstance(doc, dict) and doc.get("ok") is True and "mode" in doc:
            return HealthResult("ok", "%s: 200 with the host's health body" % label)
        return HealthResult("down", "%s: answered 200 but not with the host's health body (%d bytes)"
                                    % (label, len(body)))
    return HealthResult("down", "%s: answered %d" % (label, status))


def fetch_health(base_url, label, timeout=10.0, connection=http.client.HTTPConnection):
    """One GET /api/health. Refused = positive evidence nothing listens there (down). Every other
    failure, a timeout above all, cannot establish a state and says unknown."""
    parts = urlsplit(base_url)
    if parts.scheme != "http" or not parts.hostname:
        return HealthResult("unknown", "%s: %r is not an http://host:port address" % (label, base_url))
    conn = None
    try:
        conn = connection(parts.hostname, parts.port or 80, timeout=timeout)
        conn.request("GET", "/api/health", headers={"User-Agent": USER_AGENT, "Connection": "close"})
        resp = conn.getresponse()
        return classify_health(resp.status, resp.read(4096), label)
    except ConnectionRefusedError:
        return HealthResult("down", "%s: connection refused (nothing is listening there)" % label)
    except (OSError, http.client.HTTPException) as exc:
        return HealthResult("unknown", "%s: GET failed (%s: %s)" % (label, type(exc).__name__, exc))
    finally:
        if conn is not None:
            conn.close()


# ---------------------------------------------------------------- the host's own log and device list

_LOG_LINE = re.compile(r"^(?P<stamp>\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) \S+ (?P<method>[A-Z]+) "
                       r"(?P<path>\S+) (?P<status>\d{3}) \d+ms")
_LOG_START = re.compile(r"^=== novahos-phone started (?P<stamp>\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) ===")
_LOG_BIND = re.compile(r"^phonehost: bind=(?P<host>\S+) port=(?P<port>\d+)")

LogEvidence = namedtuple("LogEvidence",
                         "lines requests bad last_start bind last_boot boots_refused boots_ok "
                         "pair_attempts pair_ok last_pair_ok")


def scan_log(text):
    """Read the host's request log. The identity column (who was signed in) is matched and thrown
    away. Counts are since the last start line; last_boot / last_pair_ok are the newest anywhere in
    the text. `bad` counts lines that start like a request line and could not be read."""
    lines = text.splitlines()
    last_start, bind = None, None
    last_boot = None                 # (stamp, status)
    last_pair_ok = None
    since = {"boot_refused": 0, "boot_ok": 0, "pair": 0, "pair_ok": 0}
    requests = bad = 0
    for line in lines:
        m = _LOG_START.match(line)
        if m:
            last_start = m.group("stamp")
            since = {"boot_refused": 0, "boot_ok": 0, "pair": 0, "pair_ok": 0}
            continue
        m = _LOG_BIND.match(line)
        if m:
            bind = (m.group("host"), int(m.group("port")))
            continue
        if re.match(r"^\d{4}-\d\d-\d\d \d\d:", line):
            m = _LOG_LINE.match(line)
            if not m:
                bad += 1
                continue
            requests += 1
            path = m.group("path").split("?")[0]
            status = int(m.group("status"))
            if m.group("method") == "GET" and path == "/api/boot":
                last_boot = (m.group("stamp"), status)
                if status == 401:
                    since["boot_refused"] += 1
                elif status == 200:
                    since["boot_ok"] += 1
            elif m.group("method") == "POST" and path == "/api/pair":
                since["pair"] += 1
                if status == 200:
                    since["pair_ok"] += 1
                    last_pair_ok = m.group("stamp")
    return LogEvidence(len(lines), requests, bad, last_start, bind, last_boot,
                       since["boot_refused"], since["boot_ok"], since["pair"], since["pair_ok"],
                       last_pair_ok)


def read_log_tail(path, window=LOG_WINDOW_BYTES):
    """(text, total_bytes, truncated). Drops the first, possibly partial, line when it cut mid-file."""
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        if size > window:
            fh.seek(size - window)
        data = fh.read()
    text = data.decode("utf-8", "replace")
    truncated = size > window
    if truncated:
        text = text.split("\n", 1)[1] if "\n" in text else ""
    return text, size, truncated


def classify_pairing(ev, truncated=False):
    """What the host log says about pairing. Not proof about the phone: the log has no peer
    address, so a page load may be the phone or any other browser that reached the host."""
    if ev.last_boot is None:
        where = "in the last part of the log" if truncated else "in the log"
        return Signal("unknown", "pairing: NO-PAGE-LOAD-SEEN (no GET /api/boot %s: nothing has reached the "
                                 "host's page since then, or the log was cut)" % where)
    stamp, status = ev.last_boot
    if status == 200:
        return Signal("ok", "pairing: LAST-PAGE-LOAD-PAIRED (a page load at %s was accepted)" % stamp)
    if status == 401:
        if ev.last_pair_ok and ev.last_pair_ok >= stamp:
            return Signal("ok", "pairing: PAIRED-AFTER-LAST-REFUSAL (page load refused at %s, then POST "
                                "/api/pair 200 at %s)" % (stamp, ev.last_pair_ok))
        since = ("since the last host start (%s): %d pair attempt(s), %d accepted" % (
            ev.last_start, ev.pair_attempts, ev.pair_ok)) if ev.last_start else \
            "%d pair attempt(s) in the log, %d accepted" % (ev.pair_attempts, ev.pair_ok)
        return Signal("down", "pairing: LAST-PAGE-LOAD-REFUSED (GET /api/boot 401 at %s, no pairing after it; %s)"
                              % (stamp, since))
    return Signal("unknown", "pairing: the last GET /api/boot answered %d at %s" % (status, stamp))


def count_devices(path):
    """(active, enrolled) from devices.json, or None. Reads the structure only: no label, no digest
    is ever kept or printed."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        devices = doc["devices"]
        if not isinstance(devices, list) or not all(isinstance(d, dict) for d in devices):
            return None
        return sum(1 for d in devices if d.get("revoked_at") is None), len(devices)
    except (OSError, ValueError, KeyError, TypeError):
        return None


# ---------------------------------------------------------------- the verdict

def combine(ts, host, forward):
    """Tailscale and the host decide the GREYWOLF end; the forward decides FORWARD-DOWN. Anything
    that could not be read is UNKNOWN: OK is the claim that needs every reading."""
    if ts.state == "down" or host.state == "down":
        return DOWN
    if ts.state != "ok" or host.state != "ok":
        return UNKNOWN
    if forward is None:
        return OK
    if forward.state == "down":
        return FORWARD_DOWN
    if forward.state != "ok":
        return UNKNOWN
    return OK


def headline(verdict, ts, host, forward):
    if verdict == OK:
        base = "Tailscale is Running here and the host answers"
        if forward is None:
            return base + " (no forward address was given, so the overlord path is not checked)"
        return base + " and so does the forward"
    if verdict == DOWN:
        return "; ".join(s.detail for s in (ts, host) if s.state == "down")
    if verdict == FORWARD_DOWN:
        return forward.detail
    return " | ".join(s.detail for s in (ts, host, forward) if s is not None and s.state != "ok")


def next_step(verdict, phone, pairing):
    """One line naming the owner step the evidence points at. Never an action this script takes."""
    if verdict == DOWN:
        return "start or sign in to Tailscale on GREYWOLF, or start the NovahOS phone host, then run this again"
    if verdict == FORWARD_DOWN:
        return "the host is fine; check the forward on overlord (this PC cannot fix it)"
    if verdict == UNKNOWN:
        return "run this again when the PC is less busy; an unreadable or timed-out reading proves nothing"
    if phone is not None and phone.state == "down":
        return "on the iPhone: open the Tailscale app and make sure it says Connected, then try Safari again"
    if pairing is not None and pairing.state == "down":
        return ("pair the phone: at GREYWOLF double-click Pair-Phone.cmd, then type the code in the page "
                "on the iPhone (the log shows pages reaching the host and being refused as not paired)")
    return "nothing from this PC points at a fault; the phone's own request is not visible from here"


def run_tailscale(args, exe, timeout=20):
    """Run the tailscale CLI. Returns (text, None) or (None, why). stdin is closed so a scheduled
    task without a console cannot make subprocess fail on an invalid handle."""
    try:
        out = subprocess.run([exe] + list(args), capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, "%s: %s" % (type(exc).__name__, exc)
    return out.stdout.decode("utf-8", "replace"), None


def find_tailscale(explicit=None):
    if explicit:
        return explicit
    return shutil.which("tailscale") or (DEFAULT_TAILSCALE if os.path.exists(DEFAULT_TAILSCALE) else None)


def default_paths(env=os.environ):
    base = env.get("LOCALAPPDATA")
    if not base:
        return None, None
    return (os.path.join(base, "Novah", "Prime", "services", "novahos-phone.log"),
            os.path.join(base, "Novah", "phone"))


def check(host_url=None, forward_url=None, log_path=None, state_dir=None, phone_hint=None,
          do_ping=True, tailscale=None, timeout=10.0, tailscale_fn=run_tailscale, health_fn=fetch_health,
          read_log_fn=read_log_tail, devices_fn=count_devices):
    """Take every reading and combine them. Returns (verdict, evidence lines, next line)."""
    evidence = []
    exe = find_tailscale(tailscale)

    # tailscale (this PC) and the phone peer
    doc = None
    if exe is None:
        ts = Signal("unknown", "tailscale: the CLI was not found (pass --tailscale)")
    else:
        text, why = tailscale_fn(["status", "--json"], exe)
        if text is None:
            ts = Signal("unknown", "tailscale: status could not run (%s)" % why)
        else:
            try:
                doc = json.loads(text)
            except ValueError:
                doc = None
            ts = classify_tailscale(doc)
    evidence.append(ts.detail)

    phone = None
    if doc is not None:
        peers, pwhy = find_phone_peers(doc, phone_hint)
        ping = None
        ips = phone_ips(doc, phone_hint)
        if do_ping and exe is not None and ips and any(p.online for p in peers):
            ptext, _ = tailscale_fn(["ping", "--c", "3", "--timeout", "3s", ips[0]], exe, timeout=30)
            if ptext is not None:
                ping = (3, ptext)
        phone = classify_phone(peers, pwhy, ping)
    else:
        phone = Signal("unknown", "phone: not looked at (tailscale status unreadable)")

    # the host: address from the argument, else from the log's last start line
    ev, truncated, log_note = None, False, None
    if log_path is None or state_dir is None:
        dlog, dstate = default_paths()
        log_path = log_path or dlog
        state_dir = state_dir or dstate
    if log_path:
        try:
            text, size, truncated = read_log_fn(log_path)
            ev = scan_log(text)
        except OSError as exc:
            log_note = "host log unreadable (%s)" % exc
    else:
        log_note = "host log path unknown (no LOCALAPPDATA; pass --log)"

    if host_url is None and ev is not None and ev.bind is not None:
        host_url = "http://%s:%d" % ev.bind
    if host_url is None:
        host = HealthResult("unknown", "host: no address (not given and none in the host log; pass --host)")
    else:
        host = health_fn(host_url, "host", timeout)
    evidence.append(host.detail)

    forward = None
    if forward_url:
        forward = health_fn(forward_url, "forward", timeout)
        evidence.append(forward.detail)
    else:
        evidence.append("forward: not checked (no --forward or NOVAHOS_PHONE_FORWARD)")

    evidence.append(phone.detail)

    pairing = None
    if ev is not None:
        pairing = classify_pairing(ev, truncated)
        evidence.append(pairing.detail)
        note = "log: %d line(s) read, %d request(s)" % (ev.lines, ev.requests)
        if ev.bad:
            note += ", %d request-looking line(s) unreadable" % ev.bad
        if truncated:
            note += ", only the last %d KiB were read" % (LOG_WINDOW_BYTES // 1024)
        evidence.append(note + "; times are the PC's local time as logged")
    else:
        evidence.append("pairing: UNKNOWN, " + log_note)

    dev = devices_fn(os.path.join(state_dir, "devices.json")) if state_dir else None
    if dev is None:
        evidence.append("devices: unknown (devices.json unreadable or not found)")
    else:
        evidence.append("devices: %d active of %d enrolled (a count only)" % dev)

    evidence.append("not visible from here: the iPhone's own request to the forward, and what Safari shows")

    verdict = combine(ts, host, forward)
    return verdict, headline(verdict, ts, host, forward), evidence, next_step(verdict, phone, pairing)


def main(argv=None, out=sys.stdout, check_fn=check):
    ap = argparse.ArgumentParser(description="Is the GREYWOLF end of the iPhone path working?")
    ap.add_argument("--host", help="the phone host's address, http://host:port (default: from the host log)")
    ap.add_argument("--forward", default=os.environ.get("NOVAHOS_PHONE_FORWARD"),
                    help="the overlord forward's address, http://host:port (or NOVAHOS_PHONE_FORWARD)")
    ap.add_argument("--log", help="the phone host's request log (default under %%LOCALAPPDATA%%\\Novah)")
    ap.add_argument("--state", help="the phone host's state folder holding devices.json")
    ap.add_argument("--phone", help="part of the phone's Tailscale name (default: every iOS peer)")
    ap.add_argument("--tailscale", help="path to the tailscale CLI")
    ap.add_argument("--no-ping", action="store_true", help="do not send `tailscale ping` to the phone")
    ap.add_argument("--timeout", type=float, default=10.0, help="seconds to wait for each health GET")
    args = ap.parse_args(argv)
    verdict, why, evidence, nxt = check_fn(
        host_url=args.host, forward_url=args.forward, log_path=args.log, state_dir=args.state,
        phone_hint=args.phone, do_ping=not args.no_ping, tailscale=args.tailscale, timeout=args.timeout)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print("%s %s" % (verdict, why), file=out)
    for line in evidence + ["next: " + nxt, "checked_at=" + now]:
        print("  " + line, file=out)
    return EXIT[verdict]


if __name__ == "__main__":
    sys.exit(main())
