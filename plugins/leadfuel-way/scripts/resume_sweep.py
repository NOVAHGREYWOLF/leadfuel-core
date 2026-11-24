#!/usr/bin/env python
"""Resume sweep: find sessions that died on a usage limit, once the limit has reset, and write the one message each gets.

    python resume_sweep.py plan --sessions-dir DIR --usage FILE --state FILE [--self ID] [--already-sent K]
                                [--now ISO] [--max 8] --out PLAN.json

A second duty of the wake-on-answer pass (`leadfuel-way:wake`), because a routine of its own would need its own
hand-set permission mode. The script reads the desktop app's session store (passed in; this file reads no
environment) and the text `get_usage` returned for this account, and prints one `NUDGE` line per session. The
Claude session running the pass sends the message and nothing else; it never changes a permission mode.

A session is a candidate when all of these hold, read from its store file (measured 2026-11-01):
    error      matches "hit your .* limit" (`You've hit your weekly limit · resets 2pm (America/Tijuana)`)
    errorAt    within MAX_AGE_HOURS of now
    activity   `lastActivityAt` is no later than `errorAt` plus ACTIVITY_SLACK_MS. The app writes the error row a
               few milliseconds before the last activity stamp, so a strict "not after" would never match; a
               session someone has typed into since moves well past the slack and drops out by itself
    not archived, not this session, and not a scheduled run. A launch slot (`way-slot-NN`) is a real session
               (`leadfuel-way:launch`) and counts; every other routine's run does not
    reset      the time the error text names (parsed with zoneinfo; the next occurrence after errorAt, or the
               date it gives) has passed, and the text could be parsed. An unreadable reset time is `unknown`,
               and a session with an unknown reset is listed and never nudged
and the account has no usage window at 100% (an unreadable usage file stops the whole pass: `unknown`, not `clear`).

Send budget: messaging pauses after 10 sends per session until the owner types, and the wake pass spends up to 5
first, so the cap is min(--max, 10 - --already-sent). A session is nudged at most MAX_NUDGES times for one error
and not twice inside COOLDOWN_MIN minutes (the state file; the session records a nudge with `record`).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - zoneinfo ships with the Python this runs on
    ZoneInfo = None

MAX_NUDGES_PER_PASS = 8
SEND_PAUSE = 10        # messaging pauses after this many sends in one session
MAX_AGE_HOURS = 72
ACTIVITY_SLACK_MS = 120_000
COOLDOWN_MIN = 60
MAX_NUDGES = 3         # for one error; after that a person has to look
MESSAGE = "limit reset, keep going"

SID = re.compile(r"local_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
LIMIT = re.compile(r"hit your .{0,40}?limit", re.I)
# `resets 2pm (America/Tijuana)`, `resets 2:30pm (...)`, `resets Nov 7, 2pm (...)`, `resets Nov 7 at 2pm (...)`
RESET = re.compile(r"resets\s+(?:([A-Za-z]{3,9})\s+(\d{1,2})(?:,|\s+at)?\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s*\(([^)]+)\)", re.I)
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def parse_time(value):
    try:
        t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def from_ms(ms):
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def reset_time(error_text, error_at):
    """The UTC moment the usage limit named in the error text ends, or None when it cannot be read."""
    m = RESET.search(str(error_text or ""))
    if not m or ZoneInfo is None or error_at is None:
        return None
    mon, day, hour, minute, ampm, zone = m.groups()
    try:
        tz = ZoneInfo(zone.strip())
    except Exception:  # an unknown zone name is unknown, not a crash
        return None
    hour = int(hour) % 12 + (12 if ampm.lower() == "pm" else 0)
    minute = int(minute or 0)
    local = error_at.astimezone(tz)
    if mon:
        month = MONTHS.get(mon[:3].lower())
        if not month:
            return None
        try:
            at = datetime(local.year, month, int(day), hour, minute, tzinfo=tz)
        except ValueError:
            return None
        if at < local - timedelta(days=1):  # `Jan 3` written in December
            at = at.replace(year=local.year + 1)
        return at.astimezone(timezone.utc)
    at = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if at <= local:
        at += timedelta(days=1)
    return at.astimezone(timezone.utc)


def usage_state(raw):
    """('clear'|'full'|'unknown', why) from the JSON `get_usage` printed. Only a readable file with at least one
    window and none at 100% is clear."""
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
        windows = data["plan"]["windows"]
    except (TypeError, ValueError, KeyError):
        return "unknown", "the usage file could not be read"
    if not isinstance(windows, list) or not windows:
        return "unknown", "the usage file lists no window"
    full = []
    for w in windows:
        pct = w.get("percentUsed") if isinstance(w, dict) else None
        if not isinstance(pct, (int, float)):
            return "unknown", "a usage window has no percentUsed"
        if pct >= 100:
            full.append(str(w.get("label")))
    return ("full", "at 100%: " + ", ".join(full)) if full else ("clear", "no window at 100%")


def load_candidates(root):
    """[{id, title, error, error_at, last_activity, archived, task}] for every store file with an error, or None
    when the store cannot be read (None is not an empty list)."""
    if not root or not Path(root).is_dir():
        return None
    out, readable = [], 0
    for f in Path(root).glob("*/*/local_*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict) or not SID.fullmatch(str(d.get("sessionId") or "")):
            continue
        readable += 1
        if d.get("error"):
            out.append({"id": d["sessionId"], "title": str(d.get("title") or ""), "error": str(d["error"]),
                        "error_at": d.get("errorAt"), "last_activity": d.get("lastActivityAt"),
                        "archived": bool(d.get("isArchived")), "task": d.get("scheduledTaskId")})
    return out if readable else None


def is_scheduled_run(task) -> bool:
    return bool(task) and not re.fullmatch(r"way-slot-\d+", str(task))


def classify(s, now, self_id=None, max_age_hours=MAX_AGE_HOURS):
    """(verdict, why) for one stored session: 'candidate', 'unknown' (reset unreadable) or 'skip'."""
    if not LIMIT.search(s["error"]):
        return "skip", "the error is not a usage limit"
    if s["archived"]:
        return "skip", "archived"
    if self_id and s["id"] == self_id:
        return "skip", "this session"
    if is_scheduled_run(s["task"]):
        return "skip", f"a run of the routine {s['task']}"
    err_at = from_ms(s["error_at"])
    if err_at is None:
        return "skip", "no errorAt"
    if now - err_at > timedelta(hours=max_age_hours):
        return "skip", f"errorAt is over {max_age_hours} h old"
    last = from_ms(s["last_activity"])
    if last is None:
        return "unknown", "lastActivityAt is unreadable"
    if (last - err_at).total_seconds() * 1000 > ACTIVITY_SLACK_MS:
        return "skip", "active since the error"
    reset = reset_time(s["error"], err_at)
    if reset is None:
        return "unknown", "the reset time in the error text could not be read"
    if reset > now:
        return "skip", "the limit has not reset yet"
    return "candidate", "reset " + reset.strftime("%Y-%m-%dT%H:%MZ")


def make_plan(sessions, usage_raw, state, now, self_id=None, already_sent=0, max_nudges=MAX_NUDGES_PER_PASS):
    """The pass. state is {session id: {"count": n, "last": iso, "error_at": ms}}."""
    plan = {"at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "usage": None, "nudge": [], "unknown": [], "cooldown": [],
            "over_budget": [], "skipped": 0, "message": MESSAGE}
    use, why = usage_state(usage_raw)
    plan["usage"] = {"state": use, "why": why}
    if sessions is None:
        plan["usage"] = {"state": "unknown", "why": "the session store could not be read"}
        return plan
    if use != "clear":
        return plan
    budget = max(0, min(max_nudges, SEND_PAUSE - int(already_sent)))
    for s in sorted(sessions, key=lambda x: str(x["error_at"])):
        verdict, reason = classify(s, now, self_id)
        if verdict == "skip":
            plan["skipped"] += 1
            continue
        row = {"id": s["id"], "title": s["title"], "why": reason}
        if verdict == "unknown":
            plan["unknown"].append(row)
            continue
        rec = state.get(s["id"]) or {}
        if rec.get("error_at") == s["error_at"]:
            last = parse_time(rec.get("last"))
            if int(rec.get("count") or 0) >= MAX_NUDGES or (last and (now - last).total_seconds() < COOLDOWN_MIN * 60):
                plan["cooldown"].append(row)
                continue
        if len(plan["nudge"]) >= budget:
            plan["over_budget"].append(row)
            continue
        plan["nudge"].append(dict(row, error_at=s["error_at"]))
    return plan


def record(state, plan, sent_ids, now):
    """The state after the session sent to sent_ids (the ones whose send did not error)."""
    new = {k: dict(v) for k, v in state.items()}
    for row in plan["nudge"]:
        if row["id"] in sent_ids:
            old = new.get(row["id"]) or {}
            count = int(old.get("count") or 0) + 1 if old.get("error_at") == row["error_at"] else 1
            new[row["id"]] = {"count": count, "last": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "error_at": row["error_at"]}
    return new


def _read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def cmd_plan(args) -> int:
    now = parse_time(args.now) or datetime.now(timezone.utc)
    try:
        usage_raw = Path(args.usage).read_text(encoding="utf-8")
    except OSError:
        usage_raw = None
    state = _read_json(args.state, {}) if args.state else {}
    plan = make_plan(load_candidates(args.sessions_dir), usage_raw, state if isinstance(state, dict) else {}, now,
                     self_id=args.self_id, already_sent=args.already_sent, max_nudges=args.max)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    use = plan["usage"]
    if use["state"] != "clear":
        print(f"RESUME-SWEEP {use['state'].upper()}: {use['why']}; nobody nudged")
        return 0 if use["state"] == "full" else 2
    for row in plan["nudge"]:
        print(f"NUDGE to={row['id']} title={row['title']!r} ({row['why']})")
    print(f"RESUME-SWEEP nudge={len(plan['nudge'])} unknown={len(plan['unknown'])} cooldown={len(plan['cooldown'])} "
          f"over_budget={len(plan['over_budget'])} skipped={plan['skipped']}; message: {MESSAGE}")
    return 0


def cmd_record(args) -> int:
    now = parse_time(args.now) or datetime.now(timezone.utc)
    plan = _read_json(args.plan, None)
    if not isinstance(plan, dict):
        print("RESUME-SWEEP UNKNOWN: the plan file could not be read")
        return 2
    state = _read_json(args.state, {})
    sent = {s.strip() for s in args.sent.split(",") if s.strip()}
    new = record(state if isinstance(state, dict) else {}, plan, sent, now)
    Path(args.state).parent.mkdir(parents=True, exist_ok=True)
    Path(args.state).write_text(json.dumps(new, indent=2), encoding="utf-8")
    print(f"RESUME-SWEEP recorded {len(sent & {r['id'] for r in plan['nudge']})} nudge(s)")
    return 0


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan", help="pick the stranded sessions to nudge")
    p.add_argument("--sessions-dir", required=True, help="the desktop app's session store, %%APPDATA%%/Claude/claude-code-sessions")
    p.add_argument("--usage", required=True, help="the JSON get_usage printed, saved to a file")
    p.add_argument("--state", default=None, help="nudges already sent (a json file the pass keeps)")
    p.add_argument("--self", dest="self_id", default=None)
    p.add_argument("--already-sent", type=int, default=0, help="sends the wake duty already made this pass")
    p.add_argument("--max", type=int, default=MAX_NUDGES_PER_PASS)
    p.add_argument("--now", default=None)
    p.add_argument("--out", required=True)
    r = sub.add_parser("record", help="note which nudges were sent, so they are not sent again at once")
    r.add_argument("--plan", required=True)
    r.add_argument("--state", required=True)
    r.add_argument("--sent", required=True, help="comma list of session ids whose send did not error")
    r.add_argument("--now", default=None)
    args = ap.parse_args(argv)
    return cmd_plan(args) if args.cmd == "plan" else cmd_record(args)


if __name__ == "__main__":
    sys.exit(main())
