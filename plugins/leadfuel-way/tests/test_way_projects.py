"""Desks grouped by project (owner, 2026-10-07): "The sidebar group becomes the master project ...
The title becomes LANE · project part · n ... Existing sessions would move one at a time, never in
bulk."

What the hook must do about it, and must keep doing for the older forms while sessions migrate:
- read `LANE · <project part> · n` as a desk of LANE, and every older form exactly as before;
- judge a desk's successor by the desk's OWN group (its project), read from `get_session` on `self`,
  never by assuming the lane's group for a project-form title;
- refuse `move_sessions` that names more than one session;
- never move or retitle anything itself.
"""
from __future__ import annotations

import json
import re

import pytest

from kit import HOOK_PATH, PLUGIN, assistant, event, title_rec

OWNER_EXAMPLE = "INTELLIGENCE · world intel part · 3"  # the owner's own example, 2026-10-07


# --- reading the title ----------------------------------------------------------------------

@pytest.mark.parametrize(
    "title, expected",
    [
        (OWNER_EXAMPLE, ("DESK", "INTELLIGENCE")),
        ("SURFACE · shell · 1", ("DESK", "SURFACE")),
        ("NODE · router fixes · 2", ("DESK", "NODE")),     # a tier word inside the part is just a word
        ("NODE · ROUTER page · 2", ("DESK", "NODE")),
        ("ROUTER · world intel · 3", ("ROUTER", None)),     # a tier is never a desk, in any form
        ("CONDUCTOR · system build · 2", ("CONDUCTOR", None)),
        ("ROUTER #28 · one-interface", ("ROUTER", None)),
    ],
)
def test_role_of_the_project_form(hook, title, expected):
    assert hook.role_of(title) == expected


@pytest.mark.parametrize(
    "title, line",
    [
        (OWNER_EXAMPLE, ("part", "world intel part", 3)),
        ("SURFACE ·  photo   store upload  · 12", ("part", "photo store upload", 12)),
        ("SURFACE·shell·1", ("part", "shell", 1)),
        # The older forms read exactly as 0.1.7 read them.
        ("NODE · WAY-1 1/2 · build", ("task", "WAY-1", 1)),
        ("DOORS · G6 2/5 · topic", ("task", "G6", 2)),
        ("DOORS · topic", None),
        ("DOORS · topic, continued", None),
        ("DOORS · topic · x", None),
        ("DOORS ·  · 3", None),                               # no part
        ("doors · shell · 1", None),                          # a lane is upper case
        ("", None),
        (None, None),
    ],
)
def test_desk_line(hook, title, line):
    assert hook.desk_line(title) == line


@pytest.mark.parametrize("word", ["ROUTER", "CONDUCTOR"])
def test_the_project_pattern_cannot_match_a_tier(hook, word):
    assert hook.DESK_PART.match(f"{word} · world intel · 3") is None
    assert hook.DESK_PART.match(f"{word}-2 · world intel · 3") is None


def test_part_key_ignores_case_and_spacing_but_task_ids_stay_exact(hook):
    assert hook.part_key(("part", "World Intel", 1)) == hook.part_key(("part", "world intel", 9))
    assert hook.part_key(("task", "WAY-1", 1)) != hook.part_key(("task", "way-1", 1))


# --- the coordinator edit rule and the context guard do not care which desk form ------------

@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    (r / ".git").mkdir()
    return r


@pytest.mark.parametrize("title", [OWNER_EXAMPLE, "SURFACE · shell · 1", "NODE · router fixes · 2"])
def test_a_project_form_desk_keeps_its_edit_tools(hook, transcript, repo, title):
    transcript.add(title_rec(title))
    out = hook.handle(event("PreToolUse", transcript, tool_name="Edit", tool_input={"file_path": str(repo / "a.py")}))
    assert out is None


@pytest.mark.parametrize("title", ["ROUTER #28 · one-interface", "ROUTER · world intel · 3", "CONDUCTOR · system build"])
def test_coordinators_still_lose_them_whatever_follows(hook, transcript, repo, title):
    transcript.add(title_rec(title))
    out = hook.handle(event("PreToolUse", transcript, tool_name="Edit", tool_input={"file_path": str(repo / "a.py")}))
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.parametrize("title", [OWNER_EXAMPLE, "NODE · WAY-1 1/2 · build", "ROUTER #28", "CONDUCTOR · x", None])
def test_the_context_guard_and_stop_gate_read_the_model_not_the_title(hook, transcript, monkeypatch, title):
    """The guard's caps come from the model, so the new title form changes nothing there."""
    if title:
        transcript.add(title_rec(title))
    transcript.add(assistant(320_000))
    out = hook.handle(event("PostToolUse", transcript))
    assert "CONTEXT BUDGET" in out["hookSpecificOutput"]["additionalContext"] and "300k" in out["hookSpecificOutput"]["additionalContext"]
    assert hook.handle(event("Stop", transcript))["decision"] == "block"


# --- the banner -----------------------------------------------------------------------------

def test_banner_for_a_project_form_desk(hook):
    text = hook.banner("startup", OWNER_EXAMPLE, "DESK", "INTELLIGENCE", None, None, 300_000, 450_000)
    assert "world intel part" in text and "session 3" in text and "project's sidebar group" in text
    assert "not the INTELLIGENCE lane group" in text and "older desk form" not in text


@pytest.mark.parametrize("title", ["DOORS · G6 2/5 · topic", "DOORS · topic"])
def test_banner_for_an_older_form_desk_offers_self_migration_only(hook, title):
    text = hook.banner("startup", title, "DESK", "DOORS", None, None, 300_000, 450_000)
    assert "older desk form" in text and "still reads it" in text
    assert "only yourself" in text and "never in bulk" in text


def test_banner_for_an_unfiled_session_teaches_the_project_form(hook):
    text = hook.banner("startup", None, "UNFILED", None, None, None, 300_000, 450_000)
    assert "`LANE · <project part> · n`" in text and "PROJECT's sidebar group" in text
    assert "never its lane's" in text and "leadfuel-way:new-project" in text
    assert "`ROUTER #N · <project>`" in text and "`CONDUCTOR · topic`" in text


@pytest.mark.parametrize("role", ["ROUTER", "CONDUCTOR"])
def test_banner_for_a_tier_names_its_own_group(hook, role):
    text = hook.banner("startup", f"{role} · x", role, None, None, None, 300_000, 450_000)
    assert f"in the {role} sidebar group" in text


def test_session_start_reads_the_project_form(hook, transcript):
    transcript.add(title_rec(OWNER_EXAMPLE), assistant(4_000))
    out = hook.handle(event("SessionStart", transcript, source="startup"))
    text = out["hookSpecificOutput"]["additionalContext"]
    assert "DESK" in text and "INTELLIGENCE" in text and "world intel part" in text
    assert hook.load_state("sess-1")["lane"] == "INTELLIGENCE"


# --- the archive guard: a desk's group is its project ---------------------------------------

ARCHIVE = "mcp__ccd_session_mgmt__archive_session"
LIST = "mcp__ccd_session_mgmt__list_sessions"
GET = "mcp__ccd_session_mgmt__get_session"
_ids = iter(range(10_000))


def read(transcript, tool, inp, value, is_error=False):
    """Append a session-tool call and its result, the way the transcript records them."""
    tid = f"r{next(_ids)}"
    transcript.add(
        assistant(1, content=[{"type": "tool_use", "id": tid, "name": tool, "input": inp}]),
        {"type": "user", "isSidechain": False, "message": {"content": [
            {"type": "tool_result", "tool_use_id": tid, "is_error": is_error,
             "content": [{"type": "text", "text": json.dumps(value)}]}]}},
    )


def grp(name, gid=None):
    return {"id": gid if gid is not None else f"cg-{name.lower().replace(' ', '-')}", "name": name}


def row(title, group, archived=False):
    return {"sessionId": "local_next", "title": title, "isArchived": archived, "group": group}


def saw_self(transcript, title, group):
    read(transcript, GET, {"session_id": "self"}, row(title, group))


def saw_list(transcript, *rows):
    read(transcript, LIST, {"group": "x"}, list(rows))


def archive(hook, transcript):
    return hook.handle(event("PreToolUse", transcript, tool_name=ARCHIVE, tool_input={"session_id": "self"}))


def refused(out) -> bool:
    return bool(out) and out["hookSpecificOutput"]["permissionDecision"] == "deny"


WI = grp("world intel")


@pytest.mark.parametrize("successor, group", [
    ("INTELLIGENCE · world intel part · 4", WI),
    ("INTELLIGENCE · World Intel  part · 4", WI),        # case and spacing in the part do not matter
    ("INTELLIGENCE · world intel part · 6", WI),         # any later session of the part
    ("INTELLIGENCE · world intel part · 4", {"name": "World Intel"}),  # no ids: matched by name
])
def test_a_project_desk_may_archive_once_its_successor_is_live_in_its_own_group(hook, transcript, successor, group):
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_self(transcript, OWNER_EXAMPLE, WI if "id" in group else {"name": "world intel"})
    saw_list(transcript, row(successor, group))
    assert archive(hook, transcript) is None


def test_a_project_desk_that_never_read_itself_is_refused_and_told_how(hook, transcript):
    """Unknown is not a pass: the group is the project, and only `get_session` on `self` can name it."""
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_list(transcript, row("INTELLIGENCE · world intel part · 4", WI))
    out = archive(hook, transcript)
    assert refused(out)
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    assert "`get_session` with `self`" in reason and "STAY OPEN" in reason


def test_a_project_desk_never_falls_back_to_its_lane_group(hook, transcript):
    """The 0.1.7 rule (successor in the lane's group) must not quietly apply to the project form."""
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_list(transcript, row("INTELLIGENCE · world intel part · 4", grp("INTELLIGENCE")))
    assert refused(archive(hook, transcript))


@pytest.mark.parametrize("seen", [
    row("INTELLIGENCE · world intel part · 4", grp("INTELLIGENCE")),          # filed in the lane's group
    row("INTELLIGENCE · world intel part · 4", grp("reports")),               # another project
    row("INTELLIGENCE · world intel part · 4", grp("world intel", "cg-other")),  # same name, another group
    row("INTELLIGENCE · world intel part · 4", grp("ROUTER")),                # a tier group
    {"title": "INTELLIGENCE · world intel part · 4", "isArchived": False},    # group unknown
    row("INTELLIGENCE · world intel part · 4", WI, archived=True),            # already gone
    {"title": "INTELLIGENCE · world intel part · 4", "group": WI},            # archived unknown
    row("INTELLIGENCE · world intel part · 3", WI),                           # yourself
    row("INTELLIGENCE · world intel part · 2", WI),                           # your predecessor
    row("INTELLIGENCE · globe feeds · 4", WI),                                # another part
    row("SURFACE · world intel part · 4", WI),                                # another lane
    row("INTELLIGENCE · WI-3 4/4 · world intel", WI),                         # the older form: not provably the same line
    row("ROUTER #29 · world intel", WI),                                      # another tier
])
def test_what_does_not_count_as_a_project_desks_successor(hook, transcript, seen):
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_self(transcript, OWNER_EXAMPLE, WI)
    saw_list(transcript, seen)
    assert refused(archive(hook, transcript))


def test_your_own_row_never_counts_as_your_successor(hook, transcript):
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_self(transcript, "INTELLIGENCE · world intel part · 4", WI)  # e.g. read before a retitle
    assert refused(archive(hook, transcript))


def test_only_a_read_of_self_names_your_group(hook, transcript):
    """A get_session on some id is another session's row, even when it carries your title."""
    transcript.add(title_rec(OWNER_EXAMPLE))
    read(transcript, GET, {"session_id": "local_someone"}, row(OWNER_EXAMPLE, WI))
    saw_list(transcript, row("INTELLIGENCE · world intel part · 4", WI))
    assert refused(archive(hook, transcript))


def test_an_errored_self_read_names_nothing(hook, transcript):
    transcript.add(title_rec(OWNER_EXAMPLE))
    read(transcript, GET, {"session_id": "self"}, row(OWNER_EXAMPLE, WI), is_error=True)
    saw_list(transcript, row("INTELLIGENCE · world intel part · 4", WI))
    assert refused(archive(hook, transcript))


def test_the_newest_self_read_wins(hook, transcript):
    """A session the owner moved reads itself again: the guard follows the newest read."""
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_self(transcript, OWNER_EXAMPLE, grp("INTELLIGENCE"))
    saw_self(transcript, OWNER_EXAMPLE, WI)
    saw_list(transcript, row("INTELLIGENCE · world intel part · 4", WI))
    assert archive(hook, transcript) is None


def test_a_self_read_with_no_group_is_unknown_not_ungrouped(hook, transcript):
    transcript.add(title_rec(OWNER_EXAMPLE))
    read(transcript, GET, {"session_id": "self"}, {"title": OWNER_EXAMPLE, "isArchived": False})
    saw_list(transcript, row("INTELLIGENCE · world intel part · 4", WI))
    assert refused(archive(hook, transcript))


def test_sessions_seen_marks_only_the_self_read(hook, transcript):
    saw_self(transcript, OWNER_EXAMPLE, WI)
    read(transcript, GET, {"session_id": "local_x"}, row("A · b · 1", WI))
    saw_list(transcript, {**row("A · b · 2", WI), "_self": True})  # a field of that name in tool output
    rows = hook.sessions_seen(str(transcript.path))
    assert [r["_self"] for r in rows] == [True, False, False]


# --- the archive guard: the older forms keep working while sessions migrate ------------------

@pytest.mark.parametrize("own, successor, group", [
    ("NODE · WAY-1 1/2 · build", "NODE · WAY-1 2/2 · build", "NODE"),
    ("DOORS · topic", "DOORS · topic, continued", "DOORS"),
])
def test_an_older_form_desk_that_never_read_itself_keeps_the_0_1_7_rule(hook, transcript, own, successor, group):
    transcript.add(title_rec(own))
    saw_list(transcript, row(successor, grp(group)))
    assert archive(hook, transcript) is None


def test_an_older_form_desk_that_read_itself_in_its_lane_group(hook, transcript):
    transcript.add(title_rec("NODE · WAY-1 1/2 · build"))
    saw_self(transcript, "NODE · WAY-1 1/2 · build", grp("NODE"))
    saw_list(transcript, row("NODE · WAY-1 2/2 · build", grp("NODE")))
    assert archive(hook, transcript) is None


def test_an_older_form_desk_the_owner_moved_into_a_project_group(hook, transcript):
    """Its own group, once read, is the rule: the successor must be beside it, not in the lane group."""
    transcript.add(title_rec("NODE · WAY-1 1/2 · build"))
    saw_self(transcript, "NODE · WAY-1 1/2 · build", grp("way"))
    saw_list(transcript, row("NODE · WAY-1 2/2 · build", grp("NODE")))
    assert refused(archive(hook, transcript))
    saw_list(transcript, row("NODE · WAY-1 2/2 · build", grp("way")))
    assert archive(hook, transcript) is None


def test_an_older_form_desk_whose_successor_took_the_project_form_is_left_to_its_router(hook, transcript):
    transcript.add(title_rec("NODE · WAY-1 1/2 · build"))
    saw_list(transcript, row("NODE · way plugin · 2", grp("NODE")), row("NODE · way plugin · 2", grp("way")))
    assert refused(archive(hook, transcript))


@pytest.mark.parametrize("own, successor, group", [
    ("ROUTER #9", "ROUTER #10", "ROUTER"),
    ("ROUTER #27 · one-interface", "ROUTER #28 · one-interface", "ROUTER"),
    ("CONDUCTOR · system build", "CONDUCTOR · system build 2", "CONDUCTOR"),
])
def test_the_tiers_keep_their_own_groups(hook, transcript, own, successor, group):
    """A self read (the way now tells every desk to make one) changes nothing for a tier."""
    transcript.add(title_rec(own))
    saw_self(transcript, own, grp(group))
    saw_list(transcript, row(successor, grp("world intel")))
    assert refused(archive(hook, transcript))  # a router's successor is never in a project group
    saw_list(transcript, row(successor, grp(group)))
    assert archive(hook, transcript) is None


# --- one at a time, never in bulk -------------------------------------------------------------

MOVE = "mcp__ccd_sidebar__move_sessions"


def move(hook, transcript, ids, tool=MOVE, **extra):
    return hook.handle(event("PreToolUse", transcript, tool_name=tool,
                             tool_input={"session_ids": ids, "group_id": "cg-world-intel"}, **extra))


@pytest.mark.parametrize("ids", [["self"], ["local_a"], ["self", "self"], [], ["local_a", ""]])
def test_moving_one_session_is_allowed(hook, transcript, ids):
    transcript.add(title_rec("ROUTER #28 · one-interface"))
    assert move(hook, transcript, ids) is None


@pytest.mark.parametrize("title", ["ROUTER #28 · one-interface", "CONDUCTOR · x", OWNER_EXAMPLE, "NODE · WAY-1 1/1 · x", None])
@pytest.mark.parametrize("ids", [["local_a", "local_b"], ["self", "local_a"], [f"local_{i}" for i in range(40)]])
def test_moving_several_sessions_at_once_is_refused_for_everyone(hook, transcript, title, ids):
    if title:
        transcript.add(title_rec(title))
    out = move(hook, transcript, ids)
    assert refused(out)
    assert "one at a time, never in bulk" in out["hookSpecificOutput"]["permissionDecisionReason"]
    assert hook.load_state("sess-1")["bulk_moves_refused"] == 1


def test_a_background_agent_is_refused_a_bulk_move_too(hook, transcript):
    transcript.add(title_rec("ROUTER #28 · one-interface"))
    out = move(hook, transcript, ["local_a", "local_b"], agent_id="a1")
    assert refused(out) and "never in bulk" in out["hookSpecificOutput"]["permissionDecisionReason"]
    assert "bulk_moves_refused" not in hook.load_state("sess-1")  # an agent's tally is its own


def test_the_remote_move_tool_is_covered(hook, transcript):
    assert refused(move(hook, transcript, ["a", "b"], tool="mcp__claude-code-remote__move_sessions"))


def test_the_bulk_rule_has_the_role_switch(hook, transcript, monkeypatch):
    monkeypatch.setenv("WAY_ENFORCE_ROLES", "0")
    assert move(hook, transcript, ["local_a", "local_b"]) is None


@pytest.mark.parametrize("inp", ["not a dict", None, {"session_ids": "local_a,local_b"}, {"session_ids": None}])
def test_a_strange_move_input_is_left_alone(hook, transcript, inp):
    assert hook.handle(event("PreToolUse", transcript, tool_name=MOVE, tool_input=inp)) is None


def test_the_hook_registration_reaches_move_sessions():
    cfg = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    matcher = cfg["hooks"]["PreToolUse"][1]["matcher"]
    for tool in (MOVE, "mcp__claude-code-remote__move_sessions"):
        assert re.fullmatch(matcher, tool), tool


def test_the_hook_never_moves_or_retitles_anything_itself():
    """It only answers PreToolUse; no shipped script or hook output asks the app to move a session."""
    for p in [HOOK_PATH, *sorted((PLUGIN / "scripts").glob("*.py"))]:
        src = p.read_text(encoding="utf-8")
        assert not re.search(r"(move_sessions|set_session_title|create_group)\s*\(", src), p.name


# --- the skills say the same thing ----------------------------------------------------------

SKILL = {name: (PLUGIN / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
         for name in ("way", "desk", "router", "handoff", "new-project", "conductor")}
NEW_FORM = "`LANE · <project part> · n`"


@pytest.mark.parametrize("name", ["way", "desk", "router", "handoff"])
def test_the_desk_title_skills_teach_the_project_form(name):
    assert NEW_FORM in SKILL[name], name


# The 0.1.7 wording that filed a desk by its lane. It must not come back in any skill.
OLD_FILING = re.compile(
    r"group named by the lane|live in the lane's group|filed in its lane's group|One group per desk lane"
    r"|sidebar group of that name|in that lane's group",
    re.I,
)


@pytest.mark.parametrize("name", sorted(SKILL))
def test_no_skill_files_a_desk_by_its_lane(name):
    assert not OLD_FILING.search(SKILL[name]), (name, OLD_FILING.search(SKILL[name]).group(0))


def test_new_project_creates_the_project_group_and_records_it():
    text = SKILL["new-project"]
    assert "create_group" in text and "list_groups" in text and "`group`" in text
    assert "never" in text.lower() and "lane's group" in text


def test_the_router_files_each_desk_in_its_project_group_one_at_a_time():
    text = SKILL["router"]
    opening = re.search(r"^## Opening a desk\n(.*?)(?=^## )", text, re.S | re.M).group(1)
    assert "list_groups" in opening and "leadfuel-way:new-project" in opening
    assert "project's group" in opening and "one session per call" in opening
    assert "never file the desk in its lane's group" in opening.lower()


@pytest.mark.parametrize("name", ["way", "router", "new-project", "conductor"])
def test_migration_is_one_at_a_time(name):
    low = SKILL[name].lower()
    assert "one at a time" in low and "never in bulk" in low, name


def test_the_older_forms_are_still_named_as_accepted():
    assert "`LANE · <task id> n/m · topic`" in SKILL["way"] and "still" in SKILL["way"]
