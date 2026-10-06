"""NODE CAPTIVE-WAIT: the captive-portal probe says CAPTIVE only on proof, ONLINE only on two
proofs, and UNKNOWN whenever it cannot tell.

The event samples below are the shape (numeric fields only) of the real Microsoft-Windows-NCSI
log on this PC; the sequence is 10-06 02:13Z, the episode TLS-INTERCEPT matched to the TLS errors.
"""
import http.client
import importlib.util
import io
import os
import socket

import pytest

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "node", "captive_probe.py")
_spec = importlib.util.spec_from_file_location("captive_probe", _PATH)
cp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cp)

WIFI = 19985273102270464
OTHER = 1234
V4, V6 = 0, 1
NONE, LOCAL, INTERNET = 0, 1, 2
ACTIVE_OK, HOTSPOT_FAIL, SUSPECT_DNS, PASSIVE, RESET, NO_ADDR = 4, 7, 10, 13, 14, 1


def ev(rid, minute, kind="cap", luid=WIFI, fam=V4, cap=INTERNET, reason=ACTIVE_OK):
    """One NCSI event. kind 'hot' is the 4038 'Hotspot detected' event, 'cap' is 4042."""
    t = "2026-10-06T02:%02d:00.0000000Z" % minute
    if kind == "hot":
        return cp.Event(rid, t, cp.EV_HOTSPOT, luid, fam, None, None)
    return cp.Event(rid, t, cp.EV_CAPABILITY, luid, fam, cap, reason)


def newest_first(*events):
    return sorted(events, key=lambda e: e.record_id, reverse=True)


# ---------------------------------------------------------------- parse_events

def _xml(rid, event_id, data):
    fields = "".join("<Data Name='%s'>%s</Data>" % (k, v) for k, v in data.items())
    return ("<Event xmlns='http://schemas.microsoft.com/win/2004/08/events/event'><System>"
            "<EventID>%d</EventID><TimeCreated SystemTime='2026-10-06T02:13:31.1004607Z'/>"
            "<EventRecordID>%d</EventRecordID></System><EventData>%s</EventData></Event>"
            % (event_id, rid, fields))


def test_parse_reads_both_event_kinds_newest_first():
    text = (_xml(10, 4042, {"IfLuid": WIFI, "Family": 0, "Capability": 1, "CapabilityChangeReason": 7})
            + _xml(11, 4038, {"IfLuid": WIFI, "Family": 0}))
    events, bad = cp.parse_events(text)
    assert bad == 0
    assert [e.record_id for e in events] == [11, 10]
    assert events[0].event_id == cp.EV_HOTSPOT and events[0].capability is None
    assert (events[1].capability, events[1].reason) == (LOCAL, HOTSPOT_FAIL)


def test_parse_counts_an_unreadable_event_instead_of_dropping_it_silently():
    text = _xml(10, 4042, {"IfLuid": WIFI, "Family": 0}) + _xml(11, 4038, {"IfLuid": WIFI, "Family": 0})
    events, bad = cp.parse_events(text)    # the first has no Capability fields
    assert bad == 1 and len(events) == 1


def test_parse_empty_output_is_no_events():
    assert cp.parse_events("") == ([], 0)


# ---------------------------------------------------------------- classify_windows

def test_internet_after_probe_succeeded_is_online():
    sig = cp.classify_windows(newest_first(ev(1, 0)), WIFI)
    assert sig.state == "online", sig


def test_hotspot_event_is_captive_and_names_when_it_began():
    events = newest_first(ev(1, 0), ev(2, 13, cap=LOCAL, reason=HOTSPOT_FAIL), ev(3, 13, kind="hot"),
                          ev(4, 17, kind="hot"))
    sig = cp.classify_windows(events, WIFI)
    assert sig.state == "captive", sig
    assert "captive since 2026-10-06T02:13:00" in sig.detail


def test_captive_ends_when_windows_logs_internet_again():
    events = newest_first(ev(1, 13, cap=LOCAL, reason=HOTSPOT_FAIL), ev(2, 17, kind="hot"),
                          ev(3, 23, cap=INTERNET, reason=ACTIVE_OK))
    assert cp.classify_windows(events, WIFI).state == "online"


def test_hotspot_failed_capability_alone_is_captive():
    sig = cp.classify_windows(newest_first(ev(1, 13, cap=LOCAL, reason=HOTSPOT_FAIL)), WIFI)
    assert sig.state == "captive"


def test_suspect_dns_alone_is_offline_not_captive():
    # It came 4 times on this PC and cleared within seconds 3 times; once a portal followed.
    sig = cp.classify_windows(newest_first(ev(1, 0), ev(2, 13, cap=LOCAL, reason=SUSPECT_DNS)), WIFI)
    assert sig.state == "offline", sig


def test_no_address_is_offline():
    sig = cp.classify_windows(newest_first(ev(1, 0, cap=NONE, reason=NO_ADDR)), WIFI)
    assert sig.state == "offline"


def test_a_portal_in_either_family_makes_the_interface_captive():
    events = newest_first(ev(1, 0, fam=V4), ev(2, 5, fam=V6, cap=LOCAL, reason=HOTSPOT_FAIL))
    assert cp.classify_windows(events, WIFI).state == "captive"


def test_a_stale_v6_none_does_not_hide_a_current_v4_internet():
    events = newest_first(ev(1, 0, fam=V6, cap=NONE, reason=NO_ADDR), ev(2, 5, fam=V4))
    assert cp.classify_windows(events, WIFI).state == "online"


def test_other_interfaces_are_ignored():
    # A hotspot on another adapter must not turn the Wi-Fi captive.
    events = newest_first(ev(1, 0), ev(2, 5, luid=OTHER, kind="hot"))
    assert cp.classify_windows(events, WIFI).state == "online"


def test_no_events_for_the_default_route_interface_is_unknown():
    assert cp.classify_windows(newest_first(ev(1, 0, luid=OTHER)), WIFI).state == "unknown"
    assert cp.classify_windows([], WIFI).state == "unknown"


def test_no_default_route_is_unknown():
    assert cp.classify_windows(newest_first(ev(1, 0)), None).state == "unknown"


# ---------------------------------------------------------------- classify_http

REAL = b"Microsoft Connect Test"


def test_http_expected_text_is_online():
    assert cp.classify_http(200, REAL).state == "online"
    assert cp.classify_http(200, REAL + b"\r\n").state == "online"


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_http_redirect_is_captive_and_names_only_the_host(status):
    sig = cp.classify_http(status, b"", "http://10.11.12.1:8080/login?sid=SECRET123&mac=aa")
    assert sig.state == "captive"
    assert "10.11.12.1:8080" in sig.detail
    assert "SECRET123" not in sig.detail and "login" not in sig.detail


def test_http_511_is_captive():
    assert cp.classify_http(511, b"<html>log in</html>").state == "captive"


def test_http_200_with_another_page_is_captive():
    # Many portals answer every URL 200 with their own login page.
    assert cp.classify_http(200, b"<html>Welcome to Hello WiFi</html>").state == "captive"


@pytest.mark.parametrize("status", [204, 400, 403, 404, 500, 502, 503])
def test_http_other_statuses_say_nothing(status):
    assert cp.classify_http(status, b"").state == "unknown"


# ---------------------------------------------------------------- http_signal

class FakeResponse:
    def __init__(self, status, body=b"", location=None):
        self.status, self._body, self._loc = status, body, location

    def read(self, n=-1):
        return self._body

    def getheader(self, name):
        return self._loc if name == "Location" else None


def fake_connection(response=None, raises=None, log=None):
    class Conn:
        def __init__(self, host, port, timeout=None):
            self.args = (host, port)
            if log is not None:
                log.append(("connect", host, port))

        def request(self, method, path, headers=None):
            if log is not None:
                log.append((method, path))
            if raises:
                raise raises

        def getresponse(self):
            return response

        def close(self):
            pass
    return Conn


def test_http_signal_sends_exactly_one_plain_get_and_does_not_follow_a_redirect():
    log = []
    sig = cp.http_signal(connection=fake_connection(FakeResponse(302, b"", "http://portal.example/x"), log=log))
    assert sig.state == "captive"
    assert log == [("connect", cp.HTTP_HOST, 80), ("GET", cp.HTTP_PATH)]   # one request, port 80, no TLS


@pytest.mark.parametrize("exc", [socket.timeout("timed out"), ConnectionResetError("reset"),
                                 socket.gaierror(11001, "getaddrinfo failed"),
                                 http.client.RemoteDisconnected("closed")])
def test_http_signal_failure_is_unknown(exc):
    sig = cp.http_signal(connection=fake_connection(raises=exc))
    assert sig.state == "unknown", sig
    assert "failed" in sig.detail


# ---------------------------------------------------------------- the verdict

S = cp.Signal


@pytest.mark.parametrize("win,web,verdict", [
    ("online", "online", cp.ONLINE),
    ("captive", "captive", cp.CAPTIVE),
    ("unknown", "captive", cp.CAPTIVE),
    ("online", "captive", cp.CAPTIVE),          # a fresh portal reply beats an older Windows reading
    ("captive", "unknown", cp.CAPTIVE),         # Windows saw a portal and the network will not answer
    ("captive", "offline", cp.CAPTIVE),
    ("captive", "skipped", cp.CAPTIVE),         # --no-http can still prove CAPTIVE
    ("captive", "online", cp.UNKNOWN),          # the signals disagree: do not wait, do not call it fine
    ("online", "unknown", cp.UNKNOWN),
    ("unknown", "online", cp.UNKNOWN),
    ("unknown", "unknown", cp.UNKNOWN),
    ("offline", "online", cp.UNKNOWN),
    ("offline", "unknown", cp.UNKNOWN),
    ("online", "skipped", cp.UNKNOWN),          # --no-http can never say ONLINE
    ("unknown", "skipped", cp.UNKNOWN),
    ("offline", "skipped", cp.UNKNOWN),
])
def test_combine_truth_table(win, web, verdict):
    assert cp.combine(S(win, "w"), S(web, "h")) == verdict


def test_online_needs_both_signals_every_other_pairing_is_not_online():
    states = ["online", "captive", "offline", "unknown", "skipped"]
    for w in states:
        for h in states:
            if (w, h) != ("online", "online"):
                assert cp.combine(S(w, ""), S(h, "")) != cp.ONLINE, (w, h)


def test_check_never_runs_the_http_probe_with_no_http():
    def boom():
        raise AssertionError("http probe ran under --no-http")
    verdict, evidence, why = cp.check(use_http=False, win_fn=lambda: S("online", "w"), web_fn=boom)
    assert verdict == cp.UNKNOWN


# ---------------------------------------------------------------- windows_signal degrades to unknown

def test_windows_signal_without_a_route_is_unknown(monkeypatch):
    monkeypatch.setattr(cp, "default_route_luid", lambda: (None, "no default route"))
    assert cp.windows_signal().state == "unknown"


def test_windows_signal_with_an_unreadable_log_is_unknown(monkeypatch):
    monkeypatch.setattr(cp, "default_route_luid", lambda: (WIFI, None))

    def nope(*a, **k):
        raise FileNotFoundError("wevtutil")
    monkeypatch.setattr(cp, "read_ncsi_events", nope)
    assert cp.windows_signal().state == "unknown"


def test_windows_signal_with_garbage_output_is_unknown(monkeypatch):
    monkeypatch.setattr(cp, "default_route_luid", lambda: (WIFI, None))
    monkeypatch.setattr(cp, "read_ncsi_events", lambda *a, **k: "not xml at all <<<")
    assert cp.windows_signal().state == "unknown"


def test_windows_signal_with_only_unreadable_events_is_unknown(monkeypatch):
    monkeypatch.setattr(cp, "default_route_luid", lambda: (WIFI, None))
    monkeypatch.setattr(cp, "read_ncsi_events",
                        lambda *a, **k: _xml(1, 4042, {"IfLuid": WIFI, "Family": 0}))
    assert cp.windows_signal().state == "unknown"


# ---------------------------------------------------------------- main: output, exit codes, --wait

def run_main(argv, verdicts):
    """Run main with scripted check results. Returns (exit code, output, number of checks, slept)."""
    results = list(verdicts)
    calls, slept = [], []
    clock = {"t": 0.0}

    def fake_check(use_http=True):
        calls.append(use_http)
        v = results.pop(0) if len(results) > 1 else results[0]
        return v, ["windows: w", "http: h"], "why " + v

    def fake_sleep(s):
        slept.append(s)
        clock["t"] += s

    out = io.StringIO()
    rc = cp.main(argv, out=out, sleep=fake_sleep, clock=lambda: clock["t"], check_fn=fake_check)
    return rc, out.getvalue(), calls, slept


@pytest.mark.parametrize("verdict,code", [(cp.ONLINE, 0), (cp.UNKNOWN, 2), (cp.CAPTIVE, 3)])
def test_main_first_line_is_the_verdict_and_the_exit_code_matches(verdict, code):
    rc, text, calls, slept = run_main([], [verdict])
    assert rc == code
    assert text.splitlines()[0] == "%s why %s" % (verdict, verdict)
    assert text.splitlines()[-1].startswith("  checked_at=")
    assert slept == [] and len(calls) == 1


def test_main_without_wait_never_sleeps_even_when_captive():
    rc, text, calls, slept = run_main([], [cp.CAPTIVE])
    assert rc == 3 and slept == []


def test_main_wait_rechecks_until_the_portal_clears():
    rc, text, calls, slept = run_main(["--wait", "600", "--every", "60"],
                                      [cp.CAPTIVE, cp.CAPTIVE, cp.CAPTIVE, cp.ONLINE])
    assert rc == 0 and len(calls) == 4 and slept == [60, 60, 60]
    assert text.splitlines()[0].startswith("ONLINE")
    assert "waited 180 s over 4 check(s)" in text


def test_main_wait_gives_up_still_captive_and_says_so():
    rc, text, calls, slept = run_main(["--wait", "150", "--every", "60"], [cp.CAPTIVE])
    assert rc == 3 and len(calls) == 3 and sum(slept) == 120
    assert text.splitlines()[0].startswith("CAPTIVE")
    assert "still captive" in text


def test_main_wait_stops_waiting_on_unknown():
    # Waiting is for a portal that is proven. UNKNOWN is returned at once.
    rc, text, calls, slept = run_main(["--wait", "600"], [cp.UNKNOWN])
    assert rc == 2 and slept == [] and len(calls) == 1


def test_main_passes_no_http_through():
    rc, text, calls, slept = run_main(["--no-http"], [cp.CAPTIVE])
    assert calls == [False]


def test_main_clamps_a_tiny_interval_so_it_cannot_hammer_the_portal():
    rc, text, calls, slept = run_main(["--wait", "60", "--every", "1"], [cp.CAPTIVE])
    assert slept and all(s >= 15 for s in slept)


# ---------------------------------------------------------------- the hard rules, as a guard

def test_the_probe_never_touches_tls_certificates_or_a_portal_form():
    """Owner's hard rules: never disable certificate verification, never trust or install the
    portal's certificate, never submit anything to the portal. The probe makes no TLS connection
    at all. If a later edit reaches for any of these, this fails first."""
    with open(_PATH, encoding="utf-8") as f:
        code = "\n".join(line.split("#", 1)[0] for line in f.read().splitlines())
    for banned in ("import ssl", "from ssl", "HTTPSConnection", "https://", "_create_unverified_context",
                   "CERT_NONE", "check_hostname", "verify=", "NODE_TLS_REJECT_UNAUTHORIZED",
                   "certutil", "Import-Certificate", '"POST"', "'POST'", "urlencode", "cookiejar",
                   "getpass", "password", "token"):
        assert banned not in code, banned
    assert cp.HTTP_URL.startswith("http://")
    assert 'conn.request("GET"' in code
