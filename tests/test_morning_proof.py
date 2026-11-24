"""WATCH p16-2: the morning proof read says OK only when it can see the thing it reports on.

The subject of these tests is the false OK. Every watcher has the same four ways to fake a pass, and each
is tested for every source that has it: the source is absent, the source cannot be read, the source is
old (a stale OK is not OK), and the source is a copy taken before the run it should hold. A fixture is a
throwaway dict of files and canned `gh` answers; nothing here reads the real estate, runs `gh`, opens a
socket or writes outside tmp_path.
"""
import datetime as dt
import importlib.util
import json
import os
import socket
import ssl

import pytest

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "watch", "morning_proof.py")
_spec = importlib.util.spec_from_file_location("morning_proof", _PATH)
mp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mp)

UTC = dt.timezone.utc
# 2026-11-23 04:50 PST. Pacific is UTC-8 in November, so 12:50Z.
NOW = dt.datetime(2026, 11, 23, 12, 50, 0, tzinfo=UTC)
H = dt.timedelta(hours=1)
M = dt.timedelta(minutes=1)


def utc(s):
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def z(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def compact(t):
    return t.strftime("%Y%m%dT%H%M%SZ")


class FakeIO:
    """Files by exact path, canned gh answers by leading args, canned TLS answers by host."""

    def __init__(self):
        self.files = {}          # path -> (text, mtime)
        self.dirs = {}           # path -> [names]
        self.gh_answers = {}     # tuple(args prefix) -> (rc, out)
        self.gh_calls = []
        self.tls_answers = None  # None = live TLS off
        self.vault = None
        self.tls_calls = []

    def read(self, path):
        if path in self.files:
            text, mtime = self.files[path]
            if isinstance(text, Exception):
                return mp.Read(None, None, "unreadable: " + text.__class__.__name__)
            return mp.Read(text, mtime, None)
        return mp.Read(None, None, "missing")

    def listdir(self, path):
        return self.dirs.get(path)

    def gh(self, args):
        self.gh_calls.append(tuple(args))
        for k, v in self.gh_answers.items():
            if tuple(args[:len(k)]) == k:
                return v
        return 1, "no canned answer for %r" % (args,)

    def tls(self, host):
        self.tls_calls.append(host)
        v = self.tls_answers[host]
        if isinstance(v, Exception):
            raise v
        return v

    def live_tls(self):
        return self.tls_answers is not None

    def vault_private(self, now):
        if isinstance(self.vault, Exception):
            raise self.vault
        return self.vault


def make_ctx(now=NOW, io=None):
    io = io or FakeIO()
    return mp.Ctx(now=now, io=io, paths=mp.make_paths(inputs_dir=os.path.join("X", "inputs"), hub_dir="HUB"))


def put(ctx, key, text, mtime=None):
    ctx.io.files[ctx.paths[key]] = (text, mtime or ctx.now - 10 * M)


# ---------------------------------------------------------------- time and the slot rule

def test_pacific_conversion_follows_daylight_time():
    assert mp.pt_to_utc(dt.datetime(2026, 11, 23, 2, 15)) == utc("2026-11-23T10:15:00Z")   # PST
    assert mp.pt_to_utc(dt.datetime(2026, 7, 23, 2, 15)) == utc("2026-07-23T09:15:00Z")    # PDT
    assert mp.fmt_pt(utc("2026-11-23T12:50:00Z")) == "Nov 23, 4:50 AM PST"


def test_latest_slot_start_is_never_in_the_future():
    assert mp.latest_slot_start(NOW, (2, 15)) == utc("2026-11-23T10:15:00Z")
    assert mp.latest_slot_start(NOW, (4, 10)) == utc("2026-11-23T12:10:00Z")
    assert mp.latest_slot_start(NOW, (4, 55)) == utc("2026-11-22T12:55:00Z")  # not yet today


def R(ts, state, detail="d"):
    return mp.Result(ts, state, detail)


SLOT = (2, 15)
TODAY_SLOT = utc("2026-11-23T10:15:00Z")


@pytest.mark.parametrize("state,want", [("ok", "OK"), ("fail", "FAIL"), ("unknown", "UNKNOWN")])
def test_a_result_in_the_slot_decides(state, want):
    status, ev, at = mp.judge_scheduled([R(TODAY_SLOT + 3 * M, state)], NOW, SLOT, 90, observed_at=NOW)
    assert status == want and at == TODAY_SLOT + 3 * M


def test_no_lines_at_all_is_unknown():
    assert mp.judge_scheduled([], NOW, SLOT, 90, observed_at=NOW)[0] == "UNKNOWN"


def test_a_stale_ok_is_not_ok():
    old = [R(TODAY_SLOT - 72 * H, "ok")]
    status, ev, _ = mp.judge_scheduled(old, NOW, SLOT, 90, observed_at=NOW)
    assert status == "UNKNOWN" and "no run result" in ev


def test_yesterdays_ok_does_not_cover_a_slot_that_has_closed():
    yesterday = [R(TODAY_SLOT - 24 * H, "ok")]
    assert mp.judge_scheduled(yesterday, NOW, SLOT, 90, observed_at=NOW)[0] == "UNKNOWN"


def test_while_todays_window_is_open_yesterdays_result_stands_with_a_note():
    slot = (4, 30)   # 04:30 PST; at 04:50 the window (330 min) is open
    prev = utc("2026-11-22T12:30:00Z") + 90 * M
    status, ev, _ = mp.judge_scheduled([R(prev, "ok")], NOW, slot, 330, observed_at=NOW)
    assert status == "OK" and "not logged yet" in ev
    later = NOW + 8 * H   # same data once the window has closed
    assert mp.judge_scheduled([R(prev, "ok")], later, slot, 330, observed_at=later)[0] == "UNKNOWN"


def test_a_manual_ok_does_not_rescue_a_failed_scheduled_run():
    rows = [R(TODAY_SLOT + 2 * M, "fail", "boom"), R(TODAY_SLOT + 3 * H, "ok", "manual")]
    status, ev, _ = mp.judge_scheduled(rows, NOW + 4 * H, SLOT, 90, observed_at=NOW + 4 * H)
    assert status == "FAIL" and "later off-schedule" in ev


def test_a_manual_ok_alone_does_not_prove_the_timer():
    rows = [R(TODAY_SLOT + 5 * H, "ok", "manual")]
    assert mp.judge_scheduled(rows, NOW + 6 * H, SLOT, 90, observed_at=NOW + 6 * H)[0] == "UNKNOWN"


def test_a_copy_taken_before_the_window_closed_cannot_vouch_for_it():
    took = TODAY_SLOT - 30 * M     # the mirror predates the run, so a missing line proves nothing
    status, ev, _ = mp.judge_scheduled([R(TODAY_SLOT - 24 * H, "ok")], NOW, SLOT, 90, observed_at=took)
    assert status == "UNKNOWN" and "before that window closed" in ev


def test_future_dated_lines_are_ignored_and_named():
    status, ev, _ = mp.judge_scheduled([R(NOW + 3 * H, "ok")], NOW, SLOT, 90, observed_at=NOW)
    assert status == "UNKNOWN" and "future-dated" in ev


# ---------------------------------------------------------------- the line parsers

def vz(start, end_hex="6B016F2B", status="OK", vmid=103):
    return "UPID:overlord:000563D6:003ACA36:%08X:vzdump:%d:root@pam: %s %s" % (int(start.timestamp()), vmid, end_hex, status)


def test_vzdump_ok_and_error_and_other_vm_and_running():
    t = TODAY_SLOT + 4 * M
    text = "\n".join([
        vz(t - 24 * H),
        vz(t, status="could not activate storage 'r710-backup': storage 'r710-backup' is not online"),
        vz(t + M, vmid=104),
        "UPID:overlord:000563D7:003ACA37:%08X:vzdump:103:root@pam:" % int((t + 2 * M).timestamp()),
        "UPID:overlord:000563D8:003ACA38:%08X:qmstart:103:root@pam: 6B016F2B OK" % int(t.timestamp()),
        "garbage",
    ])
    rows = mp.parse_vzdump(text, 103)
    assert [(r.state) for r in rows] == ["ok", "fail", "unknown"]
    assert rows[0].ts == t - 24 * H and "not online" in rows[1].detail and "no end" in rows[2].detail


def test_vzdump_warnings_are_not_ok():
    rows = mp.parse_vzdump(vz(TODAY_SLOT, status="WARNINGS: 1"), 103)
    assert rows[0].state == "fail"


def vs(t, body):
    return "%s %s" % (compact(t), body)


def test_vault_sync_lines():
    t = TODAY_SLOT + 30 * M
    rows = mp.parse_vault_sync("\n".join([
        vs(t, "OK files=59860 bytes=1 drift710=0 drift620=0 greywolf_newest=x"),
        vs(t + M, "OK files=5 drift710=3 drift620=0"),
        vs(t + 2 * M, "OK files=5"),
        vs(t + 3 * M, "UNKNOWN WHY: 710 unreachable"),
        vs(t + 4 * M, "FAIL pull rc=2"),
        "not a line",
    ]))
    assert [r.state for r in rows] == ["ok", "fail", "unknown", "unknown", "fail"]
    assert "drift" in rows[1].detail and "format" in rows[2].detail and "710 unreachable" in rows[3].detail


def test_greywolf_state_lines():
    t = utc("2026-11-23T12:14:48Z")
    rows = mp.parse_greywolf("\n".join([
        vs(t, "OK state-x.tar 2771739136 bytes since 2026-11-19T04:10:04 db1 integrity=ok db2 integrity=ok"),
        vs(t + M, "OK state-x.tar 5 bytes since y integrity=ok db2 integrity=corrupt"),
        vs(t + 2 * M, "OK state-x.tar 5 bytes since y"),
        vs(t + 3 * M, "SKIPPED GREYWOLF unreachable"),
        vs(t + 4 * M, "FAILED cannot reach the 710"),
    ]))
    assert [r.state for r in rows] == ["ok", "fail", "unknown", "fail", "fail"]


def test_nightly_full_run_lines_map_like_the_scoreboard_probe():
    base = "main=aaaaaaaaaaaa collected=%s passed=1 failed=0 skipped=0 errors=0 wall=3h host=H"
    rows = mp.parse_nightly_full("\n".join([
        z(TODAY_SLOT) + " PASS " + base % "16415",
        z(TODAY_SLOT + H) + " FAIL main=b collected=- failed=5",
        z(TODAY_SLOT + 2 * H) + ' UNKNOWN main=c reason="exceeded the 270 min wall cap; killed, no verdict"',
        z(TODAY_SLOT + 3 * H) + " SKIPPED-BUSY main=d",
        "    tests/test_x.py::test_y",
    ]))
    assert [r.state for r in rows] == ["ok", "fail", "unknown", "unknown"]
    assert "wall cap" in rows[2].detail


def test_library_lines_ignore_dry_runs_and_check_the_error_count():
    t = utc("2026-11-23T10:30:01Z")
    rows = mp.parse_library("\n".join([
        z(t) + " status=ok dry=False secs=5 errors=0 x=1",
        z(t + M) + " status=ok dry=True secs=5",
        z(t + 2 * M) + " status=ok dry=False secs=5 errors=2",
        z(t + 3 * M) + ' status=errors dry=False secs=5 errors=1 errors_text=["proof counts disagree (see STATS-337.json)"]',
        z(t + 4 * M) + " status=ok",
    ]))
    assert [r.state for r in rows] == ["ok", "fail", "fail", "unknown"]
    assert "proof counts disagree" in rows[2].detail


# ---------------------------------------------------------------- sources that live on another machine

OVERLORD = [("vzdump-vm103", "vzdump_mirror"), ("vault-sync", "vault_sync_mirror"),
            ("greywolf-state-pull", "greywolf_mirror")]


def watcher(wid):
    return dict((w[0], w[2]) for w in mp.WATCHERS)[wid]


@pytest.mark.parametrize("wid,key", OVERLORD)
def test_absent_mirror_is_unknown_and_names_the_exact_path_to_expose(wid, key):
    ctx = make_ctx()
    f = watcher(wid)(ctx)
    assert f.status == "UNKNOWN"
    assert ctx.paths[key] in f.evidence and "overlord" in f.evidence


@pytest.mark.parametrize("wid,key", OVERLORD)
def test_unreadable_mirror_is_unknown(wid, key):
    ctx = make_ctx()
    ctx.io.files[ctx.paths[key]] = (PermissionError(), NOW)
    f = watcher(wid)(ctx)
    assert f.status == "UNKNOWN" and "unreadable" in f.evidence


@pytest.mark.parametrize("wid,key", OVERLORD)
def test_mirror_without_a_modification_time_is_unknown(wid, key):
    ctx = make_ctx()
    ctx.io.files[ctx.paths[key]] = ("whatever", None)
    f = watcher(wid)(ctx)
    assert f.status == "UNKNOWN" and "modification time" in f.evidence


def overlord_text(wid, t, good=True):
    if wid == "vzdump-vm103":
        return vz(t, status="OK" if good else "storage 'r710-backup' is not online")
    if wid == "vault-sync":
        return vs(t, "OK files=1 bytes=2 drift710=0 drift620=0" if good else "UNKNOWN WHY: 710 unreachable")
    return vs(t, "OK state-x.tar 1 bytes since y integrity=ok" if good else "FAILED cannot reach the 710")


SLOT_OF = {"vzdump-vm103": TODAY_SLOT + 4 * M, "vault-sync": utc("2026-11-23T10:47:28Z"),
           "greywolf-state-pull": utc("2026-11-23T12:14:48Z")}


@pytest.mark.parametrize("wid,key", OVERLORD)
def test_fresh_mirror_with_a_good_run_is_ok(wid, key):
    ctx = make_ctx()
    put(ctx, key, overlord_text(wid, SLOT_OF[wid]))
    f = watcher(wid)(ctx)
    assert f.status == "OK", f.evidence


@pytest.mark.parametrize("wid,key", OVERLORD)
def test_fresh_mirror_with_a_bad_run_is_not_ok(wid, key):
    ctx = make_ctx()
    put(ctx, key, overlord_text(wid, SLOT_OF[wid], good=False))
    assert watcher(wid)(ctx).status in ("FAIL", "UNKNOWN")


@pytest.mark.parametrize("wid,key", [o for o in OVERLORD if o[0] != "greywolf-state-pull"])
def test_a_mirror_older_than_tonights_run_cannot_pass(wid, key):
    ctx = make_ctx()
    put(ctx, key, overlord_text(wid, SLOT_OF[wid] - 24 * H), mtime=NOW - 20 * H)
    f = watcher(wid)(ctx)
    assert f.status == "UNKNOWN", f.evidence


def test_vault_private_sync_passes_through_its_own_reader_and_survives_its_crash():
    ctx = make_ctx()
    ctx.io.vault = {"state": "ok", "reason": "pushed and verified 2 target(s) 3.0 h ago", "last_start": "2026-11-23T09:00:00Z"}
    assert watcher("vault-private-sync")(ctx).status == "OK"
    ctx.io.vault = {"state": "failed", "reason": "exit 2: scan found unreviewed findings"}
    assert watcher("vault-private-sync")(ctx).status == "FAIL"
    ctx.io.vault = {"state": "unknown", "reason": "no log file"}
    assert watcher("vault-private-sync")(ctx).status == "UNKNOWN"
    ctx.io.vault = {"state": "ok-ish"}
    assert watcher("vault-private-sync")(ctx).status == "UNKNOWN"
    ctx.io.vault = RuntimeError("module missing")
    assert watcher("vault-private-sync")(ctx).status == "UNKNOWN"


# ---------------------------------------------------------------- local logs

def test_nightly_full_run_reads_the_log_and_never_passes_a_missing_one():
    ctx = make_ctx()
    f = watcher("nightly-full-run")(ctx)
    assert f.status == "UNKNOWN" and ctx.paths["nightly_log"] in f.evidence
    line = z(utc("2026-11-22T17:01:40Z")) + ' UNKNOWN main=79e54d232b75 collected=- reason="exceeded the 270 min wall cap; killed, no verdict"'
    put(ctx, "nightly_log", line)
    assert watcher("nightly-full-run")(ctx).status == "UNKNOWN"
    put(ctx, "nightly_log", z(utc("2026-11-22T14:00:00Z")) + " PASS main=a collected=9 failed=0")
    assert watcher("nightly-full-run")(ctx).status == "OK"
    put(ctx, "nightly_log", z(utc("2026-11-22T14:00:00Z")) + " FAIL main=a collected=9 failed=3")
    assert watcher("nightly-full-run")(ctx).status == "FAIL"


def test_nightly_pass_from_two_nights_ago_is_not_ok():
    ctx = make_ctx()
    put(ctx, "nightly_log", z(utc("2026-11-21T14:00:00Z")) + " PASS main=a collected=9 failed=0")
    assert watcher("nightly-full-run")(ctx).status == "UNKNOWN"


def test_library_nightly_failed_slot_run_is_fail_even_after_a_manual_ok():
    ctx = make_ctx(now=utc("2026-11-24T01:00:00Z"))   # 5 PM PST on the 23rd
    put(ctx, "library_log", "\n".join([
        z(utc("2026-11-23T10:30:01Z")) + ' status=errors dry=False secs=61 errors=1 errors_text=["proof counts disagree"]',
        z(utc("2026-11-24T00:31:57Z")) + " status=ok dry=False secs=85 errors=0",
    ]))
    f = watcher("library-nightly")(ctx)
    assert f.status == "FAIL" and "later off-schedule" in f.evidence


def test_library_nightly_ok_and_missing():
    ctx = make_ctx()
    assert watcher("library-nightly")(ctx).status == "UNKNOWN"
    put(ctx, "library_log", z(utc("2026-11-23T10:30:01Z")) + " status=ok dry=False secs=61 errors=0")
    assert watcher("library-nightly")(ctx).status == "OK"


# ---------------------------------------------------------------- feeds, snapshots, counts

def test_utilization_feed_age():
    ctx = make_ctx()
    f = watcher("utilization-feed")(ctx)
    assert f.status == "UNKNOWN" and ctx.paths["util_mirror"] in f.evidence and "/var/lib/cluster/utilization.json" in f.evidence
    put(ctx, "util_mirror", json.dumps({"schema": "utilization-1", "generated_at": z(NOW - 12 * M)}), mtime=NOW - 10 * M)
    assert watcher("utilization-feed")(ctx).status == "OK"
    put(ctx, "util_mirror", json.dumps({"schema": "utilization-1", "generated_at": z(NOW - 4 * H)}), mtime=NOW - 10 * M)
    f = watcher("utilization-feed")(ctx)
    assert f.status == "FAIL" and "feed" in f.evidence
    put(ctx, "util_mirror", json.dumps({"generated_at": z(NOW - 30 * H)}), mtime=NOW - 30 * H)
    assert watcher("utilization-feed")(ctx).status == "UNKNOWN"          # the copy is old: cannot tell feed from copy
    put(ctx, "util_mirror", json.dumps({"schema": "utilization-1", "hosts": {}}))
    f = watcher("utilization-feed")(ctx)
    assert f.status == "UNKNOWN" and "timestamp" in f.evidence
    put(ctx, "util_mirror", "{not json")
    assert watcher("utilization-feed")(ctx).status == "UNKNOWN"
    put(ctx, "util_mirror", json.dumps({"generated_at": z(NOW + 5 * H)}))
    assert watcher("utilization-feed")(ctx).status == "UNKNOWN"          # future-dated


def card(answer="A", answered=None, routed=None, **kw):
    c = {"answer": answer, "answered_at": z(answered or NOW - 5 * H), "routed": routed}
    c.update(kw)
    return c


def test_cards_answered_and_not_routed():
    ctx = make_ctx()
    f = watcher("cards-unrouted")(ctx)
    assert f.status == "UNKNOWN" and ctx.paths["cards_snapshot"] in f.evidence
    cards = {"q1": card(routed={"at": z(NOW - H), "by": "wake-on-answer"}),
             "q2": card(answer=None),
             "q3": card(answer="not_yet", kind="step"),
             "q4": card(status="withdrawn"),
             "q5": card(answered=NOW - 20 * M)}
    put(ctx, "cards_snapshot", json.dumps(cards))
    f = watcher("cards-unrouted")(ctx)
    assert f.status == "OK", f.evidence          # q5 is inside the 2 h grace, the rest are routed or not answered
    cards["q6"] = card(answered=NOW - 3 * H)
    put(ctx, "cards_snapshot", json.dumps({"questions": cards}))
    f = watcher("cards-unrouted")(ctx)
    assert f.status == "FAIL" and "q6" in f.evidence and "2 answered" in f.evidence
    put(ctx, "cards_snapshot", json.dumps([dict(card(answered=NOW - 3 * H), id="q9")]))
    assert watcher("cards-unrouted")(ctx).status == "FAIL"


def test_cards_snapshot_that_is_old_or_unreadable_is_unknown():
    ctx = make_ctx()
    put(ctx, "cards_snapshot", json.dumps({}), mtime=NOW - 30 * H)
    assert watcher("cards-unrouted")(ctx).status == "UNKNOWN"
    put(ctx, "cards_snapshot", json.dumps({}), mtime=NOW - 5 * M)
    assert watcher("cards-unrouted")(ctx).status == "OK"               # empty, fresh: nothing waits
    put(ctx, "cards_snapshot", "[1, 2]")
    assert watcher("cards-unrouted")(ctx).status == "UNKNOWN"
    put(ctx, "cards_snapshot", json.dumps({"q1": {"answer": "A", "routed": None}}))
    assert watcher("cards-unrouted")(ctx).status == "UNKNOWN"          # answered, no time: cannot tell if it is stuck
    put(ctx, "cards_snapshot", json.dumps({"exported_at": z(NOW - 40 * H), "cards": {}}), mtime=NOW - M)
    assert watcher("cards-unrouted")(ctx).status == "UNKNOWN"          # the export's own stamp wins over the file's


NOTES = "# Nightly desk-archival review, run 2026-11-23 ~02:00-02:20 PT\nResult: %d PASS, 132 CHECK FIRST, 144 KEEP, 7 LIVE (Remote Control) of 283 unarchived (list_sessions limit 1000).\n"


def put_notes(ctx, text, name="NOTES-2026-11-23.md", mtime=None):
    d = ctx.paths["archive_dir"]
    ctx.io.dirs[d] = ctx.io.dirs.get(d, []) + [name]
    ctx.io.files[os.path.join(d, name)] = (text, mtime or utc("2026-11-23T10:05:51Z"))


def test_finished_desks_not_archived():
    ctx = make_ctx()
    assert watcher("done-desks-unarchived")(ctx).status == "UNKNOWN"
    put_notes(ctx, NOTES % 0)
    f = watcher("done-desks-unarchived")(ctx)
    assert f.status == "OK" and "132 check first" in f.evidence
    ctx = make_ctx()
    put_notes(ctx, NOTES % 4)
    f = watcher("done-desks-unarchived")(ctx)
    assert f.status == "FAIL" and "4 pass the gate" in f.evidence
    ctx = make_ctx()
    put_notes(ctx, "the format changed\n")
    assert watcher("done-desks-unarchived")(ctx).status == "UNKNOWN"
    ctx = make_ctx()
    put_notes(ctx, NOTES % 0, name="NOTES-2026-11-21.md", mtime=utc("2026-11-21T10:05:00Z"))
    assert watcher("done-desks-unarchived")(ctx).status == "UNKNOWN"   # the 11-23 review did not run


# ---------------------------------------------------------------- gh

def runs(*rows):
    return json.dumps(list(rows))


def run_row(rid, concl="success", status="completed", age_h=6, sha="a" * 40):
    t = NOW - age_h * H
    return {"databaseId": rid, "conclusion": concl, "status": status, "headSha": sha, "event": "push",
            "createdAt": z(t - 30 * M), "updatedAt": z(t)}


def gh_hub(ctx, rows, jobs=None, log="step\nOK: ran 16415 == collected 16415\n"):
    jobs = jobs if jobs is not None else {"jobs": [{"databaseId": 77, "name": "pytest", "conclusion": "success"}]}
    ctx.io.gh_answers[("run", "list")] = (0, rows)
    ctx.io.gh_answers[("run", "view")] = (0, json.dumps(jobs))
    ctx.io.gh_answers[("api",)] = (0, log)


def test_hub_tests_success_with_the_count_is_ok():
    ctx = make_ctx()
    gh_hub(ctx, runs(run_row(5)))
    f = watcher("hub-tests-main")(ctx)
    assert f.status == "OK" and "16415" in f.evidence and "aaaaaaa" in f.evidence


def test_hub_tests_failure_is_fail_and_cancelled_runs_say_nothing():
    ctx = make_ctx()
    gh_hub(ctx, runs(run_row(6, "cancelled"), run_row(5, "failure")))
    assert watcher("hub-tests-main")(ctx).status == "FAIL"
    gh_hub(ctx, runs(run_row(7, "cancelled"), run_row(6, "skipped")))
    assert watcher("hub-tests-main")(ctx).status == "UNKNOWN"
    gh_hub(ctx, runs(run_row(8, None, "in_progress"), run_row(5, "success")))
    f = watcher("hub-tests-main")(ctx)
    assert f.status == "OK" and "in progress" in f.evidence


def test_hub_tests_success_without_a_readable_count_is_unknown():
    ctx = make_ctx()
    gh_hub(ctx, runs(run_row(5)), log="no guard line here")
    assert watcher("hub-tests-main")(ctx).status == "UNKNOWN"
    gh_hub(ctx, runs(run_row(5)), log="OK: ran 10 == collected 11")
    assert watcher("hub-tests-main")(ctx).status == "UNKNOWN"
    gh_hub(ctx, runs(run_row(5)), jobs={"jobs": [{"databaseId": 1, "name": "lint", "conclusion": "success"}]})
    assert watcher("hub-tests-main")(ctx).status == "UNKNOWN"
    gh_hub(ctx, runs(run_row(5)))
    ctx.io.gh_answers[("api",)] = (1, "HTTP 404")
    assert watcher("hub-tests-main")(ctx).status == "UNKNOWN"


def test_hub_tests_stale_success_is_not_ok_and_gh_errors_are_unknown():
    ctx = make_ctx()
    gh_hub(ctx, runs(run_row(5, age_h=100)))
    assert watcher("hub-tests-main")(ctx).status == "UNKNOWN"
    ctx.io.gh_answers[("run", "list")] = (1, "gh: not logged in")
    assert watcher("hub-tests-main")(ctx).status == "UNKNOWN"
    ctx.io.gh_answers[("run", "list")] = (0, "<html>")
    assert watcher("hub-tests-main")(ctx).status == "UNKNOWN"
    ctx.io.gh_answers[("run", "list")] = (0, "[]")
    assert watcher("hub-tests-main")(ctx).status == "UNKNOWN"


def pr_row(n, draft=False, age_h=1):
    return {"number": n, "isDraft": draft, "createdAt": z(NOW - age_h * H), "updatedAt": z(NOW - age_h * H)}


def test_open_hub_prs():
    ctx = make_ctx()
    ctx.io.gh_answers[("pr", "list")] = (0, json.dumps([pr_row(1), pr_row(2, draft=True, age_h=900)]))
    f = watcher("hub-open-prs")(ctx)
    assert f.status == "OK" and "2 open" in f.evidence and "1 draft" in f.evidence
    ctx.io.gh_answers[("pr", "list")] = (0, json.dumps([pr_row(1, age_h=100)]))
    f = watcher("hub-open-prs")(ctx)
    assert f.status == "FAIL" and "#1" in f.evidence
    ctx.io.gh_answers[("pr", "list")] = (0, "[]")
    assert watcher("hub-open-prs")(ctx).status == "OK"


def test_open_hub_prs_that_hit_the_list_limit_are_unknown_not_a_count():
    ctx = make_ctx()
    ctx.io.gh_answers[("pr", "list")] = (0, json.dumps([pr_row(i) for i in range(mp.PR_LIST_LIMIT)]))
    f = watcher("hub-open-prs")(ctx)
    assert f.status == "UNKNOWN" and "limit" in f.evidence
    ctx.io.gh_answers[("pr", "list")] = (1, "error")
    assert watcher("hub-open-prs")(ctx).status == "UNKNOWN"


def test_gh_is_only_ever_asked_to_read():
    for ok in (["run", "list", "--limit", "3"], ["run", "view", "5", "--json", "jobs"], ["pr", "list"],
               ["api", "repos/{owner}/{repo}/actions/jobs/7/logs"]):
        mp.assert_read_only_gh(ok)
    for bad in (["pr", "merge", "5"], ["pr", "close", "5"], ["run", "rerun", "5"], ["workflow", "run", "x"],
                ["api", "repos/x/y", "-X", "POST"], ["api", "repos/x/y", "--method", "DELETE"],
                ["api", "repos/x/y", "-f", "a=b"], ["secret", "list"], []):
        with pytest.raises(ValueError):
            mp.assert_read_only_gh(bad)


# ---------------------------------------------------------------- certificates

class _Verify(ssl.SSLCertVerificationError):
    pass


def test_certificate_days_left():
    ctx = make_ctx()
    f = watcher("cert-leadfuel-cloud")(ctx)
    assert f.status == "UNKNOWN" and "--live-tls" in f.evidence and ctx.io.tls_calls == []   # off: no handshake is made
    ctx.io.tls_answers = {"leadfuel.cloud": {"not_after": NOW + dt.timedelta(days=50.1)},
                          "www.leadfuel.cloud": {"not_after": NOW + dt.timedelta(days=9)}}
    assert watcher("cert-leadfuel-cloud")(ctx).status == "OK"
    f = watcher("cert-www-leadfuel-cloud")(ctx)
    assert f.status == "FAIL" and "9.0 days" in f.evidence


def test_certificate_that_will_not_verify_or_cannot_be_reached():
    ctx = make_ctx()
    err = _Verify(1, "certificate has expired")
    ctx.io.tls_answers = {"leadfuel.cloud": err, "www.leadfuel.cloud": socket.timeout("timed out")}
    assert watcher("cert-leadfuel-cloud")(ctx).status == "FAIL"
    f = watcher("cert-www-leadfuel-cloud")(ctx)
    assert f.status == "UNKNOWN" and "timeout" in f.evidence.lower()
    ctx.io.tls_answers = {"leadfuel.cloud": {"not_after": NOW - H}, "www.leadfuel.cloud": {}}
    assert watcher("cert-leadfuel-cloud")(ctx).status == "FAIL"
    assert watcher("cert-www-leadfuel-cloud")(ctx).status == "UNKNOWN"


# ---------------------------------------------------------------- the report

def test_every_watcher_in_the_done_when_has_a_line():
    ids = [w[0] for w in mp.WATCHERS]
    assert ids == ["vzdump-vm103", "vault-sync", "greywolf-state-pull", "nightly-full-run", "library-nightly",
                   "vault-private-sync", "hub-tests-main", "utilization-feed", "cert-leadfuel-cloud",
                   "cert-www-leadfuel-cloud", "cards-unrouted", "hub-open-prs", "done-desks-unarchived"]


def test_an_empty_world_reads_all_unknown_never_ok():
    ctx = make_ctx()
    rep = mp.build_report(ctx)
    assert len(rep["lines"]) == 13
    assert rep["summary"] == {"OK": 0, "FAIL": 0, "UNKNOWN": 13}


def test_a_crashing_watcher_becomes_unknown_and_the_others_still_run(monkeypatch):
    def boom(ctx):
        raise RuntimeError("secret detail that must not matter")
    monkeypatch.setattr(mp, "WATCHERS", [("a", "A", boom)] + list(mp.WATCHERS[1:]))
    rep = mp.build_report(make_ctx())
    assert rep["lines"][0]["status"] == "UNKNOWN" and "RuntimeError" in rep["lines"][0]["evidence"]
    assert len(rep["lines"]) == 13


def test_a_reader_that_always_says_ok_is_caught_by_its_own_controls(monkeypatch):
    assert mp.run_controls(NOW)[0] is True
    monkeypatch.setattr(mp, "judge_scheduled", lambda *a, **k: ("OK", "always", None))
    ok, bad = mp.run_controls(NOW)
    assert not ok and bad
    rep = mp.build_report(make_ctx())
    assert rep["controls_ok"] is False
    assert all(l["status"] == "UNKNOWN" and "controls failed" in l["evidence"] for l in rep["lines"])


def test_text_file_has_one_line_per_watcher_and_a_dated_name(tmp_path):
    ctx = make_ctx(now=utc("2026-11-24T00:50:00Z"))   # 4:50 PM PST on the 23rd
    put(ctx, "library_log", z(utc("2026-11-23T10:30:01Z")) + " status=ok dry=False secs=61 errors=0",
        mtime=utc("2026-11-24T00:40:00Z"))
    rep = mp.build_report(ctx)
    txt_path, json_path = mp.write_report(rep, str(tmp_path))
    assert os.path.basename(txt_path) == "proof-2026-11-23.txt" and os.path.basename(json_path) == "proof-2026-11-23.json"
    lines = open(txt_path, encoding="utf-8").read().splitlines()
    body = [l for l in lines if not l.startswith("#")]
    assert len(body) == 13 and all(l.count(" | ") >= 2 for l in body)
    assert sum(1 for l in body if l.split(" | ")[1] == "OK") == 1
    assert lines[0].startswith("# MORNING PROOF 2026-11-23") and "OK 1" in lines[0]
    data = json.loads(open(json_path, encoding="utf-8").read())
    assert data["schema"] == mp.SCHEMA and data["generated_at"] == "2026-11-24T00:50:00Z"
    assert sorted(os.listdir(tmp_path)) == ["proof-2026-11-23.json", "proof-2026-11-23.txt"]   # no temp files left


def test_a_second_read_the_same_day_replaces_the_file(tmp_path):
    rep = mp.build_report(make_ctx())
    mp.write_report(rep, str(tmp_path))
    ctx = make_ctx()
    put(ctx, "library_log", z(utc("2026-11-23T10:30:01Z")) + " status=ok dry=False secs=61 errors=0")
    path, _ = mp.write_report(mp.build_report(ctx), str(tmp_path))
    assert " | OK | " in open(path, encoding="utf-8").read()


def test_a_read_before_0445_says_so():
    early = mp.build_report(make_ctx(now=utc("2026-11-23T11:30:00Z")))   # 3:30 AM PST
    assert early["early_read"] is True and "EARLY" in mp.render_text(early).splitlines()[0]
    assert mp.build_report(make_ctx())["early_read"] is False


def test_evidence_is_one_clean_line():
    rep = mp.build_report(make_ctx())
    for l in rep["lines"]:
        assert "\n" not in l["evidence"] and len(l["evidence"]) <= mp.EVIDENCE_MAX


# ---------------------------------------------------------------- the command line

def test_offline_run_opens_no_socket_runs_no_gh_and_writes_only_the_report(tmp_path, monkeypatch):
    def no_socket(*a, **k):
        raise AssertionError("the morning read opened a socket")
    monkeypatch.setattr(socket, "socket", no_socket)
    monkeypatch.setattr(socket, "create_connection", no_socket)
    import subprocess

    def no_proc(*a, **k):
        raise AssertionError("the morning read started a process")
    monkeypatch.setattr(subprocess, "run", no_proc)
    monkeypatch.setattr(subprocess, "Popen", no_proc)
    inputs = tmp_path / "in"
    inputs.mkdir()
    out = tmp_path / "out"
    rc = mp.main(["run", "--offline", "--now", "2026-11-23T12:50:00Z", "--inputs-dir", str(inputs), "--out-dir", str(out),
                  "--nightly-log", str(tmp_path / "none.log"), "--library-log", str(tmp_path / "none2.log"),
                  "--archive-dir", str(tmp_path / "nonedir"), "--vault-log", str(tmp_path / "none3.log")])
    assert rc == 3                                  # all UNKNOWN, no FAIL
    assert sorted(os.listdir(out)) == ["proof-2026-11-23.json", "proof-2026-11-23.txt"]
    assert os.listdir(inputs) == []                 # read-only: it never writes beside its inputs


def test_exit_code_mirrors_the_worst_line_but_the_file_is_the_verdict():
    assert mp.exit_code({"OK": 13, "FAIL": 0, "UNKNOWN": 0}) == 0
    assert mp.exit_code({"OK": 5, "FAIL": 1, "UNKNOWN": 7}) == 1
    assert mp.exit_code({"OK": 5, "FAIL": 0, "UNKNOWN": 8}) == 3


def test_selftest_prints_every_control_and_passes(capsys):
    assert mp.main(["selftest"]) == 0
    out = capsys.readouterr().out
    assert "controls ok" in out.lower()
