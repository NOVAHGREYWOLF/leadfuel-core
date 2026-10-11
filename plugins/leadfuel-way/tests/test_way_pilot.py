"""Tests for scripts/way_pilot.py's analyzer. The streams mirror the record shapes `claude -p
--output-format stream-json --verbose --include-hook-events` really emitted (one was captured with the
CLI logged out, which is the case that matters: a failed run must not read as a pass)."""
from __future__ import annotations

import json

import pytest

from kit import PLUGIN, load_module

BANNER = "THE WAY (leadfuel-way plugin 0.1.0; this banner proves its hooks are live).\nTitle: None. Role: UNFILED."
GUARD = "CONTEXT BUDGET: ~18k tokens (handoff point 5k, hard cap 1000k). Finish the step."
REASON = "THE WAY: this session is at ~18k tokens. Run the `leadfuel-way:handoff` skill now."


@pytest.fixture(scope="module")
def pilot():
    return load_module(PLUGIN / "scripts" / "way_pilot.py", "way_pilot_under_test")


def hook(event, payload=None, outcome="success"):
    out = json.dumps(payload) + "\r\n" if payload else ""
    return {"type": "system", "subtype": "hook_response", "hook_event": event, "hook_name": event,
            "output": out, "stdout": out, "stderr": "", "exit_code": 0, "outcome": outcome}


def ctx(event, text):
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}


def asst(*blocks, model="claude-haiku-4-5-20251001"):
    return {"type": "assistant", "message": {"model": model, "content": list(blocks)}}


def tool(name, **inp):
    return {"type": "tool_use", "id": "t", "name": name, "input": inp}


AUTH_FAIL = [
    hook("SessionStart", ctx("SessionStart", BANNER)),
    hook("UserPromptSubmit"),
    {"type": "assistant", "error": "authentication_failed", "is_api_error_message": True,
     "message": {"model": "<synthetic>", "content": []}},
    {"type": "result", "is_error": True, "result": "Failed to authenticate: OAuth session expired and could not be refreshed"},
]

FULL = [
    hook("SessionStart", ctx("SessionStart", BANNER)),
    hook("UserPromptSubmit"),
    asst(tool("Bash", command="git log --oneline")),
    hook("PostToolUse", ctx("PostToolUse", GUARD)),
    asst(tool("Write", file_path="notes.txt")),
    hook("Stop", {"decision": "block", "reason": REASON}, outcome="blocking"),
    asst(tool("Write", file_path=".conductor/desks/handoffs/PILOT-001.md")),
    hook("Stop"),
    {"type": "result", "is_error": False, "result": "done"},
]


def verdicts(pilot, stream):
    return [s for _, s, _ in pilot.analyze(json.dumps(r) for r in stream)]


def test_a_complete_run_is_all_ok(pilot):
    assert verdicts(pilot, FULL) == ["OK", "OK", "OK"]


def test_a_logged_out_run_proves_the_banner_and_nothing_else(pilot):
    """The real pilot of 2026-10-02: the hook ran, the model call failed. The rest is UNKNOWN, not OK."""
    results = pilot.analyze(json.dumps(r) for r in AUTH_FAIL)
    assert [s for _, s, _ in results] == ["OK", "UNKNOWN", "UNKNOWN"]
    assert "authentication_failed" in results[1][2]


def test_the_banner_evidence_is_the_first_line_of_the_text_the_model_got(pilot):
    [(_, _, evidence), *_] = pilot.analyze(json.dumps(r) for r in FULL)
    assert evidence.startswith("THE WAY (leadfuel-way plugin 0.1.0")


def test_no_hook_events_at_all_is_unknown_not_fail_or_ok(pilot):
    assert verdicts(pilot, [AUTH_FAIL[2], AUTH_FAIL[3]])[0] == "UNKNOWN"


def test_hooks_that_ran_without_the_banner_are_a_failure(pilot):
    assert verdicts(pilot, [hook("SessionStart"), *FULL[1:]])[0] == "FAIL"


def test_a_model_that_ran_past_the_cap_with_a_silent_guard_is_a_failure(pilot):
    silent = [r for r in FULL if not (r.get("hook_event") == "PostToolUse")]
    assert verdicts(pilot, silent)[1] == "FAIL"


def test_a_model_that_ran_and_was_never_stopped_is_a_failure(pilot):
    no_stop = [r for r in FULL if r.get("hook_event") != "Stop"][:-2]  # also drop the handoff write
    assert verdicts(pilot, no_stop)[2] == "FAIL"


def test_a_block_that_no_handoff_followed_is_a_failure(pilot):
    stream = [r for r in FULL if "handoffs" not in json.dumps(r)]
    assert verdicts(pilot, stream)[2] == "FAIL"


def test_a_handoff_written_before_the_block_does_not_count(pilot):
    early = [FULL[0], FULL[1], asst(tool("Write", file_path="handoff-early.md")), FULL[3], FULL[5]]
    assert verdicts(pilot, early)[2] == "FAIL"


def test_a_shell_handoff_commit_counts(pilot):
    stream = [*FULL[:6], asst(tool("Bash", command="git add handoff-1.md && git commit -m handoff")), FULL[7]]
    assert verdicts(pilot, stream)[2] == "OK"


def test_a_shell_that_only_mentions_handoff_does_not_count(pilot):
    stream = [*FULL[:6], asst(tool("Bash", command="ls handoffs")), FULL[7]]
    assert verdicts(pilot, stream)[2] == "FAIL"


def test_garbage_lines_are_skipped(pilot):
    lines = ["", "not json", "[1, 2]", *(json.dumps(r) for r in FULL)]
    assert [s for _, s, _ in pilot.analyze(lines)] == ["OK", "OK", "OK"]


def test_exit_codes(pilot, tmp_path):
    ok, unknown = tmp_path / "ok.jsonl", tmp_path / "unknown.jsonl"
    ok.write_text("\n".join(json.dumps(r) for r in FULL), encoding="utf-8")
    unknown.write_text("\n".join(json.dumps(r) for r in AUTH_FAIL), encoding="utf-8")
    assert pilot.main(["--analyze", str(ok)]) == 0
    assert pilot.main(["--analyze", str(unknown)]) == 2
