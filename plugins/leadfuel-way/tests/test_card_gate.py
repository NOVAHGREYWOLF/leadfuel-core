"""The Stop card gate: a turn that ends on an owner ask in chat, with no card written, is sent back once.

Owner, 2026-11-01, card q9124 A. The gate blocks once per stop (the harness marks the retry, so it never loops),
at most three times a session, never for a turn a person started, never for a turn that wrote a card.
"""
from __future__ import annotations

import json

import pytest

from kit import SONNET, event

CROSS = "<cross-session-message from=\"local_x\">STATUS please</cross-session-message>"
ASK_TEXT = "Done with the build.\nSTATUS: NEEDS-NOVAH | NODE | no PR | needs your call on slot 07"


def user(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def said(text):
    return {"type": "assistant", "isSidechain": False,
            "message": {"model": SONNET, "usage": {"input_tokens": 10}, "content": [{"type": "text", "text": text}]}}


def wrote(name, **inp):
    return {"type": "assistant", "isSidechain": False,
            "message": {"model": SONNET, "usage": {"input_tokens": 10},
                        "content": [{"type": "tool_use", "id": "t", "name": name, "input": inp}]}}


def tool_result():
    return {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t", "content": "ok"}]}}


def test_a_machine_started_turn_that_ends_on_an_ask_is_blocked_once(hook, transcript):
    transcript.add(user(CROSS), said(ASK_TEXT))
    out = hook.handle(event("Stop", transcript))
    assert out["decision"] == "block" and "post_card.py" in out["reason"] and "q9124" in out["reason"]
    assert hook.load_state("sess-1")["card_stops_blocked"] == 1
    assert hook.handle(event("Stop", transcript, stop_hook_active=True)) is None  # the retry is never blocked


@pytest.mark.parametrize("text", ["ASK: NODE | which one? ", "> **ASK:** x", "  STATUS: NEEDS-NOVAH | a | b | c"])
def test_the_ask_markers_match_after_markdown_emphasis(hook, transcript, text):
    transcript.add(user(CROSS), said("intro\n" + text))
    assert hook.handle(event("Stop", transcript))["decision"] == "block"


@pytest.mark.parametrize("text", ["STATUS: DONE | NODE | pr | fine", "I will ask: later", "the task: do it", "STATUS: BLOCKED | x | y | z"])
def test_a_turn_without_an_owner_ask_is_not_blocked(hook, transcript, text):
    transcript.add(user(CROSS), said(text))
    assert hook.handle(event("Stop", transcript)) is None


def test_a_card_written_in_the_turn_passes(hook, transcript):
    transcript.add(user(CROSS), wrote("ArtifactData", action="set", collection="questions", doc_id="q9200", file_path="x.json"),
                   tool_result(), said(ASK_TEXT))
    assert hook.handle(event("Stop", transcript)) is None


def test_a_card_batch_written_through_the_mcp_name_passes(hook, transcript):
    transcript.add(user(CROSS), wrote("mcp__x__ArtifactData", action="batch", writes=[{"op": "set", "collection": "questions"}]),
                   tool_result(), said(ASK_TEXT))
    assert hook.handle(event("Stop", transcript)) is None


def test_an_artifact_read_is_not_a_card(hook, transcript):
    transcript.add(user(CROSS), wrote("ArtifactData", action="get", collection="questions", doc_id="q1"), tool_result(), said(ASK_TEXT))
    assert hook.handle(event("Stop", transcript))["decision"] == "block"


def test_a_card_from_an_earlier_turn_does_not_count(hook, transcript):
    transcript.add(user(CROSS), wrote("ArtifactData", action="set", collection="questions", doc_id="q1"), said("posted"),
                   user(CROSS), said(ASK_TEXT))
    assert hook.handle(event("Stop", transcript))["decision"] == "block"


def test_a_turn_a_person_started_is_never_blocked(hook, transcript):
    transcript.add(user("what do you need from me?"), said(ASK_TEXT))
    assert hook.handle(event("Stop", transcript)) is None


def test_a_scheduled_run_prompt_is_a_machine_prompt(hook, transcript):
    transcript.add(user("<system-reminder>x</system-reminder>\n[SCHEDULED TASK - AUTOMATED]"), said(ASK_TEXT))
    assert hook.handle(event("Stop", transcript))["decision"] == "block"


def test_it_blocks_at_most_three_times_a_session(hook, transcript):
    transcript.add(user(CROSS), said(ASK_TEXT))
    assert [bool(hook.handle(event("Stop", transcript))) for _ in range(4)] == [True, True, True, False]


def test_the_gate_can_be_switched_off(hook, transcript, monkeypatch):
    monkeypatch.setenv("WAY_CARD_GATE", "0")
    transcript.add(user(CROSS), said(ASK_TEXT))
    assert hook.handle(event("Stop", transcript)) is None


def test_roles_off_turns_the_gate_off_too(hook, transcript, monkeypatch):
    monkeypatch.setenv("WAY_ENFORCE_ROLES", "0")
    transcript.add(user(CROSS), said(ASK_TEXT))
    assert hook.handle(event("Stop", transcript)) is None


def test_an_unreadable_transcript_is_unknown_not_a_block(hook, tmp_path):
    assert hook.turn_asks_owner(str(tmp_path / "missing.jsonl")) is None


def test_a_transcript_with_no_user_record_is_unknown(hook, transcript):
    transcript.add(said(ASK_TEXT))
    assert hook.turn_asks_owner(str(transcript.path)) is None


def test_a_handoff_block_comes_first_and_the_gate_waits(hook, transcript, monkeypatch):
    monkeypatch.setenv("SESSION_SOFT_TOKENS", "1000")
    transcript.add(user(CROSS), {"type": "assistant", "isSidechain": False, "message": {
        "model": SONNET, "usage": {"input_tokens": 5000}, "content": [{"type": "text", "text": ASK_TEXT}]}})
    out = hook.handle(event("Stop", transcript))
    assert "handoff" in out["reason"] and not hook.load_state("sess-1").get("card_stops_blocked")
