"""WATCH Q354: the nightly full-run job says PASS only on proof, and UNKNOWN when it cannot see.

Three layers: the classifier on sample pytest output, the slot-acquire loop against a fake lock helper
(a fake clock, so nothing sleeps), and the whole job against real local git repos (a bare `origin`, a hub
clone, a fake `scripts/heavy_lock.py`, a conftest that prints the same `base:` / `scope:` lines as the hub's).
Nothing here touches the network, the estate's lock directory or the real hub.
"""
import importlib.util
import os
import subprocess
import sys
import textwrap
import types

import pytest

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "watch", "nightly_full_run.py")
_spec = importlib.util.spec_from_file_location("nightly_full_run", _PATH)
nfr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nfr)

SHA = "abcdef0123456789abcdef0123456789abcdef01"


def out(passed=1490, skipped=8, xfailed=2, failed=0, errors=0, selected=1500, base="abcdef0", ids="", extra=""):
    bits = [f"{n} {w}" for n, w in ((failed, "failed"), (passed, "passed"), (skipped, "skipped"),
                                    (xfailed, "xfailed"), (errors, "error" if errors == 1 else "errors")) if n]
    return ("." * 20 + "\n" + extra
            + "=== this run is a statement about ===\n"
            + f"  base:  {base}\n  scope: {selected} tests selected\n"
            + ("=== short test summary info ===\n" + ids if ids else "")
            + ", ".join(bits) + " in 12.00s (0:00:12)\n")


def cls(rc, text, **kw):
    kw.setdefault("expected_sha", SHA)
    # By default the independent bare count agrees with the run's own scope line, so the older tests keep
    # testing what they tested; the bare-count rule has its own tests below.
    kw.setdefault("bare_collected", nfr.parse_pytest_output(text)["collected"])
    return nfr.classify(rc, text, **kw)


# ── the classifier ────────────────────────────────────────────────────────────────────────────

def test_positive_controls_hold():
    assert nfr.self_check() is None


def test_clean_run_is_pass():
    r = cls(0, out())
    assert r["status"] == "PASS", r
    assert (r["collected"], r["passed"], r["failed"], r["skipped"], r["errors"]) == (1500, 1490, 0, 8, 0)


def test_log_lines_printed_after_the_summary_do_not_hide_it():
    # Real hub output (seen 2026-10-11): app log lines arrive AFTER "5 passed in 20.26s" at interpreter exit,
    # some of them starting with a digit and one containing "in 3s".
    trail = ("2026-10-11 04:52:15,122 INFO [outcomes] schema ensured (pg=False)\n"
             "2026-10-11 04:52:15,793 WARNING [app] DDL skipped in 3s: (sqlite3.OperationalError) near EXISTS\n"
             "[SQL: ALTER TABLE t ADD COLUMN IF NOT EXISTS x TEXT]\n")
    r = cls(0, out() + trail)
    assert r["status"] == "PASS" and r["passed"] == 1490, r


def test_a_log_line_that_only_looks_like_a_summary_is_not_one():
    r = cls(0, "....\n2026-10-11 04:52:15 INFO 3 passed checks finished in 3s\n")
    assert r["status"] == "UNKNOWN" and "without a final summary" in r["reason"]


def test_failures_are_fail_with_ids():
    ids = ("FAILED tests/test_a.py::test_x[a b] - assert 1 == 2\n"
           "FAILED tests/test_a.py::test_x[a b] - again\n"
           "ERROR tests/test_c.py::test_z\n")
    r = cls(1, out(passed=1495, failed=1, errors=1, skipped=2, xfailed=1, ids=ids))
    assert r["status"] == "FAIL", r
    assert r["ids"] == ["FAILED tests/test_a.py::test_x[a b]", "ERROR tests/test_c.py::test_z"]


def test_captured_log_lines_are_not_mistaken_for_ids():
    noisy = "ERROR    root:app.py:10 something logged during a test\nFAILED to connect\n"
    r = cls(1, out(passed=1499, failed=1, skipped=0, xfailed=0, extra=noisy, ids="FAILED tests/t.py::t - x\n"))
    assert r["status"] == "FAIL"
    assert r["ids"] == ["FAILED tests/t.py::t"]


def test_collection_error_exit_2_is_fail():
    r = cls(2, "ERROR tests/test_broken.py\n" * 0 + "=== short test summary info ===\n"
                "ERROR tests/test_broken.py - ImportError: x\n1 error in 3.00s\n")
    assert r["status"] == "FAIL", r
    assert r["ids"] == ["ERROR tests/test_broken.py"]


def test_failure_with_no_base_line_is_still_fail_but_says_so():
    text = "=== short test summary info ===\nFAILED t.py::t - x\n1 failed, 3 passed in 1.00s\n"
    r = cls(1, text)
    assert r["status"] == "FAIL" and "base-line-missing" in r["notes"]


@pytest.mark.parametrize("rc,text,why", [
    (3221225477, "....\nWindows fatal exception: access violation\n", "without a final summary"),
    (0, "", "without a final summary"),
    (5, "no tests ran in 0.01s\n", "rc=5"),
    (0, out(base="9999999"), "not the commit"),
    (0, out().replace("  base:  abcdef0\n", ""), "base line is missing"),
    (0, out().replace("  scope: 1500 tests selected\n", ""), "scope"),
    (0, out(passed=1400), "add up"),
    (0, out(selected=3, passed=1, skipped=1, xfailed=1), "floor"),
    (0, out(passed=0, skipped=1500, xfailed=0), "nothing passed"),
    (0, out(failed=1), "failure(s) reported"),
    (1, out(), "no failures counted"),
])
def test_everything_else_is_unknown_never_pass(rc, text, why):
    r = cls(rc, text)
    assert r["status"] == "UNKNOWN", r
    assert why in r["reason"], r["reason"]


def test_timeout_and_no_exit_code_are_unknown():
    assert cls(None, out(), timed_out=True)["status"] == "UNKNOWN"
    assert cls(None, out())["status"] == "UNKNOWN"
    # even a clean-looking exit code and summary cannot rescue a run that was killed at the cap
    killed = cls(0, out(), timed_out=True)
    assert killed["status"] == "UNKNOWN" and "wall cap" in killed["reason"]


def test_base_with_uncommitted_files_after_run_is_noted_not_failed():
    r = cls(0, out().replace("abcdef0\n", "abcdef0 (+2 uncommitted)\n"))
    assert r["status"] == "PASS" and "tree-dirty-after-run=2" in r["notes"]


def test_a_sharp_drop_in_collected_is_noted():
    assert any("fell" in n for n in cls(0, out(), prev_collected=2000)["notes"])
    assert not cls(0, out(), prev_collected=1520)["notes"]


def test_previous_collected_reads_the_last_pass_or_fail_line():
    log = ("2026-10-12T13:00:00Z PASS main=a collected=6000 passed=1\n"
           "2026-10-13T13:00:00Z SKIPPED-BUSY main=b collected=- passed=-\n"
           "2026-10-14T13:00:00Z UNKNOWN main=c collected=7777\n")
    assert nfr.previous_collected(log) == 6000
    assert nfr.previous_collected("") is None and nfr.previous_collected(None) is None


# ── the bare collection count ─────────────────────────────────────────────────────────────────

def test_bare_count_that_matches_the_run_is_pass():
    assert cls(0, out(), bare_collected=1500)["status"] == "PASS"


def test_bare_count_that_differs_is_unknown_naming_both_numbers():
    r = cls(0, out(), bare_collected=1512)
    assert r["status"] == "UNKNOWN" and "1512" in r["reason"] and "1500" in r["reason"], r


def test_bare_count_unknown_is_unknown_never_pass():
    r = cls(0, out(), bare_collected=None, bare_why="the collection exited rc=2")
    assert r["status"] == "UNKNOWN" and r["reason"].startswith("bare collection count not established")
    assert "rc=2" in r["reason"]
    # the default, for a caller that forgets to pass it, is the safe one
    assert nfr.classify(0, out(), expected_sha=SHA)["status"] == "UNKNOWN"


def test_a_fail_stays_fail_but_notes_a_bare_count_it_could_not_match():
    text = out(passed=1495, failed=1, errors=1, skipped=2, xfailed=1, ids="FAILED a.py::t - m\n")
    differs = cls(1, text, bare_collected=1600)
    unknown = cls(1, text, bare_collected=None)
    same = cls(1, text, bare_collected=1500)
    assert differs["status"] == unknown["status"] == same["status"] == "FAIL"
    assert "bare-collected-1600-vs-run-1500" in differs["notes"]
    assert "bare-count-unknown" in unknown["notes"]
    assert not any("bare" in n for n in same["notes"])


@pytest.mark.parametrize("rc,text,count", [
    (0, "a.py::t1\na.py::t2\n\n15012 tests collected in 45.31s\n", 15012),
    (0, "15000/15012 tests collected (12 deselected) in 45.31s\n", 15000),
    (0, "1 test collected in 0.01s\n", 1),
    # the hub conftest's scope line wins over pytest's own summary
    (0, "=== this run is a statement about ===\n  base:  abcdef0\n  scope: 14990 tests selected\n"
        "15012 tests collected in 45.31s\n", 14990),
    (0, "  scope: 7 tests selected\n", 7),
])
def test_collect_parser_reads_the_count(rc, text, count):
    assert nfr.parse_collect_output(rc, text)["count"] == count


def test_collect_parser_notes_a_scope_that_disagrees_with_the_summary():
    got = nfr.parse_collect_output(0, "  scope: 14990 tests selected\n15012 tests collected in 45.31s\n")
    assert got["count"] == 14990 and got["notes"] == ["collect-summary-15012-vs-scope-14990"]


@pytest.mark.parametrize("rc,text,timed_out,why", [
    (2, "ERROR t.py\n!!! Interrupted: 1 error during collection !!!\n  scope: 3 tests selected\n"
        "3 tests collected, 1 error in 9.68s\n", False, "1 error"),
    (1, "3 tests collected, 2 errors in 7.17s\n", False, "2 error"),
    (5, "no tests collected in 0.01s\n", False, "rc=5"),
    (0, "something else entirely\n", False, "neither"),
    (None, "15012 tests collected in 45.31s\n", True, "killed at its cap"),
    (None, "", False, "exit code"),
])
def test_a_collection_with_errors_or_no_summary_is_not_a_count(rc, text, timed_out, why):
    got = nfr.parse_collect_output(rc, text, timed_out=timed_out)
    assert got["count"] is None and why in got["why"], got


# ── the time budget ───────────────────────────────────────────────────────────────────────────

def test_wait_window_leaves_the_run_its_allowance():
    assert nfr.wait_window(285, 1, 90) == 90                       # default night: the wait is not clipped
    assert nfr.wait_window(285, 1, 240, min_run_minutes=120) == 164
    assert nfr.wait_window(285, 200, 90, min_run_minutes=120) == 0  # never negative
    assert nfr.wait_window(285, 0, 0) == 0


def test_caps_are_clipped_to_what_is_left_and_never_above_it():
    assert nfr.clip_cap(270, 285, 1) == 270                         # granted at once: about 4.5 h
    assert nfr.clip_cap(270, 285, 92) == 285 - 92 - nfr.END_SLACK_MINUTES
    assert nfr.clip_cap(30, 285, 280) == 2
    assert nfr.clip_cap(270, 285, 300) == 0
    for elapsed in (0, 10, 91.5, 150, 281, 284.9):
        for cap in (30, 270, 1000):
            got = nfr.clip_cap(cap, 285, elapsed)
            assert 0 <= got <= cap and got <= max(0, 285 - elapsed - nfr.END_SLACK_MINUTES)


def test_the_defaults_fit_inside_the_task_limit():
    assert nfr.BUDGET_MINUTES <= 5 * 60 - 10
    assert nfr.WAIT_MINUTES + nfr.MIN_RUN_MINUTES <= nfr.BUDGET_MINUTES
    assert nfr.CAP_MINUTES <= nfr.BUDGET_MINUTES - nfr.END_SLACK_MINUTES
    assert nfr.MUTEX_STALE_HOURS * 60 > nfr.BUDGET_MINUTES


# ── progress, stall and the cap ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text,pct", [
    ("....................................................................... [ 93%]\n"
     "....................................................................... [ 94%]\n....", 94),
    ("..... [  5%]\n", 5),
    ("..... [100%]\n", 100),
    ("tests/test_x.py::test_y[ 5%] PASSED\n", None),      # a marker that is not at the end of a line
    ("....\n", None),
    ("", None),
])
def test_progress_marker(text, pct):
    assert nfr.last_progress(text) == pct


def test_cap_reason_keeps_the_old_prefix_and_adds_progress_and_pace():
    r = nfr.killed_reason(timed_out=True, stalled=False, cap_minutes=270, stall_minutes=30, pct=90,
                          elapsed_s=270 * 60, bare=15000)
    assert r.startswith("exceeded the 270 min wall cap; killed, no verdict")
    assert "; reached 90% (about 13500 of 15000 tests)" in r and "at this pace the run needs about 300 min" in r
    plain = nfr.killed_reason(timed_out=True, stalled=False, cap_minutes=180, stall_minutes=30, pct=None,
                              elapsed_s=10800, bare=None)
    assert plain == "exceeded the 180 min wall cap; killed, no verdict"


def test_stall_reason():
    r = nfr.killed_reason(timed_out=False, stalled=True, cap_minutes=270, stall_minutes=30, pct=47,
                          elapsed_s=3600, bare=15000)
    assert r == "no output for 30 min at 47%; killed as stalled, no verdict"
    assert cls(None, out(), stalled=True)["status"] == "UNKNOWN"


class FakeProc:
    """A child that finishes at `finish_at` (fake seconds), or never; kill() makes poll() answer -9."""

    def __init__(self, fc, finish_at=None, rc=0):
        self.fc, self.finish_at, self.rc, self.killed, self.pid = fc, finish_at, rc, False, 0

    def poll(self):
        if self.killed:
            return -9
        if self.finish_at is not None and self.fc.t >= self.finish_at:
            return self.rc
        return None

    def wait(self, timeout=None):
        return self.poll()

    def kill(self):
        self.killed = True


def fake_output(fc, grows_until, pct_per_minute=1.0, bytes_per_second=10):
    def size():
        return int(min(fc.t, grows_until) * bytes_per_second)

    def tail():
        pct = min(100, int(min(fc.t, grows_until) / 60.0 * pct_per_minute))
        return "." * 70 + f" [{pct:3d}%]\n...."
    return size, tail


def test_watch_child_kills_a_stalled_run_and_reports_where(monkeypatch):
    fc = FakeClock()
    proc = FakeProc(fc)
    size, tail = fake_output(fc, grows_until=47 * 60)            # 47 min of output, then nothing
    said, killed = [], []
    w = nfr.watch_child(proc, size=size, tail=tail, cap_s=270 * 60, stall_s=30 * 60, progress_every_s=600,
                        poll_s=30, say=said.append, clock=fc.clock, sleep=fc.sleep,
                        kill=lambda p: (killed.append(p), p.kill()))
    assert w["stalled"] and not w["timed_out"] and w["rc"] is None and killed == [proc]
    assert w["pct"] == 47
    assert 77 * 60 <= fc.t <= 78 * 60                             # 47 min + 30 min of silence, give or take a poll
    assert max(fc.sleeps) <= 30
    assert said and said[0].startswith("progress 10% after 10m00s (output")
    assert len(said) == 7                                         # one line every 10 min up to 70 min


def test_watch_child_kills_at_the_cap_and_never_sleeps_past_it():
    fc = FakeClock()
    proc = FakeProc(fc)
    size, tail = fake_output(fc, grows_until=10 ** 9, pct_per_minute=0.35)
    w = nfr.watch_child(proc, size=size, tail=tail, cap_s=270 * 60, stall_s=30 * 60, poll_s=30,
                        clock=fc.clock, sleep=fc.sleep, kill=lambda p: p.kill())
    assert w["timed_out"] and not w["stalled"] and w["rc"] is None
    assert fc.t == 270 * 60 and w["pct"] == 94
    res = nfr.classify(None, tail(), timed_out=True, cap_minutes=270, progress=w["pct"], elapsed_s=w["elapsed"],
                       bare_collected=15000, expected_sha=SHA)
    assert res["status"] == "UNKNOWN" and not res["finished"]
    assert "reached 94% (about 14100 of 15000 tests)" in res["reason"] and "needs about 287 min" in res["reason"]


def test_watch_child_returns_the_exit_code_of_a_run_that_finishes():
    fc = FakeClock()
    proc = FakeProc(fc, finish_at=100 * 60, rc=1)
    size, tail = fake_output(fc, grows_until=10 ** 9)
    w = nfr.watch_child(proc, size=size, tail=tail, cap_s=270 * 60, stall_s=30 * 60, poll_s=30,
                        clock=fc.clock, sleep=fc.sleep, kill=lambda p: pytest.fail("must not kill"))
    assert w["rc"] == 1 and not w["timed_out"] and not w["stalled"] and fc.t == 100 * 60


def test_a_quiet_but_growing_run_is_not_a_stall():
    fc = FakeClock()
    proc = FakeProc(fc, finish_at=200 * 60)
    # grows by one byte every 29 min: slow, but never 30 min without growth
    w = nfr.watch_child(proc, size=lambda: int(fc.t // (29 * 60)), tail=lambda: "", cap_s=270 * 60,
                        stall_s=30 * 60, poll_s=30, clock=fc.clock, sleep=fc.sleep,
                        kill=lambda p: pytest.fail("must not kill"))
    assert w["rc"] == 0 and w["pct"] is None


# ── the log line ──────────────────────────────────────────────────────────────────────────────

def test_format_pass_line_and_fail_ids():
    res = cls(0, out())
    line = nfr.format_result("PASS", sha=SHA, res=res, wall_s=2052, wait_s=0, py="3.12.10-venv", pytest_version="9.1.1",
                             when=nfr.dt.datetime(2026, 10, 12, 13, 7, 22, tzinfo=nfr.dt.timezone.utc), host="H")
    assert line == ("2026-10-12T13:07:22Z PASS main=abcdef012345 collected=1500 passed=1490 failed=0 skipped=8 errors=0 "
                    "xfail=2 xpass=0 wall=34m12s wait=0m00s py=3.12.10-venv pytest=9.1.1 host=H "
                    "bare=- collect=- progress=- budget=-\n")
    fail = cls(1, out(passed=1495, failed=1, errors=1, skipped=2, xfailed=1, ids="FAILED a.py::t - m\nERROR b.py::u\n"))
    text = nfr.format_result("FAIL", sha=SHA, res=fail, wall_s=60, wait_s=0, py=None, pytest_version=None, reason=fail["reason"])
    assert text.count("\n") == 3 and text.splitlines()[1] == "  FAILED a.py::t" and text.splitlines()[2] == "  ERROR b.py::u"


OLD_FIELDS = ["main", "collected", "passed", "failed", "skipped", "errors", "xfail", "xpass", "wall", "wait",
              "py", "pytest", "host"]


def test_new_fields_come_after_host_and_old_fields_keep_their_positions():
    killed = cls(None, out(), timed_out=True, cap_minutes=270, progress=94, elapsed_s=270 * 60, bare_collected=15000)
    line = nfr.format_result("UNKNOWN", sha=SHA, res=killed, wall_s=16200, wait_s=0, py="3.12.10-venv",
                             pytest_version="9.0.3", reason=killed["reason"], notes=["n1"], host="H", bare=15000,
                             collect_s=65, progress=94, budget_minutes=285,
                             when=nfr.dt.datetime(2026, 11, 8, 13, 30, tzinfo=nfr.dt.timezone.utc))
    toks = line.split(" ")
    assert toks[0] == "2026-11-08T13:30:00Z" and toks[1] == "UNKNOWN"
    assert [t.split("=", 1)[0] for t in toks[2:2 + len(OLD_FIELDS)]] == OLD_FIELDS
    assert toks[2 + len(OLD_FIELDS):2 + len(OLD_FIELDS) + 4] == ["bare=15000", "collect=1m05s", "progress=94%", "budget=285"]
    rest = " ".join(toks[2 + len(OLD_FIELDS) + 4:])
    assert rest.startswith('reason="exceeded the 270 min wall cap; killed, no verdict; reached 94%')
    assert line.rstrip("\n").endswith('note="n1"')
    # the old reader of collected= is not confused by the new collect= field
    assert nfr.previous_collected(line.replace("UNKNOWN", "PASS")) == 1500


def test_not_run_lines_carry_dashes_and_a_one_line_reason():
    text = nfr.format_result("SKIPPED-BUSY", sha=SHA, res=None, wall_s=None, wait_s=5400, py=None, pytest_version=None,
                             reason='slot-1: live,\nsuite "run" pid 7')
    assert text.count("\n") == 1
    assert "collected=- passed=- failed=- skipped=- errors=-" in text and "wall=-" in text and "wait=1h30m00s" in text
    assert "reason=\"slot-1: live, suite 'run' pid 7\"" in text


def test_long_id_lists_are_capped_in_the_log():
    res = {"collected": 5, "passed": 0, "failed": 150, "skipped": 0, "errors": 0, "ids": [f"FAILED t.py::t{i}" for i in range(150)]}
    text = nfr.format_result("FAIL", sha=SHA, res=res, wall_s=1, wait_s=0, py=None, pytest_version=None)
    assert len(text.splitlines()) == 1 + nfr.IDS_IN_LOG + 1 and "and 50 more" in text.splitlines()[-1]


# ── the pytest child's environment ────────────────────────────────────────────────────────────

def test_child_env_drops_secrets_and_steering_and_keeps_the_rest(monkeypatch):
    for k in ("MY_API_KEY", "GH_TOKEN", "DB_PASSWORD", "SENTRY_DSN", "PYTEST_ADDOPTS", "DATABASE_URL",
              "HUB_TEST_USE_AMBIENT_DB", "GITHUB_ACTIONS", "HEAVY_LOCK_TOKEN"):
        monkeypatch.setenv(k, "x")
    monkeypatch.setenv("PATH_KEEP_ME", "1")
    env = nfr.scrubbed_env({"HEAVY_LOCK_TOKEN": "mine"})
    for k in ("MY_API_KEY", "GH_TOKEN", "DB_PASSWORD", "SENTRY_DSN", "PYTEST_ADDOPTS", "DATABASE_URL",
              "HUB_TEST_USE_AMBIENT_DB", "GITHUB_ACTIONS"):
        assert k not in env, k
    assert env["HEAVY_LOCK_TOKEN"] == "mine" and env["PATH_KEEP_ME"] == "1"
    assert env["PYTHONFAULTHANDLER"] == "1" and "PYTHONUTF8" not in env


# ── the refusal text of the real helper ───────────────────────────────────────────────────────

@pytest.mark.parametrize("text,kind", [
    ("heavy lock: REFUSED: hub CI is BUSY (novah-runner-novahub-2 is running a job). No local full suite while a hub runner is busy (owner q205).", "busy"),
    ("heavy lock: REFUSED: every heavy slot is taken -- slot-1: live, suite-run-speed pid 62772 on GREYWOLF since 2026-10-11T11:10:08Z tree F:\\x desk SUITE. An 'unknown' holder is not reclaimed automatically; look at it.", "busy"),
    ("heavy lock: REFUSED: every heavy slot is taken -- slot-1: unknown, holder unreadable. An 'unknown' holder ...", "unknown"),
    ("heavy lock: REFUSED: hub CI is UNKNOWN (docker ps failed: CalledProcessError). No local full suite ...", "unknown"),
    ("heavy lock: REFUSED: hub CI is UNKNOWN (no hub runner container is running).", "unknown"),
    ("", "unknown"),
    ("something nobody has seen before", "unknown"),
])
def test_refusal_kinds(text, kind):
    assert nfr.lock_refusal_kind(text) == kind


# ── the slot loop, against a fake helper and a fake clock ────────────────────────────────────

FAKE_HELPER = textwrap.dedent('''\
    import os, sys

    def acquire():  # the orchestrator only checks that the file looks like the real helper
        pass

    mode = os.environ.get("FAKE_LOCK_MODE", "grant")
    d = os.environ.get("FAKE_LOCK_DIR", ".")
    cmd = sys.argv[1]
    if cmd == "status":
        print("slot-1: free")
    elif cmd == "release":
        with open(os.path.join(d, "RELEASED"), "w") as fh:
            fh.write(sys.argv[sys.argv.index("--token") + 1])
        print("heavy lock: released")
    elif cmd == "acquire":
        tf = sys.argv[sys.argv.index("--token-file") + 1]
        n_file = os.path.join(d, "calls")
        n = int(open(n_file).read()) + 1 if os.path.exists(n_file) else 1
        open(n_file, "w").write(str(n))
        if mode == "busy-then-grant" and n > 2:
            mode = "grant"
        if mode == "grant":
            open(tf, "w").write("tok123")
            print("heavy lock: granted slot-1 to nightly-full-run")
        elif mode in ("busy", "busy-then-grant"):
            open(tf, "w").write("")
            print("heavy lock: REFUSED: every heavy slot is taken -- slot-1: live, other-job pid 1 on H since T tree X desk D.")
            sys.exit(3)
        elif mode == "ci-unknown":
            open(tf, "w").write("")
            print("heavy lock: REFUSED: hub CI is UNKNOWN (docker ps failed: CalledProcessError).")
            sys.exit(3)
        elif mode == "exempt":
            open(tf, "w").write("")
            print("heavy lock: not taken -- no lock root at X (not the estate box)")
        elif mode == "crash":
            print("boom")
            sys.exit(2)
        elif mode == "grant-then-hang":     # killed by the timeout AFTER the token is on disk
            open(tf, "w").write("tok123")
            print("heavy lock: granted slot-1 to nightly-full-run", flush=True)
            import time; time.sleep(120)
        elif mode == "hang-then-grant":     # the first attempt hangs (docker under load), the next one grants
            if n == 1:
                import time; time.sleep(120)
            open(tf, "w").write("tok123")
            print("heavy lock: granted slot-1 to nightly-full-run")
''')


class FakeClock:
    def __init__(self):
        self.t = 0.0
        self.sleeps = []

    def clock(self):
        return self.t

    def sleep(self, s):
        self.sleeps.append(s)
        self.t += s


def slot_ctx(tmp_path, monkeypatch, mode):
    state = tmp_path / "state"
    state.mkdir()
    helper = state / "heavy_lock.py"
    helper.write_text(FAKE_HELPER, encoding="utf-8")
    monkeypatch.setenv("FAKE_LOCK_MODE", mode)
    monkeypatch.setenv("FAKE_LOCK_DIR", str(state))
    ctx = nfr.Ctx(nfr.parse_args(["--state", str(state), "--log", str(tmp_path / "log"), "--hub", str(tmp_path / "hub")]))
    ctx.helper = str(helper)
    return ctx


def test_slot_granted_first_try(tmp_path, monkeypatch):
    ctx = slot_ctx(tmp_path, monkeypatch, "grant")
    fc = FakeClock()
    assert nfr.acquire_slot(ctx, wait_minutes=90, poll_seconds=120, sleep=fc.sleep, clock=fc.clock) == "tok123"
    assert fc.sleeps == []


def test_slot_busy_then_granted_after_polling(tmp_path, monkeypatch):
    ctx = slot_ctx(tmp_path, monkeypatch, "busy-then-grant")
    fc = FakeClock()
    assert nfr.acquire_slot(ctx, wait_minutes=90, poll_seconds=120, sleep=fc.sleep, clock=fc.clock) == "tok123"
    assert fc.sleeps == [120, 120]


def test_slot_busy_for_the_whole_wait_is_skipped_busy_and_runs_nothing(tmp_path, monkeypatch):
    ctx = slot_ctx(tmp_path, monkeypatch, "busy")
    fc = FakeClock()
    with pytest.raises(nfr.Stop) as ei:
        nfr.acquire_slot(ctx, wait_minutes=10, poll_seconds=120, sleep=fc.sleep, clock=fc.clock)
    assert ei.value.status == "SKIPPED-BUSY" and "slot-1: live" in ei.value.reason
    assert 4 <= len(fc.sleeps) <= 5 and sum(fc.sleeps) <= 600


def test_zero_wait_tries_once(tmp_path, monkeypatch):
    ctx = slot_ctx(tmp_path, monkeypatch, "busy")
    fc = FakeClock()
    with pytest.raises(nfr.Stop) as ei:
        nfr.acquire_slot(ctx, wait_minutes=0, poll_seconds=120, sleep=fc.sleep, clock=fc.clock)
    assert ei.value.status == "SKIPPED-BUSY" and fc.sleeps == []


@pytest.mark.parametrize("mode,why", [("ci-unknown", "could not be established"), ("exempt", "took no slot"),
                                      ("crash", "failed rc=2")])
def test_slot_that_cannot_be_established_is_unknown_not_busy_and_not_granted(tmp_path, monkeypatch, mode, why):
    ctx = slot_ctx(tmp_path, monkeypatch, mode)
    fc = FakeClock()
    with pytest.raises(nfr.Stop) as ei:
        nfr.acquire_slot(ctx, wait_minutes=5, poll_seconds=120, sleep=fc.sleep, clock=fc.clock)
    assert ei.value.status == "UNKNOWN" and why in ei.value.reason


def test_an_acquire_that_times_out_after_writing_its_token_uses_the_token(tmp_path, monkeypatch):
    # a real timeout, a real kill: the fake helper writes the token and then hangs
    monkeypatch.setattr(nfr, "ACQUIRE_TIMEOUT_SECONDS", 5)
    ctx = slot_ctx(tmp_path, monkeypatch, "grant-then-hang")
    fc = FakeClock()
    assert nfr.acquire_slot(ctx, wait_minutes=90, poll_seconds=120, sleep=fc.sleep, clock=fc.clock) == "tok123"
    assert fc.sleeps == [] and "acquire-helper-timed-out-after-grant" in ctx.notes


def test_an_acquire_that_times_out_without_a_token_is_retried_not_the_end(tmp_path, monkeypatch):
    monkeypatch.setattr(nfr, "ACQUIRE_TIMEOUT_SECONDS", 5)
    ctx = slot_ctx(tmp_path, monkeypatch, "hang-then-grant")
    fc = FakeClock()
    assert nfr.acquire_slot(ctx, wait_minutes=90, poll_seconds=120, sleep=fc.sleep, clock=fc.clock) == "tok123"
    assert fc.sleeps == [120]


def test_run_helper_reports_a_timeout_as_rc_99_timeoutexpired(tmp_path, monkeypatch):
    ctx = slot_ctx(tmp_path, monkeypatch, "hang-then-grant")
    rc, text = nfr.run_helper(ctx, "acquire", "--job", "j", "--pid", "1", "--token-file",
                              str(tmp_path / "tf"), timeout=3)
    assert rc == 99 and "TimeoutExpired" in text


def test_acquire_timing_out_every_time_ends_unknown_inside_the_wait_window(tmp_path, monkeypatch):
    ctx = slot_ctx(tmp_path, monkeypatch, "grant")
    seen = []

    def fake_helper(_ctx, *args, timeout=180):
        seen.append(timeout)
        return 99, "helper could not run: TimeoutExpired"
    monkeypatch.setattr(nfr, "run_helper", fake_helper)
    fc = FakeClock()
    with pytest.raises(nfr.Stop) as ei:
        nfr.acquire_slot(ctx, wait_minutes=10, poll_seconds=120, sleep=fc.sleep, clock=fc.clock)
    assert ei.value.status == "UNKNOWN" and "timed out" in ei.value.reason
    assert len(seen) >= 2 and set(seen) == {nfr.ACQUIRE_TIMEOUT_SECONDS} and sum(fc.sleeps) <= 600


def test_a_helper_that_cannot_start_at_all_still_ends_the_night_at_once(tmp_path, monkeypatch):
    ctx = slot_ctx(tmp_path, monkeypatch, "grant")
    monkeypatch.setattr(nfr, "run_helper", lambda _c, *a, timeout=180: (99, "helper could not run: FileNotFoundError"))
    fc = FakeClock()
    with pytest.raises(nfr.Stop) as ei:
        nfr.acquire_slot(ctx, wait_minutes=10, poll_seconds=120, sleep=fc.sleep, clock=fc.clock)
    assert ei.value.status == "UNKNOWN" and "rc=99" in ei.value.reason and fc.sleeps == []


# ── the whole job against real local git repos ────────────────────────────────────────────────

HUB_CONFTEST = textwrap.dedent('''\
    import os, subprocess
    _HERE = os.path.dirname(os.path.abspath(__file__))
    _SEL = None

    def pytest_collection_modifyitems(session, config, items):
        global _SEL
        _SEL = len(items)

    def pytest_terminal_summary(terminalreporter):
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=_HERE, capture_output=True, text=True).stdout.strip()
        terminalreporter.section("this run is a statement about")
        terminalreporter.write_line(f"  base:  {sha}")
        terminalreporter.write_line(f"  scope: {_SEL} tests selected")
''')

TESTS_OK = textwrap.dedent('''\
    import os

    def test_one(): assert True
    def test_two(): assert True
    def test_three(): assert True

    def test_secret_names_never_reach_the_child():
        assert os.environ.get("FAKE_API_KEY") is None

    def test_child_holds_the_slot_token():
        assert os.environ.get("HEAVY_LOCK_TOKEN") == "tok123"
''')

TESTS_FAIL = TESTS_OK + "\ndef test_broken(): assert 1 == 2\n"

GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.invalid", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0"}


def g(cwd, *args):
    env = dict(os.environ, **GIT_ENV)
    p = subprocess.run(["git", *args], cwd=str(cwd), env=env, capture_output=True, text=True)
    assert p.returncode == 0, (args, p.stderr)
    return p.stdout.strip()


def commit_hub(hub, tests_text):
    (hub / "tests").mkdir(exist_ok=True)
    (hub / "tests" / "test_suite.py").write_text(tests_text, encoding="utf-8")
    g(hub, "add", "-A")
    g(hub, "commit", "-q", "-m", "tests")
    g(hub, "push", "-q", "origin", "main")
    return g(hub, "rev-parse", "HEAD")


@pytest.fixture
def job(tmp_path, monkeypatch):
    for k, v in GIT_ENV.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("FAKE_LOCK_DIR", str(tmp_path))
    monkeypatch.setenv("FAKE_LOCK_MODE", "grant")
    monkeypatch.setenv("FAKE_API_KEY", "must-not-leak")
    origin = tmp_path / "origin.git"
    hub = tmp_path / "hub"
    g(tmp_path, "init", "-q", "--bare", str(origin))
    g(tmp_path, "init", "-q", "-b", "main", str(hub))
    g(hub, "remote", "add", "origin", str(origin))
    (hub / "scripts").mkdir()
    (hub / "scripts" / "heavy_lock.py").write_text(FAKE_HELPER, encoding="utf-8")
    (hub / "conftest.py").write_text(HUB_CONFTEST, encoding="utf-8")
    (hub / ".gitignore").write_text(".claude/\n__pycache__/\n", encoding="utf-8")
    sha = commit_hub(hub, TESTS_OK)

    def args(*extra):
        return nfr.parse_args(["--hub", str(hub), "--log", str(tmp_path / "logs" / "nightly.log"),
                               "--state", str(tmp_path / "state"), "--python", sys.executable,
                               "--min-collected", "1", "--wait-minutes", "0", *extra])

    return types.SimpleNamespace(tmp=tmp_path, hub=hub, sha=sha, args=args, log=tmp_path / "logs" / "nightly.log",
                                 wt=hub / ".claude" / "worktrees" / "nightly-full-run", state=tmp_path / "state")


def lines(job):
    return job.log.read_text(encoding="utf-8").splitlines()


def test_full_pass_night(job):
    assert nfr.run(job.args()) == 0
    first = lines(job)[0]
    assert len(lines(job)) == 1 and " PASS " in first, lines(job)
    assert f"main={job.sha[:12]}" in first and "collected=5 passed=5 failed=0 skipped=0 errors=0" in first
    assert "must-not-leak" not in job.log.read_text(encoding="utf-8")
    # the dedicated worktree is a clean detached checkout of exactly that commit
    assert g(job.wt, "rev-parse", "HEAD") == job.sha
    assert subprocess.run(["git", "symbolic-ref", "-q", "HEAD"], cwd=str(job.wt), capture_output=True).returncode != 0
    assert g(job.wt, "status", "--porcelain") == ""
    # the slot was released with the token it was given, and the mutex is gone
    assert (job.tmp / "RELEASED").read_text(encoding="utf-8") == "tok123"
    assert not (job.state / "nightly.lock").exists()
    # raw output is kept locally, not in the log
    assert list((job.state / "runs").glob("*/pytest.out"))
    # the independent bare count agreed, and the new fields sit after host=
    assert list((job.state / "runs").glob("*/collect.out"))
    tail = first.split(" host=", 1)[1].split(" ")
    assert tail[1] == "bare=5" and tail[2].startswith("collect=") and tail[2] != "collect=-"
    assert tail[3:5] == ["progress=-", "budget=285"]


def test_second_night_updates_the_same_worktree_to_the_new_main(job):
    assert nfr.run(job.args()) == 0
    new_sha = commit_hub(job.hub, TESTS_OK + "\ndef test_four(): assert True\n")
    assert nfr.run(job.args()) == 0
    assert g(job.wt, "rev-parse", "HEAD") == new_sha
    assert "collected=6 passed=6" in lines(job)[1] and f"main={new_sha[:12]}" in lines(job)[1]


def test_failing_main_is_fail_with_the_id_and_nonzero_exit(job):
    commit_hub(job.hub, TESTS_FAIL)
    assert nfr.run(job.args()) == 1
    ls = lines(job)
    assert " FAIL " in ls[0] and "failed=1" in ls[0] and "passed=5" in ls[0]
    assert ls[1].strip() == "FAILED tests/test_suite.py::test_broken"
    assert (job.tmp / "RELEASED").exists()


def test_busy_slot_is_skipped_busy_and_nothing_ran(job, monkeypatch):
    monkeypatch.setenv("FAKE_LOCK_MODE", "busy")
    assert nfr.run(job.args()) == 3
    assert " SKIPPED-BUSY " in lines(job)[0] and "collected=-" in lines(job)[0] and "wall=-" in lines(job)[0]
    assert not job.wt.exists() and not (job.state / "runs").exists()
    assert not (job.tmp / "RELEASED").exists()


def test_exempt_lock_helper_means_no_run(job, monkeypatch):
    monkeypatch.setenv("FAKE_LOCK_MODE", "exempt")
    assert nfr.run(job.args()) == 2
    assert " UNKNOWN " in lines(job)[0] and not job.wt.exists()


def test_dry_run_stops_before_pytest_takes_no_slot_and_writes_no_line(job):
    assert nfr.run(job.args("--dry-run")) == 0
    assert not job.log.exists()
    assert g(job.wt, "rev-parse", "HEAD") == job.sha and g(job.wt, "status", "--porcelain") == ""
    assert not (job.state / "runs").exists() and not (job.tmp / "calls").exists()
    assert not (job.state / "nightly.lock").exists()


def test_a_folder_that_is_not_the_worktree_is_never_touched(job):
    job.wt.mkdir(parents=True)
    (job.wt / "precious.txt").write_text("keep", encoding="utf-8")
    assert nfr.run(job.args()) == 2
    assert (job.wt / "precious.txt").read_text(encoding="utf-8") == "keep"
    assert " UNKNOWN " in lines(job)[0] and "not touching it" in lines(job)[0]
    assert not (job.state / "runs").exists()


def test_local_edits_in_the_dedicated_worktree_are_discarded_not_tested(job):
    assert nfr.run(job.args()) == 0
    (job.wt / "tests" / "test_suite.py").write_text("def test_x(): assert False\n", encoding="utf-8")
    (job.wt / "stray.py").write_text("x = 1\n", encoding="utf-8")
    assert nfr.run(job.args()) == 0
    assert not (job.wt / "stray.py").exists() and " PASS " in lines(job)[1]


def test_a_live_run_in_progress_blocks_a_second_one(job):
    job.state.mkdir()
    (job.state / "nightly.lock").write_text('{"pid": %d, "time": %s}' % (os.getpid(), nfr.time.time()), encoding="utf-8")
    assert nfr.run(job.args()) == 2
    assert "in progress" in lines(job)[0]
    assert (job.state / "nightly.lock").exists()          # not removed by the run that did nothing
    assert not job.wt.exists()


def test_a_dead_runs_mutex_is_stale_and_replaced(job):
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    job.state.mkdir()
    (job.state / "nightly.lock").write_text('{"pid": %d, "time": %s}' % (dead.pid, nfr.time.time()), encoding="utf-8")
    assert nfr.run(job.args()) == 0
    assert (job.state / "nightly.lock.stale").exists() and not (job.state / "nightly.lock").exists()


def test_an_unreachable_remote_is_unknown_not_a_pass_on_a_stale_main(job):
    g(job.hub, "remote", "set-url", "origin", str(job.tmp / "no-such-origin.git"))
    assert nfr.run(job.args()) == 2
    assert " UNKNOWN " in lines(job)[0] and "git fetch failed" in lines(job)[0]
    assert not job.wt.exists()


def test_an_interpreter_without_pytest_is_unknown_before_any_slot_is_taken(job):
    assert nfr.run(job.args("--python", str(job.tmp / "no-python"))) == 2
    assert " UNKNOWN " in lines(job)[0] and not (job.tmp / "calls").exists()


def test_a_run_that_dies_mid_suite_is_unknown_and_releases_the_slot(job):
    commit_hub(job.hub, TESTS_OK + "\ndef test_dies():\n    import os\n    os._exit(7)\n")
    assert nfr.run(job.args()) == 2
    assert " UNKNOWN " in lines(job)[0] and "without a final summary" in lines(job)[0]
    assert (job.tmp / "RELEASED").exists()


def test_a_run_over_the_wall_cap_is_killed_and_unknown(job):
    commit_hub(job.hub, TESTS_OK + "\ndef test_hangs():\n    import time\n    time.sleep(120)\n")
    assert nfr.run(job.args("--cap-minutes", "0.1")) == 2
    assert " UNKNOWN " in lines(job)[0] and "exceeded the 0.1 min wall cap" in lines(job)[0]
    assert (job.tmp / "RELEASED").exists()


def test_a_collection_that_cannot_count_still_runs_the_suite_but_cannot_pass(job):
    assert nfr.run(job.args("--collect-cap-minutes", "0")) == 2
    first = lines(job)[0]
    assert " UNKNOWN " in first and "bare collection count not established" in first and "bare=-" in first
    assert "collected=5 passed=5 failed=0" in first          # pytest still ran, under the slot
    assert (job.tmp / "RELEASED").exists()


def test_a_failing_main_with_no_bare_count_is_still_fail_with_a_note(job):
    commit_hub(job.hub, TESTS_FAIL)
    assert nfr.run(job.args("--collect-cap-minutes", "0")) == 1
    assert " FAIL " in lines(job)[0] and "bare-count-unknown" in lines(job)[0]


def test_a_budget_used_up_before_pytest_is_unknown_and_runs_nothing(job):
    assert nfr.run(job.args("--budget-minutes", "1")) == 2
    first = lines(job)[0]
    assert " UNKNOWN " in first and "budget was used up before pytest could start" in first and "budget=1" in first
    assert not list((job.state / "runs").glob("*/pytest.out"))
    assert (job.tmp / "RELEASED").exists()
