"""own-3: the payout ledger. One list of what the game has paid in real life, and what it counts.

The rule (owner, 2026-11-21: "the game that pays out in real life"; defaults on his standing words, 2026-11-23):
four kinds of payout count, and only these.

    money_in        money that arrived (unit: usd)
    money_saved     a recurring cost that stopped, or a bill avoided (unit: usd)
    hours_returned  time handed back to him (unit: hours)
    thing_running   something now running without him (unit: count)

Every line must trace to a MEASURED outcome from the loop (own-1), never to a click. A line without that
trace is not dropped silently: it goes to `refused` with the reason, so a missing measurement reads as a
gap and not as a smaller total. Totals are per kind. Dollars, hours and things are never added together.

A ledger built from no readable outcome source says `unknown`, not zero. Zero means "I read the source and
it holds no paid outcome"; `unknown` means "I could not read it". The two must never look alike.
"""
from __future__ import annotations

import datetime as dt
import math
from typing import Any, Iterable, Optional

KINDS = {
    "money_in": "usd",
    "money_saved": "usd",
    "hours_returned": "hours",
    "thing_running": "count",
}

# Where a measured outcome may come from. A click, a self-report or a status the user typed is not a source.
MEASURED_SOURCES = {"loop", "ledger", "sensor", "bank", "invoice", "calendar", "run_log"}


def _refuse(o: Any, why: str) -> dict:
    return {"id": o.get("id") if isinstance(o, dict) else None, "why": why}


def _parse_date(v: Any) -> Optional[dt.date]:
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    if isinstance(v, str):
        try:
            return dt.date.fromisoformat(v[:10])
        except ValueError:
            return None
    return None


def build_ledger(outcomes: Optional[Iterable[Any]]) -> dict:
    """Return {"status", "lines", "totals", "refused"}.

    status: "unknown" when `outcomes` is None (source unreadable); "empty" when read and nothing paid;
    "ok" when at least one line counted. `totals` has one entry per kind that has a line, never a grand total.
    """
    if outcomes is None:
        return {"status": "unknown", "lines": [], "totals": {}, "refused": [],
                "note": "the outcome source could not be read; this is not zero"}
    lines, refused, seen = [], [], set()
    for o in outcomes:
        if not isinstance(o, dict):
            refused.append(_refuse(o, "not a record"))
            continue
        oid = o.get("id")
        if not oid:
            refused.append(_refuse(o, "no id, so it cannot be traced"))
            continue
        if oid in seen:
            refused.append(_refuse(o, "duplicate id, counted once"))
            continue
        kind = o.get("kind")
        if kind not in KINDS:
            refused.append(_refuse(o, "kind does not count: %r" % (kind,)))
            continue
        if o.get("measured") is not True or o.get("source") not in MEASURED_SOURCES:
            refused.append(_refuse(o, "not a measured outcome (source %r)" % (o.get("source"),)))
            continue
        date = _parse_date(o.get("date"))
        if date is None:
            refused.append(_refuse(o, "no usable date"))
            continue
        value = o.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            refused.append(_refuse(o, "value is not a non-negative number"))
            continue
        if o.get("unit", KINDS[kind]) != KINDS[kind]:
            refused.append(_refuse(o, "unit %r is not %r" % (o.get("unit"), KINDS[kind])))
            continue
        seen.add(oid)
        lines.append({"id": oid, "date": date.isoformat(), "kind": kind, "value": value,
                      "unit": KINDS[kind], "source": o["source"], "trace": o.get("trace") or oid})
    lines.sort(key=lambda r: (r["date"], r["id"]))
    totals: dict = {}
    for ln in lines:
        t = totals.setdefault(ln["kind"], {"unit": ln["unit"], "value": 0, "lines": 0})
        t["value"] += ln["value"]
        t["lines"] += 1
    return {"status": "ok" if lines else "empty", "lines": lines, "totals": totals, "refused": refused}


def render_text(ledger: dict) -> str:
    """The one screen as plain text: what the room shows, so the room and the CLI cannot disagree."""
    if ledger["status"] == "unknown":
        return "Payouts: UNKNOWN (%s)" % ledger.get("note", "source unreadable")
    out = ["Payouts: %s" % ("none yet (source read, nothing paid)" if ledger["status"] == "empty" else "running totals")]
    for kind, t in sorted(ledger["totals"].items()):
        out.append("  %-15s %s %s (%d line%s)" % (kind, ("%g" % t["value"]), t["unit"], t["lines"], "" if t["lines"] == 1 else "s"))
    for ln in ledger["lines"]:
        out.append("  %s  %-15s %g %s  <- %s" % (ln["date"], ln["kind"], ln["value"], ln["unit"], ln["trace"]))
    if ledger["refused"]:
        out.append("  not counted: %d (%s)" % (len(ledger["refused"]), "; ".join(sorted({r["why"] for r in ledger["refused"]}))))
    return "\n".join(out)
