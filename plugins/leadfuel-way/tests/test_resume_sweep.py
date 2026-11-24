"""resume_sweep.py: nudge the sessions a usage limit stranded, once, after the limit has reset, and never on a guess.

The store fields and the error text are measured (2026-11-01, three stranded sessions): `error` is
`You've hit your weekly limit · resets 2pm (America/Tijuana)`, `errorAt` and `lastActivityAt` are epoch
milliseconds and `lastActivityAt` runs 13 to 18 ms AFTER `errorAt` on a session nobody has touched since.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest

from kit import PLUGIN, load_module

SCRIPT = PLUGIN / "scripts" / "resume_sweep.py"
A = "local_70900e3f-0b7b-4e15-8ff5-13159ea0fa64"
B = "local_7be31255-2247-4700-bdf1-9b2df91f6bcb"
C = "local_bacae5ff-75ed-4538-aaff-97a75dec78ec"
ME = "local_17e8ba63-4dd2-4846-8c8a-629b9c3750b2"
ERR = "You've hit your weekly limit · resets 2pm (America/Tijuana)"
ERR_AT = 1793480286321                       # 2026-10-31T20:58:06Z
NOW = datetime(2026, 11, 1, 2, 0, tzinfo=timezone.utc)  # an hour past the 21:00Z reset
CLEAR = json.dumps({"plan": {"windows": [{"label": "Weekly · all models", "percentUsed": 26}]}})
FULL = json.dumps({"plan": {"windows": [{"label": "Weekly · all models", "percentUsed": 100}]}})


@pytest.fixture(scope="module")
def rs():
    return load_module(SCRIPT, "resume_sweep_under_test")


def sess(sid=A, error=ERR, error_at=ERR_AT, last=None, archived=False, task=None, title="NODE · x part · 1"):
    return {"id": sid, "title": title, "error": error, "error_at": error_at,
            "last_activity": error_at + 15 if last is None else last, "archived": archived, "task": task}


def plan(rs, sessions, usage=CLEAR, state=None, now=NOW, **kw):
    return rs.make_plan(sessions, usage, state or {}, now, **kw)


# ---- the reset time ------------------------------------------------------------------------------------

def test_the_reset_time_is_read_in_the_zone_the_text_names(rs):
    at = rs.from_ms(ERR_AT)
    assert rs.reset_time(ERR, at) == datetime(2026, 10, 31, 21, 0, tzinfo=timezone.utc)  # 2pm PDT is 21:00Z


def test_a_reset_after_midnight_local_is_the_next_day(rs):
    at = rs.from_ms(ERR_AT)
    # 9am on 2026-11-01 is already PST: daylight time ended at 2am that morning
    assert rs.reset_time("You've hit your weekly limit · resets 9am (America/Tijuana)", at) == datetime(
        2026, 11, 1, 17, 0, tzinfo=timezone.utc)


def test_a_dated_reset_with_minutes_is_read(rs):
    at = rs.from_ms(ERR_AT)
    assert rs.reset_time("You've hit your weekly limit · resets Nov 7, 2:30pm (America/Tijuana)", at) == datetime(
        2026, 11, 7, 22, 30, tzinfo=timezone.utc)  # PST by then


@pytest.mark.parametrize("text", ["", "You've hit your weekly limit", "resets soon (America/Tijuana)",
                                  "resets 2pm (Not/AZone)", "resets Foo 7, 2pm (America/Tijuana)"])
def test_an_unreadable_reset_is_none_never_a_guess(rs, text):
    assert rs.reset_time(text, rs.from_ms(ERR_AT)) is None


# ---- who is a candidate ------------------------------------------------------------------------------------

def test_a_stranded_session_after_the_reset_is_nudged(rs):
    p = plan(rs, [sess()])
    assert [r["id"] for r in p["nudge"]] == [A] and p["usage"]["state"] == "clear" and p["message"] == "limit reset, keep going"


def test_before_the_reset_nobody_is_nudged(rs):
    p = plan(rs, [sess()], now=datetime(2026, 10, 31, 20, 59, tzinfo=timezone.utc))
    assert p["nudge"] == [] and p["skipped"] == 1


@pytest.mark.parametrize("over", [
    {"archived": True}, {"task": "wake-on-answer"}, {"task": "merge-desk-refresh"},
    {"error": "API Error: overloaded"}, {"last": ERR_AT + 3_600_000},   # someone typed into it since
    {"error_at": ERR_AT - 80 * 3_600_000, "last": ERR_AT - 80 * 3_600_000 + 5},  # over 72 h old
])
def test_sessions_that_are_not_stranded_are_skipped(rs, over):
    assert plan(rs, [sess(**over)])["nudge"] == []


def test_a_launch_slot_run_is_a_real_session_and_counts(rs):
    assert [r["id"] for r in plan(rs, [sess(task="way-slot-02")])["nudge"]] == [A]


def test_the_sweeping_session_itself_is_never_nudged(rs):
    assert plan(rs, [sess(sid=ME)], self_id=ME)["nudge"] == []


def test_an_unreadable_reset_is_listed_as_unknown_and_not_nudged(rs):
    p = plan(rs, [sess(error="You've hit your weekly limit")])
    assert p["nudge"] == [] and [r["id"] for r in p["unknown"]] == [A]


# ---- the usage gate ------------------------------------------------------------------------------------------

def test_a_window_at_100_percent_stops_the_pass(rs):
    p = plan(rs, [sess()], usage=FULL)
    assert p["nudge"] == [] and p["usage"]["state"] == "full"


@pytest.mark.parametrize("raw", [None, "", "not json", "{}", json.dumps({"plan": {"windows": []}}),
                                 json.dumps({"plan": {"windows": [{"label": "x"}]}})])
def test_an_unreadable_usage_file_is_unknown_and_nudges_nobody(rs, raw):
    p = plan(rs, [sess()], usage=raw)
    assert p["nudge"] == [] and p["usage"]["state"] == "unknown"


def test_an_unreadable_session_store_is_unknown_not_empty(rs, tmp_path):
    assert rs.load_candidates(tmp_path / "missing") is None
    assert rs.load_candidates(tmp_path) is None
    assert plan(rs, None)["usage"]["state"] == "unknown"


# ---- budget and repeats ------------------------------------------------------------------------------------

def many(n):
    return [sess(sid=f"local_{i:08x}-0000-4000-8000-000000000000", error_at=ERR_AT + i) for i in range(n)]


def test_at_most_eight_a_pass_and_the_rest_wait(rs):
    p = plan(rs, many(11))
    assert len(p["nudge"]) == 8 and len(p["over_budget"]) == 3


def test_the_cap_leaves_room_for_the_wake_sends_under_the_ten_send_pause(rs):
    assert len(plan(rs, many(11), already_sent=5)["nudge"]) == 5
    assert plan(rs, many(11), already_sent=10)["nudge"] == []


def test_a_nudge_is_not_repeated_inside_the_cooldown_or_past_three(rs):
    s = sess()
    recent = {A: {"count": 1, "last": (NOW - timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ"), "error_at": ERR_AT}}
    assert plan(rs, [s], state=recent)["nudge"] == [] and len(plan(rs, [s], state=recent)["cooldown"]) == 1
    old = {A: {"count": 1, "last": (NOW - timedelta(minutes=90)).strftime("%Y-%m-%dT%H:%M:%SZ"), "error_at": ERR_AT}}
    assert [r["id"] for r in plan(rs, [s], state=old)["nudge"]] == [A]
    spent = {A: {"count": 3, "last": (NOW - timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ"), "error_at": ERR_AT}}
    assert plan(rs, [s], state=spent)["nudge"] == []


def test_a_new_error_resets_the_count(rs):
    old = {A: {"count": 3, "last": (NOW - timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ"), "error_at": ERR_AT - 999}}
    assert [r["id"] for r in plan(rs, [sess()], state=old)["nudge"]] == [A]


def test_record_counts_only_the_sends_that_did_not_error(rs):
    p = plan(rs, [sess(sid=A), sess(sid=B, error_at=ERR_AT + 1)])
    new = rs.record({}, p, {A}, NOW)
    assert new[A]["count"] == 1 and B not in new
    assert rs.record(new, p, {A}, NOW + timedelta(hours=2))[A]["count"] == 2


# ---- the command line ----------------------------------------------------------------------------------------

def _run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", timeout=60)


def _store(tmp_path, sessions):
    d = tmp_path / "acct" / "env"
    d.mkdir(parents=True)
    for s in sessions:
        (d / f"{s['id']}.json").write_text(json.dumps({
            "sessionId": s["id"], "title": s["title"], "error": s["error"], "errorAt": s["error_at"],
            "lastActivityAt": s["last_activity"], "isArchived": s["archived"], "scheduledTaskId": s["task"]}), encoding="utf-8")
    return tmp_path


def test_cli_plan_then_record(tmp_path):
    store = _store(tmp_path / "store", [sess(sid=A), sess(sid=B, archived=True)])
    usage = tmp_path / "usage.json"
    usage.write_text(CLEAR, encoding="utf-8")
    out, state = tmp_path / "plan.json", tmp_path / "state.json"
    run = _run("plan", "--sessions-dir", store, "--usage", usage, "--state", state, "--now", "2026-11-01T02:00:00Z", "--out", out)
    assert run.returncode == 0, run.stderr
    assert f"NUDGE to={A}" in run.stdout and B not in run.stdout and "nudge=1" in run.stdout
    rec = _run("record", "--plan", out, "--state", state, "--sent", A, "--now", "2026-11-01T02:01:00Z")
    assert rec.returncode == 0 and json.loads(state.read_text(encoding="utf-8"))[A]["count"] == 1
    again = _run("plan", "--sessions-dir", store, "--usage", usage, "--state", state, "--now", "2026-11-01T02:10:00Z", "--out", out)
    assert "NUDGE" not in again.stdout and "cooldown=1" in again.stdout


def test_cli_with_no_usage_file_says_unknown_and_exits_2(tmp_path):
    store = _store(tmp_path / "store", [sess()])
    run = _run("plan", "--sessions-dir", store, "--usage", tmp_path / "missing.json", "--out", tmp_path / "p.json")
    assert run.returncode == 2 and "UNKNOWN" in run.stdout and "NUDGE" not in run.stdout


def test_the_script_has_no_network_no_environment_and_no_permission_change():
    import ast
    text = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(text)
    imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not imported & {"socket", "http", "urllib", "requests", "httpx", "smtplib", "ftplib", "subprocess", "os", "webbrowser"}
    assert "set_session_permission_mode" not in text


def test_the_wake_skill_runs_the_sweep_and_names_its_limits():
    skill = (PLUGIN / "skills" / "wake" / "SKILL.md").read_text(encoding="utf-8")
    assert "resume_sweep.py" in skill and "limit reset, keep going" in skill and "get_usage" in skill
    assert "--already-sent" in skill and "Never change a permission mode" in skill
