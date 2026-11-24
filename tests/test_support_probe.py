"""SUPPORT K07: the probe says OK only when it saw the message land, and the compose file cannot expose or start anything.

Nothing here opens a socket, starts Docker, or sends mail: the inbox is a fake, the clock is a list, the fetch is a lambda.
"""
import importlib.util
import os
import re

import pytest

_ROOT = os.path.join(os.path.dirname(__file__), os.pardir, "support")
_spec = importlib.util.spec_from_file_location("support_probe", os.path.join(_ROOT, "probe.py"))
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)
COMPOSE = open(os.path.join(_ROOT, "chatwoot.compose.yml"), encoding="utf-8").read()


class FakeInbox:
    def __init__(self, deliver=True):
        self.deliver, self.sent, self.got = deliver, [], set()

    def send(self, address, token):
        self.sent.append((address, token))
        if self.deliver:
            self.got.add(token)

    def find(self, token):
        return token in self.got


class Clock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s


def _run(inbox, **kw):
    c = Clock()
    return pr.self_test(inbox.send, inbox.find, "help@example.test", clock=c.now, sleep=c.sleep, **kw)


def test_landed_message_is_ok():
    inbox = FakeInbox(deliver=True)
    r = _run(inbox)
    assert r.state == pr.OK and inbox.sent[0][0] == "help@example.test"


def test_message_that_never_lands_is_fail():
    assert _run(FakeInbox(deliver=False), wait_s=20, poll_s=5).state == pr.FAIL


def test_no_sender_is_unknown_never_ok():
    assert pr.self_test(None, lambda t: True, "x@example.test").state == pr.UNKNOWN


def test_send_that_raises_is_unknown_not_fail():
    def boom(a, t):
        raise OSError("down")
    assert pr.self_test(boom, lambda t: True, "x@example.test").state == pr.UNKNOWN


def test_unreadable_inbox_is_unknown_not_fail():
    def bad_find(t):
        raise RuntimeError("api 500")
    assert pr.self_test(lambda a, t: None, bad_find, "x@example.test").state == pr.UNKNOWN


def test_a_finder_that_always_says_yes_is_the_control_for_ok():
    # the OK path is only meaningful because the FAIL path exists: same code, finder that never sees it
    assert _run(FakeInbox(deliver=False), wait_s=5, poll_s=5).state != pr.OK


@pytest.mark.parametrize("host,ok", [
    ("127.0.0.1", True), ("localhost", True), ("::1", True), ("100.101.102.103", True), ("box.tail1234.ts.net", True),
    ("8.8.8.8", False), ("example.com", False), ("192.168.1.5", False), ("100.128.0.1", False), ("", False),
])
def test_only_loopback_and_tailnet_hosts_are_allowed(host, ok):
    assert pr.host_allowed(host) is ok


def test_other_hosts_are_refused_before_any_fetch():
    called = []
    r = pr.check_surface("https://example.com/api", fetch=lambda u, t: called.append(u) or 200)
    assert r.state == pr.UNKNOWN and not called


def test_surface_states():
    assert pr.check_surface("http://127.0.0.1:3000/api", fetch=lambda u, t: 200).state == pr.OK
    assert pr.check_surface("http://127.0.0.1:3000/api", fetch=lambda u, t: 502).state == pr.FAIL
    assert pr.check_surface("http://127.0.0.1:3000/api", fetch=lambda u, t: 302).state == pr.UNKNOWN

    def timeout(u, t):
        raise TimeoutError()
    assert pr.check_surface("http://127.0.0.1:3000/api", fetch=timeout).state == pr.UNKNOWN


def test_zero_tickets_only_reads_as_quiet_when_the_probe_is_ok():
    assert "nobody has written" in pr.inbox_state(pr.Result(pr.OK, ""), 0)
    for state in (pr.FAIL, pr.UNKNOWN):
        s = pr.inbox_state(pr.Result(state, "x"), 0)
        assert s.startswith("unknown") and "nobody" not in s and "no tickets" not in s


def test_cli_without_a_sender_exits_unknown(capsys):
    assert pr.main(["--self-test"]) == 2
    assert "UNKNOWN" in capsys.readouterr().out


# --- the compose file -------------------------------------------------------------------------------------

def test_compose_publishes_only_on_loopback():
    ports = re.findall(r'^\s*-\s*"([^"]*:\d+:\d+)"', COMPOSE, re.M)
    assert ports, "no published port found; the check would pass on an empty list"
    for p in ports:
        assert p.startswith("127.0.0.1:"), p


def test_compose_is_off_by_default_every_service_has_the_profile():
    services = re.findall(r"^  ([a-z]+):\n    image:", COMPOSE, re.M)
    assert set(services) == {"rails", "sidekiq", "postgres", "redis"}
    assert COMPOSE.count('profiles: ["support"]') == len(services)


def test_compose_pins_images_and_holds_no_secret():
    for img in re.findall(r"image:\s*(\S+)", COMPOSE):
        assert ":" in img and not img.endswith(":latest"), img
    for line in COMPOSE.splitlines():
        if re.search(r"(PASSWORD|SECRET_KEY_BASE)\s*:", line):
            assert "${" in line and ":?" in line, f"secret not a required variable: {line.strip()}"
