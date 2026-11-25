"""NODE oss-4: the Healthchecks compose cannot start by itself, cannot be reached off the machine, and names no
outside alert channel; the ping wrapper is off by default, refuses a hosted base, and never alters the job's exit code.

Nothing here starts Docker or opens a network connection: resolution and the HTTP opener are fakes.
"""
import importlib.util
import json
import os
import re
import socket

_ROOT = os.path.join(os.path.dirname(__file__), os.pardir, "node")
_spec = importlib.util.spec_from_file_location("ping_after_run", os.path.join(_ROOT, "ping_after_run.py"))
par = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(par)
COMPOSE = open(os.path.join(_ROOT, "healthchecks.compose.yml"), encoding="utf-8").read()
LIVE = "\n".join(l for l in COMPOSE.splitlines() if not l.lstrip().startswith("#"))


def test_service_is_profile_gated_and_pinned():
    assert 'profiles: ["monitor"]' in LIVE
    img = re.search(r"image:\s*(\S+)", LIVE).group(1)
    assert ":" in img and not img.endswith(":latest")


def test_ports_are_loopback_only():
    ports = re.findall(r'-\s*"([^"]*\d+:\d+)"', LIVE)
    assert ports and all(p.startswith("127.0.0.1:") for p in ports)


def test_no_hosted_url_and_site_root_is_loopback():
    assert not re.search(r"hc-ping\.com|healthchecks\.io", LIVE)
    root = re.search(r"SITE_ROOT:\s*(\S+)", LIVE).group(1)
    assert root.startswith("http://127.0.0.1")


def test_no_outside_alert_channel_is_configured():
    keys = set(re.findall(r"^\s+([A-Z][A-Z0-9_]+):", LIVE, re.M))
    banned = re.compile(r"EMAIL|SMTP|SLACK|TELEGRAM|PUSHOVER|DISCORD|TWILIO|SIGNAL|MATRIX|APPRISE|WEBHOOK|SENTRY|PD_|OPSGENIE|MSTEAMS|SMS|WHATSAPP|TRELLO|LINENOTIFY|GITHUB_|SHELL_ENABLED", re.I)
    assert not [k for k in keys if banned.search(k)]
    assert 'REGISTRATION_OPEN: "False"' in LIVE


def test_secret_is_required_not_written():
    assert "SECRET_KEY: ${HEALTHCHECKS_SECRET_KEY:?" in LIVE


# --- the wrapper ---------------------------------------------------------------------------------------------

def _res(*ips):
    return lambda host, port, type=0: [(2, 1, 6, "", (ip, port)) for ip in ips]


class Opener:
    def __init__(self, fail=False):
        self.reqs, self.fail = [], fail

    def __call__(self, req, timeout=0):
        self.reqs.append((req.full_url, req.data))
        if self.fail:
            raise OSError("down")
        return self

    def close(self):
        pass


def _checks(tmp_path):
    f = tmp_path / "checks.json"
    f.write_text(json.dumps({"nightly": "uuid-1"}))
    return str(f)


def test_off_by_default_runs_job_and_sends_nothing(capsys):
    op = Opener()
    rc = par.main(["--check", "nightly", "--", "x"], env={}, run=lambda c: 5, opener=op)
    assert rc == 5 and op.reqs == [] and "ping off" in capsys.readouterr().err


def test_success_pings_and_failure_pings_fail(tmp_path):
    env = {"HC_PING_BASE": "http://127.0.0.1:8000", "HC_CHECKS_FILE": _checks(tmp_path)}
    op = Opener()
    assert par.main(["--check", "nightly", "--", "x"], env=env, run=lambda c: 0, resolve=_res("127.0.0.1"), opener=op) == 0
    assert par.main(["--check", "nightly", "--", "x"], env=env, run=lambda c: 3, resolve=_res("127.0.0.1"), opener=op) == 3
    assert [r[0] for r in op.reqs] == ["http://127.0.0.1:8000/ping/uuid-1", "http://127.0.0.1:8000/ping/uuid-1/fail"]


def test_hosted_or_public_base_is_refused_and_job_still_exits_its_code(tmp_path):
    env = {"HC_PING_BASE": "http://hc-ping.com", "HC_CHECKS_FILE": _checks(tmp_path)}
    op = Opener()
    rc = par.main(["--check", "nightly", "--", "x"], env=env, run=lambda c: 0, resolve=_res("8.8.8.8"), opener=op)
    assert rc == 0 and op.reqs == []


def test_https_and_mixed_resolution_are_refused():
    assert not par.check_base("https://127.0.0.1", _res("127.0.0.1"))[0]
    assert not par.check_base("http://h", _res("10.0.0.5", "8.8.8.8"))[0]
    assert par.check_base("http://h", _res("100.64.1.2"))[0]


def test_unresolvable_base_is_refused():
    def boom(*a, **k):
        raise socket.gaierror
    assert not par.check_base("http://nowhere", boom)[0]


def test_ping_failure_never_changes_exit_code(tmp_path, capsys):
    env = {"HC_PING_BASE": "http://127.0.0.1:8000", "HC_CHECKS_FILE": _checks(tmp_path)}
    rc = par.main(["--check", "nightly", "--", "x"], env=env, run=lambda c: 0, resolve=_res("127.0.0.1"), opener=Opener(fail=True))
    assert rc == 0 and "ping failed" in capsys.readouterr().err


def test_unknown_check_name_skips_and_cannot_start_is_127(tmp_path):
    env = {"HC_PING_BASE": "http://127.0.0.1:8000", "HC_CHECKS_FILE": _checks(tmp_path)}
    op = Opener()
    assert par.main(["--check", "other", "--", "x"], env=env, run=lambda c: 0, resolve=_res("127.0.0.1"), opener=op) == 0
    assert op.reqs == []
    def nope(c):
        raise FileNotFoundError
    assert par.main(["--check", "nightly", "--", "x"], env=env, run=nope, resolve=_res("127.0.0.1"), opener=op) == 127
    assert op.reqs[-1][0].endswith("/fail")
