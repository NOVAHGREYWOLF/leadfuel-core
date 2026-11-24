"""own-2: the level rule. Where each new level comes from, what passes it, how it gets harder, why it never runs out.

Written rule (proposal for the owner's approval; applied as the default on his standing words 2026-11-23):

1. SOURCE. After the eight opening levels (the tutorial), every new level is drawn from his own life, in this
   order: an open gap that blocks something (gaps engine), then a goal he confirmed, then a re-check of a level
   he already passed whose result is older than RECHECK_DAYS (a result that stops being true is a new level).
2. PASS. A level passes only when a measured outcome exists for it (see game/payout_ledger.py). Not on a click,
   not on a self-report, not on a task being marked done.
3. DIFFICULTY. tier = 1 + passed // LEVELS_PER_TIER, capped at TIER_CAP; a level also carries the number of
   things it blocks. Harder means more at stake and a bigger result required, never more clicks.
4. NEVER RUNS OUT. If nothing is owed the answer is `nothing_owed` with the next date anything can come due.
   It is not "game over". New gaps open as his life changes, and passed levels come back for a re-check.
5. DECLINE. A level he declines retires for DECLINE_DAYS (the same 30 days `command_quests.py` uses) and
   returns only if the gap still blocks something.
6. A boss is a confirmed goal Prime runs end to end; a mission is a goal with what it needs. Those two
   definitions are the docs' version (GAME-DESIGN.md sections 4 and 5), recorded here as the default.

Pure functions: the caller passes the data and `today`. Nothing here reads a file or a clock.
"""
from __future__ import annotations

import datetime as dt
import hashlib
from typing import Iterable, Optional

DECLINE_DAYS = 30
RECHECK_DAYS = 90
LEVELS_PER_TIER = 5
TIER_CAP = 12
TUTORIAL = ["Listening", "Speaking", "Hunting", "Reaching", "Guarding", "Scheduling", "Keeping house", "Thinking like you"]

PASS_KINDS = ("money_in", "money_saved", "hours_returned", "thing_running")


def level_id(kind: str, key: str) -> str:
    return "L-" + hashlib.sha1(("%s|%s" % (kind, key)).encode("utf-8")).hexdigest()[:10]


def tier(passed_count: int) -> int:
    return min(TIER_CAP, 1 + max(0, passed_count) // LEVELS_PER_TIER)


def _d(v) -> Optional[dt.date]:
    if isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        return None


def _make(kind: str, key: str, title: str, blocks: int, passed_count: int) -> dict:
    return {"id": level_id(kind, key), "source": kind, "key": key, "title": title,
            "blocks": blocks, "tier": tier(passed_count),
            "passes_when": "a measured outcome of kind %s exists for it" % "/".join(PASS_KINDS)}


def next_level(open_gaps: Iterable[dict], goals: Iterable[dict], passed: Iterable[dict],
               declined: Iterable[dict], today: dt.date) -> dict:
    """Pick the next level. Inputs are plain dicts.

    open_gaps: {"key", "title", "blocks": int}   goals: {"key", "title", "confirmed": bool}
    passed:    {"id", "key", "source", "title", "passed_on"}   declined: {"id", "declined_on"}
    Returns {"level": dict} or {"level": None, "reason": "nothing_owed", "next_check": iso date or None}.
    """
    passed = list(passed)
    passed_ids = {p["id"] for p in passed}
    retired = {}
    for d in declined:
        on = _d(d.get("declined_on"))
        if on is not None:
            retired[d["id"]] = on + dt.timedelta(days=DECLINE_DAYS)
    n = len(passed)

    def open_(lid: str) -> bool:
        return lid not in passed_ids and not (lid in retired and retired[lid] > today)

    gaps = sorted(open_gaps, key=lambda g: (-int(g.get("blocks", 0)), str(g["key"])))
    for g in gaps:
        if int(g.get("blocks", 0)) > 0 and open_(level_id("gap", g["key"])):
            return {"level": _make("gap", g["key"], g["title"], int(g["blocks"]), n)}
    for g in sorted(goals, key=lambda g: str(g["key"])):
        if g.get("confirmed") is True and open_(level_id("goal", g["key"])):
            return {"level": _make("goal", g["key"], g["title"], 0, n)}
    soonest = None
    for p in sorted(passed, key=lambda p: (str(p.get("passed_on")), p["id"])):
        on = _d(p.get("passed_on"))
        if on is None:
            continue
        due = on + dt.timedelta(days=RECHECK_DAYS)
        if due <= today:
            lvl = _make("recheck", p["id"], "Still true? " + p["title"], 0, n)
            if lvl["id"] not in passed_ids and open_(lvl["id"]):
                return {"level": lvl}
        elif soonest is None or due < soonest:
            soonest = due
    for lid, until in retired.items():
        if until > today and (soonest is None or until < soonest):
            soonest = until
    return {"level": None, "reason": "nothing_owed", "next_check": soonest.isoformat() if soonest else None}


def passes(level: dict, ledger: dict) -> bool:
    """True only if the ledger (game.payout_ledger.build_ledger) holds a counted line traced to this level.
    An unknown or empty ledger passes nothing."""
    if ledger.get("status") != "ok":
        return False
    return any(str(ln.get("trace", "")).startswith(level["id"]) for ln in ledger["lines"])
