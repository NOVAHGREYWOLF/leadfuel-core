"""The Stop hook's ledger gate: a session that is finishing writes its one-page ledger doc first."""
from __future__ import annotations

import pytest

from kit import assistant, event, title_rec, tool_use

STATUS = "STATUS: DONE | LEDGER-2 | https://example.invalid/pull/1 | fake"
DOC = "F:/Claude Sessions/ledger/example/NODE/2026-10-01/LEDGER-2.md"


@pytest.fixture
def desk(transcript):
    transcript.add(title_rec("NODE · LEDGER-2 1/1 · topic"), assistant(5_000))
    return transcript


def test_blocks_once_a_finished_session_has_no_ledger_doc(hook, desk):
    desk.add(tool_use("SendMessage", to="ROUTER #7", message=STATUS))
    out = hook.handle(event("Stop", desk))
    assert out["decision"] == "block" and "ledger" in out["reason"]
    assert hook.handle(event("Stop", desk)) is None  # once per session, never a loop


def test_does_not_loop_on_the_harness_retry(hook, desk):
    desk.add(tool_use("SendMessage", to="r", message=STATUS))
    assert hook.handle(event("Stop", desk, stop_hook_active=True)) is None


def test_passes_when_the_doc_was_written(hook, desk):
    desk.add(tool_use("SendMessage", to="r", message=STATUS), tool_use("Write", file_path=DOC))
    assert hook.handle(event("Stop", desk)) is None


def test_passes_when_a_shell_command_wrote_the_doc(hook, desk):
    desk.add(tool_use("SendMessage", to="r", message=STATUS), tool_use("Bash", command=f'cat > "{DOC}" <<EOF'))
    assert hook.handle(event("Stop", desk)) is None


def test_reading_the_ledger_is_not_writing_it(hook, desk):
    desk.add(tool_use("SendMessage", to="r", message=STATUS), tool_use("Read", file_path=DOC),
             tool_use("Bash", command=f'cat "{DOC}"'))
    assert hook.handle(event("Stop", desk))["decision"] == "block"


def test_a_handoff_counts_as_finishing(hook, desk):
    desk.add(tool_use("Write", file_path="C:/r/.conductor/desks/handoffs/LEDGER-2-001.md"))
    assert hook.handle(event("Stop", desk))["decision"] == "block"


@pytest.mark.parametrize("message", ["STATUS: CONTINUING | T | no PR | still going", "hello", "ASK: T | q"])
def test_a_working_session_is_left_alone(hook, desk, message):
    desk.add(tool_use("SendMessage", to="r", message=message))
    assert hook.handle(event("Stop", desk)) is None


def test_an_untitled_session_is_left_alone(hook, transcript):
    """No role means no ledger identity (who is blank): unknown, so it asks nothing."""
    transcript.add(assistant(5_000), tool_use("SendMessage", to="r", message=STATUS))
    assert hook.handle(event("Stop", transcript)) is None


def test_off_switch(hook, desk, monkeypatch):
    monkeypatch.setenv("WAY_LEDGER", "0")
    desk.add(tool_use("SendMessage", to="r", message=STATUS))
    assert hook.handle(event("Stop", desk)) is None


def test_guard_off_switch_also_disables_it(hook, desk, monkeypatch):
    monkeypatch.setenv("SESSION_GUARD_OFF", "1")
    desk.add(tool_use("SendMessage", to="r", message=STATUS))
    assert hook.handle(event("Stop", desk)) is None


def test_the_handoff_gate_still_runs_after_the_ledger_ask(hook, transcript, monkeypatch):
    monkeypatch.setenv("SESSION_SOFT_TOKENS", "1000")
    transcript.add(title_rec("NODE · T 1/1 · x"), assistant(5_000), tool_use("SendMessage", to="r", message=STATUS), assistant(5_000))
    assert "ledger" in hook.handle(event("Stop", transcript))["reason"]
    out = hook.handle(event("Stop", transcript))
    assert out["decision"] == "block" and "handoff" in out["reason"]
