"""The launcher (0.1.12, owner pick 264, 2026-10-14): a slot run cannot run or update a scheduled task, so
every session asks one standing regular session to launch. The hook half is tested against synthetic
transcripts; the skill and doc half is pinned so they cannot overclaim.

Measured by conductor 037 and taken on trust here (nothing in these tests re-measures the app): a slot
run's `update_scheduled_task` is refused, its `run_scheduled_task` is refused in every state, and a slot
task's title must differ from the session title it sets.
"""
from __future__ import annotations

import re

import pytest

from kit import PLUGIN, assistant, event, title_rec, tool_use

REPO = PLUGIN.parents[1]
LAUNCH = (PLUGIN / "skills" / "launch" / "SKILL.md").read_text(encoding="utf-8")
DOC = (REPO / "docs" / "SLOT-LAUNCH.md").read_text(encoding="utf-8")
SKILL = {p.parent.name: p.read_text(encoding="utf-8") for p in (PLUGIN / "skills").glob("*/SKILL.md")}

SLOT_FIRST = {"type": "user", "message": {"role": "user", "content": [
    {"type": "text", "text": "brief...\nYou were launched into a way slot (way-slot-02) by session local_x for session local_y. First..."}]}}
PLAIN_FIRST = {"type": "user", "message": {"role": "user", "content": "do the task"}}
RUN = "mcp__scheduled-tasks__run_scheduled_task"
UPDATE = "mcp__scheduled-tasks__update_scheduled_task"
SEND = "mcp__ccd_session_mgmt__send_message"


def pre(transcript, tool, **inp):
    return event("PreToolUse", transcript, tool_name=tool, tool_input=inp)


def denied(out):
    return bool(out) and out["hookSpecificOutput"].get("permissionDecision") == "deny"


@pytest.mark.parametrize("tool", [RUN, UPDATE])
def test_a_slot_run_may_not_run_or_update_a_scheduled_task_and_is_told_to_ask(hook, transcript, tool):
    transcript.add(SLOT_FIRST, title_rec("ROUTER #55 · one-interface"), assistant(5000))
    out = hook.handle(pre(transcript, tool, taskId="way-slot-03"))
    assert denied(out)
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    assert "LAUNCH-REQUEST" in reason and "Ask the launcher" in reason


@pytest.mark.parametrize("tool", [RUN, UPDATE])
def test_a_regular_session_is_not_stopped_from_launching(hook, transcript, tool):
    """The hook cannot tell a regular session from a launcher, and a regular session with no launcher
    live still runs the steps itself: only a slot run is refused."""
    transcript.add(PLAIN_FIRST, title_rec("ROUTER #55 · one-interface"), assistant(5000))
    assert not denied(hook.handle(pre(transcript, tool, taskId="way-slot-03")))


def test_the_marker_is_read_from_the_first_user_message_only(hook, transcript):
    """A session that merely quotes the phrase later (a desk reading the doc) is not a slot run."""
    quote = {"type": "user", "message": {"role": "user", "content": "launched into a way slot (way-slot-02)"}}
    transcript.add(PLAIN_FIRST, assistant(5000), quote)
    assert not denied(hook.handle(pre(transcript, RUN, taskId="way-slot-03")))


def test_the_slot_marker_survives_a_transcript_longer_than_the_tail(hook, transcript):
    transcript.add(SLOT_FIRST, title_rec("ROUTER #55 · one-interface"))
    filler = assistant(5000, content=[{"type": "text", "text": "x" * 200_000}])
    for _ in range(5):  # 1 MB, so the first message is outside the 768 KB tail
        transcript.add(filler)
    assert denied(hook.handle(pre(transcript, UPDATE, taskId="way-slot-03")))


def test_roles_off_switch_disables_the_refusal(hook, transcript, monkeypatch):
    monkeypatch.setenv("WAY_ENFORCE_ROLES", "0")
    transcript.add(SLOT_FIRST, assistant(5000))
    assert not denied(hook.handle(pre(transcript, RUN, taskId="way-slot-03")))


def handoff_write(path=".conductor/router/handoffs/router-055.md"):
    return tool_use("Write", file_path=path)


def stop(transcript, **extra):
    return hook_event("Stop", transcript, **extra)


def hook_event(name, transcript, **extra):
    return event(name, transcript, **extra)


def test_a_slot_run_router_that_hands_off_without_asking_is_sent_back_once(hook, transcript):
    transcript.add(SLOT_FIRST, title_rec("ROUTER #55 · one-interface"), assistant(5000), handoff_write())
    out = hook.handle(stop(transcript))
    assert out and out["decision"] == "block"
    assert "LAUNCH-REQUEST" in out["reason"] and "Do not archive" in out["reason"]
    # the harness marks the retry: never block twice in one stop
    assert hook.handle(stop(transcript, stop_hook_active=True)) is None


def test_asking_the_launcher_satisfies_the_gate(hook, transcript):
    ask = tool_use(SEND, session_id="local_launcher", message="LAUNCH-REQUEST\nrequester: local_y\ntitle: ROUTER #56 · one-interface")
    transcript.add(SLOT_FIRST, title_rec("ROUTER #55 · one-interface"), assistant(5000), handoff_write(), ask)
    assert hook.handle(stop(transcript)) is None


def test_a_message_that_only_mentions_the_word_does_not_count_as_asking(hook, transcript):
    chatter = tool_use(SEND, session_id="local_y", message="I will send a LAUNCH-REQUEST later")
    transcript.add(SLOT_FIRST, title_rec("CONDUCTOR · automation"), assistant(5000), handoff_write(), chatter)
    assert hook.handle(stop(transcript))["decision"] == "block"


def test_a_slot_run_desk_is_not_gated_because_its_router_opens_its_successor(hook, transcript):
    transcript.add(SLOT_FIRST, title_rec("NODE · full system automation part · 4"), assistant(5000),
                   handoff_write(".conductor/desks/handoffs/X-001.md"))
    assert hook.handle(stop(transcript)) is None


def test_no_handoff_written_means_no_gate(hook, transcript):
    transcript.add(SLOT_FIRST, title_rec("ROUTER #55 · one-interface"), assistant(5000))
    assert hook.handle(stop(transcript)) is None


def test_a_router_that_was_not_launched_into_a_slot_is_not_gated(hook, transcript):
    transcript.add(PLAIN_FIRST, title_rec("ROUTER #55 · one-interface"), assistant(5000), handoff_write())
    assert hook.handle(stop(transcript)) is None


def test_the_gate_gives_up_after_three_blocks(hook, transcript):
    transcript.add(SLOT_FIRST, title_rec("ROUTER #55 · one-interface"), assistant(5000), handoff_write())
    results = [hook.handle(stop(transcript)) for _ in range(5)]
    assert sum(1 for r in results if r) == 3


def test_the_hook_registers_the_two_scheduled_task_tools_on_the_session_tool_matcher():
    import json
    cfg = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    matcher = cfg["hooks"]["PreToolUse"][1]["matcher"]
    for tool in (RUN, UPDATE, "mcp__ccd_session_mgmt__archive_session"):
        assert re.search(matcher, tool), tool
    assert not re.search(matcher, "mcp__scheduled-tasks__list_scheduled_tasks")
    assert not re.search(matcher, "mcp__scheduled-tasks__list_task_runs")


# --- the skill and the doc ------------------------------------------------------------------

def test_the_launch_skill_records_the_rule_the_request_and_the_launcher():
    for needle in ("## Ask the launcher", "## If you are the launcher", "LAUNCH-REQUEST", "LAUNCHED", "LAUNCH-FAILED",
                   "never call `run_scheduled_task` or `update_scheduled_task` themselves", "clear_session",
                   "slot NN | <TITLE>", "`GO` comes from the launcher", "SLOT-NOT-BYPASS", "no-free-slot"):
        assert needle in LAUNCH, needle


def test_the_three_walls_are_recorded_and_marked_as_taken_on_trust():
    block = LAUNCH.split("## Ask the launcher")[1].split("## What a slot is")[0]
    assert "not re-verified by this desk" in block
    for needle in ("update_scheduled_task", "must differ", "Run it from a regular session instead"):
        assert needle in block, needle
    doc = DOC.split("## Three walls")[1].split("## The launcher session")[0]
    assert "taken on trust" in DOC and "Run it from a regular session instead" in doc


def test_the_task_title_can_never_equal_the_session_title():
    step4 = re.search(r"^4\. \*\*Load and run it\.\*\*.*$", LAUNCH, re.M).group(0)
    assert "`slot NN | <TITLE>`" in step4 and "must never be equal" in step4
    assert "The launcher never creates a task" in LAUNCH


def test_the_slot_block_names_the_go_sender_and_the_report_target_separately():
    block = re.search(r"## The slot block\n.*?```\n(.*?)```", LAUNCH, re.S).group(1)
    assert "<launcher id>" in block and "<requester id>" in block
    assert re.search(r"message from <launcher id> begins with GO", block)
    assert "Report to <requester id>" in block
    assert "Never call run_scheduled_task or update_scheduled_task" in block
    # the marker the hook looks for is exactly the block's first sentence
    assert "You were launched into a way slot (<slot id>)" in block


def test_the_marker_the_hook_reads_matches_the_slot_block(hook):
    block = re.search(r"## The slot block\n.*?```\n(.*?)```", LAUNCH, re.S).group(1)
    filled = block.replace("<slot id>", "way-slot-04").replace("<launcher id>", "local_a").replace("<requester id>", "local_b")
    assert hook.SLOT_RUN.search(filled).group(1) == "way-slot-04"


@pytest.mark.parametrize("name", ["handoff", "router", "conductor", "way", "desk"])
def test_every_skill_where_successors_are_launched_says_to_ask_the_launcher(name):
    text = SKILL[name]
    assert "Ask the launcher" in text or "asking the launcher" in text or "ask the launcher" in text, name


def test_nobody_archives_on_a_launched_reply_alone():
    for name in ("handoff", "way"):
        assert "launcher's reply alone" in SKILL[name] or "`LAUNCHED` reply" in SKILL[name], name
    assert "Do not archive yourself on the strength of `LAUNCHED` alone" in LAUNCH


def test_the_launcher_design_answers_model_permission_rotation_and_creation_honestly():
    sec = DOC.split("## The launcher session")[1].split("## A stop for the walls")[0]
    for needle in ("**Model.**", "Sonnet", "**Permission.**", "Bypass", "**Rotation.**", "clear_session",
                   "**Can a session create it without the owner? No.**", "one paste", "Unverified"):
        assert needle in sec, needle
    # nothing claims the launcher was started or that an unattended update was seen to work
    assert "was started" not in sec and "Not measured on either model yet" in sec


def test_the_version_is_bumped_and_the_hook_says_so(hook):
    # 0.1.12 introduced the launcher; later bumps (0.1.13, wake) keep it, so this is a floor, not an equality
    assert tuple(int(x) for x in hook.VERSION.split(".")) >= (0, 1, 12)
    assert "0.1.12" in (PLUGIN / "README.md").read_text(encoding="utf-8")


def test_no_email_in_the_new_text():
    assert not re.search(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", LAUNCH + DOC, re.I)
