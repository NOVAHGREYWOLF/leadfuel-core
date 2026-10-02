"""Tests for hooks/way_hook.py: the pure functions first, then each event, then the process."""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from kit import HAIKU, HOOK_PATH, OPUS, SONNET, assistant, event, title_rec, tool_use


# --- role_of --------------------------------------------------------------------------------

@pytest.mark.parametrize(
    "title, expected",
    [
        ("CONDUCTOR · plan + task list", ("CONDUCTOR", None)),
        ("conductor · lower case", ("CONDUCTOR", None)),
        ("ROUTER #4", ("ROUTER", None)),
        ("ROUTER #12 · leadfuel-way", ("ROUTER", None)),
        ("DOORS · G6 2/5 · topic", ("DESK", "DOORS")),
        ("SENSORS · WAY-1 1/1 · topic", ("DESK", "SENSORS")),
        # A session in the ROUTER lane with a task is a desk, not a router: it may work.
        ("ROUTER · WAY-1 1/1 · leadfuel-way plugin build", ("DESK", "ROUTER")),
        ("Build the leadfuel-way plugin", ("UNFILED", None)),
        ("", ("UNFILED", None)),
        (None, ("UNFILED", None)),
    ],
)
def test_role_of(hook, title, expected):
    assert hook.role_of(title) == expected


# --- caps and the guard ---------------------------------------------------------------------

def test_caps_by_model(hook):
    assert hook.caps_for(HAIKU) == (120_000, 150_000)
    assert hook.caps_for(OPUS) == (300_000, 450_000)
    assert hook.caps_for(SONNET) == (300_000, 450_000)
    assert hook.caps_for(None) == (300_000, 450_000)


def test_caps_env_override_applies_to_every_model(hook, monkeypatch):
    monkeypatch.setenv("SESSION_SOFT_TOKENS", "5000")
    monkeypatch.setenv("SESSION_HARD_TOKENS", "90000")
    assert hook.caps_for(HAIKU) == (5_000, 90_000)
    assert hook.caps_for(OPUS) == (5_000, 90_000)


def test_caps_bad_env_falls_back(hook, monkeypatch):
    monkeypatch.setenv("SESSION_SOFT_TOKENS", "lots")
    assert hook.caps_for(SONNET) == (300_000, 450_000)


def test_guard_silent_below_soft(hook):
    assert hook.guard_message(299_999, 0, 300_000, 450_000) == (None, 0)


def test_guard_speaks_at_soft_then_renags_only_after_a_gap(hook):
    msg, warned = hook.guard_message(300_000, 0, 300_000, 450_000)
    assert "CONTEXT BUDGET" in msg and "300k" in msg and "handoff" in msg
    assert warned == 300_000
    assert hook.guard_message(305_000, warned, 300_000, 450_000)[0] is None
    again, warned2 = hook.guard_message(310_000, warned, 300_000, 450_000)
    assert again is not None and warned2 == 310_000


def test_guard_hard_cap_wording(hook):
    msg, _ = hook.guard_message(460_000, 0, 300_000, 450_000)
    assert "HARD CAP" in msg and "Start nothing" in msg


# --- the banner -----------------------------------------------------------------------------

def test_banner_for_unfiled_session_tells_it_to_file_itself(hook):
    text = hook.banner("startup", None, "UNFILED", None, SONNET, None, 300_000, 450_000)
    assert "THE WAY" in text and "not filed" in text and "leadfuel-way:way" in text
    assert "not measured yet" in text  # unknown size is said, never shown as 0k


def test_banner_for_desk_names_role_lane_and_caps(hook):
    text = hook.banner("startup", "DOORS · G6 2/5 · x", "DESK", "DOORS", HAIKU, 12_000, 120_000, 150_000)
    assert "DESK" in text and "DOORS" in text and "120k" in text and "150k" in text and "12k" in text
    assert "not filed" not in text


def test_banner_notes_compact_and_resume(hook):
    assert "compacted" in hook.banner("compact", "T", "DESK", "X", None, None, 1, 2)
    assert "Resumed" in hook.banner("resume", "T", "DESK", "X", None, None, 1, 2)


# --- coordinator write rule -----------------------------------------------------------------

def test_in_git_checkout(hook, tmp_path):
    repo = tmp_path / "repo"
    (repo / "sub").mkdir(parents=True)
    (repo / ".git").mkdir()
    assert hook.in_git_checkout(str(repo / "sub" / "file.py"))
    assert not hook.in_git_checkout(str(tmp_path / "elsewhere" / "file.py"))


def test_in_git_checkout_accepts_a_worktree_dot_git_file(hook, tmp_path):
    wt = tmp_path / "wt"
    wt.mkdir()
    (wt / ".git").write_text("gitdir: /somewhere")
    assert hook.in_git_checkout(str(wt / "a.py"))


def test_coordinator_write_rule(hook, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    assert not hook.write_allowed_for_coordinator(str(repo / "code.py"))
    assert hook.write_allowed_for_coordinator(str(repo / ".conductor" / "router" / "handoffs" / "router-005.md"))
    assert hook.write_allowed_for_coordinator(str(repo / "docs" / "HANDOFF.md"))
    assert hook.write_allowed_for_coordinator(str(repo / ".conductor" / "state.json"))
    assert hook.write_allowed_for_coordinator(str(tmp_path / "notes" / "scratch.md"))  # not a checkout


# --- transcript readers ---------------------------------------------------------------------

def test_last_turn_takes_the_last_main_thread_turn(hook, transcript):
    transcript.add(assistant(50_000), assistant(90_000, sidechain=True), assistant(60_000, model=OPUS))
    tokens, model, size = hook.last_turn(str(transcript.path))
    assert (tokens, model) == (60_000, OPUS) and size == transcript.size


def test_last_turn_sums_cache_tokens(hook, transcript):
    rec = assistant(0)
    rec["message"]["usage"] = {"input_tokens": 10, "cache_read_input_tokens": 200, "cache_creation_input_tokens": 3}
    transcript.add(rec)
    assert hook.last_turn(str(transcript.path))[0] == 213


def test_last_turn_unknown_is_none_not_zero(hook, transcript, tmp_path):
    assert hook.last_turn(str(transcript.path))[0] is None  # empty transcript
    transcript.add({"type": "user", "message": {"content": "hi"}})
    assert hook.last_turn(str(transcript.path))[0] is None  # no assistant turn yet
    assert hook.last_turn(str(tmp_path / "missing.jsonl")) == (None, None, 0)


def test_last_turn_survives_a_cut_first_line_in_the_tail(hook, transcript, monkeypatch):
    transcript.add(assistant(1_000), assistant(2_000))
    monkeypatch.setattr(hook, "TAIL_BYTES", transcript.size - 10)  # cuts the first record mid-line
    assert hook.last_turn(str(transcript.path))[0] == 2_000


def test_scan_title_newest_wins(hook, transcript):
    transcript.add(title_rec("first"), assistant(1), title_rec("second"))
    assert hook.scan_title(str(transcript.path))[0] == "second"
    assert hook.session_title(str(transcript.path)) == "second"


def test_scan_title_does_not_consume_a_partial_last_line(hook, transcript):
    transcript.add(title_rec("whole"))
    with transcript.path.open("ab") as fh:
        fh.write(b'{"type": "custom-title", "customTi')  # still being written
    title, offset = hook.scan_title(str(transcript.path))
    assert title == "whole"
    assert offset < transcript.size  # resumes before the unfinished line


def test_cached_title_reads_only_what_was_appended(hook, transcript):
    state: dict = {}
    transcript.add(title_rec("DOORS · A 1/1 · t"))
    assert hook.cached_title(str(transcript.path), state) == "DOORS · A 1/1 · t"
    first_offset = state["title_scan"]["offset"]
    transcript.add(assistant(10))
    assert hook.cached_title(str(transcript.path), state) == "DOORS · A 1/1 · t"  # remembered
    assert state["title_scan"]["offset"] > first_offset
    transcript.add(title_rec("ROUTER #5"))
    assert hook.cached_title(str(transcript.path), state) == "ROUTER #5"  # a retitle is seen


def test_cached_title_resets_when_the_file_shrinks(hook, transcript):
    state: dict = {}
    transcript.add(title_rec("old title"), assistant(1))
    hook.cached_title(str(transcript.path), state)
    transcript.path.write_bytes(b"")
    transcript.add(title_rec("new"))
    assert hook.cached_title(str(transcript.path), state) == "new"


def test_handoff_detection_by_tool(hook, transcript):
    start = transcript.size
    assert not hook.handoff_written_since(str(transcript.path), start)
    transcript.add(tool_use("Write", file_path="C:/r/.conductor/router/handoffs/router-005.md"))
    assert hook.handoff_written_since(str(transcript.path), start)


@pytest.mark.parametrize(
    "tool, inp, counts",
    [
        ("Bash", {"command": "git add .conductor/router/handoffs/router-005.md && git commit -m 'router handoff'"}, True),
        ("Bash", {"command": "cat notes > HANDOFF.md"}, True),
        ("PowerShell", {"command": "Set-Content -Path handoff-7.md -Value x"}, True),
        ("Bash", {"command": "ls .conductor/router/handoffs"}, False),  # mentions, does not write
        ("Bash", {"command": "grep -r handoff ."}, False),
        ("Write", {"file_path": "C:/r/src/app.py"}, False),
        ("Edit", {"file_path": "C:/r/HANDOFF.md"}, True),
        ("mcp__x__ArtifactData", {"collection": "tasks", "data": {"handoff": "text"}}, True),
        ("mcp__x__ArtifactData", {"collection": "tasks", "data": {"status": "ok"}}, False),
    ],
)
def test_handoff_detection_cases(hook, transcript, tool, inp, counts):
    start = transcript.size
    transcript.add(tool_use(tool, **inp))
    assert hook.handoff_written_since(str(transcript.path), start) is counts


def test_handoff_before_the_offset_does_not_count(hook, transcript):
    transcript.add(tool_use("Write", file_path="handoff-old.md"))
    start = transcript.size
    transcript.add(assistant(5))
    assert not hook.handoff_written_since(str(transcript.path), start)


def test_handoff_in_a_subagent_does_not_count(hook, transcript):
    start = transcript.size
    rec = tool_use("Write", file_path="handoff.md")
    rec["isSidechain"] = True
    transcript.add(rec)
    assert not hook.handoff_written_since(str(transcript.path), start)


# --- SessionStart ---------------------------------------------------------------------------

def banner_of(out):
    assert out["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    return out["hookSpecificOutput"]["additionalContext"]


def test_session_start_injects_the_banner(hook, transcript):
    transcript.add(title_rec("DOORS · G6 2/5 · topic"), assistant(4_000, model=HAIKU))
    text = banner_of(hook.handle(event("SessionStart", transcript, source="startup")))
    assert "THE WAY" in text and "DESK" in text and "DOORS" in text and "120k" in text


def test_session_start_on_an_empty_transcript_says_unfiled_and_unmeasured(hook, transcript):
    text = banner_of(hook.handle(event("SessionStart", transcript, source="startup")))
    assert "not filed" in text and "not measured yet" in text


def test_session_start_on_a_missing_transcript_does_not_raise(hook, tmp_path):
    out = hook.handle({"hook_event_name": "SessionStart", "session_id": "s", "transcript_path": str(tmp_path / "no.jsonl")})
    assert "THE WAY" in banner_of(out)


def test_compact_resets_what_was_crossed(hook, transcript, monkeypatch):
    monkeypatch.setenv("SESSION_SOFT_TOKENS", "1000")
    transcript.add(assistant(5_000))
    hook.handle(event("UserPromptSubmit", transcript))
    state = hook.load_state("sess-1")
    assert "soft_crossed_at" in state and state["last_warned"]
    hook.handle(event("SessionStart", transcript, source="compact"))
    state = hook.load_state("sess-1")
    assert "soft_crossed_at" not in state and "last_warned" not in state


# --- UserPromptSubmit / PostToolUse (the guard) ---------------------------------------------

@pytest.mark.parametrize("name", ["UserPromptSubmit", "PostToolUse"])
def test_guard_silent_below_the_cap_and_loud_above(hook, transcript, name):
    transcript.add(assistant(100_000))
    assert hook.handle(event(name, transcript)) is None
    transcript.add(assistant(320_000))
    out = hook.handle(event(name, transcript))
    assert out["hookSpecificOutput"]["hookEventName"] == name
    assert "CONTEXT BUDGET" in out["hookSpecificOutput"]["additionalContext"]


def test_guard_uses_the_haiku_cap(hook, transcript):
    transcript.add(assistant(125_000, model=HAIKU))
    assert "CONTEXT BUDGET" in hook.handle(event("PostToolUse", transcript))["hookSpecificOutput"]["additionalContext"]


def test_guard_does_not_nag_every_call(hook, transcript):
    transcript.add(assistant(320_000))
    assert hook.handle(event("PostToolUse", transcript)) is not None
    assert hook.handle(event("PostToolUse", transcript)) is None


def test_guard_unknown_size_is_silent_not_small(hook, transcript):
    assert hook.handle(event("UserPromptSubmit", transcript)) is None
    assert "tokens" not in hook.load_state("sess-1")  # nothing recorded as if measured


def test_guard_off_switch(hook, transcript, monkeypatch):
    monkeypatch.setenv("SESSION_GUARD_OFF", "1")
    transcript.add(assistant(900_000))
    assert hook.handle(event("UserPromptSubmit", transcript)) is None


def test_guard_records_the_crossing_offset(hook, transcript, monkeypatch):
    monkeypatch.setenv("SESSION_SOFT_TOKENS", "1000")
    size = transcript.add(assistant(5_000))
    hook.handle(event("PostToolUse", transcript))
    assert hook.load_state("sess-1")["soft_crossed_at"] == size


# --- Stop -----------------------------------------------------------------------------------

@pytest.fixture
def over_cap(transcript, monkeypatch):
    monkeypatch.setenv("SESSION_SOFT_TOKENS", "1000")
    monkeypatch.setenv("SESSION_HARD_TOKENS", "50000")
    transcript.add(assistant(5_000))
    return transcript


def test_stop_blocks_past_the_cap_with_no_handoff(hook, over_cap):
    out = hook.handle(event("Stop", over_cap))
    assert out["decision"] == "block" and "handoff" in out["reason"] and "5k" in out["reason"]
    assert hook.load_state("sess-1")["stops_blocked"] == 1


def test_stop_does_not_loop(hook, over_cap):
    assert hook.handle(event("Stop", over_cap, stop_hook_active=True)) is None


def test_stop_passes_after_a_handoff_written_since_crossing(hook, over_cap):
    hook.handle(event("UserPromptSubmit", over_cap))  # records the crossing
    over_cap.add(tool_use("Write", file_path="C:/r/.conductor/router/handoffs/router-009.md"))
    assert hook.handle(event("Stop", over_cap)) is None


def test_stop_ignores_a_handoff_from_before_the_crossing(hook, transcript, monkeypatch):
    monkeypatch.setenv("SESSION_SOFT_TOKENS", "1000")
    transcript.add(tool_use("Write", file_path="handoff-early.md"), assistant(300))
    hook.handle(event("UserPromptSubmit", transcript))  # below the cap: records nothing
    transcript.add(assistant(5_000))
    hook.handle(event("UserPromptSubmit", transcript))  # crosses here
    assert hook.handle(event("Stop", transcript))["decision"] == "block"


def test_stop_blocks_without_ever_seeing_the_crossing(hook, over_cap):
    """The first hook to see a session past the cap is Stop itself: it still has to ask."""
    assert hook.load_state("sess-1") == {}
    assert hook.handle(event("Stop", over_cap))["decision"] == "block"


def test_stop_below_the_cap_and_with_unknown_size_never_blocks(hook, transcript, monkeypatch):
    assert hook.handle(event("Stop", transcript)) is None  # unknown
    transcript.add(assistant(10_000))
    assert hook.handle(event("Stop", transcript)) is None  # known, small


def test_stop_off_switch(hook, over_cap, monkeypatch):
    monkeypatch.setenv("SESSION_GUARD_OFF", "1")
    assert hook.handle(event("Stop", over_cap)) is None


def test_hard_cap_needs_its_own_handoff(hook, transcript, monkeypatch):
    monkeypatch.setenv("SESSION_SOFT_TOKENS", "1000")
    monkeypatch.setenv("SESSION_HARD_TOKENS", "20000")
    transcript.add(assistant(5_000))
    hook.handle(event("UserPromptSubmit", transcript))
    transcript.add(tool_use("Write", file_path="handoff.md"))
    assert hook.handle(event("Stop", transcript)) is None  # soft satisfied
    transcript.add(assistant(25_000))
    hook.handle(event("UserPromptSubmit", transcript))  # crosses the hard cap
    out = hook.handle(event("Stop", transcript))
    assert out["decision"] == "block" and "hard cap" in out["reason"]


# --- PreToolUse -----------------------------------------------------------------------------

@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    (r / ".git").mkdir()
    return r


def pre(hook, transcript, tool, path, **extra):
    return hook.handle(event("PreToolUse", transcript, tool_name=tool, tool_input={"file_path": str(path)}, **extra))


@pytest.mark.parametrize("title", ["ROUTER #4", "ROUTER #7 · leadfuel-way", "CONDUCTOR · plan + task list"])
@pytest.mark.parametrize("tool", ["Edit", "Write", "MultiEdit"])
def test_coordinators_may_not_edit_inside_a_checkout(hook, transcript, repo, title, tool):
    transcript.add(title_rec(title))
    out = pre(hook, transcript, tool, repo / "src" / "app.py")
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "does no work" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_coordinators_may_write_handoffs_and_conductor_state(hook, transcript, repo):
    transcript.add(title_rec("ROUTER #4"))
    assert pre(hook, transcript, "Write", repo / ".conductor" / "router" / "handoffs" / "router-005.md") is None
    assert pre(hook, transcript, "Write", repo / ".conductor" / "project.json") is None


def test_coordinators_may_write_outside_a_checkout(hook, transcript, tmp_path):
    transcript.add(title_rec("CONDUCTOR · x"))
    assert pre(hook, transcript, "Write", tmp_path / "scratch" / "notes.md") is None


def test_desks_and_unfiled_sessions_are_not_blocked(hook, transcript, repo):
    for title in ("DOORS · G6 2/5 · topic", "ROUTER · WAY-1 1/1 · build", "just a title"):
        transcript.add(title_rec(title))
        assert pre(hook, transcript, "Edit", repo / "a.py") is None


def test_a_session_that_retitles_itself_is_judged_by_its_new_title(hook, transcript, repo):
    transcript.add(title_rec("DOORS · G6 1/1 · x"))
    assert pre(hook, transcript, "Edit", repo / "a.py") is None
    transcript.add(title_rec("ROUTER #9"))
    assert pre(hook, transcript, "Edit", repo / "a.py")["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_non_write_tools_are_never_denied(hook, transcript, repo):
    transcript.add(title_rec("ROUTER #4"))
    assert hook.handle(event("PreToolUse", transcript, tool_name="Bash", tool_input={"command": "ls"})) is None
    assert hook.handle(event("PreToolUse", transcript, tool_name="Read", tool_input={"file_path": str(repo / "a.py")})) is None


def test_notebook_edit_uses_notebook_path(hook, transcript, repo):
    transcript.add(title_rec("ROUTER #4"))
    out = hook.handle(event("PreToolUse", transcript, tool_name="NotebookEdit", tool_input={"notebook_path": str(repo / "n.ipynb")}))
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_role_rule_off_switch(hook, transcript, repo, monkeypatch):
    monkeypatch.setenv("WAY_ENFORCE_ROLES", "0")
    transcript.add(title_rec("ROUTER #4"))
    assert pre(hook, transcript, "Edit", repo / "a.py") is None


# --- state and the process ------------------------------------------------------------------

def test_every_event_is_counted(hook, transcript):
    for name in ("SessionStart", "UserPromptSubmit", "PostToolUse", "Stop", "PreToolUse"):
        hook.handle(event(name, transcript))
    assert hook.load_state("sess-1")["seen"] == {
        "SessionStart": 1, "UserPromptSubmit": 1, "PostToolUse": 1, "Stop": 1, "PreToolUse": 1,
    }


def test_unknown_events_are_harmless(hook, transcript):
    assert hook.handle(event("SomethingNew", transcript)) is None


def test_state_path_is_sanitised(hook, tmp_path):
    p = hook._state_path("../../evil/..\\id")
    assert p.parent == hook.state_dir() and ".." not in p.name and "/" not in p.name


def run_hook(stdin: str, tmp_path, **env):
    import os

    full = {**os.environ, "WAY_STATE_DIR": str(tmp_path / "proc-state"), **env}
    return subprocess.run([sys.executable, str(HOOK_PATH)], input=stdin, text=True, capture_output=True, env=full, timeout=30)


@pytest.mark.parametrize("stdin", ["", "not json", "[]", "null", "{}", '{"hook_event_name": 5}'])
def test_the_process_never_fails_on_garbage(tmp_path, stdin):
    done = run_hook(stdin, tmp_path)
    assert done.returncode == 0


def test_the_process_prints_json_the_harness_can_read(tmp_path, transcript):
    transcript.add(title_rec("DOORS · G6 2/5 · topic"))
    done = run_hook(json.dumps(event("SessionStart", transcript, source="startup")), tmp_path)
    assert done.returncode == 0
    out = json.loads(done.stdout)
    assert out["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "THE WAY" in out["hookSpecificOutput"]["additionalContext"]


def test_the_process_blocks_a_stop_over_the_cap(tmp_path, transcript):
    transcript.add(assistant(9_000))
    done = run_hook(json.dumps(event("Stop", transcript)), tmp_path, SESSION_SOFT_TOKENS="1000")
    assert json.loads(done.stdout)["decision"] == "block"
