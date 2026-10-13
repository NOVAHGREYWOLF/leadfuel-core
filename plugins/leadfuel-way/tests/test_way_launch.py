"""The launch skill (0.1.11, owner 2026-10-13: "when a session needs to create a new session this
should be automated. I shouldn't have to say yes.") and what it claims.

The skill is advice, and advice that overstates what was measured is how the estate got a "launcher"
that started sessions nobody could see. So these tests pin two things: the procedure names the pieces
it needs, and it does not claim anything the probes could not show.
"""
from __future__ import annotations

import re

import pytest

from kit import PLUGIN

REPO = PLUGIN.parents[1]
LAUNCH = (PLUGIN / "skills" / "launch" / "SKILL.md").read_text(encoding="utf-8")
DOC = (REPO / "docs" / "SLOT-LAUNCH.md").read_text(encoding="utf-8")
SKILL = {p.parent.name: p.read_text(encoding="utf-8") for p in (PLUGIN / "skills").glob("*/SKILL.md")}


def test_the_procedure_names_the_tools_and_the_slots():
    for needle in ("run_scheduled_task", "update_scheduled_task", "list_task_runs", "set_session_model",
                   "set_session_effort", "get_session", "list_scheduled_tasks", "way-slot-01", "way-slot-06"):
        assert needle in LAUNCH, needle


def test_the_slot_block_has_every_placeholder_and_the_self_check():
    block = re.search(r"## The slot block\n.*?```\n(.*?)```", LAUNCH, re.S).group(1)
    for needle in ("<slot id>", "<launcher id>", "<TITLE>", "<write actions>", "SLOT-NOT-BYPASS", "READY",
                   "GO", "bypassPermissions", "PowerShell", "mcp__ccd_session_mgmt__send_message",
                   "Never call move_sessions", "Never call archive_session on self"):
        assert needle in block, needle


def test_the_not_bypass_signal_is_a_line_in_the_transcript_not_a_send():
    """Measured 2026-10-13: a run in default mode cannot send a message (it needs a person's approval),
    so the first launch's SLOT-NOT-BYPASS never reached its launcher. The line has to be readable from
    the session's transcript."""
    block = re.search(r"## The slot block\n.*?```\n(.*?)```", LAUNCH, re.S).group(1)
    step2 = re.search(r"^2\. .*$", block, re.M).group(0)
    assert 'end your turn with the single line "SLOT-NOT-BYPASS' in step2 and "refused" in step2
    assert "send_message to" not in step2
    assert "list_events" in LAUNCH and "cannot send one" in LAUNCH


def test_the_skill_does_not_claim_what_was_not_measured():
    low = LAUNCH.lower()
    assert "notifyoncompletion" in low and "not verified" in low
    assert "do not design on it" in low
    # claude --bg was tested dead; the skill must say so, not offer it
    assert re.search(r"`claude --bg` is not a way", LAUNCH)
    # a run id is not proof of a working session
    assert "returning an id says a session began" in LAUNCH


def test_the_model_is_pinned_in_the_slot_file_and_effort_is_not_claimed_to_be():
    """Measured 2026-10-13: a `model:` frontmatter line in the slot's SKILL.md starts the run on that
    model; an `effort:` line is ignored. The procedure must pin the model on every launch (a stale line
    would be reused silently) and must not promise an effort pin."""
    step4 = re.search(r"^4\. \*\*Load and run it\.\*\*.*$", LAUNCH, re.M).group(0)
    assert "`model: <model_id>`" in step4 and "on every launch" in step4
    assert "Effort cannot be pinned this way" in step4
    limits = LAUNCH.split("## Limits")[1]
    assert "An `effort:` line is ignored" in limits
    assert "`model:` line in the slot's `SKILL.md` frontmatter sets the run's model" in limits
    assert "`model:` line" in DOC and "an `effort:` line is not" in DOC


def test_the_skill_says_a_slot_session_has_no_group_and_does_not_try_to_give_it_one():
    assert "No project group, ever" in LAUNCH
    assert "Never move or retitle another session" in LAUNCH


def test_the_owner_steps_are_named_as_the_owners():
    assert "Owner steps, once, that no session can do" in LAUNCH
    assert "Bypass" in LAUNCH


def test_a_chip_is_the_last_resort_and_must_be_announced():
    assert LAUNCH.index("3. **A launch slot (this skill)**") < LAUNCH.index("4. **A `spawn_task` chip**")
    assert "Say in the same message that it is a chip and why" in LAUNCH


@pytest.mark.parametrize("name", ["way", "router", "handoff", "desk", "conductor", "new-project"])
def test_every_skill_that_starts_or_is_started_points_at_the_launch_skill(name):
    assert "leadfuel-way:launch" in SKILL[name], name


def test_the_router_keeps_the_desk_agent_path_and_the_chip_fallback():
    opening = re.search(r"^## Opening a desk\n(.*?)(?=^## )", SKILL["router"], re.S | re.M).group(1)
    assert "background agent" in opening and "launch it into a slot" in opening.lower()
    assert "spawn_task" in opening and "Say in the same message that it is a chip and why" in opening


def test_the_handoff_skill_proves_a_slot_successor_without_a_group():
    text = SKILL["handoff"]
    assert "`scheduledTaskId` equal to its slot" in text and "Do not wait for a group" in text


def test_the_doc_separates_measured_from_trusted_from_unverified():
    for heading in ("## Measured on 2026-10-13", "## Taken on trust", "## Not verified", "## Owner steps"):
        assert heading in DOC, heading
    assert "notifyOnCompletion" in DOC.split("## Not verified")[1]


def test_the_doc_and_skill_carry_no_email_and_the_version_is_named():
    assert not re.search(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", LAUNCH + DOC, re.I)
    assert "0.1.11" in DOC and "0.1.11" in SKILL["router"]
