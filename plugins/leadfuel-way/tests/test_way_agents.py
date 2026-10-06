"""Background agents (AUTO-DESKS): a router runs a desk as an Agent-tool worker in its own worktree.

Claude Code fires a subagent's hooks with the PARENT session's session_id and transcript_path plus an
`agent_id` (measured 2026-10-06 on CLI 2.1.286: a probe agent's two writes landed in its parent's state
file, read the parent's title, and moved the recorded role from UNFILED to the parent's DESK/NODE). So
every rule that reads "the session" must decide whether it is looking at the session or at one of its
agents. These tests replay that event shape.
"""
from __future__ import annotations

import json

import pytest

from kit import HAIKU, SONNET, Transcript, assistant, event, title_rec

AGENT = "a035da45a87a52bad"


def agent_event(name, transcript, agent=AGENT, **extra):
    return event(name, transcript, agent_id=agent, agent_type="general-purpose", **extra)


def write(hook, transcript, path, agent=AGENT, tool="Edit"):
    ev = agent_event if agent else event
    kw = {"agent": agent} if agent else {}
    return hook.handle(ev("PreToolUse", transcript, tool_name=tool, tool_input={"file_path": str(path)}, **kw))


def denied(out) -> bool:
    return bool(out) and out["hookSpecificOutput"]["permissionDecision"] == "deny"


def cwd_rec(cwd, sidechain=False) -> dict:
    return {"type": "user", "isSidechain": sidechain, "cwd": str(cwd), "message": {"content": "x"}}


@pytest.fixture
def estate(tmp_path):
    """The measured layout: the router runs in a main checkout; the Agent tool's worktree sits inside it."""
    core = tmp_path / "core"
    (core / ".git").mkdir(parents=True)
    agent_wt = core / ".claude" / "worktrees" / f"agent-{AGENT}"
    agent_wt.mkdir(parents=True)
    (agent_wt / ".git").write_text("gitdir: ../../../.git/worktrees/x\n", encoding="utf-8")
    hub = tmp_path / "hub"
    (hub / ".git").mkdir(parents=True)
    hub_wt = hub / ".claude" / "worktrees" / "task-1"
    hub_wt.mkdir(parents=True)
    (hub_wt / ".git").write_text("gitdir: ../../../.git/worktrees/task-1\n", encoding="utf-8")
    router_wt = core / ".claude" / "worktrees" / "router-21"
    router_wt.mkdir(parents=True)
    (router_wt / ".git").write_text("gitdir: ../../../.git/worktrees/router-21\n", encoding="utf-8")
    return {"core": core, "agent_wt": agent_wt, "hub": hub, "hub_wt": hub_wt, "router_wt": router_wt, "tmp": tmp_path}


@pytest.fixture
def router(transcript, estate):
    """ROUTER #21's transcript, running in the main checkout, as the agent's hook events point at it."""
    transcript.add(title_rec("ROUTER #21"), cwd_rec(estate["core"]), assistant(200_000))
    return transcript


def agent_transcript(hook, transcript, agent=AGENT) -> Transcript:
    from pathlib import Path
    p = Path(hook.agent_transcript(str(transcript.path), agent))
    p.parent.mkdir(parents=True, exist_ok=True)
    return Transcript(p)


# --- the pure parts ---------------------------------------------------------------------------

def test_agent_of_reads_only_the_subagent_field(hook):
    assert hook.agent_of({"agent_id": AGENT}) == AGENT
    assert hook.agent_of({}) is None
    assert hook.agent_of({"agent_id": ""}) is None
    assert hook.agent_of({"agent_type": "general-purpose"}) is None  # the type alone does not say subagent
    assert hook.agent_of({"agent_id": "../../etc"}) == "etc"  # never a path


def test_agent_transcript_is_where_claude_code_keeps_it(hook, tmp_path):
    parent = tmp_path / "proj" / "97cdedb3.jsonl"
    assert hook.agent_transcript(str(parent), AGENT) == str(tmp_path / "proj" / "97cdedb3" / "subagents" / f"agent-{AGENT}.jsonl")


def test_session_cwd_is_the_main_threads_newest(hook, transcript, tmp_path):
    assert hook.session_cwd(str(transcript.path)) is None  # unknown, not a guess
    transcript.add(cwd_rec(tmp_path / "old"), cwd_rec(tmp_path / "new"), cwd_rec(tmp_path / "agent", sidechain=True))
    assert hook.session_cwd(str(transcript.path)) == str(tmp_path / "new")
    assert hook.session_cwd(str(tmp_path / "missing.jsonl")) is None


def test_git_root_tells_a_worktree_from_a_main_checkout(hook, estate):
    assert hook.git_root(str(estate["agent_wt"] / "a.py")) == estate["agent_wt"].resolve()
    assert (hook.git_root(str(estate["agent_wt"] / "a.py")) / ".git").is_file()
    assert (hook.git_root(str(estate["core"] / "a.py")) / ".git").is_dir()
    assert hook.git_root(str(estate["tmp"] / "scratch" / "n.md")) is None


def test_write_allowed_for_agent(hook, estate):
    core, wt, hub, hub_wt, rwt = estate["core"], estate["agent_wt"], estate["hub"], estate["hub_wt"], estate["router_wt"]
    allowed = hook.write_allowed_for_agent
    # Router in the main checkout (the measured case).
    assert allowed(str(wt / "skills" / "way.md"), str(core))          # its own Agent-tool worktree
    assert allowed(str(hub_wt / "app.py"), str(core))                 # a worktree it took in another repo
    assert not allowed(str(core / "README.md"), str(core))            # the router's own checkout
    assert not allowed(str(hub / "app.py"), str(core))                # a shared main checkout
    # What a coordinator may write itself stays allowed.
    assert allowed(str(core / ".conductor" / "router" / "handoffs" / "router-021.md"), str(core))
    assert allowed(str(estate["tmp"] / "scratch" / "n.md"), str(core))
    # Router in its own linked worktree: that worktree is still the router's, not the agent's.
    assert not allowed(str(rwt / "a.py"), str(rwt))
    assert allowed(str(wt / "a.py"), str(rwt))
    # Coordinator cwd unknown: only an Agent-tool worktree is provably not the router's.
    assert allowed(str(wt / "a.py"), None)
    assert not allowed(str(hub_wt / "a.py"), None)
    assert not allowed(str(rwt / "a.py"), None)


# --- PreToolUse: writes -----------------------------------------------------------------------

@pytest.mark.parametrize("tool", ["Edit", "Write", "MultiEdit"])
def test_a_routers_agent_may_edit_its_own_worktree(hook, router, estate, tool):
    """Before 0.1.7 this was refused: the agent read the router's title and was judged a ROUTER."""
    assert write(hook, router, estate["agent_wt"] / "plugins" / "x.py", tool=tool) is None


def test_a_routers_agent_may_not_edit_the_routers_checkout(hook, router, estate):
    out = write(hook, router, estate["core"] / "README.md")
    assert denied(out)
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    assert "background agent" in reason and "isolation: worktree" in reason


def test_a_routers_agent_may_not_edit_a_shared_main_checkout(hook, router, estate):
    assert denied(write(hook, router, estate["hub"] / "app.py"))


def test_the_router_itself_still_does_no_work_even_in_an_agents_worktree(hook, router, estate):
    out = write(hook, router, estate["agent_wt"] / "a.py", agent=None)
    assert denied(out) and "does no work" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_a_conductors_agent_is_judged_the_same_way(hook, transcript, estate):
    transcript.add(title_rec("CONDUCTOR · system build"), cwd_rec(estate["core"]))
    assert write(hook, transcript, estate["agent_wt"] / "a.py") is None
    assert denied(write(hook, transcript, estate["core"] / "a.py"))


def test_a_desks_agent_is_not_restricted(hook, transcript, estate):
    transcript.add(title_rec("NODE · AUTO-DESKS 1/1"), cwd_rec(estate["core"]))
    assert write(hook, transcript, estate["core"] / "a.py") is None


def test_with_the_routers_cwd_unknown_only_an_agent_worktree_passes(hook, transcript, estate):
    transcript.add(title_rec("ROUTER #21"))  # no record names a cwd
    assert write(hook, transcript, estate["agent_wt"] / "a.py") is None
    assert denied(write(hook, transcript, estate["hub_wt"] / "a.py"))


def test_role_rule_off_switch_covers_agents(hook, router, estate, monkeypatch):
    monkeypatch.setenv("WAY_ENFORCE_ROLES", "0")
    assert write(hook, router, estate["core"] / "README.md") is None


# --- PreToolUse: session tools ----------------------------------------------------------------

def session_tool(hook, transcript, tool, agent=AGENT, **inp):
    ev = agent_event if agent else event
    kw = {"agent": agent} if agent else {}
    return hook.handle(ev("PreToolUse", transcript, tool_name=tool, tool_input=inp, **kw))


@pytest.mark.parametrize("target", ["self", "local_d51bda2e", ""])
def test_an_agent_never_archives_anything(hook, router, target):
    out = session_tool(hook, router, "mcp__ccd_session_mgmt__archive_session", session_id=target)
    assert denied(out) and "never archives" in out["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.parametrize("tool, inp", [
    ("mcp__ccd_sidebar__move_sessions", {"session_ids": ["self"], "group_id": "cg-node"}),
    ("mcp__ccd_sidebar__move_sessions", {"session_ids": "self"}),
    ("mcp__ccd_sidebar__move_sessions", {"session_ids": ["local_a", " SELF "]}),
    ("mcp__ccd_session_mgmt__set_session_title", {"session_id": "self", "title": "NODE · X 1/1"}),
])
def test_an_agent_may_not_title_or_file_self_because_self_is_its_parent(hook, router, tool, inp):
    """The way's first-turn step (title and file yourself) would move the ROUTER into a desk group."""
    out = session_tool(hook, router, tool, **inp)
    assert denied(out) and "not a sidebar session" in out["hookSpecificOutput"]["permissionDecisionReason"]


@pytest.mark.parametrize("tool, inp", [
    ("mcp__ccd_sidebar__move_sessions", {"session_ids": ["local_a"], "group_id": "cg-node"}),
    ("mcp__ccd_session_mgmt__set_session_title", {"session_id": "local_a", "title": "x"}),
    ("mcp__ccd_sidebar__move_sessions", {"session_ids": None}),
])
def test_an_agent_naming_another_session_is_not_refused_here(hook, router, tool, inp):
    assert session_tool(hook, router, tool, **inp) is None


def test_the_session_itself_may_still_title_and_file_itself(hook, router):
    assert session_tool(hook, router, "mcp__ccd_sidebar__move_sessions", agent=None, session_ids=["self"]) is None
    assert session_tool(hook, router, "mcp__ccd_session_mgmt__set_session_title", agent=None, session_id="self") is None


def test_the_sessions_own_archive_still_goes_through_the_successor_guard(hook, router):
    out = session_tool(hook, router, "mcp__ccd_session_mgmt__archive_session", agent=None, session_id="self")
    assert denied(out) and "STAY OPEN" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_session_tool_rule_off_switch(hook, router, monkeypatch):
    monkeypatch.setenv("WAY_ENFORCE_ROLES", "0")
    assert session_tool(hook, router, "mcp__ccd_sidebar__move_sessions", session_ids=["self"]) is None


# --- the guard measures the agent, not its parent -----------------------------------------------

def test_a_small_agent_of_a_big_router_is_not_told_to_hand_off(hook, transcript):
    transcript.add(title_rec("ROUTER #21"), assistant(400_000))  # the router is past its cap
    agent_transcript(hook, transcript).add(assistant(20_000, model=SONNET, sidechain=True))
    assert hook.handle(agent_event("PostToolUse", transcript)) is None


def test_a_big_agent_is_told_to_hand_off_as_an_agent(hook, transcript):
    transcript.add(title_rec("ROUTER #21"), assistant(10_000))
    agent_transcript(hook, transcript).add(assistant(310_000, model=SONNET, sidechain=True))
    msg = hook.handle(agent_event("PostToolUse", transcript))["hookSpecificOutput"]["additionalContext"]
    assert "this agent is at ~310k" in msg and "STATUS: CONTINUING" in msg and "background agent" in msg
    assert "give the owner" not in msg  # an agent has no owner prompt to give


def test_a_haiku_agent_gets_the_haiku_cap(hook, transcript):
    transcript.add(title_rec("ROUTER #21"), assistant(10_000))
    agent_transcript(hook, transcript).add(assistant(125_000, model=HAIKU, sidechain=True))
    assert "CONTEXT BUDGET" in hook.handle(agent_event("PostToolUse", transcript))["hookSpecificOutput"]["additionalContext"]


def test_an_agent_whose_transcript_cannot_be_found_is_unknown_not_small(hook, transcript):
    transcript.add(title_rec("ROUTER #21"), assistant(400_000))
    assert hook.handle(agent_event("PostToolUse", transcript)) is None
    assert "tokens" not in hook.load_state(f"sess-1--{AGENT}", "agents")


def test_agent_events_never_write_the_parents_state(hook, router, estate):
    hook.handle(event("PostToolUse", router))  # the router's own turn records its state
    before = json.loads(json.dumps(hook.load_state("sess-1")))
    agent_transcript(hook, router).add(assistant(310_000, model=SONNET, sidechain=True))
    hook.handle(agent_event("PostToolUse", router))
    write(hook, router, estate["agent_wt"] / "a.py")
    session_tool(hook, router, "mcp__ccd_sidebar__move_sessions", session_ids=["self"])
    after = hook.load_state("sess-1")
    after.pop("updated_at", None), before.pop("updated_at", None)
    assert after == before
    mine = hook.load_state(f"sess-1--{AGENT}", "agents")
    assert mine["tokens"] == 310_000 and "soft_crossed_at" in mine and mine["session_tools_refused"] == 1


def test_agent_state_stays_out_of_the_files_the_doctor_reads(hook, router):
    agent_transcript(hook, router).add(assistant(5_000, model=SONNET, sidechain=True))
    hook.handle(agent_event("PostToolUse", router))
    assert not list(hook.state_dir().glob(f"*{AGENT}*.json"))
    assert list((hook.state_dir() / "agents").glob(f"*{AGENT}*.json"))


def test_the_parents_own_guard_is_unchanged(hook, transcript):
    transcript.add(assistant(310_000))
    msg = hook.handle(event("PostToolUse", transcript))["hookSpecificOutput"]["additionalContext"]
    assert "give the owner" in msg and "this agent" not in msg


# --- the matcher sends the session tools to the hook ---------------------------------------------

def test_hooks_json_routes_the_self_tools_to_the_hook():
    import re

    from kit import PLUGIN
    cfg = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    matcher = cfg["hooks"]["PreToolUse"][1]["matcher"]
    for tool in ("mcp__ccd_session_mgmt__archive_session", "mcp__claude-code-remote__archive_session",
                 "mcp__ccd_sidebar__move_sessions", "mcp__ccd_session_mgmt__set_session_title"):
        assert re.fullmatch(matcher, tool), tool
    for tool in ("mcp__ccd_session_mgmt__unarchive_session", "mcp__ccd_session_mgmt__list_sessions",
                 "mcp__ccd_session_mgmt__set_session_model"):
        assert not re.fullmatch(matcher, tool), tool
