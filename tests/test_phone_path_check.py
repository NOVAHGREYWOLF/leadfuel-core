"""NODE desks-3-6: the phone path check says OK only when it saw every reading, DOWN only on positive
evidence, UNKNOWN when a reading could not be taken, and never says the phone works.

Every address, name and identity here is synthetic (documentation addresses, example.test). Nothing
reads the real machine: the tailscale CLI, the host log, devices.json and the network are all
replaced by the test, except one loopback HTTP server the test starts on 127.0.0.1.
"""
import http.client
import http.server
import importlib.util
import io
import json
import os
import socket
import threading

import pytest

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "node", "phone_path_check.py")
_spec = importlib.util.spec_from_file_location("phone_path_check", _PATH)
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)

WHO = "someone@example.test"        # the identity column of the host log: must never be printed
HOST = "http://192.0.2.10:8106"
FORWARD = "http://192.0.2.20:8106"


def ts_doc(state="Running", phone_online=True, health=None, self_online=True, extra_peers=None):
    peers = {"nodekey:aa": {"HostName": "iphone", "OS": "iOS", "Online": phone_online,
                            "TailscaleIPs": ["192.0.2.30", "fd7a::30"]},
             "nodekey:bb": {"HostName": "overlord", "OS": "linux", "Online": True,
                            "TailscaleIPs": ["192.0.2.20"]}}
    peers.update(extra_peers or {})
    return {"BackendState": state, "Health": health, "Self": {"Online": self_online}, "Peer": peers}


PONGS = ("pong from iphone (192.0.2.30) via DERP(lax) in 68ms\n"
         "pong from iphone (192.0.2.30) via DERP(lax) in 102ms\n"
         "pong from iphone (192.0.2.30) via DERP(lax) in 77ms\n")
HEALTH_BODY = json.dumps({"ok": True, "mode": "LOCAL", "model": "m"}).encode()


# ---------------------------------------------------------------- tailscale on this PC

def test_running_is_ok():
    assert pc.classify_tailscale(ts_doc()).state == "ok"


@pytest.mark.parametrize("state", ["NeedsLogin", "Stopped", "NeedsMachineAuth"])
def test_a_state_that_needs_the_owner_is_down(state):
    sig = pc.classify_tailscale(ts_doc(state))
    assert sig.state == "down" and state in sig.detail


@pytest.mark.parametrize("state", ["Starting", "NoState"])
def test_a_state_in_flux_is_unknown_not_down(state):
    assert pc.classify_tailscale(ts_doc(state)).state == "unknown"


@pytest.mark.parametrize("doc", [None, [], "Running", {}, {"BackendState": 3}])
def test_an_unreadable_status_is_unknown(doc):
    assert pc.classify_tailscale(doc).state == "unknown"


def test_the_self_online_flag_is_ignored_because_it_reads_false_on_a_working_node():
    # Measured 2026-11-23, tailscale 1.104.5: Self.Online false, LastSeen year 1, Running, and the
    # phone answered `tailscale ping` 3 of 3. Trusting the flag made the check say UNKNOWN every time.
    assert pc.classify_tailscale(ts_doc(self_online=False)).state == "ok"


def test_health_warnings_are_shown_without_changing_the_state():
    sig = pc.classify_tailscale(ts_doc(health=["The coordination server is slow"]))
    assert sig.state == "ok" and "coordination server" in sig.detail


# ---------------------------------------------------------------- the phone peer and the ping

def test_ios_peers_are_the_phone_by_default_and_other_peers_are_not():
    peers, why = pc.find_phone_peers(ts_doc())
    assert [p.name for p in peers] == ["iphone"] and "iOS" in why


def test_a_hint_selects_by_name_and_an_empty_result_says_how_it_was_filtered():
    peers, _ = pc.find_phone_peers(ts_doc(), hint="overlord")
    assert [p.name for p in peers] == ["overlord"]
    peers, why = pc.find_phone_peers(ts_doc(), hint="nothing-called-this")
    assert peers == [] and "nothing-called-this" in why


def test_no_peer_list_is_explained_not_called_offline():
    peers, why = pc.find_phone_peers({"BackendState": "Running"})
    assert peers == [] and "no peer list" in why
    assert pc.classify_phone(peers, why).state == "unknown"


def test_phone_addresses_are_ipv4_only():
    assert pc.phone_ips(ts_doc()) == ["192.0.2.30"]


def test_parse_ping_reads_derp_and_direct_routes():
    n, routes, ms = pc.parse_ping(PONGS + "pong from iphone (192.0.2.30) via 198.51.100.7:41641 in 12ms\n")
    assert n == 4 and routes[0] == "DERP(lax)" and routes[-1] == "198.51.100.7:41641"
    assert ms == [68.0, 102.0, 77.0, 12.0]


def test_parse_ping_of_a_timeout_is_zero_pongs():
    assert pc.parse_ping("ping \"192.0.2.30\" timed out\n") == (0, [], [])
    assert pc.parse_ping(None) == (0, [], [])


def test_phone_with_pongs_is_ok_and_names_the_route():
    peers, why = pc.find_phone_peers(ts_doc())
    sig = pc.classify_phone(peers, why, (3, PONGS))
    assert sig.state == "ok" and "3 of 3" in sig.detail and "DERP(lax)" in sig.detail


def test_phone_online_but_silent_to_ping_is_down_on_the_phone_side():
    peers, why = pc.find_phone_peers(ts_doc())
    sig = pc.classify_phone(peers, why, (3, "ping timed out\n"))
    assert sig.state == "down" and "0 of 3" in sig.detail


def test_phone_offline_without_a_ping_is_down_and_says_the_ping_did_not_run():
    peers, why = pc.find_phone_peers(ts_doc(phone_online=False))
    sig = pc.classify_phone(peers, why, None)
    assert sig.state == "down" and "not run" in sig.detail and "Offline" in sig.detail


# ---------------------------------------------------------------- health of the host and the forward

def test_the_hosts_own_health_body_is_ok():
    assert pc.classify_health(200, HEALTH_BODY, "host").state == "ok"


@pytest.mark.parametrize("status,body", [
    (200, b"<html>GREYWOLF is offline</html>"),         # the forward's own page is not the host
    (200, b"{\"ok\": true}"),                            # JSON, but not the host's body (no mode)
    (200, b"{\"ok\": false, \"mode\": \"LOCAL\"}"),
    (200, b""),
    (404, b""), (502, b"bad gateway"), (503, b""),
])
def test_anything_else_that_answers_is_down(status, body):
    assert pc.classify_health(status, body, "forward").state == "down"


class RefusingConnection:
    def __init__(self, *a, **k): pass
    def request(self, *a, **k): raise ConnectionRefusedError(10061, "refused")
    def close(self): pass


class TimingOutConnection(RefusingConnection):
    def request(self, *a, **k): raise socket.timeout("timed out")


class BrokenConnection(RefusingConnection):
    def request(self, *a, **k): raise http.client.BadStatusLine("garbage")


class UnreachableConnection(RefusingConnection):
    def request(self, *a, **k): raise OSError(10049, "address not valid in its context")


def test_connection_refused_is_positive_evidence_of_down():
    assert pc.fetch_health(HOST, "host", connection=RefusingConnection).state == "down"


@pytest.mark.parametrize("conn", [TimingOutConnection, BrokenConnection, UnreachableConnection])
def test_a_timeout_or_any_other_failure_is_unknown_never_down(conn):
    sig = pc.fetch_health(HOST, "host", connection=conn)
    assert sig.state == "unknown"


@pytest.mark.parametrize("url", ["", "192.0.2.10:8106", "https://192.0.2.10:8106", "http://"])
def test_an_address_that_is_not_http_host_port_is_unknown(url):
    assert pc.fetch_health(url, "host").state == "unknown"


class _Health(http.server.BaseHTTPRequestHandler):
    seen = []

    def do_GET(self):   # noqa: N802
        _Health.seen.append((self.path, self.headers.get("User-Agent")))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(HEALTH_BODY)

    def log_message(self, *a):
        pass


def test_a_real_loopback_server_answers_ok_and_gets_exactly_one_get():
    srv = http.server.HTTPServer(("127.0.0.1", 0), _Health)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        _Health.seen.clear()
        sig = pc.fetch_health("http://127.0.0.1:%d" % srv.server_address[1], "host", timeout=5)
    finally:
        srv.shutdown()
        srv.server_close()
    assert sig.state == "ok"
    assert [p for p, _ in _Health.seen] == ["/api/health"]
    assert _Health.seen[0][1].startswith("leadfuel-phone-path-check")


def test_a_closed_loopback_port_is_down():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    assert pc.fetch_health("http://127.0.0.1:%d" % port, "host", timeout=3).state == "down"


# ---------------------------------------------------------------- the host log

LOG = """\
=== novahos-phone started 2026-11-09 16:43:11 ===
phonehost: bind=192.0.2.10 port=8106 allow=%(who)s mode=LOCAL tools=off model=m history=C:\\x
phonehost: state=C:\\x\\phone paired=1 brain=on remote=client
2026-11-09 16:43:18 %(who)s GET /api/health 200 62ms -
2026-11-09 23:57:57 %(who)s GET / 200 0ms -
2026-11-09 23:57:58 %(who)s GET /api/boot 401 0ms -
2026-11-10 11:46:43 %(who)s GET /api/boot 401 0ms -
=== novahos-phone started 2026-11-22 19:06:03 ===
phonehost: bind=192.0.2.11 port=8107 allow=%(who)s mode=LOCAL tools=off model=m history=C:\\x
2026-11-23 14:25:27 %(who)s POST /api/ask 401 14ms -
""" % {"who": WHO}


def test_scan_reads_the_last_start_and_the_last_bind_not_the_first():
    ev = pc.scan_log(LOG)
    assert ev.last_start == "2026-11-22 19:06:03" and ev.bind == ("192.0.2.11", 8107)


def test_counts_restart_at_each_start_line_but_last_boot_does_not():
    ev = pc.scan_log(LOG)
    assert (ev.boots_refused, ev.boots_ok, ev.pair_attempts, ev.pair_ok) == (0, 0, 0, 0)
    assert ev.last_boot == ("2026-11-10 11:46:43", 401)


def test_counts_within_the_last_start_window():
    ev = pc.scan_log(LOG.split("=== novahos-phone started 2026-11-22")[0])
    assert (ev.boots_refused, ev.last_start) == (2, "2026-11-09 16:43:11")


def test_pair_attempts_and_the_accepted_one_are_counted_separately():
    text = LOG + ("2026-11-23 15:00:00 %s POST /api/pair 401 12ms -\n"
                  "2026-11-23 15:01:00 %s POST /api/pair 200 40ms -\n"
                  "2026-11-23 15:01:02 %s GET /api/boot?x=1 200 3ms -\n" % (WHO, WHO, WHO))
    ev = pc.scan_log(text)
    assert (ev.pair_attempts, ev.pair_ok, ev.last_pair_ok) == (2, 1, "2026-11-23 15:01:00")
    assert ev.last_boot == ("2026-11-23 15:01:02", 200)       # the query string is dropped


def test_request_looking_lines_that_cannot_be_read_are_counted_not_dropped():
    ev = pc.scan_log("2026-11-23 14:25:27 garbled\n2026-11-23 14:25:28 %s GET / 200 0ms -\n" % WHO)
    assert (ev.bad, ev.requests) == (1, 1)


def test_the_identity_column_is_not_kept_anywhere_in_the_evidence():
    assert WHO not in repr(pc.scan_log(LOG))


def test_a_log_with_no_page_load_is_unknown_and_says_so():
    ev = pc.scan_log("=== novahos-phone started 2026-11-22 19:06:03 ===\n")
    sig = pc.classify_pairing(ev)
    assert sig.state == "unknown" and "NO-PAGE-LOAD-SEEN" in sig.detail


def test_a_refused_page_load_with_no_pairing_after_it_is_down_and_gives_the_counts():
    sig = pc.classify_pairing(pc.scan_log(LOG.split("=== novahos-phone started 2026-11-22")[0]))
    assert sig.state == "down" and "LAST-PAGE-LOAD-REFUSED" in sig.detail
    assert "2 pair attempt" not in sig.detail and "0 pair attempt(s), 0 accepted" in sig.detail


def test_a_pairing_after_the_refusal_is_no_longer_down():
    base = LOG.split("=== novahos-phone started 2026-11-22")[0]
    sig = pc.classify_pairing(pc.scan_log(base + "2026-11-23 15:01:00 %s POST /api/pair 200 40ms -\n" % WHO))
    assert sig.state == "ok" and "PAIRED-AFTER-LAST-REFUSAL" in sig.detail
    # a pairing BEFORE the refusal does not clear it
    early = "2026-11-08 01:42:00 %s POST /api/pair 200 40ms -\n" % WHO
    assert pc.classify_pairing(pc.scan_log(early + base)).state == "down"


def test_an_accepted_page_load_is_ok():
    ev = pc.scan_log("2026-11-23 15:01:02 %s GET /api/boot 200 3ms -\n" % WHO)
    sig = pc.classify_pairing(ev)
    assert sig.state == "ok" and "LAST-PAGE-LOAD-PAIRED" in sig.detail


def test_a_truncated_read_is_said_in_the_unknown_case():
    sig = pc.classify_pairing(pc.scan_log(""), truncated=True)
    assert sig.state == "unknown" and "last part of the log" in sig.detail


def test_read_log_tail_drops_the_cut_first_line(tmp_path):
    p = tmp_path / "phone.log"
    p.write_text("".join("2026-11-23 14:25:%02d %s GET /x 200 0ms -\n" % (i % 60, WHO) for i in range(200)))
    text, size, truncated = pc.read_log_tail(str(p), window=2000)
    assert truncated and size > 2000
    assert all(line.startswith("2026-11-23") for line in text.splitlines())
    text, size, truncated = pc.read_log_tail(str(p), window=10 ** 9)
    assert not truncated and len(text.splitlines()) == 200


# ---------------------------------------------------------------- devices.json

def test_count_devices_counts_active_and_enrolled_and_returns_only_numbers(tmp_path):
    p = tmp_path / "devices.json"
    p.write_text(json.dumps({"version": 1, "pending": None, "devices": [
        {"id": "d0123456789", "label": "iPhone", "revoked_at": None, "secret_sha256": "a" * 64},
        {"id": "d9876543210", "label": "old", "revoked_at": 1.5, "secret_sha256": "b" * 64}]}))
    got = pc.count_devices(str(p))
    assert got == (1, 2) and all(isinstance(n, int) for n in got)


@pytest.mark.parametrize("content", ["not json", "{}", '{"devices": 3}', '{"devices": [1]}', ""])
def test_unreadable_device_files_are_none_not_zero(tmp_path, content):
    p = tmp_path / "devices.json"
    p.write_text(content)
    assert pc.count_devices(str(p)) is None


def test_a_missing_device_file_is_none(tmp_path):
    assert pc.count_devices(str(tmp_path / "nope.json")) is None


# ---------------------------------------------------------------- the verdict

S = pc.Signal


@pytest.mark.parametrize("ts,host,fwd,want", [
    (S("ok", ""), S("ok", ""), None, pc.OK),
    (S("ok", ""), S("ok", ""), S("ok", ""), pc.OK),
    (S("down", ""), S("ok", ""), S("ok", ""), pc.DOWN),
    (S("ok", ""), S("down", ""), S("ok", ""), pc.DOWN),
    (S("ok", ""), S("ok", ""), S("down", ""), pc.FORWARD_DOWN),
    (S("ok", ""), S("down", ""), S("down", ""), pc.DOWN),            # the PC end is the first fault
    (S("unknown", ""), S("ok", ""), None, pc.UNKNOWN),                # a host answer proves nothing about the tunnel
    (S("ok", ""), S("unknown", ""), None, pc.UNKNOWN),
    (S("ok", ""), S("ok", ""), S("unknown", ""), pc.UNKNOWN),
    (S("unknown", ""), S("unknown", ""), S("unknown", ""), pc.UNKNOWN),
    (S("down", ""), S("unknown", ""), None, pc.DOWN),
])
def test_combine(ts, host, fwd, want):
    assert pc.combine(ts, host, fwd) == want


# ---------------------------------------------------------------- the whole check, with every reading faked

class World:
    """Fakes for every reading, and a record of what the check asked for."""

    def __init__(self, doc=None, ping=PONGS, health=None, log="default", devices=(1, 2), cli_text=None):
        self.doc = ts_doc() if doc is None else doc
        self.ping = ping
        self.health = health or {HOST: S("ok", "host: 200"), FORWARD: S("ok", "forward: 200")}
        self.log = LOG.split("=== novahos-phone started 2026-11-22")[0] if log == "default" else log
        self.devices = devices
        self.cli_text = cli_text
        self.cli_calls, self.gets = [], []

    def tailscale_fn(self, args, exe, timeout=20):
        self.cli_calls.append(list(args))
        if args[0] == "status":
            return (self.cli_text if self.cli_text is not None else json.dumps(self.doc)), None
        return self.ping, None

    def health_fn(self, url, label, timeout=10.0):
        self.gets.append(url)
        return self.health[url]

    def read_log_fn(self, path):
        if self.log is False:
            raise OSError("no such file")
        return self.log, len(self.log), False

    def devices_fn(self, path):
        return self.devices

    def run(self, **kw):
        kw.setdefault("host_url", HOST)
        kw.setdefault("log_path", "log")
        kw.setdefault("state_dir", "state")
        kw.setdefault("tailscale", "tailscale")
        return pc.check(tailscale_fn=self.tailscale_fn, health_fn=self.health_fn,
                        read_log_fn=self.read_log_fn, devices_fn=self.devices_fn, **kw)


def test_all_readings_good_is_ok_and_the_only_traffic_is_one_get_per_address_and_a_ping():
    w = World()
    verdict, why, ev, nxt = w.run(forward_url=FORWARD)
    assert verdict == pc.OK
    assert w.gets == [HOST, FORWARD]
    assert w.cli_calls[0] == ["status", "--json"] and w.cli_calls[1][0] == "ping" and len(w.cli_calls) == 2
    assert w.cli_calls[1][-1] == "192.0.2.30"                  # the phone, no other address
    assert any("not visible from here" in line for line in ev)


def test_ok_with_no_forward_says_the_forward_was_not_checked():
    verdict, why, ev, _ = World().run()
    assert verdict == pc.OK and "not checked" in why and any(l.startswith("forward: not checked") for l in ev)


def test_no_ping_flag_sends_no_ping():
    w = World()
    w.run(do_ping=False)
    assert [c[0] for c in w.cli_calls] == ["status"]


def test_the_phone_is_not_pinged_when_tailscale_says_it_is_offline():
    w = World(doc=ts_doc(phone_online=False))
    verdict, _, ev, nxt = w.run()
    assert [c[0] for c in w.cli_calls] == ["status"]
    assert verdict == pc.OK and "Tailscale" in nxt and "iPhone" in nxt


def test_tailscale_stopped_on_the_pc_is_down():
    verdict, why, _, nxt = World(doc=ts_doc("Stopped")).run()
    assert verdict == pc.DOWN and "Stopped" in why and "Tailscale" in nxt


def test_host_refusing_is_down():
    w = World(health={HOST: S("down", "host: connection refused")})
    assert w.run()[0] == pc.DOWN


def test_host_timing_out_is_unknown_not_down():
    w = World(health={HOST: S("unknown", "host: GET failed (timeout)")})
    verdict, why, _, nxt = w.run()
    assert verdict == pc.UNKNOWN and "timeout" in why and "again" in nxt


def test_forward_down_with_a_good_host_is_forward_down():
    w = World(health={HOST: S("ok", "host: 200"), FORWARD: S("down", "forward: answered 502")})
    verdict, why, _, nxt = w.run(forward_url=FORWARD)
    assert verdict == pc.FORWARD_DOWN and "502" in why and "overlord" in nxt


def test_a_missing_tailscale_cli_is_unknown_even_when_the_host_answers():
    w = World()
    def gone(args, exe, timeout=20):
        return None, "FileNotFoundError: no such file"
    verdict, why, _, _ = pc.check(host_url=HOST, log_path="l", state_dir="s", tailscale="tailscale",
                                  tailscale_fn=gone, health_fn=w.health_fn, read_log_fn=w.read_log_fn,
                                  devices_fn=w.devices_fn)
    assert verdict == pc.UNKNOWN and "could not run" in why


def test_unparseable_tailscale_output_is_unknown():
    assert World(cli_text="not json at all").run()[0] == pc.UNKNOWN


def test_no_host_address_anywhere_is_unknown_and_makes_no_get():
    w = World(log="")                      # a log with no bind line, and no --host
    verdict, why, _, _ = w.run(host_url=None)
    assert verdict == pc.UNKNOWN and "no address" in why and w.gets == []


def test_the_host_address_comes_from_the_log_when_none_is_given():
    w = World(log=LOG, health={"http://192.0.2.11:8107": S("ok", "host: 200")})
    verdict, *_ = w.run(host_url=None)
    assert verdict == pc.OK and w.gets == ["http://192.0.2.11:8107"]


def test_a_refused_page_load_points_at_pairing_when_everything_else_is_fine():
    verdict, _, ev, nxt = World().run(forward_url=FORWARD)
    assert verdict == pc.OK
    assert "Pair-Phone.cmd" in nxt
    assert any("LAST-PAGE-LOAD-REFUSED" in l for l in ev)


def test_an_unreadable_log_is_unknown_for_pairing_and_the_host_check_still_runs():
    w = World(log=False)
    verdict, _, ev, _ = w.run()
    assert verdict == pc.OK
    assert any(l.startswith("pairing: UNKNOWN") for l in ev)


def test_unreadable_devices_are_reported_as_unknown_not_zero():
    _, _, ev, _ = World(devices=None).run()
    assert any(l.startswith("devices: unknown") for l in ev)


def test_the_identity_column_never_reaches_the_evidence():
    _, why, ev, nxt = World().run(forward_url=FORWARD)
    assert WHO not in " ".join([why, nxt] + ev)


# ---------------------------------------------------------------- main

def _fake_check(verdict, why="why", ev=("a", "b"), nxt="n"):
    def fn(**kw):
        return verdict, why, list(ev), nxt
    return fn


@pytest.mark.parametrize("verdict,code", [(pc.OK, 0), (pc.UNKNOWN, 2), (pc.DOWN, 3), (pc.FORWARD_DOWN, 4)])
def test_main_prints_the_verdict_first_indents_the_evidence_and_exits(verdict, code):
    out = io.StringIO()
    rc = pc.main([], out=out, check_fn=_fake_check(verdict))
    lines = out.getvalue().splitlines()
    assert rc == code and lines[0] == "%s why" % verdict
    assert all(l.startswith("  ") for l in lines[1:]) and lines[-2] == "  next: n"
    assert lines[-1].startswith("  checked_at=")


def test_main_passes_the_options_through_and_never_claims_the_phone_works():
    seen = {}
    def fn(**kw):
        seen.update(kw)
        return pc.OK, "ok", ["x"], "n"
    out = io.StringIO()
    pc.main(["--host", HOST, "--forward", FORWARD, "--no-ping", "--phone", "pho", "--timeout", "3"], out=out, check_fn=fn)
    assert seen["host_url"] == HOST and seen["forward_url"] == FORWARD and seen["do_ping"] is False
    assert seen["phone_hint"] == "pho" and seen["timeout"] == 3.0
    assert "phone works" not in out.getvalue().lower()


def test_main_reads_the_forward_from_the_environment(monkeypatch):
    monkeypatch.setenv("NOVAHOS_PHONE_FORWARD", FORWARD)
    seen = {}
    def fn(**kw):
        seen.update(kw)
        return pc.OK, "ok", [], "n"
    pc.main([], out=io.StringIO(), check_fn=fn)
    assert seen["forward_url"] == FORWARD


def test_the_module_writes_no_real_address_or_identity():
    src = open(_PATH, encoding="utf-8").read()
    for needle in ("100.98.", "100.112.", "@gmail", "novahgreywolf"):
        assert needle not in src
