"""NODE: is this PC's network behind a captive portal right now?  CAPTIVE, ONLINE or UNKNOWN.

Why (CAPTIVE-WAIT; owner answered q290 = C, 2026-10-06). The PC's Wi-Fi sometimes drops into a
captive portal, for seconds or for hours. While it does, the portal answers HTTPS for every site
with its own self-signed certificate and its DNS gives wrong answers. Windows' connectivity check
(NCSI) notices and logs "Hotspot detected". TLS-INTERCEPT matched 89 of 89
DEPTH_ZERO_SELF_SIGNED_CERT errors to those windows, and the CI runners share the host's network,
so everything fails at once. During an episode a certificate error is the network, not the code,
the runner or the vendor: wait and retry; do not fail the task, restart or recreate anything.

Two signals, and ONLINE needs both:
  windows  Windows' own verdict, read from the Microsoft-Windows-NCSI/Operational event log for
           the interface that carries the default route. Numeric fields only, so the reading
           does not depend on the display language. Local: it sends nothing.
  http     ONE plain-HTTP GET of http://www.msftconnecttest.com/connecttest.txt, the URL Windows
           itself probes. Redirects are NOT followed; the body must be exactly the known text.

Verdict, printed as the first line (evidence follows, indented):
  CAPTIVE  a signal positively saw a portal, and the http probe did not just reach the real page
           (exit 3)
  ONLINE   both signals say the internet is reachable (exit 0)
  UNKNOWN  anything else: a signal could not run, the two disagree, or the network is down
           without a portal (exit 2)
A probe that cannot tell says UNKNOWN, never ONLINE.

What it never does: it makes no TLS connection, so there is no certificate to check or to trust;
it never follows the portal's redirect, never submits anything to it and reads no credentials.
The only traffic is the one GET above (one per check with --wait); --no-http sends nothing and
can then say CAPTIVE or UNKNOWN, never ONLINE.

Usage:
    python captive_probe.py                       one check
    python captive_probe.py --wait 540            while CAPTIVE, re-check every 60 s for up to 540 s
    python captive_probe.py --no-http             Windows' log only; nothing leaves the machine

Stdlib only. The source and tests live in leadfuel-core (node/); the runner stall check runs a
copy next to itself in the CI notes folder.
"""
import argparse
import datetime as dt
import http.client
import os
import socket
import struct
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from collections import namedtuple
from urllib.parse import urlsplit

ONLINE, CAPTIVE, UNKNOWN = "ONLINE", "CAPTIVE", "UNKNOWN"
EXIT = {ONLINE: 0, UNKNOWN: 2, CAPTIVE: 3}

HTTP_HOST = "www.msftconnecttest.com"
HTTP_PATH = "/connecttest.txt"
HTTP_URL = "http://" + HTTP_HOST + HTTP_PATH
HTTP_EXPECT = b"Microsoft Connect Test"
USER_AGENT = "leadfuel-captive-probe/1"

NCSI_LOG = "Microsoft-Windows-NCSI/Operational"
EV_HOTSPOT = 4038      # "Hotspot detected on interface %1 (Family: %2)"
EV_CAPABILITY = 4042   # "Capability change on %1 (%2 Family: %3 Capability: %4 ChangeReason: %5)"
FAMILY = {0: "IPv4", 1: "IPv6"}
CAPABILITY = {0: "None", 1: "Local", 2: "Internet"}
# Every reason this PC's log has shown (5,000 events, 2026-08-20..10-06). Others print by number.
REASON = {1: "NoAddress", 2: "NoGlobalAddress", 4: "ActiveHttpProbeSucceeded",
          7: "ActiveHttpProbeFailedHotspotDetected", 10: "SuspectDnsProbeFailed",
          13: "PassivePacketHops", 14: "CapabilityReset"}
REASON_HOTSPOT = 7
# NOT a portal by itself: SuspectDnsProbeFailed came 4 times and cleared within 2-20 s three
# times; only once (10-06 02:13:20Z) did a hotspot follow. It reads as "offline", not "captive".
_NS = "{http://schemas.microsoft.com/win/2004/08/events/event}"
# A documentation address (TEST-NET-1): only used to ask the routing table which interface would
# carry internet traffic. No packet is sent to it.
_ROUTE_PROBE_ADDR = "192.0.2.1"

Signal = namedtuple("Signal", "state detail")   # state: captive | online | offline | unknown | skipped
Event = namedtuple("Event", "record_id time event_id luid family capability reason")


# ---------------------------------------------------------------- windows: NCSI's own verdict

def parse_events(xml_text):
    """wevtutil /f:xml prints <Event> elements back to back with no root. Returns Events, newest
    first by record id, and the number of <Event> elements that could not be read."""
    root = ET.fromstring("<Events>" + xml_text + "</Events>")
    events, bad = [], 0
    for el in root.iter(_NS + "Event"):
        try:
            system = el.find(_NS + "System")
            data = {d.get("Name"): (d.text or "") for d in el.iter(_NS + "Data")}
            ev_id = int(system.find(_NS + "EventID").text)
            events.append(Event(
                record_id=int(system.find(_NS + "EventRecordID").text),
                time=system.find(_NS + "TimeCreated").get("SystemTime"),
                event_id=ev_id,
                luid=int(data["IfLuid"]),
                family=int(data["Family"]),
                capability=int(data["Capability"]) if ev_id == EV_CAPABILITY else None,
                reason=int(data["CapabilityChangeReason"]) if ev_id == EV_CAPABILITY else None,
            ))
        except (AttributeError, KeyError, TypeError, ValueError):
            bad += 1
    events.sort(key=lambda e: e.record_id, reverse=True)
    return events, bad


def _event_state(ev):
    if ev.event_id == EV_HOTSPOT:
        return "captive"
    if ev.reason == REASON_HOTSPOT:
        return "captive"
    if ev.capability == 2:
        return "online"
    return "offline"


def _describe(ev):
    if ev.event_id == EV_HOTSPOT:
        return "hotspot detected"
    cap = CAPABILITY.get(ev.capability, str(ev.capability))
    return "capability %s (%s)" % (cap, REASON.get(ev.reason, "reason %s" % ev.reason))


def classify_windows(events, luid):
    """Windows' current state for one interface: the newest NCSI event per address family.
    Events must be newest first. A portal in either family makes the interface captive."""
    if luid is None:
        return Signal("unknown", "windows: cannot tell which interface carries the default route")
    mine = [e for e in events if e.luid == luid]
    if not mine:
        return Signal("unknown", "windows: no NCSI event for the default-route interface"
                                 " (luid 0x%x) in the log" % luid)
    states, parts = {}, []
    for fam in sorted({e.family for e in mine}):
        fam_events = [e for e in mine if e.family == fam]
        newest = fam_events[0]
        state = _event_state(newest)
        states[fam] = state
        text = "%s %s at %s" % (FAMILY.get(fam, "family %s" % fam), _describe(newest), newest.time)
        if state == "captive":
            since = newest
            for e in fam_events[1:]:
                if _event_state(e) != "captive":
                    break
                since = e
            text += " (captive since %s)" % since.time
        parts.append(text)
    detail = "windows: " + "; ".join(parts)
    values = set(states.values())
    if "captive" in values:
        return Signal("captive", detail)
    if "online" in values:
        return Signal("online", detail)
    return Signal("offline", detail)


def default_route_luid():
    """(luid, None) for the interface the routing table would use for internet traffic, or
    (None, why) when it cannot be read. Asks the local routing table; sends nothing."""
    if os.name != "nt":
        return None, "not Windows"
    try:
        import ctypes
        from ctypes import wintypes
        iphlp = ctypes.WinDLL("iphlpapi")
        dest = struct.unpack("<I", socket.inet_aton(_ROUTE_PROBE_ADDR))[0]
        index = wintypes.DWORD()
        rc = iphlp.GetBestInterface(wintypes.DWORD(dest), ctypes.byref(index))
        if rc != 0:
            return None, "no default route (GetBestInterface error %d)" % rc
        luid = ctypes.c_uint64()
        rc = iphlp.ConvertInterfaceIndexToLuid(wintypes.ULONG(index.value), ctypes.byref(luid))
        if rc != 0:
            return None, "ConvertInterfaceIndexToLuid error %d" % rc
        return luid.value, None
    except (OSError, AttributeError) as exc:
        return None, "routing table unreadable (%s)" % exc


def read_ncsi_events(count=500, timeout=20):
    cmd = ["wevtutil", "qe", NCSI_LOG,
           "/q:*[System[(EventID=%d or EventID=%d)]]" % (EV_HOTSPOT, EV_CAPABILITY),
           "/c:%d" % count, "/rd:true", "/f:xml"]
    out = subprocess.run(cmd, capture_output=True, timeout=timeout)
    if out.returncode != 0:
        raise OSError("wevtutil exit %d: %s" % (out.returncode,
                                                 out.stderr.decode("utf-8", "replace").strip()[:200]))
    return out.stdout.decode("utf-8", "replace")


def windows_signal():
    luid, why = default_route_luid()
    if luid is None:
        return Signal("unknown", "windows: " + why)
    try:
        events, bad = parse_events(read_ncsi_events())
    except (OSError, subprocess.SubprocessError, ET.ParseError) as exc:
        return Signal("unknown", "windows: cannot read the NCSI log (%s)" % exc)
    if bad and not events:
        return Signal("unknown", "windows: %d NCSI event(s) in the log, none readable" % bad)
    return classify_windows(events, luid)


# ---------------------------------------------------------------- http: the URL Windows probes

def classify_http(status, body, location=None):
    if status == 200 and body.strip() == HTTP_EXPECT:
        return Signal("online", "http: %s answered with the expected text" % HTTP_URL)
    if 300 <= status < 400:
        where = urlsplit(location or "")
        to = "%s://%s" % (where.scheme, where.netloc) if where.netloc else "no location"
        return Signal("captive", "http: %s redirected (%d) to %s" % (HTTP_URL, status, to))
    if status == 511:   # RFC 6585 "Network Authentication Required": made for captive portals
        return Signal("captive", "http: %s answered 511 Network Authentication Required" % HTTP_URL)
    if status == 200:
        return Signal("captive", "http: %s answered 200 with a different page (%d bytes)"
                                 % (HTTP_URL, len(body)))
    return Signal("unknown", "http: %s answered %d, which says nothing either way" % (HTTP_URL, status))


class _IPv4Connection(http.client.HTTPConnection):
    """IPv4 only, like Windows' own IPv4 probe: on this PC IPv6 has no route, and a connect that
    tries an unroutable IPv6 address first spends the whole budget before IPv4 gets a turn.
    Keeps its socket as raw_sock so the caller can shorten the timeout between steps."""

    def connect(self):
        addr = socket.getaddrinfo(self.host, self.port, socket.AF_INET, socket.SOCK_STREAM)[0][4]
        self.sock = self.raw_sock = socket.create_connection(addr, self.timeout)


def http_signal(timeout=20.0, connection=_IPv4Connection, clock=time.monotonic):
    """One GET with an overall deadline (the Wi-Fi here is slow: 2.6-7 s per GET measured on
    2026-10-06). A probe that runs out of time says unknown."""
    deadline = clock() + timeout

    def remaining():
        left = deadline - clock()
        if left <= 0:
            raise socket.timeout("no answer within %g s" % timeout)
        return left

    conn = None
    try:
        conn = connection(HTTP_HOST, 80, timeout=timeout)
        conn.request("GET", HTTP_PATH, headers={"User-Agent": USER_AGENT, "Connection": "close",
                                                "Cache-Control": "no-cache"})
        sock = getattr(conn, "raw_sock", None)
        if sock is not None:
            sock.settimeout(remaining())
        resp = conn.getresponse()
        if sock is not None:
            sock.settimeout(remaining())
        body = resp.read(4096)
        return classify_http(resp.status, body, resp.getheader("Location"))
    except (OSError, http.client.HTTPException) as exc:
        return Signal("unknown", "http: GET %s failed (%s: %s)" % (HTTP_URL, type(exc).__name__, exc))
    finally:
        if conn is not None:
            conn.close()


# ---------------------------------------------------------------- the verdict

def combine(win, web):
    """CAPTIVE is the safe direction (wait) and needs one positive sighting that the fresh http
    probe does not contradict. ONLINE is the claim that needs proof, so it needs both."""
    if web.state == "captive":
        return CAPTIVE
    if win.state == "captive" and web.state != "online":
        return CAPTIVE
    if win.state == "online" and web.state == "online":
        return ONLINE
    return UNKNOWN


def summary(verdict, win, web):
    if verdict == UNKNOWN and win.state == "captive" and web.state == "online":
        return "signals disagree: Windows last saw a portal, the http probe reached the real page"
    if verdict == CAPTIVE:
        seen = [s.detail for s in (win, web) if s.state == "captive"]
        return " | ".join(seen)
    if verdict == ONLINE:
        return "Windows and the http probe both reach the internet"
    unclear = [s.detail for s in (win, web) if s.state != "online"]
    return " | ".join(unclear)


def check(use_http=True, win_fn=windows_signal, web_fn=http_signal):
    win = win_fn()
    web = web_fn() if use_http else Signal("skipped", "http: not run (--no-http)")
    verdict = combine(win, web)
    return verdict, [win.detail, web.detail], summary(verdict, win, web)


def main(argv=None, out=sys.stdout, sleep=time.sleep, clock=time.monotonic, check_fn=check):
    ap = argparse.ArgumentParser(description="Is this PC behind a captive portal right now?")
    ap.add_argument("--no-http", action="store_true",
                    help="read Windows' log only; send nothing (can then say CAPTIVE or UNKNOWN only)")
    ap.add_argument("--wait", type=int, default=0, metavar="SECONDS",
                    help="while CAPTIVE, re-check until it clears or SECONDS have passed")
    ap.add_argument("--every", type=int, default=60, metavar="SECONDS",
                    help="re-check interval for --wait (default 60, minimum 15)")
    args = ap.parse_args(argv)
    every = max(15, args.every)

    started = clock()
    verdict, evidence, why = check_fn(use_http=not args.no_http)
    checks = 1
    while verdict == CAPTIVE and clock() - started + every <= args.wait:
        sleep(every)
        verdict, evidence, why = check_fn(use_http=not args.no_http)
        checks += 1
    if args.wait:
        waited = int(clock() - started)
        evidence = evidence + ["waited %d s over %d check(s)%s" % (
            waited, checks, "; still captive" if verdict == CAPTIVE else "")]
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print("%s %s" % (verdict, why), file=out)
    for line in evidence + ["checked_at=%s" % now]:
        print("  " + line, file=out)
    return EXIT[verdict]


if __name__ == "__main__":
    sys.exit(main())
