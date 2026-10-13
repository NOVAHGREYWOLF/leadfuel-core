"""The Sessions desk feeder must say 'unknown' whenever its inputs cannot establish a value,
and must never list a session for archiving that the Conductor desk's archive gate would refuse."""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "watch"))

import sessions_desk_feeder as f  # noqa: E402

NOW = datetime(2026, 10, 4, 21, 0, tzinfo=timezone.utc)


def sess(sid, title, running=False, last="2026-10-04T20:00:00Z", pr=None, pr_state=None, group="NODE"):
    s = {"sessionId": "local_%s-0000-0000-0000-000000000000" % sid, "title": title, "cwd": "",
         "isArchived": False, "isRunning": running, "lastActivityAt": last, "group": {"id": "g", "name": group}}
    if pr is not None:
        s["prNumber"], s["prState"] = pr, pr_state
    return s


def merged_pr(_s):
    return {"state": "MERGED", "isDraft": False, "mergedAt": "2026-10-04T19:00:00Z", "statusCheckRollup": [], "url": "u"}


def row(snap, short):
    return next(r for r in snap["rows"] if r["short"] == short)


def ev(sid, line, handoff=None):
    return {"local_%s-0000-0000-0000-000000000000" % sid: {"status_line": line, "handoff": handoff, "read_at": "2026-10-04T20:30:00Z"}}


def test_title_parsing():
    assert f.parse_title("NODE · SESSIONS-DESK-PAGE 1/1 · every session") == ("NODE", "SESSIONS-DESK-PAGE", 1, 1)
    assert f.parse_title("ARMS · INBOUND-FENCE 1/1") == ("ARMS", "INBOUND-FENCE", 1, 1)
    assert f.parse_title("ARMS · conformance gate 2/2 (successor)")[1] is None
    assert f.role_of("ROUTER #18") == "router" and f.role_of("CONDUCTOR · system build") == "conductor"


def test_nothing_read_means_unknown_not_progress():
    snap, to_read = f.build([sess("aaaaaaaa", "NODE · T1 1/1 · x", pr=5, pr_state="open")], now=NOW)
    r = row(snap, "aaaaaaaa")
    assert r["percent"] is None and "unknown" in r["percent_basis"]
    assert r["tokens"] is None
    assert r["gate"]["pushed"] == "unknown" and r["gate"]["report"] == "unknown"
    assert r["verdict"] == "keep"
    assert r["id"] in to_read


def test_archive_only_when_all_five_gate_cells_pass():
    s = [sess("aaaaaaaa", "NODE · T1 1/1 · x", pr=5, pr_state="merged")]
    full = ev("aaaaaaaa", "STATUS: DONE | T1 | merged", handoff=True)
    snap, _ = f.build(s, evidence=full, pr_lookup=merged_pr, unpushed_lookup=lambda _s: (0, "clean"), now=NOW)
    r = row(snap, "aaaaaaaa")
    assert r["verdict"] == "archive" and "archivable" in r["flags"] and r["percent"] == 100
    # one missing cell (unpushed work) keeps it
    snap, _ = f.build(s, evidence=full, pr_lookup=merged_pr, unpushed_lookup=lambda _s: (2, "2 commits"), now=NOW)
    assert row(snap, "aaaaaaaa")["verdict"] == "keep"
    # the app badge alone is not 'merged'
    snap, _ = f.build(s, evidence=full, pr_lookup=lambda _s: None, unpushed_lookup=lambda _s: (0, "clean"), now=NOW)
    r = row(snap, "aaaaaaaa")
    assert r["gate"]["merged"] == "badge" and r["verdict"] == "keep"


def test_unknown_pushed_never_archives():
    s = [sess("aaaaaaaa", "NODE · T1 1/1 · x", pr=5, pr_state="merged")]
    snap, _ = f.build(s, evidence=ev("aaaaaaaa", "STATUS: DONE | T1", True), pr_lookup=merged_pr,
                      unpushed_lookup=lambda _s: (None, "repo has no remote"), now=NOW)
    assert row(snap, "aaaaaaaa")["verdict"] == "keep"


def test_router_keeps_until_successor_is_live():
    s = [sess("11111111", "ROUTER #17"), sess("22222222", "ROUTER #18", running=True, group="ROUTER")]
    e = ev("11111111", "STATUS: DONE | router", True)
    snap, _ = f.build(s, evidence=e, unpushed_lookup=lambda _s: (0, "clean"), now=NOW)
    assert row(snap, "11111111")["verdict"] == "archive"
    assert row(snap, "22222222")["verdict"] == "keep"
    snap, _ = f.build(s[:1], evidence=e, unpushed_lookup=lambda _s: (0, "clean"), now=NOW)
    assert row(snap, "11111111")["verdict"] == "keep"


def test_rotate_past_cap_without_successor_and_haiku_cap():
    s = [sess("aaaaaaaa", "NODE · T1 1/1 · x", running=True)]
    u = {"local_aaaaaaaa-0000-0000-0000-000000000000": {"tokens": 310_000, "model": "claude-sonnet-5-5"}}
    snap, _ = f.build(s, usage=u, now=NOW)
    assert row(snap, "aaaaaaaa")["verdict"] == "rotate" and "past-cap" in row(snap, "aaaaaaaa")["flags"]
    u = {"local_aaaaaaaa-0000-0000-0000-000000000000": {"tokens": 130_000, "model": "claude-haiku-4-5"}}
    snap, _ = f.build(s, usage=u, now=NOW)
    assert row(snap, "aaaaaaaa")["verdict"] == "rotate"
    # a successor (2/2) exists: no rotate flag for the 1/1
    s2 = s + [sess("bbbbbbbb", "NODE · T1 2/2 · x", running=True)]
    u = {"local_aaaaaaaa-0000-0000-0000-000000000000": {"tokens": 310_000, "model": "claude-sonnet-5-5"}}
    snap, _ = f.build(s2, usage=u, now=NOW)
    assert row(snap, "aaaaaaaa")["verdict"] != "rotate"


def test_size_carries_forward_with_its_time():
    s = [sess("aaaaaaaa", "NODE · T1 1/1 · x", running=True)]
    u = {"local_aaaaaaaa-0000-0000-0000-000000000000": {"tokens": 100_000, "model": "m"}}
    snap, _ = f.build(s, usage=u, now=NOW)
    later = datetime(2026, 10, 4, 21, 30, tzinfo=timezone.utc)
    snap2, _ = f.build(s, prev=snap, now=later)
    r = row(snap2, "aaaaaaaa")
    assert r["tokens"] == 100_000 and r["size_at"] == "2026-10-04T21:00:00Z"


def test_only_changed_sessions_are_read_again():
    s = [sess("aaaaaaaa", "NODE · T1 1/1 · x"), sess("bbbbbbbb", "NODE · T2 1/1 · y")]
    e = {**ev("aaaaaaaa", "STATUS: CONTINUING | T1"), **ev("bbbbbbbb", "STATUS: CONTINUING | T2")}
    snap, _ = f.build(s, evidence=e, now=NOW)
    s[1] = dict(s[1], lastActivityAt="2026-10-04T20:50:00Z")
    _, to_read = f.build(s, prev=snap, now=NOW)
    assert to_read == ["local_bbbbbbbb-0000-0000-0000-000000000000"]


def test_stages():
    s = [sess("aaaaaaaa", "NODE · T1 1/1 · x", running=True),
         sess("bbbbbbbb", "NODE · T2 1/1 · x"),
         sess("cccccccc", "NODE · T3 1/1 · x", pr=9, pr_state="open"),
         sess("dddddddd", "NODE · T4 1/1 · x")]
    e = ev("bbbbbbbb", "ASK: T2 | which way?")
    tickets = [("waits", "ci-novahub", "20261004T200000Z-NODE-T4--pr", "desk: NODE · T4 1/1")]
    snap, _ = f.build(s, evidence=e, tickets=tickets, now=NOW)
    assert row(snap, "aaaaaaaa")["stage"] == "working"
    assert row(snap, "bbbbbbbb")["stage"] == "waiting-owner"
    assert row(snap, "cccccccc")["stage"] == "pr-open"
    assert row(snap, "dddddddd")["stage"] == "waiting-ci"


def test_ticket_naming_the_router_does_not_claim_the_router():
    s = [sess("8e21f892", "ROUTER #15", group="ROUTER"), sess("70fae0d7", "DOORS · B1 2/2")]
    tickets = [("holds", "full-suite", "20261004T195102Z-DOORS-B1",
                "DESK: DOORS · B1 2/2 (session local_70fae0d7-55da), router ROUTER #15 (local_8e21f892)")]
    snap, _ = f.build(s, tickets=tickets, now=NOW)
    assert row(snap, "70fae0d7")["slot"] == {"kind": "holds", "lock": "full-suite"}
    assert row(snap, "8e21f892")["slot"] is None


def test_flags_orphan_duplicate_needed_stopped_quiet():
    s = [sess("aaaaaaaa", "NODE · old style desk"),
         sess("bbbbbbbb", "NODE · T1 1/1 · x", running=True),
         sess("cccccccc", "NODE · T1 1/1 · x again", running=True),
         sess("dddddddd", "NODE · T2 1/1 · x", last="2026-10-04T18:00:00Z"),
         sess("eeeeeeee", "NODE · T3 1/1 · x", running=True, last="2026-10-04T10:00:00Z")]
    snap, _ = f.build(s, now=NOW)
    assert "orphan" in row(snap, "aaaaaaaa")["flags"]
    assert "duplicate" in row(snap, "bbbbbbbb")["flags"] and "duplicate" in row(snap, "cccccccc")["flags"]
    assert "needed-stopped" in row(snap, "dddddddd")["flags"]
    assert "quiet-running" in row(snap, "eeeeeeee")["flags"]
    assert snap["flags"]["orphan"] == ["aaaaaaaa"]


def test_archived_sessions_are_left_out_and_digest_marks_new_flags():
    s = [sess("aaaaaaaa", "NODE · old style"), dict(sess("bbbbbbbb", "NODE · gone"), isArchived=True)]
    snap, _ = f.build(s, now=NOW)
    assert [r["short"] for r in snap["rows"]] == ["aaaaaaaa"]
    text, new = f.digest(snap, {"orphan": ["aaaaaaaa"]})
    assert "orphan 1" in text and new["orphan"] == []
