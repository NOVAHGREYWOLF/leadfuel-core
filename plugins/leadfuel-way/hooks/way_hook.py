#!/usr/bin/env python
"""The way's hook: one script for every hook event, so the method is enforced, not remembered.

Why: on 2026-10-02 no session on the owner's machine had ever been told to hand off. The guard
existed, but only in one repo, behind a `python3` command that is the Microsoft Store stub on
Windows (exit 49, a non-blocking error, so it read exactly like a small session). A skill is
advice; this hook is the part that happens whether or not a session remembers the advice.

Events (one entry point, dispatched on `hook_event_name`):
    SessionStart      inject the banner: load the way, your role (from your title), your caps.
    UserPromptSubmit  guard: past the soft cap, tell the session to finish the step and hand off.
    PostToolUse       same guard.
    Stop              past the soft cap with no handoff written since crossing it: block the stop,
                      once per stop (the harness sets stop_hook_active on the retry, and a hook that
                      blocked again would loop). Hard cap: same, measured from the hard crossing.
    PreToolUse        a session whose title starts with CONDUCTOR or ROUTER (upper case; `ROUTER #N`
                      in any case) is a coordinator tier and may not edit files inside a git
                      checkout, except handoff notes and .conductor/ state. All work happens in
                      desks, and a desk's lane is never ROUTER or CONDUCTOR.
                      Also: `archive_session` on `self` is refused, for every tier, unless this
                      transcript holds a `list_sessions` / `get_session` result showing the
                      session's successor live (not archived) in its sidebar group. Owner,
                      2026-10-02: a router does not leave itself until it has a successor, and a
                      desk at its limit hands off and stays open until the new desk is live.
                      Also: `move_sessions` naming more than one session is refused. Owner,
                      2026-10-07: sessions move one at a time, never in bulk.

Titles and groups (owner, 2026-10-07: "The sidebar group becomes the master project ... The title
becomes LANE · project part · n"). A desk is titled `LANE · <project part> · n` and filed in its
PROJECT's sidebar group; the lane stays in the title. ROUTER and CONDUCTOR keep their tier groups.
Every older form is still read exactly as before, so nothing breaks while sessions migrate one at a
time: `LANE · <task id> n/m · topic`, `LANE · topic`, `ROUTER #N`, `CONDUCTOR · topic`. Because a
desk's group is no longer named by its title, the archive guard reads the desk's own group from a
`get_session` on `self`; for an older-form desk that has not read itself, the 0.1.7 rule (its lane's
group) still applies. This hook never moves or retitles a session.

Background agents (AUTO-DESKS). A router may run a desk as a background agent (the Agent tool with
isolation: worktree) instead of a chip the owner must click. Claude Code fires a subagent's hooks
with the PARENT session's session_id and transcript_path plus an `agent_id` (measured 2026-10-06
on CLI 2.1.286: a probe agent's writes landed in the parent's state file and read the parent's
title). So without the rules below a router's agent inherits the router's title and is refused
every edit, is told to hand off at the router's size, and `self` in a session tool means the router.
When `agent_id` is present:
    - writes: a coordinator's agent may edit inside a linked git worktree (a `.git` FILE at its root)
      that is not the coordinator's own checkout; never the coordinator's checkout, never a main
      checkout. With the coordinator's cwd unknown, only an Agent-tool worktree
      (`.claude/worktrees/agent-*`) is provably not the coordinator's.
    - archive_session is refused outright, and move_sessions / set_session_title on `self`: an agent
      is not a sidebar session, and `self` there is the session that started it.
    - the guard measures the agent's own transcript (`<session>/subagents/agent-<id>.jsonl`) and
      keeps its own state, so the parent's state is not written by its agents' events.

Caps follow the model the session runs on: Haiku 120k/150k (200k window), others 300k/450k.
SESSION_SOFT_TOKENS / SESSION_HARD_TOKENS override both. SESSION_GUARD_OFF=1 disables the guard
and the Stop gate; WAY_ENFORCE_ROLES=0 disables the coordinator edit rule, the agent rules and the bulk-move rule;
WAY_ARCHIVE_GUARD=0 disables the self-archive guard.

It never raises: a broken hook must not break the session it guards. What it cannot measure it
reports as unknown, never as small.
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

VERSION = "0.1.8"
TAIL_BYTES = 768 * 1024
REWARN_EVERY = 10_000  # re-nag after this many more tokens: heard, not spammy
CAPS = {"haiku": (120_000, 150_000), "default": (300_000, 450_000)}
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}
# ROUTER and CONDUCTOR are tiers, never desk lanes (owner, 2026-10-02): a title that starts with
# either word is that tier, whatever follows. The loose form is upper case only, because that is how
# tier titles are written and a natural-language title ("Router skill fixes") must not lose its edit
# tools. The numbered form `ROUTER #N` has always matched in any case.
TIERS = ("ROUTER", "CONDUCTOR")
TIER_TITLE = re.compile(r"^\s*(ROUTER|CONDUCTOR)\b")
ROUTER_NUMBERED = re.compile(r"^\s*ROUTER\s*#\s*\d+", re.I)
# The lookahead makes it impossible for a desk title to yield lane ROUTER or CONDUCTOR.
DESK_TITLE = re.compile(r"^\s*(?!(?:ROUTER|CONDUCTOR)\b)([A-Z][A-Z0-9_-]+)\s*·")
# A Stop gate is satisfied by a handoff written after the crossing: a file write whose path says
# handoff, a shell command that commits or pushes one, or a board write naming one.
HANDOFF_WORD = re.compile(r"hand-?off", re.I)
# A shell command counts only if it also writes: mentioning the word (ls, cat, grep) is not a handoff.
SHELL_WRITES = re.compile(
    r"\bgit\s+(add|commit|push)\b|>>?\s*\S|\btee\b|\b(Set|Add|Out)-Content\b|\bOut-File\b"
    r"|\b(cp|mv)\s|\b(Copy|Move|New)-Item\b",
    re.I,
)
# The older desk title carries its task id and session count: `LANE · <task id> n/m · topic`.
DESK_TASK = re.compile(r"·\s*(\S+)\s+(\d+)\s*/\s*\d+")
# The project form (owner, 2026-10-07): `LANE · <project part> · n`. The sidebar group is the project,
# the lane stays first in the title, the part says what the session does, n counts the sessions that
# have done that part. Same lane rule as DESK_TITLE: never ROUTER or CONDUCTOR.
DESK_PART = re.compile(r"^\s*(?!(?:ROUTER|CONDUCTOR)\b)([A-Z][A-Z0-9_-]+)\s*·\s*([^·]*[^·\s])\s*·\s*(\d+)\s*$")
SESSION_READS = ("list_sessions", "get_session")
# Session tools whose `self` means the parent session when a subagent calls them.
SELF_TOOLS = ("__move_sessions", "__set_session_title")
# The Agent tool's isolation worktrees: <repo>/.claude/worktrees/agent-<agent id>.
AGENT_WORKTREE = re.compile(r"/\.claude/worktrees/agent-[^/]+/", re.I)


# --- transcript ---------------------------------------------------------------------------

def _tail(path: str, nbytes: int = TAIL_BYTES) -> tuple[str, int]:
    p = Path(path)
    size = p.stat().st_size
    with p.open("rb") as fh:
        fh.seek(max(0, size - nbytes))
        return fh.read().decode("utf-8", errors="replace"), size


def _records(text: str):
    for line in text.splitlines():
        try:
            yield json.loads(line)
        except ValueError:
            continue  # the first line of a tail may be cut mid-record


def last_turn(transcript_path: str, agent: bool = False) -> tuple[int | None, str | None, int]:
    """(context tokens the last main-thread turn sent, its model, transcript size).

    Tokens are input + cache_read + cache_creation: the size of the context that turn sent.
    None when the transcript is unreadable or has no main-thread turn yet (unknown, not zero).
    `agent=True` reads a subagent's own transcript, where every record is a sidechain.
    """
    try:
        text, size = _tail(transcript_path)
    except OSError:
        return None, None, 0
    for rec in reversed(list(_records(text))):
        if rec.get("type") != "assistant" or (rec.get("isSidechain") and not agent):
            continue
        msg = rec.get("message") or {}
        usage = msg.get("usage") or {}
        total = sum(
            int(usage.get(k) or 0)
            for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
        )
        if total:
            return total, msg.get("model"), size
    return None, None, size


def scan_title(transcript_path: str, start: int = 0) -> tuple[str | None, int]:
    """(newest custom title in the bytes from `start`, offset to resume from).

    Reads only the new bytes and stops at the last complete line, so a caller that keeps the
    offset pays for what was appended, not for the whole transcript (they reach tens of MB).
    """
    try:
        with Path(transcript_path).open("rb") as fh:
            fh.seek(max(0, start))
            data = fh.read()
    except OSError:
        return None, start
    cut = data.rfind(b"\n") + 1
    title = None
    for line in data[:cut].split(b"\n"):
        if b'"custom-title"' not in line:
            continue
        try:
            rec = json.loads(line.decode("utf-8", errors="replace"))
        except ValueError:
            continue
        title = rec.get("customTitle") or title
    return title, start + cut


def session_cwd(transcript_path: str) -> str | None:
    """The working directory of the session's own main thread (its newest record that names one), or
    None. A subagent's hook event may carry the agent's cwd, so the coordinator's is read here."""
    try:
        text, _ = _tail(transcript_path)
    except OSError:
        return None
    for line in reversed(text.splitlines()):
        if '"cwd"' not in line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict) and not rec.get("isSidechain") and rec.get("cwd"):
            return str(rec["cwd"])
    return None


def agent_of(event: dict) -> str | None:
    """The subagent's id when this hook fires inside one (an Agent-tool worker), else None. Claude Code
    sends `agent_id` only for subagents; session_id and transcript_path stay the parent's."""
    aid = "".join(c for c in str(event.get("agent_id") or "") if c.isalnum() or c in "-_")[:80]
    return aid or None


def agent_transcript(transcript_path: str, agent_id: str) -> str:
    """Where Claude Code keeps a subagent's own transcript: <session>.jsonl -> <session>/subagents/agent-<id>.jsonl."""
    p = Path(transcript_path)
    return str(p.with_suffix("") / "subagents" / f"agent-{agent_id}.jsonl")


def session_title(transcript_path: str) -> str | None:
    """The newest title the app or the session gave itself, or None."""
    return scan_title(transcript_path)[0]


def cached_title(transcript_path: str, state: dict) -> str | None:
    """session_title, remembering how far it has read in `state` (see scan_title)."""
    scan = state.get("title_scan") or {}
    start = int(scan.get("offset") or 0)
    try:
        if Path(transcript_path).stat().st_size < start:
            scan, start = {}, 0  # the file was replaced: read it afresh
    except OSError:
        return scan.get("title")
    found, offset = scan_title(transcript_path, start)
    title = found or scan.get("title")
    state["title_scan"] = {"offset": offset, "title": title}
    return title


def handoff_written_since(transcript_path: str, offset: int) -> bool:
    """True if a main-thread tool call after byte `offset` wrote or pushed a handoff."""
    try:
        with Path(transcript_path).open("rb") as fh:
            fh.seek(max(0, offset))
            text = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return False
    for rec in _records(text):
        if rec.get("type") != "assistant" or rec.get("isSidechain"):
            continue
        for block in (rec.get("message") or {}).get("content") or []:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = str(block.get("name") or "")
            inp = block.get("input") or {}
            if name in WRITE_TOOLS:
                target = str(inp.get("file_path") or inp.get("notebook_path") or "")
            elif name in SHELL_TOOLS:
                target = str(inp.get("command") or "")
            elif "ArtifactData" in name or "set_session_title" in name:
                target = json.dumps(inp)
            else:
                continue
            if not HANDOFF_WORD.search(target):
                continue
            if name in SHELL_TOOLS and not SHELL_WRITES.search(target):
                continue
            return True
    return False


def _json_in(text: str):
    """The JSON value in a tool result's text, tolerating a line of prose around it, or None."""
    try:
        return json.loads(text)
    except ValueError:
        pass
    for open_, close in (("[", "]"), ("{", "}")):
        i, j = text.find(open_), text.rfind(close)
        if 0 <= i < j:
            try:
                return json.loads(text[i:j + 1])
            except ValueError:
                continue
    return None


def _result_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(b.get("text") or "") for b in content if isinstance(b, dict))
    return ""


def sessions_seen(transcript_path: str) -> list[dict]:
    """Every session row this session has read back with list_sessions / get_session (main thread,
    within the transcript tail), oldest first. A row is whatever the tool returned: it is judged by
    is_successor, which treats a missing field as unknown, never as a pass.

    A row from `get_session` on `self` is this session's own and is marked `_self: True`: it is how
    the archive guard learns a desk's own sidebar group (list_sessions leaves the caller out)."""
    try:
        text, _ = _tail(transcript_path)
    except OSError:
        return []
    asked: dict[str, bool] = {}  # tool_use id -> was it a get_session on self
    rows: list[dict] = []
    for rec in _records(text):
        if rec.get("isSidechain"):
            continue
        for block in (rec.get("message") or {}).get("content") or []:
            if not isinstance(block, dict):
                continue
            name = str(block.get("name") or "")
            if block.get("type") == "tool_use" and name.endswith(SESSION_READS):
                inp = block.get("input") if isinstance(block.get("input"), dict) else {}
                own = name.endswith("get_session") and str(inp.get("session_id") or "").strip().lower() == "self"
                asked[str(block.get("id") or "")] = own
            elif block.get("type") == "tool_result" and str(block.get("tool_use_id") or "") in asked:
                if block.get("is_error"):
                    continue
                own = asked[str(block.get("tool_use_id") or "")]
                value = _json_in(_result_text(block.get("content")))
                if isinstance(value, dict):
                    value = value.get("sessions", [value]) if isinstance(value.get("sessions"), list) else [value]
                if isinstance(value, list):
                    # Set on every row, so a field of that name in a tool's own output cannot pose as one.
                    rows.extend({**r, "_self": own} for r in value if isinstance(r, dict))
    return rows


# --- policy (pure, so it can be tested) ---------------------------------------------------

def role_of(title: str | None) -> tuple[str, str | None]:
    """(CONDUCTOR | ROUTER | DESK | UNFILED, lane or None). A tier is never a lane."""
    if not title:
        return "UNFILED", None
    m = TIER_TITLE.match(title)
    if m:
        return m.group(1), None
    if ROUTER_NUMBERED.match(title):
        return "ROUTER", None
    m = DESK_TITLE.match(title)
    if m:
        return "DESK", m.group(1).upper()
    return "UNFILED", None


def _router_number(title: str) -> int | None:
    m = re.match(r"^\s*ROUTER\s*#\s*(\d+)", title or "", re.I)
    return int(m.group(1)) if m else None


def desk_line(title: str | None) -> tuple[str, str, int] | None:
    """Which line of sessions a desk title belongs to, so a successor can be told from a stranger.

    ("task", <task id>, n) for the older form `LANE · <task id> n/m · topic`;
    ("part", <project part>, n) for the project form `LANE · <project part> · n` (owner, 2026-10-07);
    None for anything else, such as `LANE · topic`. The older form is tried first, so a title that
    carries `n/m` is read exactly as 0.1.7 read it. The part keeps its case; compare with part_key.
    """
    t = title or ""
    m = DESK_TASK.search(t)
    if m:
        return "task", m.group(1), int(m.group(2))
    m = DESK_PART.match(t)
    if m:
        return "part", " ".join(m.group(2).split()), int(m.group(3))
    return None


def part_key(line: tuple[str, str, int]) -> tuple[str, str]:
    """(form, key) two titles must share to be one line: the part ignores case and spacing; a task id
    is compared exactly, as before."""
    form, key, _ = line
    return form, key.casefold() if form == "part" else key


def group_of(row: dict) -> tuple[str, str] | None:
    """(id, name) of the sidebar group a session row names, or None when the row does not say: a row
    with no `group` (the app had not reported groups) is unknown, never ungrouped."""
    g = row.get("group")
    if not isinstance(g, dict):
        return None
    gid, name = str(g.get("id") or "").strip(), str(g.get("name") or "").strip()
    return (gid, name) if gid or name else None


def same_group(a: tuple[str, str] | None, b: tuple[str, str] | None) -> bool:
    """By id when both rows carry one (two groups may share a name), else by name, ignoring case."""
    if a is None or b is None:
        return False
    if a[0] and b[0]:
        return a[0] == b[0]
    return bool(a[1]) and a[1].casefold() == b[1].casefold()


def own_group(rows: list[dict]) -> tuple[str, str] | None:
    """This session's own sidebar group, from its newest `get_session` on `self`, or None (unknown)."""
    for r in reversed(rows):
        if r.get("_self"):
            return group_of(r)
    return None


def is_successor(own_title: str | None, row: dict, mine: tuple[str, str] | None = None) -> bool:
    """True only if `row` (a session as list_sessions / get_session returns it) is provably this
    session's successor: live, filed in the right group, and the next of the same line. Anything the
    row does not say (no `isArchived`, no `group`) is unknown, and unknown is not live.

    ROUTER #N: another ROUTER, numbered above N when both carry a number, in the ROUTER group.
    CONDUCTOR: another CONDUCTOR in the CONDUCTOR group (there is only ever one).
    DESK: the same lane (it stays in the title), in the same sidebar group as this session (`mine`,
    read from a `get_session` on `self`), never a tier group, and the next of the same line:
      `LANE · <project part> · n`      the same part, n advanced;
      `LANE · <task id> n/m · topic`   the same task id, n advanced (the older form);
      `LANE · topic`                   any desk of the lane (the older form).
    With `mine` unknown, an older-form desk keeps the 0.1.7 rule (its lane's group). A project-form
    desk does not: its group is its project, which only a read of itself can name, so unknown refuses.
    Across forms nothing counts: an older-form desk whose successor took the project form is archived
    by its router, not by itself.
    """
    own_role, own_lane = role_of(own_title)
    title = str(row.get("title") or "")
    if own_role == "UNFILED" or not title or title == own_title:
        return False
    if row.get("isArchived") is not False:
        return False
    theirs = group_of(row)
    role, lane = role_of(title)
    if role != own_role:
        return False
    if own_role in TIERS:
        if theirs is None or theirs[1].upper() != own_role:
            return False
        if own_role == "ROUTER":
            m, t = _router_number(own_title or ""), _router_number(title)
            if m is not None and (t is None or t <= m):
                return False
        return True
    if lane != own_lane or theirs is None or theirs[1].upper() in TIERS:
        return False
    mine_line, their_line = desk_line(own_title), desk_line(title)
    if mine is not None:
        if not same_group(mine, theirs):
            return False
    elif mine_line is not None and mine_line[0] == "part":
        return False
    elif theirs[1].upper() != (own_lane or ""):
        return False
    if mine_line is None:
        return True
    return their_line is not None and part_key(their_line) == part_key(mine_line) and their_line[2] > mine_line[2]


def archive_refusal(own_title: str | None, rows: list[dict]) -> str | None:
    """The reason to refuse archiving yourself, or None when a live successor has been seen."""
    mine = own_group(rows)
    if any(is_successor(own_title, r, mine) for r in rows if not r.get("_self")):
        return None
    role, lane = role_of(own_title)
    line = desk_line(own_title)
    if role == "DESK" and mine is not None:
        where = f"your own group, {mine[1] or mine[0]}"
    elif role == "DESK" and line is not None and line[0] == "part":
        where = ("your project's group, which this session has not read: run `get_session` with `self` "
                 "so the guard can see it")
    elif role == "DESK":
        where = f"{lane}, or your own group once `get_session` with `self` has shown it"
    else:
        where = role if role in TIERS else "unfiled: title and file yourself first"
    return (
        "THE WAY: you may not archive yourself until your successor is live and visible in its "
        f"sidebar group ({where}). Owner, 2026-10-02: a "
        "session never leaves before its successor exists. If the successor can only be a paste "
        "prompt, give the owner the prompt and STAY OPEN: the successor archives you once it is live. "
        "If you started it yourself, run `list_sessions` with that group (a desk also `get_session` "
        "with `self`) and archive only once the result shows it, not archived."
    )


def bulk_move_refusal(inp: dict) -> str | None:
    """Why this `move_sessions` call is refused, or None. Owner, 2026-10-07: existing sessions move
    one at a time, never in bulk. One id per call (`self` or another session) is always allowed."""
    ids = inp.get("session_ids") if isinstance(inp, dict) else None
    if not isinstance(ids, list):
        return None
    distinct = {str(i).strip().lower() for i in ids if str(i or "").strip()}
    if len(distinct) <= 1:
        return None
    return (
        f"THE WAY: this call moves {len(distinct)} sessions at once. Owner, 2026-10-07: sessions move "
        "one at a time, never in bulk. Move one session per call, and only a session you are filing "
        "now (a desk you just opened) or yourself on your own first turn; migrating other existing "
        "sessions is the owner's, one at a time."
    )


def cap_override(now: float | None = None) -> tuple[int, int] | None:
    """A machine-wide forced cap for piloting: <state dir>/caps-override.json
    {"soft": int, "hard": int, "expires": epoch seconds}. It lapses by itself, so a forgotten one
    cannot leave every session on the machine handing off early. Written by scripts/way_caps.py."""
    try:
        data = json.loads((state_dir() / "caps-override.json").read_text(encoding="utf-8"))
        soft, hard, expires = int(data["soft"]), int(data["hard"]), float(data["expires"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if (now if now is not None else time.time()) >= expires or soft <= 0 or hard < soft:
        return None
    return soft, hard


def caps_for(model: str | None) -> tuple[int, int]:
    """Env beats a live override file beats the model's default."""
    soft, hard = CAPS["haiku"] if model and "haiku" in model.lower() else CAPS["default"]
    soft, hard = cap_override() or (soft, hard)
    try:
        soft = int(os.environ.get("SESSION_SOFT_TOKENS") or soft)
        hard = int(os.environ.get("SESSION_HARD_TOKENS") or hard)
    except ValueError:
        pass
    return soft, hard


AGENT_HANDOFF = (
    "You are a background agent, not a sidebar session: finish the step, commit and push your branch, "
    "write your handoff note in the repo (a path containing 'handoff', per the `leadfuel-way:handoff` "
    "desk row), and end with `STATUS: CONTINUING | <task id> | <PR url or no PR> | handoff <path>`. "
    "The router starts a fresh agent from the note."
)


def guard_message(tokens: int, last_warned: int, soft: int, hard: int, agent: bool = False) -> tuple[str | None, int]:
    """(message or None, new last_warned). `agent` words it for a background agent."""
    if tokens < soft:
        return None, last_warned
    if last_warned and tokens - last_warned < REWARN_EVERY:
        return None, last_warned
    k = tokens // 1000
    if agent:
        cap = f"HARD CAP {hard // 1000}k" if tokens >= hard else f"handoff point {soft // 1000}k, hard cap {hard // 1000}k"
        return f"CONTEXT BUDGET: this agent is at ~{k}k tokens ({cap}). Start nothing new. {AGENT_HANDOFF}", tokens
    if tokens >= hard:
        return (
            f"CONTEXT BUDGET: HARD CAP. This session is at ~{k}k tokens (cap {hard // 1000}k). "
            "Start nothing. Run the `leadfuel-way:handoff` skill now: write the note, commit and push it, give the "
            "owner the one prompt for a fresh session, end your turn."
        ), tokens
    return (
        f"CONTEXT BUDGET: ~{k}k tokens (handoff point {soft // 1000}k, hard cap {hard // 1000}k). "
        "Finish the step you are on, start nothing new, and run the `leadfuel-way:handoff` skill: write the note, "
        "commit and push it, give the owner the one prompt for a fresh session, end your turn. "
        "If you try to end a turn without a handoff note, the Stop hook will send you back to write it."
    ), tokens


def banner(source: str, title: str | None, role: str, lane: str | None, model: str | None,
           tokens: int | None, soft: int, hard: int) -> str:
    size = f"~{tokens // 1000}k tokens" if tokens else "not measured yet (no turn so far)"
    lines = [
        f"THE WAY (leadfuel-way plugin {VERSION}; this banner proves its hooks are live).",
        f"Title: {title!r}. Role: {role}" + (f", desk lane {lane}." if lane else "."),
        "1. Invoke the skill `leadfuel-way:way` now, before any work, then the skill for your role "
        "(`leadfuel-way:conductor`, `leadfuel-way:router` or `leadfuel-way:desk`).",
    ]
    line = desk_line(title) if role == "DESK" else None
    if role == "UNFILED":
        lines.append(
            "2. You are not filed. Before any work, title and file yourself (`leadfuel-way:way`, section 2a): "
            "a desk `LANE · <project part> · n` in its PROJECT's sidebar group, never its lane's (a project "
            "with no group gets one from `leadfuel-way:new-project`, step 2); a router `ROUTER #N · <project>` "
            "in the ROUTER group; the conductor `CONDUCTOR · topic` in the CONDUCTOR group. Move only "
            "yourself (`self`)."
        )
    elif role == "DESK" and line is not None and line[0] == "part":
        lines.append(
            f"2. Your title files you as a desk: lane {lane}, project part '{line[1]}', session {line[2]}. "
            f"Check you are in your project's sidebar group (not the {lane} lane group)."
        )
    elif role == "DESK":
        lines.append(
            "2. Your title is in an older desk form; every hook still reads it. Desks are now filed by "
            "project (owner, 2026-10-07): `LANE · <project part> · n` in the project's sidebar group. On "
            "this first turn you may migrate yourself, and only yourself, if your brief names the project "
            "and its group exists; otherwise keep your title and group. Never move or retitle other "
            "sessions to migrate them: one at a time, never in bulk."
        )
    else:
        lines.append(f"2. Your title files you. Check you are in the {role} sidebar group.")
    lines.append(
        f"3. Handoff guard is live for model {model or 'unknown'}: hand off at {soft // 1000}k, "
        f"hard stop at {hard // 1000}k. Size now: {size}. Past {soft // 1000}k the Stop hook sends "
        "you back to write the handoff each time you try to end a turn without one."
    )
    if source == "compact":
        lines.append("4. Your context was just compacted. Re-read your handoff and live state before acting.")
    if source == "resume":
        lines.append("4. Resumed session: re-read live state (gh, git ls-remote, the pages) before acting.")
    lines.append("No banner at the start of a session means these hooks are not live: say so, and rotate by judgment.")
    return "\n".join(lines)


def git_root(path: str) -> Path | None:
    """The nearest folder at or above `path` holding `.git` (a directory: a main checkout; a file: a
    linked worktree), or None."""
    try:
        p = Path(path).resolve()
    except (OSError, RuntimeError):
        return None
    for d in [p, *p.parents]:
        if (d / ".git").exists():
            return d
    return None


def in_git_checkout(path: str) -> bool:
    return git_root(path) is not None


def write_allowed_for_coordinator(path: str) -> bool:
    low = path.replace("\\", "/").lower()
    if HANDOFF_WORD.search(low) or "/.conductor/" in low:
        return True
    return not in_git_checkout(path)


def _same_dir(a: Path, b: Path) -> bool:
    return os.path.normcase(str(a)) == os.path.normcase(str(b))


def write_allowed_for_agent(path: str, coordinator_cwd: str | None) -> bool:
    """May a coordinator's background agent write `path`? It is a desk when it works in its own
    worktree: anything the coordinator may write itself, plus a linked git worktree (a `.git` file at
    its root) that is not the coordinator's own checkout. Never the coordinator's checkout, never a
    main checkout (a desk does not edit a shared checkout). With the coordinator's cwd unknown, only an
    Agent-tool worktree is provably not the coordinator's: unknown is not a pass."""
    if write_allowed_for_coordinator(path):
        return True
    root = git_root(path)
    if root is None or not (root / ".git").is_file():
        return False
    if coordinator_cwd is None:
        return bool(AGENT_WORKTREE.search(str(root).replace("\\", "/") + "/"))
    own = git_root(coordinator_cwd)
    return own is None or not _same_dir(root, own)


def agent_session_refusal(tool: str, inp: dict) -> str | None:
    """Why a background agent may not make this session-tool call, or None. An agent is not a sidebar
    session: it is never titled, filed or archived, and `self` there is the session that started it."""
    if tool.endswith("__archive_session"):
        return (
            "THE WAY: a background agent never archives a session. `self` here is the session that "
            "started you, and archiving it would end every agent it runs. Report with your final message "
            "(STATUS line); the router archives through its gate."
        )
    targets = inp.get("session_ids") if tool.endswith("__move_sessions") else [inp.get("session_id")]
    if isinstance(targets, str):
        targets = [targets]
    if not isinstance(targets, list):
        return None
    if tool.endswith(SELF_TOOLS) and any(str(t or "").strip().lower() == "self" for t in targets):
        return (
            "THE WAY: a background agent is not a sidebar session and is never titled or filed. `self` "
            "here is the session that started you. Skip the way's titling and grouping step: your router "
            "records you on its roster."
        )
    return None


# --- state --------------------------------------------------------------------------------

def state_dir() -> Path:
    """Where per-session state lives. WAY_STATE_DIR overrides it (tests and the doctor use that)."""
    return Path(os.environ.get("WAY_STATE_DIR") or Path(tempfile.gettempdir()) / "leadfuel-way")


def _state_path(session_id: str, sub: str = "") -> Path:
    """`sub` keeps background agents' state out of the per-session files the doctor reads."""
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")[:80] or "unknown"
    d = state_dir() / sub if sub else state_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{safe}.json"


def load_state(session_id: str, sub: str = "") -> dict:
    try:
        return json.loads(_state_path(session_id, sub).read_text())
    except (OSError, ValueError):
        return {}


def save_state(session_id: str, state: dict, sub: str = "") -> None:
    try:
        state["updated_at"] = time.time()
        _state_path(session_id, sub).write_text(json.dumps(state))
    except OSError:
        pass


def _guard(state: dict, name: str, tokens: int | None, model: str | None, size: int,
           agent: bool = False) -> dict | None:
    """The context guard for one transcript: record the crossings in `state`, speak past the cap."""
    if tokens is None:
        return None
    soft, hard = caps_for(model)
    state.update(tokens=tokens, model=model)
    if tokens >= soft and "soft_crossed_at" not in state:
        state["soft_crossed_at"] = size
    if tokens >= hard and "hard_crossed_at" not in state:
        state["hard_crossed_at"] = size
    msg, state["last_warned"] = guard_message(tokens, int(state.get("last_warned") or 0), soft, hard, agent)
    return {"hookSpecificOutput": {"hookEventName": name, "additionalContext": msg}} if msg else None


# --- dispatch -----------------------------------------------------------------------------

def handle(event: dict) -> dict | None:
    name = event.get("hook_event_name") or ""
    sid = str(event.get("session_id") or "")
    tpath = str(event.get("transcript_path") or "")
    state = load_state(sid)
    # A subagent's events carry the parent's session_id: they keep their own state and never write the
    # parent's, so an agent cannot reset its parent's crossings or race its saves.
    agent = agent_of(event)
    akey = f"{sid}--{agent}" if agent else ""
    astate = load_state(akey, "agents") if agent else {}
    tally = astate if agent else state
    seen = tally.setdefault("seen", {})
    seen[name] = seen.get(name, 0) + 1
    out: dict | None = None
    guard_off = os.environ.get("SESSION_GUARD_OFF") == "1"
    roles_on = os.environ.get("WAY_ENFORCE_ROLES", "1") != "0"
    tool = str(event.get("tool_name") or "")
    tin = event.get("tool_input")
    tin = tin if isinstance(tin, dict) else {}
    # Session-tool refusals, as (state counter, reason). The agent rule speaks first: it is the more
    # specific answer when an agent names `self` among several sessions.
    session_refusal: tuple[str, str] | None = None
    if name == "PreToolUse" and roles_on:
        if agent and tool.endswith(SELF_TOOLS + ("__archive_session",)):
            reason = agent_session_refusal(tool, tin)
            session_refusal = ("session_tools_refused", reason) if reason else None
        if session_refusal is None and tool.endswith("__move_sessions"):
            reason = bulk_move_refusal(tin)
            session_refusal = ("bulk_moves_refused", reason) if reason else None

    if name == "SessionStart":
        if event.get("source") in ("compact", "clear"):
            # The context just shrank: what was crossed before no longer holds.
            for k in ("soft_crossed_at", "hard_crossed_at", "last_warned"):
                state.pop(k, None)
        title = cached_title(tpath, state)
        role, lane = role_of(title)
        tokens, model, _ = last_turn(tpath)
        soft, hard = caps_for(model)
        state.update(title=title, role=role, lane=lane)
        out = {"hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": banner(str(event.get("source") or "startup"), title, role, lane,
                                        model, tokens, soft, hard),
        }}

    elif name in ("UserPromptSubmit", "PostToolUse") and not guard_off:
        if agent:
            # The agent's own size, not its parent's: a desk agent hands off at its cap, never the router's.
            out = _guard(astate, name, *last_turn(agent_transcript(tpath, agent), agent=True), agent=True)
        else:
            out = _guard(state, name, *last_turn(tpath))

    elif name == "Stop" and not guard_off:
        tokens, model, size = last_turn(tpath)
        if tokens is not None and not event.get("stop_hook_active"):
            soft, hard = caps_for(model)
            if tokens >= soft:
                state.setdefault("soft_crossed_at", size)
                if tokens >= hard:
                    state.setdefault("hard_crossed_at", size)
                key = "hard_crossed_at" if tokens >= hard else "soft_crossed_at"
                if not handoff_written_since(tpath, int(state[key])):
                    state["stops_blocked"] = int(state.get("stops_blocked") or 0) + 1
                    out = {"decision": "block", "reason": (
                        f"THE WAY: this session is at ~{tokens // 1000}k tokens, past its "
                        f"{'hard cap ' + str(hard // 1000) if tokens >= hard else 'handoff point ' + str(soft // 1000)}k, "
                        "and no handoff note has been written since. Run the `leadfuel-way:handoff` skill now: "
                        "write the note (path containing 'handoff'), commit and push it, give the owner "
                        "the one prompt for a fresh session, then end your turn."
                    )}

    elif session_refusal:
        # An agent touching `self` is told why that is never its call; anyone moving several sessions
        # at once (agents included) is told to move one at a time.
        key, reason = session_refusal
        tally[key] = int(tally.get(key) or 0) + 1
        out = {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }}

    elif name == "PreToolUse" and agent and roles_on and tool.endswith(SELF_TOOLS + ("__archive_session",)):
        pass  # an agent's session-tool call that names another session, one at a time: not this hook's

    elif name == "PreToolUse" and tool.endswith("__archive_session"):
        target = str(tin.get("session_id") or "").strip()
        if os.environ.get("WAY_ARCHIVE_GUARD", "1") != "0" and target.lower() == "self":
            title = cached_title(tpath, state)
            reason = archive_refusal(title, sessions_seen(tpath))
            if reason:
                state["archives_refused"] = int(state.get("archives_refused") or 0) + 1
                out = {"hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }}

    elif name == "PreToolUse" and roles_on:
        path = str(tin.get("file_path") or tin.get("notebook_path") or "")
        role = None
        if tool in WRITE_TOOLS and path:
            # Read the title fresh: a session can retitle itself after SessionStart. For an agent this
            # is its parent's title, which decides whether the agent rule applies at all.
            role, lane = role_of(cached_title(tpath, state))
            state.update(role=role, lane=lane)
        if role in TIERS and agent and not write_allowed_for_agent(path, session_cwd(tpath)):
            out = {"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"THE WAY: you are a background agent of a {role}, and {path} is not in your own "
                    "worktree. A desk agent edits only its own linked worktree: the one the Agent tool "
                    "made (isolation: worktree), or for another repo one you take there with "
                    "`git worktree add .claude/worktrees/<task> -b <task>`. Never the router's own "
                    "checkout or a shared main checkout."
                ),
            }}
        elif role in TIERS and not agent and not write_allowed_for_coordinator(path):
            out = {"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"THE WAY: a {role} does no work. Editing {path} belongs to a desk session: "
                    "open one for this task (the `leadfuel-way:router` skill says how) and hand it over. "
                    "Handoff notes and .conductor/ state are allowed."
                ),
            }}

    if agent:
        save_state(akey, astate, "agents")
    else:
        save_state(sid, state)
    return out


def main() -> int:
    try:
        event = json.load(sys.stdin)
        out = handle(event)
        if out:
            print(json.dumps(out))
    except Exception:  # noqa: BLE001 - a guard must never break the session it guards
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
