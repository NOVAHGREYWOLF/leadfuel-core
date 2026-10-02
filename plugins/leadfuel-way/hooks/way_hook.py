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
                      Also once per session: a titled session that has reported a final STATUS or written a
                      handoff, but wrote no doc under a `ledger` folder, is sent back to write it
                      (WAY_LEDGER=0 disables).
    PreToolUse        a session whose title starts with CONDUCTOR or ROUTER (upper case; `ROUTER #N`
                      in any case) is a coordinator tier and may not edit files inside a git
                      checkout, except handoff notes and .conductor/ state. All work happens in
                      desks, and a desk's lane is never ROUTER or CONDUCTOR.

Caps follow the model the session runs on: Haiku 120k/150k (200k window), others 300k/450k.
SESSION_SOFT_TOKENS / SESSION_HARD_TOKENS override both. SESSION_GUARD_OFF=1 disables the guard
and the Stop gate; WAY_ENFORCE_ROLES=0 disables the PreToolUse rule.

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

VERSION = "0.1.2"
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


# A session is finishing when it reports a final-ish STATUS to its router, or has written a handoff.
FINISH_STATUS = re.compile(r"\bSTATUS:\s*(DONE|BLOCKED|NEEDS-NOVAH)\b")
MESSAGE_TOOLS = ("SendMessage", "send_message")
# A ledger doc is a markdown file written under a folder named `ledger` (ledger/<project>/<who>/<date>/<id>.md).
LEDGER_PATH = re.compile(r"[/\\]ledger[/\\][^\s\"']+\.md", re.I)


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


def last_turn(transcript_path: str) -> tuple[int | None, str | None, int]:
    """(context tokens the last main-thread turn sent, its model, transcript size).

    Tokens are input + cache_read + cache_creation: the size of the context that turn sent.
    None when the transcript is unreadable or has no main-thread turn yet (unknown, not zero).
    """
    try:
        text, size = _tail(transcript_path)
    except OSError:
        return None, None, 0
    for rec in reversed(list(_records(text))):
        if rec.get("type") != "assistant" or rec.get("isSidechain"):
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


def _tool_calls(transcript_path: str, offset: int = 0):
    """(name, input) of every main-thread tool call after byte `offset`."""
    try:
        with Path(transcript_path).open("rb") as fh:
            fh.seek(max(0, offset))
            text = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return
    for rec in _records(text):
        if rec.get("type") != "assistant" or rec.get("isSidechain"):
            continue
        for block in (rec.get("message") or {}).get("content") or []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                yield str(block.get("name") or ""), block.get("input") or {}


def finish_reported(transcript_path: str) -> bool:
    """True if this session has reported DONE/BLOCKED/NEEDS-NOVAH to a router, or written a handoff."""
    try:
        size = Path(transcript_path).stat().st_size
    except OSError:
        return False
    for name, inp in _tool_calls(transcript_path, max(0, size - TAIL_BYTES)):
        blob = json.dumps(inp)
        if any(t in name for t in MESSAGE_TOOLS) and FINISH_STATUS.search(blob):
            return True
        if name in WRITE_TOOLS | SHELL_TOOLS and HANDOFF_WORD.search(blob) and (
            name in WRITE_TOOLS or SHELL_WRITES.search(blob)
        ):
            return True
    return False


def ledger_written(transcript_path: str) -> bool:
    """True if this session wrote a markdown file under a `ledger` folder (a file write or a shell write)."""
    try:
        size = Path(transcript_path).stat().st_size
    except OSError:
        return False
    for name, inp in _tool_calls(transcript_path, max(0, size - TAIL_BYTES)):
        if name in WRITE_TOOLS:
            if LEDGER_PATH.search(str(inp.get("file_path") or "")):
                return True
        elif name in SHELL_TOOLS:
            cmd = str(inp.get("command") or "")
            if LEDGER_PATH.search(cmd) and SHELL_WRITES.search(cmd):
                return True
    return False


LEDGER_REASON = (
    "THE WAY: you are finishing (a final STATUS or a handoff was sent) and no ledger doc has been written. "
    "Write your one-page ledger doc now, per F:/Claude Sessions/ledger/README.md (format v1): "
    "ledger/<project>/<who>/<date>/<id>.md, 10 header lines then ## Done / ## Why / ## Open. "
    "The folder is private: never commit it or copy it into a repo. Then end your turn. "
    "This is asked once per session."
)


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


def guard_message(tokens: int, last_warned: int, soft: int, hard: int) -> tuple[str | None, int]:
    """(message or None, new last_warned)."""
    if tokens < soft:
        return None, last_warned
    if last_warned and tokens - last_warned < REWARN_EVERY:
        return None, last_warned
    k = tokens // 1000
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
    if role == "UNFILED":
        lines.append(
            "2. You are not filed. Before any work, title yourself `LANE · topic`, `ROUTER #N` or "
            "`CONDUCTOR · topic` and move yourself into the sidebar group of that name."
        )
    else:
        lines.append("2. Your title files you. Check you are in the sidebar group it names.")
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


def in_git_checkout(path: str) -> bool:
    try:
        p = Path(path).resolve()
    except (OSError, RuntimeError):
        return False
    for d in [p, *p.parents]:
        if (d / ".git").exists():
            return True
    return False


def write_allowed_for_coordinator(path: str) -> bool:
    low = path.replace("\\", "/").lower()
    if HANDOFF_WORD.search(low) or "/.conductor/" in low:
        return True
    return not in_git_checkout(path)


# --- state --------------------------------------------------------------------------------

def state_dir() -> Path:
    """Where per-session state lives. WAY_STATE_DIR overrides it (tests and the doctor use that)."""
    return Path(os.environ.get("WAY_STATE_DIR") or Path(tempfile.gettempdir()) / "leadfuel-way")


def _state_path(session_id: str) -> Path:
    safe = "".join(c for c in session_id if c.isalnum() or c in "-_")[:80] or "unknown"
    d = state_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{safe}.json"


def load_state(session_id: str) -> dict:
    try:
        return json.loads(_state_path(session_id).read_text())
    except (OSError, ValueError):
        return {}


def save_state(session_id: str, state: dict) -> None:
    try:
        state["updated_at"] = time.time()
        _state_path(session_id).write_text(json.dumps(state))
    except OSError:
        pass


# --- dispatch -----------------------------------------------------------------------------

def handle(event: dict) -> dict | None:
    name = event.get("hook_event_name") or ""
    sid = str(event.get("session_id") or "")
    tpath = str(event.get("transcript_path") or "")
    state = load_state(sid)
    seen = state.setdefault("seen", {})
    seen[name] = seen.get(name, 0) + 1
    out: dict | None = None
    guard_off = os.environ.get("SESSION_GUARD_OFF") == "1"

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
        tokens, model, size = last_turn(tpath)
        if tokens is not None:
            soft, hard = caps_for(model)
            state.update(tokens=tokens, model=model)
            if tokens >= soft and "soft_crossed_at" not in state:
                state["soft_crossed_at"] = size
            if tokens >= hard and "hard_crossed_at" not in state:
                state["hard_crossed_at"] = size
            msg, state["last_warned"] = guard_message(tokens, int(state.get("last_warned") or 0), soft, hard)
            if msg:
                out = {"hookSpecificOutput": {"hookEventName": name, "additionalContext": msg}}

    elif name == "Stop" and not guard_off:
        tokens, model, size = last_turn(tpath)
        if (os.environ.get("WAY_LEDGER", "1") != "0" and not event.get("stop_hook_active")
                and not state.get("ledger_asked")
                and role_of(cached_title(tpath, state))[0] != "UNFILED"
                and finish_reported(tpath) and not ledger_written(tpath)):
            state["ledger_asked"] = True  # once per session: a hook that blocked again would loop
            out = {"decision": "block", "reason": LEDGER_REASON}
        elif tokens is not None and not event.get("stop_hook_active"):
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

    elif name == "PreToolUse" and os.environ.get("WAY_ENFORCE_ROLES", "1") != "0":
        tool = str(event.get("tool_name") or "")
        inp = event.get("tool_input") or {}
        path = str(inp.get("file_path") or inp.get("notebook_path") or "")
        role = None
        if tool in WRITE_TOOLS and path:
            # Read the title fresh: a session can retitle itself after SessionStart.
            role, lane = role_of(cached_title(tpath, state))
            state.update(role=role, lane=lane)
        if role in ("CONDUCTOR", "ROUTER") and not write_allowed_for_coordinator(path):
            out = {"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"THE WAY: a {role} does no work. Editing {path} belongs to a desk session: "
                    "open one for this task (the `leadfuel-way:router` skill says how) and hand it over. "
                    "Handoff notes and .conductor/ state are allowed."
                ),
            }}

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
