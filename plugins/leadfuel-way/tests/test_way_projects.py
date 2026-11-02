"""Desks grouped by project (owner, 2026-10-07): "The sidebar group becomes the master project ...
The title becomes LANE · project part · n ... Existing sessions would move one at a time, never in
bulk."

What the hook must do about it, and must keep doing for the older forms while sessions migrate:
- read `LANE · <project> part · n` (the owner's wording, card q346 = B) as a desk of LANE, and every
  other form exactly as before, the 0.1.8 `LANE · <project part> · n` with a free-text part included;
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
        ("SURFACE · one-interface part · 1", ("part", "one-interface part", 1)),
        ("SURFACE · shell · 1", ("part", "shell", 1)),         # the 0.1.8 free-text part is still read
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

def banner_line_2(text: str) -> str:
    """The banner's second line, where the title is explained. Line 1 quotes the whole title, so a check
    on the whole text would pass whatever the explanation says."""
    return next(l for l in text.splitlines() if l.startswith("2. "))


def test_banner_for_a_project_form_desk(hook):
    text = hook.banner("startup", OWNER_EXAMPLE, "DESK", "INTELLIGENCE", None, None, 300_000, 450_000)
    line = banner_line_2(text)
    assert "lane INTELLIGENCE" in line and "project 'world intel'" in line and "session 3" in line
    assert "project's sidebar group" in line and "not the INTELLIGENCE lane group" in line
    assert "world intel part" not in line  # the project is named; the word `part` is not part of its name
    assert "older desk form" not in text


def test_banner_names_the_project_not_the_word_part(hook):
    """The title carries the project's name and the word `part`; the banner must name the project only."""
    text = hook.banner("startup", "SURFACE · one-interface part · 1", "DESK", "SURFACE", None, None, 300_000, 450_000)
    line = banner_line_2(text)
    assert "project 'one-interface'" in line and "one-interface part" not in line


def test_banner_for_a_0_1_8_free_text_part_still_works(hook):
    """`SURFACE · shell · 1` was taught by 0.1.8. It keeps working and nobody is told to retitle it."""
    text = hook.banner("startup", "SURFACE · shell · 1", "DESK", "SURFACE", None, None, 300_000, 450_000)
    line = banner_line_2(text)
    assert "lane SURFACE" in line and "'shell'" in line and "session 1" in line
    assert "project's sidebar group" in line and "retitle" not in line.lower()


def test_banner_for_a_title_that_is_only_the_word_part(hook):
    """No project name to take out: the banner must not print an empty one."""
    text = hook.banner("startup", "SURFACE · part · 2", "DESK", "SURFACE", None, None, 300_000, 450_000)
    assert "project ''" not in text and "session 2" in banner_line_2(text)


@pytest.mark.parametrize("title", ["DOORS · G6 2/5 · topic", "DOORS · topic"])
def test_banner_for_an_older_form_desk_offers_self_migration_only(hook, title):
    text = hook.banner("startup", title, "DESK", "DOORS", None, None, 300_000, 450_000)
    assert "older desk form" in text and "still reads it" in text
    assert "only yourself" in text and "never in bulk" in text
    assert "`LANE · <project> part · n`" in text and "<project part>" not in text


def test_banner_for_an_unfiled_session_teaches_the_project_form(hook):
    text = hook.banner("startup", None, "UNFILED", None, None, None, 300_000, 450_000)
    assert "`LANE · <project> part · n`" in text and "PROJECT's sidebar group" in text
    assert "<project part>" not in text and "followed by the word `part`" in text
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
    ("INTELLIGENCE · World Intel  part · 4", WI),        # case and spacing in the project do not matter
    ("INTELLIGENCE · world intel part · 6", WI),         # any later session of the lane in the project
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
    row("INTELLIGENCE · globe feeds part · 4", WI),                           # another project's name
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
         for name in ("way", "desk", "router", "handoff", "new-project", "conductor", "launch")}
NEW_FORM = "`LANE · <project> part · n`"


@pytest.mark.parametrize("name", ["way", "desk", "router", "handoff", "conductor"])
def test_the_desk_title_skills_teach_the_project_form(name):
    assert NEW_FORM in SKILL[name], name


@pytest.mark.parametrize("name", ["way", "router"])
def test_the_owners_own_example_is_in_the_skills_that_title_desks(name):
    assert OWNER_EXAMPLE in SKILL[name], name


def test_the_way_defines_the_title_in_the_owners_words():
    """Lane, then the project's name followed by the word `part`, then n; the task is not in the title."""
    text = SKILL["way"]
    assert "followed by the word `part`" in text and "The task id leaves the title" in text
    assert "What the desk does is not in the title" in text


# The 0.1.8 wording of the middle: a free-text "project part". 0.1.9 replaced it with the project's name
# and the word `part`, and nothing that teaches a title may bring the placeholder or the phrase back.
OLD_PART_WORDING = re.compile(r"<project part>|lower-case words|a part names one task only")
SHIPPED_TEXT = {
    **{f"skills/{n}": SKILL[n] for n in SKILL},
    "README.md": (PLUGIN / "README.md").read_text(encoding="utf-8"),
    "hooks/way_hook.py": HOOK_PATH.read_text(encoding="utf-8"),
}


@pytest.mark.parametrize("where", sorted(SHIPPED_TEXT))
def test_nothing_shipped_teaches_the_0_1_8_part_wording(where):
    found = OLD_PART_WORDING.search(SHIPPED_TEXT[where])
    assert not found, (where, found.group(0))


def test_the_readme_names_the_new_form_and_the_owners_example():
    text = SHIPPED_TEXT["README.md"]
    assert NEW_FORM in text and OWNER_EXAMPLE in text


@pytest.mark.parametrize("middle, project", [
    ("world intel part", "world intel"),
    ("World  Intel PART", "World  Intel"),
    ("one-interface part", "one-interface"),
    ("shell", None),            # the 0.1.8 free-text part
    ("part", None),             # only the word: no project to name
    ("departed", None),         # the word must stand alone
    ("photo store upload", None),
])
def test_project_of_takes_the_word_part_off_the_end(hook, middle, project):
    assert hook.project_of(middle) == project


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


# --- a successor launched into a slot (0.1.11, leadfuel-way:launch) --------------------------
# The app refuses to file a scheduled run in any sidebar group, so a slot successor's `group` is
# null by construction. The archive guard reads its `way-slot-NN` scheduledTaskId in the group's
# place, and every other test (live, same role, the next of the same line) still applies.

def slot(title, task="way-slot-01", archived=False, **extra):
    return {"sessionId": "local_slot", "title": title, "isArchived": archived, "group": None,
            "scheduledTaskId": task, **extra}


def saw_slot(transcript, value):
    read(transcript, GET, {"session_id": "local_slot"}, value)


@pytest.mark.parametrize("own, successor", [
    ("ROUTER #9", "ROUTER #10 · atlas"),
    ("ROUTER #9 · atlas", "ROUTER #10 · atlas"),
    ("CONDUCTOR · system build", "CONDUCTOR · system build 2"),
])
def test_a_tier_successor_launched_into_a_slot_counts_without_a_group(hook, transcript, own, successor):
    transcript.add(title_rec(own))
    saw_slot(transcript, slot(successor))
    assert archive(hook, transcript) is None


@pytest.mark.parametrize("task", [f"way-slot-{n:02d}" for n in range(1, 7)])
def test_every_slot_counts(hook, transcript, task):
    transcript.add(title_rec("ROUTER #9"))
    saw_slot(transcript, slot("ROUTER #10", task=task))
    assert archive(hook, transcript) is None


def test_a_project_desk_may_archive_once_its_slot_successor_is_live(hook, transcript):
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_self(transcript, OWNER_EXAMPLE, WI)
    saw_slot(transcript, slot("INTELLIGENCE · world intel part · 4"))
    assert archive(hook, transcript) is None


def test_a_slot_successor_is_judged_without_the_desks_own_group(hook, transcript):
    """The slot id replaces the group comparison, so a desk that never read itself is not stuck."""
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_slot(transcript, slot("INTELLIGENCE · world intel part · 4"))
    assert archive(hook, transcript) is None


@pytest.mark.parametrize("own, seen", [
    ("ROUTER #9", slot("ROUTER #10", archived=True)),                    # already gone
    ("ROUTER #9", {k: v for k, v in slot("ROUTER #10").items() if k != "isArchived"}),  # archived unknown
    ("ROUTER #9", slot("ROUTER #8")),                                     # an older router
    ("ROUTER #9", slot("ROUTER #9")),                                     # yourself
    ("ROUTER #9", slot("CONDUCTOR · x")),                                 # another tier
    ("ROUTER #9", slot("INTELLIGENCE · world intel part · 4")),           # a desk is not a router
    ("ROUTER #9", slot("ROUTER #10", task="daily-standup")),              # some other scheduled task
    ("ROUTER #9", slot("ROUTER #10", task="way-slot-1")),                 # not a slot id
    ("ROUTER #9", slot("ROUTER #10", task="way-slot-001")),
    ("ROUTER #9", slot("ROUTER #10", task="xway-slot-01")),
    ("ROUTER #9", slot("ROUTER #10", task="")),
    ("ROUTER #9", {k: v for k, v in slot("ROUTER #10").items() if k != "scheduledTaskId"}),  # unknown
    (OWNER_EXAMPLE, slot("INTELLIGENCE · world intel part · 2")),         # the predecessor, not the successor
    (OWNER_EXAMPLE, slot("INTELLIGENCE · world intel part · 3")),         # the same part number
    (OWNER_EXAMPLE, slot("INTELLIGENCE · reports part · 4")),             # another project
    (OWNER_EXAMPLE, slot("DOORS · world intel part · 4")),                # another lane
    (OWNER_EXAMPLE, slot("ROUTER #10")),                                  # a tier
])
def test_what_does_not_count_as_a_slot_successor(hook, transcript, own, seen):
    transcript.add(title_rec(own))
    saw_self(transcript, own, WI)
    saw_slot(transcript, seen)
    assert refused(archive(hook, transcript))


@pytest.mark.parametrize("value, expected", [
    ({"scheduledTaskId": "way-slot-01"}, True),
    ({"scheduledTaskId": " way-slot-06 "}, True),
    ({"scheduledTaskId": "way-slot-1"}, False),
    ({"scheduledTaskId": "way-slot-001"}, False),
    ({"scheduledTaskId": "daily-standup"}, False),
    ({"scheduledTaskId": None}, False),
    ({}, False),
])
def test_is_slot_row_reads_only_a_slot_id(hook, value, expected):
    assert hook.is_slot_row(value) is expected


def test_the_refusal_tells_a_session_how_a_slot_successor_is_proved(hook, transcript):
    transcript.add(title_rec("ROUTER #9"))
    reason = archive(hook, transcript)["hookSpecificOutput"]["permissionDecisionReason"]
    assert "leadfuel-way:launch" in reason and "way-slot-NN" in reason and "STAY OPEN" in reason


def test_the_banner_tells_an_unfiled_session_that_a_slot_session_cannot_be_filed(hook):
    text = hook.banner("startup", None, "UNFILED", None, None, None, 1, 2)
    assert "leadfuel-way:launch" in text and "cannot be filed" in text


# --- a desk nested under its router lives in a tier group (0.1.24) -----------------------------
# Owner, 2026-11-01, Router desk card q1029 option B: routers stay in the ROUTER group, a desk its
# router opens with `start_session` is nested under it and so lands in that same group (the app files
# a nested session in its opener's group, and `move_sessions` refuses to move it alone), and the title
# carries the project. So a nested desk's own group is a TIER group, and so is its nested successor's.
#
# What the guard may then accept, and the only thing: a successor row in a tier group counts when this
# desk is itself nested in that same tier group, both titles are project-form lines of the same
# project with n advanced, AND the row proves this session opened it (`startedBy`, which
# list_sessions gives a linked session, or `parentSessionId`, which get_session gives, equals this
# session's own `sessionId` from its get_session on `self`). The group alone proves nothing: every
# desk of every project the router opened sits in that group. A missing or different opener, or an
# unknown own id or own group, is unknown, and unknown refuses.
#
# Recognising a successor is not the same as letting the desk go: a recognised successor that is still
# nested under the desk (its row names the desk as opener and does not show `detached: true`) makes the
# self-archive refused (the guard floor, the last section of this file). The accept tests in this section
# therefore give the successor row `detached=True`.

RG = grp("ROUTER")
CG = grp("CONDUCTOR")
ME = "local_desk_me"            # this desk's own sessionId, as its get_session on self reports it
THEM = "local_desk_next"        # the successor row's own sessionId
OTHER = "local_someone_else"    # a session that is neither of them
NEXT = "INTELLIGENCE · world intel part · 4"


def saw_me(transcript, group=RG, title=OWNER_EXAMPLE, sid=ME, drop=()):
    """The nested desk reading itself: get_session on `self`, with the id the opener proof needs."""
    value = {"sessionId": sid, "title": title, "isArchived": False, "group": group}
    for key in drop:
        value.pop(key, None)
    read(transcript, GET, {"session_id": "self"}, value)


def nested(title=NEXT, group=RG, by=ME, field="startedBy", archived=False, drop=(), **extra):
    """A successor row as list_sessions / get_session returns it, naming its opener in `field`."""
    value = {"sessionId": THEM, "title": title, "isArchived": archived, "group": group, **extra}
    if by is not None:
        value[field] = by
    for key in drop:
        value.pop(key, None)
    return value


@pytest.mark.parametrize("field", ["startedBy", "parentSessionId"])
@pytest.mark.parametrize("successor", [
    NEXT,
    "INTELLIGENCE · World Intel  part · 4",   # case and spacing in the project do not matter
    "INTELLIGENCE · world intel part · 6",    # any later session of the lane in the project
])
def test_a_nested_desk_may_archive_once_the_successor_it_opened_is_live_in_the_router_group(hook, transcript, field, successor):
    # Since the guard floor (end of this file) a successor still NESTED under the desk is refused; the guard
    # recognises this one and lets the desk go only because the row shows it `detached`. The refusal for the
    # same rows without `detached` is `test_a_desk_refuses_to_archive_while_its_nested_successor_is_live`.
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_me(transcript)
    saw_list(transcript, nested(successor, field=field, detached=True))
    assert archive(hook, transcript) is None


def test_the_successor_may_be_read_with_get_session_on_its_own_id(hook, transcript):
    """get_session names the opener as `parentSessionId`; the guard reads rows from either tool."""
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_me(transcript)
    read(transcript, GET, {"session_id": THEM}, nested(field="parentSessionId", detached=True))
    assert archive(hook, transcript) is None


def test_both_opener_fields_may_be_present_when_they_agree(hook, transcript):
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_me(transcript)
    saw_list(transcript, nested(parentSessionId=ME, detached=True))
    assert archive(hook, transcript) is None


def test_the_groups_may_be_matched_by_name_when_no_ids_are_given(hook, transcript):
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_me(transcript, group={"name": "ROUTER"})
    saw_list(transcript, nested(group={"name": "router"}, detached=True))
    assert archive(hook, transcript) is None


def test_the_0_1_8_free_text_part_is_not_proven_in_a_tier_group(hook, transcript):
    """`desk_line` reads `LANE · shell · 1` as a part line, but it names no project: in the ROUTER group,
    which every project's desks share, the opener proof would be the only thing left to tell a successor
    from a stranger. A check that can lean on one proof only says unknown, so it refuses."""
    transcript.add(title_rec("SURFACE · shell · 1"))
    saw_me(transcript, title="SURFACE · shell · 1")
    saw_list(transcript, nested("SURFACE · shell · 2"))
    assert refused(archive(hook, transcript))


REFUSED_NESTED = [
    # The opener proof: a stranger in the ROUTER group is exactly what the group alone cannot tell apart.
    pytest.param(nested(by=None), id="no-opener-field"),
    pytest.param(nested(by=OTHER), id="another-session-started-it"),
    pytest.param(nested(by=OTHER, field="parentSessionId"), id="another-session-is-its-parent"),
    pytest.param(nested(by=""), id="empty-opener"),
    pytest.param(nested(by="   "), id="blank-opener"),
    pytest.param(nested(by={"sessionId": ME}), id="opener-not-a-string"),
    pytest.param(nested(by=[ME]), id="opener-a-list"),
    pytest.param({**nested(by=ME), "parentSessionId": OTHER}, id="the-two-opener-fields-disagree"),
    pytest.param({**nested(by=OTHER), "parentSessionId": ME}, id="the-two-opener-fields-disagree-the-other-way"),
    pytest.param({**nested(by={"x": 1}), "parentSessionId": ME}, id="an-unreadable-opener-beside-a-good-one"),
    # The group: the opener proof never stands in for it.
    pytest.param(nested(group=grp("INTELLIGENCE")), id="filed-in-the-lane-group"),
    pytest.param(nested(group=WI), id="filed-in-a-project-group"),
    pytest.param(nested(group=CG), id="filed-in-the-conductor-group"),
    pytest.param(nested(group=grp("ROUTER", "cg-another-router")), id="same-name-another-group"),
    pytest.param(nested(group=None), id="group-unknown"),
    # Liveness.
    pytest.param(nested(archived=True), id="already-archived"),
    pytest.param(nested(drop=("isArchived",)), id="archived-unknown"),
    pytest.param(nested(archived="false"), id="archived-not-a-boolean"),
    # The line: same lane, same project, n advanced, project form on both sides.
    pytest.param(nested("INTELLIGENCE · world intel part · 3"), id="same-n-as-yourself"),
    pytest.param(nested("INTELLIGENCE · WORLD INTEL part · 3"), id="same-n-another-case"),
    pytest.param(nested("INTELLIGENCE · world intel part · 2"), id="your-predecessor"),
    pytest.param(nested("INTELLIGENCE · globe feeds part · 4"), id="another-project-in-the-same-group"),
    pytest.param(nested("SURFACE · world intel part · 4"), id="another-lane"),
    pytest.param(nested("INTELLIGENCE · WI-3 4/4 · world intel"), id="older-task-form"),
    pytest.param(nested("INTELLIGENCE · world intel"), id="older-topic-form"),
    pytest.param(nested("ROUTER #29 · world intel"), id="another-tier"),
    pytest.param(nested("Fix the tests"), id="not-a-desk-title"),
    pytest.param(nested(""), id="no-title"),
]


@pytest.mark.parametrize("seen", REFUSED_NESTED)
def test_what_does_not_count_as_a_nested_desks_successor(hook, transcript, seen):
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_me(transcript)
    saw_list(transcript, seen)
    assert refused(archive(hook, transcript))


@pytest.mark.parametrize("renamed", [
    {"id": "cg-router", "name": "Routers"},   # the same group id under another name
    {"id": "cg-router"},                      # the same group id, the name left out
])
def test_a_tier_group_renamed_between_two_reads_cannot_turn_the_opener_proof_off(hook, transcript, renamed):
    """The branch must not hinge on the row's group NAME alone: the id says it is this desk's own tier
    group, so a stranger there still needs the opener proof, and the opener turns it back on."""
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_me(transcript, group={"id": "cg-router", "name": "ROUTER"})
    saw_list(transcript, nested(group=renamed, by=None))
    assert refused(archive(hook, transcript))
    saw_list(transcript, nested(group=renamed, by=OTHER))
    assert refused(archive(hook, transcript))
    saw_list(transcript, nested(group=renamed, by=ME, detached=True))  # recognised; detached, so the floor lets go
    assert archive(hook, transcript) is None


def test_a_project_desk_does_not_borrow_the_tier_rule_from_a_row_that_carries_its_group_id(hook, transcript):
    """Its own group is a project group. A row with that group's id but named ROUTER is not a tier group
    for this desk: the tier branch needs the desk's own group to be one, whatever the opener field says."""
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_me(transcript, group=grp("world intel", "cg-g1"))
    saw_list(transcript, nested(group=grp("ROUTER", "cg-g1"), by=ME))
    assert refused(archive(hook, transcript))


@pytest.mark.parametrize("own, successor", [
    ("NODE · WAY-1 1/2 · build", "NODE · WAY-1 2/2 · build"),            # both older task form
    ("DOORS · topic", "DOORS · topic, continued"),                       # both older topic form
    ("NODE · way plugin part · 2", "NODE · WAY-1 3/3 · build"),          # project form, then older
    ("NODE · WAY-1 1/2 · build", "NODE · way plugin part · 3"),          # older, then project form
    ("NODE · way plugin part · 2", "NODE · way plugin part"),            # no n at all
])
def test_the_older_forms_stay_refused_in_a_tier_group_even_with_the_opener_proof(hook, transcript, own, successor):
    """That group is shared by every project: `LANE · topic` has nothing to tell a stranger from a successor."""
    transcript.add(title_rec(own))
    saw_me(transcript, title=own)
    saw_list(transcript, nested(successor))
    assert refused(archive(hook, transcript))


# What the guard does not know about itself is unknown, and unknown refuses.

@pytest.mark.parametrize("mine", [
    pytest.param(dict(drop=("sessionId",)), id="self-read-has-no-sessionId"),
    pytest.param(dict(sid=""), id="self-read-has-an-empty-sessionId"),
    pytest.param(dict(sid="  "), id="self-read-has-a-blank-sessionId"),
    pytest.param(dict(sid=None), id="self-read-sessionId-is-null"),
    pytest.param(dict(sid=["local_desk_me"]), id="self-read-sessionId-is-not-a-string"),
    pytest.param(dict(drop=("group",)), id="self-read-has-no-group"),
    pytest.param(dict(group=None), id="self-read-group-is-null"),
    pytest.param(dict(group=WI), id="self-is-in-a-project-group-not-the-router-group"),
    pytest.param(dict(group=CG), id="self-is-in-the-conductor-group-the-successor-in-the-router-group"),
    pytest.param(dict(group=grp("ROUTER", "cg-another-router")), id="self-is-in-another-group-named-router"),
    pytest.param(dict(group=grp("INTELLIGENCE")), id="self-is-in-its-lane-group"),
])
def test_unknown_about_yourself_refuses_even_with_the_opener_proof(hook, transcript, mine):
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_me(transcript, **mine)
    saw_list(transcript, nested())
    assert refused(archive(hook, transcript))


def test_a_desk_that_never_read_itself_is_refused(hook, transcript):
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_list(transcript, nested())
    assert refused(archive(hook, transcript))


def test_an_errored_self_read_names_neither_group_nor_id(hook, transcript):
    transcript.add(title_rec(OWNER_EXAMPLE))
    read(transcript, GET, {"session_id": "self"},
         {"sessionId": ME, "title": OWNER_EXAMPLE, "isArchived": False, "group": RG}, is_error=True)
    saw_list(transcript, nested())
    assert refused(archive(hook, transcript))


def test_only_the_self_read_names_your_id(hook, transcript):
    """A get_session on some other id is another session's row, even when it carries your title and group."""
    transcript.add(title_rec(OWNER_EXAMPLE))
    read(transcript, GET, {"session_id": OTHER},
         {"sessionId": ME, "title": OWNER_EXAMPLE, "isArchived": False, "group": RG})
    saw_list(transcript, nested())
    assert refused(archive(hook, transcript))


def test_the_newest_self_read_names_your_id_and_group(hook, transcript):
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_me(transcript)
    saw_me(transcript, drop=("sessionId",))   # the newest read is the one that counts, and it lost the id
    saw_list(transcript, nested(detached=True))
    assert refused(archive(hook, transcript))
    saw_me(transcript)
    assert archive(hook, transcript) is None


def test_a_successor_the_router_opened_is_left_to_the_router(hook, transcript):
    """The fallback order in `way` section 2b: the router opens it beside the old desk and archives the old
    desk through its gate. The desk itself has no proof that it opened that successor."""
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_me(transcript)
    saw_list(transcript, nested(by="local_router_9"))
    assert refused(archive(hook, transcript))


def test_a_sibling_desk_of_the_same_project_is_not_your_successor(hook, transcript):
    """The ROUTER group holds every desk the router opened. A later desk of your lane and project that the
    router opened beside you matches your title, your group and your n, and was not opened by you."""
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_me(transcript)
    saw_list(transcript, nested("INTELLIGENCE · world intel part · 5", by="local_router_9"),
             nested("INTELLIGENCE · world intel part · 6", by=None))
    assert refused(archive(hook, transcript))
    saw_list(transcript, nested("INTELLIGENCE · world intel part · 4", by=ME, detached=True))
    assert archive(hook, transcript) is None


# The tiers are untouched: a router's or conductor's successor is still proven only in the ROUTER or
# CONDUCTOR group, and the opener field adds nothing there. A router the conductor opens nests under the
# conductor and lands in the CONDUCTOR group, so it is still not proven: an open item, not changed in 0.1.24.

@pytest.mark.parametrize("own, successor, group", [
    ("ROUTER #9", "ROUTER #10", "ROUTER"),
    ("CONDUCTOR · system build", "CONDUCTOR · system build 2", "CONDUCTOR"),
])
def test_a_tier_successor_is_still_proven_by_its_tier_group_alone(hook, transcript, own, successor, group):
    transcript.add(title_rec(own))
    saw_self(transcript, own, grp(group))
    saw_list(transcript, nested(successor, grp(group), by=None))
    assert archive(hook, transcript) is None


def test_a_router_in_the_conductor_group_is_still_not_proven_open_item(hook, transcript):
    transcript.add(title_rec("ROUTER #9"))
    saw_me(transcript, title="ROUTER #9", group=RG)
    saw_list(transcript, nested("ROUTER #10", CG, by=ME))
    assert refused(archive(hook, transcript))


# The pure functions, so a regression names its cause.

def test_own_session_id_is_the_newest_self_read(hook):
    rows = [{"_self": True, "sessionId": "a"}, {"_self": False, "sessionId": "b"}, {"_self": True, "sessionId": " c "}]
    assert hook.own_session_id(rows) == "c"


@pytest.mark.parametrize("rows", [
    [],
    [{"_self": False, "sessionId": "b"}],                                    # list_sessions rows are not you
    [{"_self": True, "sessionId": "a"}, {"_self": True}],                   # the newest self read lost it
    [{"_self": True, "sessionId": ""}],
    [{"_self": True, "sessionId": None}],
    [{"_self": True, "sessionId": 7}],
    [{"_self": True, "sessionId": {"id": "a"}}],
])
def test_own_session_id_is_unknown_when_it_cannot_be_read(hook, rows):
    assert hook.own_session_id(rows) is None


@pytest.mark.parametrize("row_, own_id, expected", [
    ({"startedBy": ME}, ME, True),
    ({"parentSessionId": ME}, ME, True),
    ({"startedBy": ME, "parentSessionId": ME}, ME, True),
    ({"startedBy": f" {ME} "}, ME, True),
    ({"startedBy": OTHER}, ME, False),
    ({"parentSessionId": OTHER}, ME, False),
    ({"startedBy": ME, "parentSessionId": OTHER}, ME, False),     # conflicting evidence is not proof
    ({"startedBy": OTHER, "parentSessionId": ME}, ME, False),
    ({"startedBy": ME, "parentSessionId": ""}, ME, True),          # an empty field says nothing
    ({}, ME, False),
    ({"startedBy": ""}, ME, False),
    ({"startedBy": None}, ME, False),
    ({"startedBy": {"sessionId": ME}}, ME, False),
    ({"startedBy": ME}, None, False),                              # own id unknown
    ({"startedBy": ME}, "", False),
    ({"startedBy": ""}, "", False),                                # two empty strings are not a match
    ({"startedBy": None}, None, False),
])
def test_opened_by_needs_the_row_to_name_this_session(hook, row_, own_id, expected):
    assert hook.opened_by(row_, own_id) is expected


def mine_of(hook, group):
    """`mine` as is_successor takes it: the (id, name) pair own_group reads off a get_session on `self`."""
    return hook.group_of({"group": group})


def test_is_successor_still_takes_its_old_positional_arguments(hook):
    """Existing callers pass (own_title, row, mine); the opener proof is a new keyword."""
    wi, rg = mine_of(hook, WI), mine_of(hook, RG)
    assert hook.is_successor(OWNER_EXAMPLE, row("INTELLIGENCE · world intel part · 4", WI), wi)
    assert not hook.is_successor(OWNER_EXAMPLE, row("INTELLIGENCE · world intel part · 4", RG), wi)
    assert hook.is_successor("ROUTER #9", row("ROUTER #10", RG))
    assert not hook.is_successor(OWNER_EXAMPLE, row("INTELLIGENCE · world intel part · 4", RG), rg)  # no id: unknown


def test_is_successor_in_a_tier_group_needs_the_new_keyword(hook):
    successor, rg = nested(), mine_of(hook, RG)
    assert hook.is_successor(OWNER_EXAMPLE, successor, rg, own_id=ME)
    assert not hook.is_successor(OWNER_EXAMPLE, successor, rg)                  # no id: unknown
    assert not hook.is_successor(OWNER_EXAMPLE, successor, rg, own_id=OTHER)
    assert not hook.is_successor(OWNER_EXAMPLE, successor, None, own_id=ME)     # no group: unknown
    assert not hook.is_successor(OWNER_EXAMPLE, successor, mine_of(hook, WI), own_id=ME)


def test_a_successor_in_a_project_group_needs_no_opener_proof(hook):
    """Everything outside a tier group is exactly as before: the group is the project, the title the line."""
    wi = mine_of(hook, WI)
    assert hook.is_successor(OWNER_EXAMPLE, row("INTELLIGENCE · world intel part · 4", WI), wi)
    assert hook.is_successor(OWNER_EXAMPLE, row("INTELLIGENCE · world intel part · 4", WI), wi, own_id=ME)


# Positive controls: these tests only mean something if removing the opener check would flip them. A
# hook that tested the group alone must accept the stranger below, so the refusals above rest on
# `opened_by` and not on something incidental.

@pytest.mark.parametrize("stranger", [
    # detached=True: the patched check below calls every row opened by this desk, and a nested row is
    # refused by the floor for a different reason; a detached one isolates the opener test.
    pytest.param(nested(by=None, detached=True), id="no-opener-field"),
    pytest.param(nested(by=OTHER, detached=True), id="another-opener"),
])
def test_positive_control_a_group_only_check_would_accept_the_stranger(hook, transcript, monkeypatch, stranger):
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_me(transcript)
    saw_list(transcript, stranger)
    assert refused(archive(hook, transcript))
    monkeypatch.setattr(hook, "opened_by", lambda row_, own_id: True)  # the group-only guard
    assert archive(hook, transcript) is None


def test_positive_control_the_group_test_is_not_the_opener_test(hook, transcript, monkeypatch):
    """And the other way: the opener proof alone, in the wrong group, still refuses."""
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_me(transcript)
    saw_list(transcript, nested(group=CG))
    monkeypatch.setattr(hook, "opened_by", lambda row_, own_id: True)
    assert refused(archive(hook, transcript))


# --- the banner: a nested desk is not told it is misfiled -------------------------------------

def banner_lines(text: str) -> list[str]:
    return text.splitlines()


@pytest.mark.parametrize("title, lane", [
    (OWNER_EXAMPLE, "INTELLIGENCE"),
    ("SURFACE · shell · 1", "SURFACE"),      # the 0.1.8 free-text form
    ("SURFACE · part · 2", "SURFACE"),       # only the word `part`
])
def test_the_banner_for_a_project_form_desk_allows_for_a_nested_desk(hook, title, lane):
    text = hook.banner("startup", title, "DESK", lane, None, None, 300_000, 450_000)
    line = banner_line_2(text)
    assert "nested" in line and "ROUTER group" in line and "start_session" in line
    assert "`move_sessions` refuses to move a nested session alone" in line
    assert "`get_session` on `self`" in line and "do not try" in line
    assert "title carries the project" in line
    # still one line, and the next banner line follows it directly
    lines = banner_lines(text)
    assert lines[lines.index(line) + 1].startswith("3. ")


def test_the_nested_clause_keeps_the_older_asserted_wording(hook):
    text = hook.banner("startup", OWNER_EXAMPLE, "DESK", "INTELLIGENCE", None, None, 300_000, 450_000)
    line = banner_line_2(text)
    assert "lane INTELLIGENCE" in line and "project 'world intel'" in line and "session 3" in line
    assert "project's sidebar group" in line and "not the INTELLIGENCE lane group" in line
    assert "world intel part" not in line and "older desk form" not in text
    text = hook.banner("startup", "SURFACE · shell · 1", "DESK", "SURFACE", None, None, 300_000, 450_000)
    line = banner_line_2(text)
    assert "lane SURFACE" in line and "'shell'" in line and "session 1" in line
    assert "project's sidebar group" in line and "retitle" not in line.lower()


def test_the_unfiled_banner_says_a_nested_desk_may_already_be_filed(hook):
    text = hook.banner("startup", None, "UNFILED", None, None, None, 300_000, 450_000)
    line = banner_line_2(text)
    assert "Title: None" in line and "nested" in line and "start_session" in line
    assert line.index("`get_session` on `self`") < line.index("title and file yourself")  # read before filing
    assert "must not try to file yourself" in line
    assert "not filed" in text
    lines = banner_lines(text)
    assert lines[lines.index(line) + 1].startswith("3. ")


def test_the_unfiled_banner_keeps_everything_it_taught_before(hook):
    text = hook.banner("startup", None, "UNFILED", None, None, None, 300_000, 450_000)
    line = banner_line_2(text)
    for needle in ("`LANE · <project> part · n`", "PROJECT's sidebar group", "followed by the word `part`",
                   "never its lane's", "leadfuel-way:new-project", "`ROUTER #N · <project>`",
                   "`CONDUCTOR · topic`", "Move only yourself", "leadfuel-way:launch", "cannot be filed"):
        assert needle in line, needle
    assert "<project part>" not in text


@pytest.mark.parametrize("title", ["DOORS · G6 2/5 · topic", "DOORS · topic"])
def test_the_older_form_and_tier_banners_are_unchanged_by_the_nested_clause(hook, title):
    text = hook.banner("startup", title, "DESK", "DOORS", None, None, 300_000, 450_000)
    assert "nested" not in banner_line_2(text)
    assert "in the ROUTER sidebar group" in hook.banner("startup", "ROUTER #1", "ROUTER", None, None, None, 1, 2)


def test_session_start_for_an_untitled_nested_desk_tells_it_to_read_itself_first(hook, transcript):
    """The banner is computed before the opener titles the session: `Title: None`, UNFILED, and yet filed."""
    transcript.add(assistant(4_000))
    text = hook.handle(event("SessionStart", transcript, source="startup"))["hookSpecificOutput"]["additionalContext"]
    assert "Title: None" in text and "Role: UNFILED" in text
    assert "read" in banner_line_2(text) and "`get_session` on `self`" in banner_line_2(text)


# --- the skill says what the hook now does --------------------------------------------------------

def test_the_way_skill_states_what_the_hook_does_for_a_nested_desk():
    text = SKILL["way"]
    where = text[text.index("**Where a nested desk is filed"):]
    where = where[:where.index("\n\n")]
    assert "never proves a desk" not in where and "it never proves a desk in a tier group" not in where
    assert "0.1.24" in where and "startedBy" in where and "parentSessionId" in where
    assert "inferred" in where.lower()
    assert "CONDUCTOR group" in where   # the router the conductor opened: stated as an open item
    assert "open item" in where
    # the claim that the guard never looks at the opener is no longer unqualified
    assert "with one exception since 0.1.24" in text


def test_the_desk_skill_no_longer_says_the_banner_and_hooks_call_a_nested_desk_misfiled():
    text = SKILL["desk"]
    assert "The banner and the hooks expect the project's group and may tell you" not in text
    assert "0.1.24" in text and "startedBy" in text and "parentSessionId" in text


# --- a desk does not archive itself while its nested successor is live (the guard floor, 0.1.24) -------
# Owner, 2026-11-01: "A guard floor. A nested desk that already has a live nested successor can still
# archive itself. The guard only checks the simple case." The skills say a desk that opened a NESTED
# successor stays open and the successor archives it from inside its own first turn (`way` section 2b
# and 5, `desk`, `handoff`), because the app archives a parent's idle nested sessions together with the
# parent. So once a successor is recognised and this session is a desk, the self-archive is refused when
# a recognised row PROVES the successor is nested under this session (`opened_by(row, own_id)`) and the
# row does not positively show `detached: true`. A row with no `detached` field, which a list_sessions
# row is, counts as still nested: unknown is not a pass. What the check cannot prove it leaves as it was.

NO_SUCCESSOR_SEEN = "until your successor is live and visible in its sidebar group"  # the older refusal
LATER = "INTELLIGENCE · world intel part · 6"


def why(out) -> str:
    return out["hookSpecificOutput"]["permissionDecisionReason"]


def assert_nested_refusal(out) -> str:
    """Refused, and with the floor's own text, not the 'no successor seen' one."""
    assert refused(out)
    text = why(out)
    assert "nested under you" in text and "archives you" in text and "`get_session`" in text
    assert "STAY OPEN" in text
    assert NO_SUCCESSOR_SEEN not in text
    return text


def assert_no_successor_refusal(out) -> None:
    assert refused(out)
    text = why(out)
    assert NO_SUCCESSOR_SEEN in text and "nested under you" not in text


def desk_in(transcript, group, **mine):
    transcript.add(title_rec(OWNER_EXAMPLE))
    saw_me(transcript, group=group, **mine)


@pytest.mark.parametrize("group", [RG, WI], ids=["router-group", "project-group"])
@pytest.mark.parametrize("field", ["startedBy", "parentSessionId"])
@pytest.mark.parametrize("successor", [NEXT, "INTELLIGENCE · World Intel  part · 4", LATER], ids=["next", "case-and-spacing", "later-n"])
def test_a_desk_refuses_to_archive_while_its_nested_successor_is_live(hook, transcript, group, field, successor):
    """The nested successor names this desk as its opener (`startedBy` in list_sessions, `parentSessionId` in
    get_session) and is live in the desk's own group: the desk stays open and the successor archives it."""
    desk_in(transcript, group)
    saw_list(transcript, nested(successor, group=group, field=field))
    assert_nested_refusal(archive(hook, transcript))


@pytest.mark.parametrize("group", [RG, WI], ids=["router-group", "project-group"])
def test_both_opener_fields_agreeing_still_refuse(hook, transcript, group):
    desk_in(transcript, group)
    saw_list(transcript, nested(group=group, parentSessionId=ME))
    assert_nested_refusal(archive(hook, transcript))


def test_a_nested_successor_read_with_get_session_on_its_own_id_refuses(hook, transcript):
    desk_in(transcript, RG)
    read(transcript, GET, {"session_id": THEM}, nested(field="parentSessionId"))
    assert_nested_refusal(archive(hook, transcript))


def test_groups_matched_by_name_alone_still_refuse(hook, transcript):
    desk_in(transcript, {"name": "ROUTER"})
    saw_list(transcript, nested(group={"name": "router"}))
    assert_nested_refusal(archive(hook, transcript))


def test_the_same_successor_read_twice_still_refuses(hook, transcript):
    """A list_sessions row and then a get_session row of one session: the newest decides, and both say nested."""
    desk_in(transcript, WI)
    saw_list(transcript, nested(group=WI, field="startedBy"))
    read(transcript, GET, {"session_id": THEM}, nested(group=WI, field="parentSessionId"))
    assert_nested_refusal(archive(hook, transcript))


@pytest.mark.parametrize("flag", ["true", "True", "yes", 1, 0, False, None, [], {}, [True]], ids=repr)
@pytest.mark.parametrize("group", [RG, WI], ids=["router-group", "project-group"])
def test_detached_has_to_be_the_boolean_true_to_clear_the_refusal(hook, transcript, group, flag):
    """Unknown is not a pass: a string, a number, a null or `false` does not say the successor left."""
    desk_in(transcript, group)
    saw_list(transcript, nested(group=group, detached=flag))
    assert_nested_refusal(archive(hook, transcript))


def test_the_refusal_text_says_what_to_do(hook, transcript):
    desk_in(transcript, WI)
    saw_list(transcript, nested(group=WI))
    text = assert_nested_refusal(archive(hook, transcript))
    assert text.startswith("THE WAY:") and "leadfuel-way:desk" in text
    assert "`detach_session`" in text and "`detached: true`" in text
    assert "\n" not in text                                   # one paragraph
    assert ME not in text and THEM not in text                # no session ids
    assert text == hook.NESTED_SUCCESSOR_REFUSAL
    assert hook.load_state("sess-1")["archives_refused"] == 1


# What does not change: a recognised successor the desk cannot be shown to have opened still lets it go.

@pytest.mark.parametrize("field", ["startedBy", "parentSessionId"])
@pytest.mark.parametrize("group", [RG, WI], ids=["router-group", "project-group"])
def test_a_detached_successor_lets_the_desk_archive(hook, transcript, group, field):
    desk_in(transcript, group)
    saw_list(transcript, nested(group=group, field=field, detached=True))
    assert archive(hook, transcript) is None


@pytest.mark.parametrize("seen", [
    pytest.param(nested(group=WI, by="local_router_9"), id="the-router-opened-it-beside-the-desk"),
    pytest.param(nested(group=WI, by=None), id="no-opener-field"),
    pytest.param(nested(group=WI, by=""), id="empty-opener"),
    pytest.param(nested(group=WI, by={"sessionId": ME}), id="opener-not-a-string"),
    pytest.param({**nested(group=WI, by=ME), "parentSessionId": OTHER}, id="the-two-opener-fields-disagree"),
])
def test_a_project_group_successor_not_proven_nested_leaves_the_floor_as_it_was(hook, transcript, seen):
    desk_in(transcript, WI)
    saw_list(transcript, seen)
    assert archive(hook, transcript) is None


def test_a_desk_that_cannot_read_its_own_id_cannot_prove_the_successor_nested(hook, transcript):
    """Not a proof, so not a block: the guard as it stood. (A tier-group desk without its id is refused by
    the recognition itself, `test_unknown_about_yourself_refuses_even_with_the_opener_proof`.)"""
    desk_in(transcript, WI, drop=("sessionId",))
    saw_list(transcript, nested(group=WI))
    assert archive(hook, transcript) is None


def test_a_slot_successor_is_not_nested_and_still_lets_the_desk_archive(hook, transcript):
    desk_in(transcript, WI)
    saw_slot(transcript, slot("INTELLIGENCE · world intel part · 4"))
    assert archive(hook, transcript) is None


def test_no_successor_seen_keeps_its_own_refusal(hook, transcript):
    desk_in(transcript, RG)
    assert_no_successor_refusal(archive(hook, transcript))
    saw_list(transcript, nested(by=OTHER))                    # recognised by nobody: another opener in the tier group
    assert_no_successor_refusal(archive(hook, transcript))


@pytest.mark.parametrize("own, successor, group", [
    ("ROUTER #9", "ROUTER #10", "ROUTER"),
    ("ROUTER #27 · one-interface", "ROUTER #28 · one-interface", "ROUTER"),
    ("CONDUCTOR · system build", "CONDUCTOR · system build 2", "CONDUCTOR"),
])
@pytest.mark.parametrize("by", [ME, None, OTHER], ids=["opened-by-me", "no-opener", "opened-by-another"])
def test_routers_and_conductors_are_not_touched_by_the_floor(hook, transcript, own, successor, group, by):
    """For a tier the nested-successor rule is a preference in the skills (`leadfuel-way:router`, Rotate
    step 4), not a rule: a recognised successor still lets it archive, nested under it or not."""
    transcript.add(title_rec(own))
    saw_self(transcript, own, grp(group))
    saw_list(transcript, nested(successor, grp(group), by=by))
    assert archive(hook, transcript) is None


# The newest read of each session decides (rows with no sessionId stand alone).

def test_a_later_read_showing_the_nested_successor_archived_no_longer_recognises_it(hook, transcript):
    desk_in(transcript, WI)
    saw_list(transcript, nested(group=WI))
    assert_nested_refusal(archive(hook, transcript))
    read(transcript, GET, {"session_id": THEM}, nested(group=WI, field="parentSessionId", archived=True))
    assert_no_successor_refusal(archive(hook, transcript))     # not the floor's text: nothing is live any more


def test_a_later_read_showing_the_nested_successor_detached_lets_the_desk_go(hook, transcript):
    desk_in(transcript, RG)
    saw_list(transcript, nested())
    assert_nested_refusal(archive(hook, transcript))
    read(transcript, GET, {"session_id": THEM}, nested(field="parentSessionId", detached=True))
    assert archive(hook, transcript) is None


def test_the_newest_read_wins_even_over_an_older_detached_one(hook, transcript):
    """By design, unknown is not a pass: a later list_sessions row has no `detached` field, so it counts as
    nested again. To clear the refusal, read the successor with get_session on its id."""
    desk_in(transcript, WI)
    read(transcript, GET, {"session_id": THEM}, nested(group=WI, field="parentSessionId", detached=True))
    assert archive(hook, transcript) is None
    saw_list(transcript, nested(group=WI))
    assert_nested_refusal(archive(hook, transcript))


def test_one_detached_successor_does_not_clear_another_that_is_still_nested(hook, transcript):
    """Two sessions, two ids: the newest read of EACH is judged. One detached does not clear the other."""
    desk_in(transcript, WI)
    gone, live = {"sessionId": "local_gone"}, {"sessionId": "local_live"}
    saw_list(transcript, {**nested(group=WI, detached=True), **gone}, {**nested(LATER, group=WI), **live})
    assert_nested_refusal(archive(hook, transcript))


def test_a_nested_successor_with_no_session_id_is_judged_as_read(hook, transcript):
    desk_in(transcript, WI)
    seen = nested(group=WI)
    del seen["sessionId"]
    saw_list(transcript, seen, {**seen, "detached": True})   # no ids: neither row replaces the other
    assert_nested_refusal(archive(hook, transcript))


def test_latest_reads_keeps_the_newest_row_of_each_session(hook):
    a1, a2, b = {"sessionId": "a", "n": 1}, {"sessionId": "a", "n": 2}, {"sessionId": "b"}
    assert hook.latest_reads([a1, b, a2]) == [b, a2]
    assert hook.latest_reads([]) == []
    assert hook.latest_reads([{"sessionId": " a ", "n": 1}, {"sessionId": "a", "n": 2}]) == [{"sessionId": "a", "n": 2}]


@pytest.mark.parametrize("sid", [None, "", "  ", 7, ["a"], {"id": "a"}], ids=repr)
def test_rows_with_no_readable_session_id_stand_alone(hook, sid):
    r1, r2 = {"sessionId": sid, "n": 1}, {"sessionId": sid, "n": 2}
    assert hook.latest_reads([r1, r2]) == [r1, r2]
    assert hook.latest_reads([{"n": 1}, {"n": 2}]) == [{"n": 1}, {"n": 2}]


def test_sessions_seen_still_returns_every_read_in_order(hook, transcript):
    """The newest-per-session pick is the floor's own; the reader keeps every row, as before."""
    saw_list(transcript, nested(), nested(detached=True))
    read(transcript, GET, {"session_id": THEM}, nested(field="parentSessionId"))
    assert [r.get("detached") for r in hook.sessions_seen(str(transcript.path))] == [None, True, None]


# A positive control: the refusal rests on `opened_by`, not on something incidental.

def test_positive_control_without_the_opener_proof_the_floor_would_let_the_desk_go(hook, transcript, monkeypatch):
    desk_in(transcript, WI)
    saw_list(transcript, nested(group=WI))
    assert_nested_refusal(archive(hook, transcript))
    monkeypatch.setattr(hook, "opened_by", lambda row_, own_id: False)   # a floor that could not see the opener
    assert archive(hook, transcript) is None


def test_positive_control_a_detached_flag_alone_does_not_make_a_stranger_a_successor(hook, transcript):
    """`detached: true` lifts the floor only for a row the guard already recognises."""
    desk_in(transcript, RG)
    saw_list(transcript, nested(by=OTHER, detached=True))
    assert_no_successor_refusal(archive(hook, transcript))
