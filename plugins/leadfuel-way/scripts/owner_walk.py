#!/usr/bin/env python
"""Owner Walk executor: carry out the owner's clicks on the Owner Walk page, inside the wake-on-answer pass.

    python owner_walk.py plan  --items items.json --rows DIR --count N --versions V.json
                               [--sessions-dir DIR] [--router-current FILE] [--project "novah estate"]
                               [--self ID] [--already-sent K] [--max-sends 3] [--max-defaults 5] [--now ISO]
                               --out DIR
    python owner_walk.py cards --plan DIR/plan.json --cards DIR --versions V.json --out DIR
    python owner_walk.py judge --plan DIR/plan.json --work DIR --versions V.json [--now ISO] --out DIR

The page (https://claude.ai/artifact/1i1FhsztHxTi16NYwYhpNL, collection `walk`) writes each click as a row
`walk/<id>` with `exec: {state: "queued"}`. Before this script nothing acted on those rows. The wake pass
(`leadfuel-way:wake`, step 9b) runs the three commands around its own tool calls, the same way it runs
wake_on_answer.py: the script decides, the session reads and writes the page and sends the messages.
Nothing here touches the network.

What a row becomes (the decision is `decide`, and it is the guard):
    carry_out     a plain pick, a "something else" note, or a pre-decided (veto-only) item with no row: the
                  decision goes to the session that owns the item, which carries it out. Inward only.
    hold          the owner vetoed a pre-decided item: the owner is told to hold it.
    inward_only   "Do the default" on an item that could spend, transmit or deploy (law9): only the parts that
                  neither spend nor transmit. Never the outward part.
    law9_yes      the separate amber Yes, with a stated cost or recipient that still matches the item: relayed
                  as exactly that Yes and nothing wider. The executor itself never spends, sends or deploys.
    price_lookup  an amber Yes whose cost or recipient is not known: an agent is asked to find it read-only and
                  report back. The row ends `held` ("waiting for your Yes"), never `done`.
    typed_step    the guard needs the owner's typed yes in a desk chat: the decision is relayed, the row ends
                  `held` with that exact step.
    secret_step   a key or password is involved: relayed, `held` with "do it on the vendor page".
    card          the item is a Router desk card: the owner's answer is written onto the card, so the wake
                  pass routes it. Never over an answer the card already carries.
    refuse        a law9 item marked yes without the amber Yes, or with a stated cost that no longer matches the
                  item: nothing is sent, the row ends `held` with the reason.

The executor never writes `done`: that is the owning desk's word, with proof that the item's finish line
landed. A row ends `relayed` when the target's own transcript holds the message token (the wake pass's rule),
or the card write came back with a version. A send that failed is `failed`. A pass that cannot see what it
would need to call it either way says `unknown`. A row whose opt or time is not what the page writes is
refused (`held`). A `running` row of this executor with no token (a pass died) goes back to `queued` after
HOLD_LIMIT_MIN minutes.

Exit codes: 0 nothing to do or all done, 1 any failed, 2 any unknown or running, or inputs that cannot be read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wake_on_answer as wake  # noqa: E402  (same folder; the helpers that judge a send and read the store)

BY = "owner-walk executor (wake-on-answer)"
PAGE = "https://claude.ai/artifact/1i1FhsztHxTi16NYwYhpNL"
ROUTER_DESK = "https://claude.ai/artifact/LzmP6QcxmYh9TdvMMjS883"
MAX_SENDS = 3          # the wake pass spends up to 5 of the 10 sends a session may make; this shares what is left
SEND_BUDGET = 8        # never more than this many sends in one pass, counting the wake pass's own (--already-sent)
MAX_DEFAULTS = 5       # pre-decided items started per pass, so a veto still has time to land on the rest
MAX_ITEMS_PER_SEND = 10
MAX_MESSAGE_CHARS = 7000
HOLD_LIMIT_MIN = wake.HOLD_LIMIT_MIN
DONE, FAILED, HELD, UNKNOWN, RUNNING = "done", "failed", "held", "unknown", "running"
# The executor never writes DONE. A decision that reached its owner (the token is in the target's transcript, or
# the answer is on the card) is RELAYED; only the owning desk writes DONE, with proof that the item's finish
# line landed (DOORS 182 on PR 108: the page reads done as carried out).
RELAYED = "relayed"
QUEUED = "queued"
PAGE_TIME = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} PT$")   # what the page's pt() writes
MAX_OPT_LEN = 2
FINAL_HELD = {"price_lookup", "typed_step", "secret_step"}
KINDS = ("carry_out", "hold", "inward_only", "law9_yes", "price_lookup", "typed_step", "secret_step")


# ---- time, in Pacific (the owner reads every time in Pacific) ---------------------------------------

def _nth_sunday(year: int, month: int, n: int) -> datetime:
    d = datetime(year, month, 1)
    d += timedelta(days=(6 - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def pacific(now_iso=None) -> str:
    """'YYYY-MM-DD HH:MM PT' (the page's own format). US rule: PDT from the second Sunday of March 02:00 to the
    first Sunday of November 02:00, local. Computed, so it needs no tz database (Windows Python has none)."""
    t = wake.parse_time(now_iso) if now_iso else datetime.now(timezone.utc)
    if t is None:
        t = datetime.now(timezone.utc)
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    utc = t.astimezone(timezone.utc).replace(tzinfo=None)
    start = _nth_sunday(utc.year, 3, 2) + timedelta(hours=2 + 8)   # 02:00 PST in UTC
    end = _nth_sunday(utc.year, 11, 1) + timedelta(hours=2 + 7)    # 02:00 PDT in UTC
    offset = 7 if start <= utc < end else 8
    return (utc - timedelta(hours=offset)).strftime("%Y-%m-%d %H:%M") + " PT"


# ---- the decision -------------------------------------------------------------------------------------

def _exec(row) -> dict:
    e = (row or {}).get("exec")
    return e if isinstance(e, dict) else {}


def allowed_opts(item: dict) -> set:
    """The option keys the page can write for this item: the keys of its first question, X included, or only ''
    when it has no question."""
    sq = (item.get("sq") or [None])[0]
    keys = {""}
    for o in (sq or {}).get("opts") or []:
        m = re.match(r"^([A-Z])=", str(o))
        if m:
            keys.add(m.group(1))
    return keys


def row_problem(item: dict, row: dict):
    """Why a row cannot be trusted as written by the page, or None. Rows are viewer-written data: `opt` must be
    one of the item's own keys and `at` the page's own time format, so nothing crafted reaches a message or a
    card answer."""
    opt = row.get("opt")
    if opt is None:
        opt = ""
    if not isinstance(opt, str) or len(opt) > MAX_OPT_LEN or opt not in allowed_opts(item):
        return f"the row's option {str(opt)[:20]!r} is not one of this item's options"
    at = row.get("at")
    if at is not None and not (isinstance(at, str) and PAGE_TIME.match(at)):
        return "the row's time is not in the page's format"
    if row.get("note") is not None and not isinstance(row.get("note"), str):
        return "the row's note is not text"
    return None


def decide(item: dict, row) -> dict:
    """{'kind', 'why', 'source'} or {'kind': None} when there is nothing to do for this row.

    The guard lives here. A law9 item is carried out only on its separate amber Yes whose stated cost or
    recipient is non-empty and still equals the item's; an unknown cost only buys a read-only lookup."""
    law9 = bool(item.get("law9"))
    cls = item.get("cls") or ""
    if row is None:
        if item.get("mode") != "veto":
            return {"kind": None}
        kind = "inward_only" if law9 else {"typed": "typed_step", "secret": "secret_step"}.get(cls, "carry_out")
        return {"kind": kind, "source": "pre-decided on standing words, not vetoed",
                "why": "a veto-only item nobody vetoed: the default goes ahead"}
    if _exec(row).get("state") != QUEUED:
        return {"kind": None}
    choice = row.get("choice")
    source = "clicked on the Owner Walk page"
    problem = row_problem(item, row)
    if problem:
        return {"kind": "refuse", "source": source, "why": problem}
    if choice == "veto":
        return {"kind": "hold", "source": source, "why": "the owner vetoed a pre-decided item"}
    if choice not in ("yes", "default", "other", "price_first"):
        return {"kind": None}
    if law9:
        yes = row.get("law9_yes") if isinstance(row.get("law9_yes"), dict) else None
        stated = str((yes or {}).get("stated") or "").strip()
        current = str(item.get("law9_stated") or "").strip()
        if choice == "price_first" or (choice == "yes" and yes is not None and not stated):
            return {"kind": "price_lookup", "source": source,
                    "why": "an amber Yes with no stated cost or recipient: find it read-only, then ask again"}
        if choice == "yes":
            if yes is None:
                return {"kind": "refuse", "source": source,
                        "why": "marked yes without the separate amber Yes; a plain click never carries out a law9 item"}
            if stated != current:
                return {"kind": "refuse", "source": source,
                        "why": "the cost or recipient stated with your Yes no longer matches the item; press Yes again"}
            return {"kind": "law9_yes", "source": source, "why": "the amber Yes, for exactly what it stated",
                    "stated": stated}
        return {"kind": "inward_only", "source": source,
                "why": "default or a note on an item that could spend or transmit: inward parts only"}
    if choice == "price_first":
        return {"kind": "carry_out", "source": source, "why": "no cost is involved on this item"}
    if cls == "typed":
        return {"kind": "typed_step", "source": source, "why": "the guard needs the owner's typed yes in the desk chat"}
    if cls == "secret":
        return {"kind": "secret_step", "source": source, "why": "a key or password step on the vendor page"}
    return {"kind": "carry_out", "source": source, "why": "an inward pick"}


def wants_card(item: dict, row, kind: str) -> bool:
    """A card item gets its answer written on the Router desk card when the decision is a plain inward pick or
    the amber Yes, and the click picked an option. Defaults and notes on a law9 card are relayed instead, so
    the card never reads as an outward approval the owner did not give."""
    return bool(item.get("card")) and row is not None and bool((row or {}).get("opt")) \
        and kind in ("carry_out", "law9_yes") and row.get("choice") in ("yes", "default", "other")


# ---- who receives it ----------------------------------------------------------------------------------

def resolve_target(item: dict, sessions, router_id=None, project="novah estate", self_id=None) -> tuple:
    """(session id or None, why). The live session whose title names the item id, else the live router of the
    project (it routes to the desk), else router/current. Never a routine run, never the pass itself."""
    iid = str(item.get("id") or "")
    if sessions and len(iid) >= 3:
        pat = re.compile(r"(?<![\w-])" + re.escape(iid) + r"(?![\w-])")
        hits = [s for s in sessions if not s["archived"] and not s.get("task") and s["id"] != self_id
                and not wake.ROUTER_TITLE.match(s["title"]) and not re.match(r"^\s*CONDUCTOR\b", s["title"])
                and pat.search(s["title"])]
        if len(hits) == 1:
            return hits[0]["id"], "the live session titled " + hits[0]["title"]
    live = [x for x in wake._live_routers(sessions) if x[1] == wake._norm(project) and x[2] != self_id]
    if live:
        num, _, sid = live[-1]
        return sid, f"no live desk names {iid}, so the live router ROUTER #{num} · {project}, which routes it"
    if wake.valid_sid(router_id) and router_id != self_id and not wake.known_gone(router_id, sessions):
        return router_id, "the live router (router/current)"
    return None, "no live desk names the item and no live router was found"


# ---- the message --------------------------------------------------------------------------------------

INSTRUCTION = {
    "carry_out": "Carry it out. It is inward and reversible; anything that would spend, transmit or deploy still "
                 "needs its own Yes.",
    "hold": "HOLD this item. Do not proceed with its default. Wait for the owner.",
    "inward_only": "Do ONLY the parts that neither spend nor transmit nor deploy. The outward part waits for the "
                   "owner's separate amber Yes on the Owner Walk page.",
    "law9_yes": "The owner's amber Yes covers exactly what it stated (below) and nothing wider. Carry it out "
                "through your lane's own guard; anything beyond the stated cost or recipient needs a new Yes.",
    "price_lookup": "Find the exact cost or recipient READ-ONLY (no spend, no send, no production write) and "
                    "report it back on the row as exec.state held with the figure in proof. Do not carry it out.",
    "typed_step": "The guard needs the owner's typed yes in the owning desk's own chat. Prepare everything around it and "
                  "wait for that typed yes; the click is not it.",
    "secret_step": "A key or password step is involved: the owner does it on the vendor page. Prepare everything "
                   "else and never ask for the secret in chat.",
}


def token(iid: str, row, target: str) -> str:
    seed = f"walk|{iid}|{(row or {}).get('at')}|{(row or {}).get('choice')}|{target}"
    return "WALK-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:10]


def compose(entries: list, when: str, to_router: bool = False) -> str:
    """One message for one target. entries: [{'item', 'row', 'decision', 'token'}]."""
    ids = ", ".join(e["item"]["id"] for e in entries)
    lines = [f"OWNER-WALK: the owner decided {len(entries)} item(s) on the Owner Walk page ({PAGE}): {ids}. "
             f"Relayed by the wake-on-answer pass at {when}. Each line says what he chose and what you may do."]
    if to_router:
        lines.append("You get these as the live router: no live desk names the item. Forward each one, unchanged, to the "
                     "desk session that owns its lane (a session id, never a sidebar group), or open one; do not do the "
                     "work yourself.")
    for e in entries:
        it, row, dec = e["item"], e["row"] or {}, e["decision"]
        choice = row.get("choice") or "default"
        opt = row.get("opt") or ""
        lines.append(f"- {it['id']}: {wake._short(it.get('title'), 140)}")
        lines.append(f"  choice: {choice}{(' ' + opt) if opt else ''} ({dec['source']}{', ' + row['at'] if row.get('at') else ''})")
        if row.get("note"):
            lines.append(f"  the owner's note: {wake._short(row.get('note'), 400)}")
        if dec.get("stated"):
            lines.append(f"  the Yes states: {wake._short(dec['stated'], 300)}")
        if e["row"] is None and it.get("dflt"):
            lines.append(f"  the default: {wake._short(it.get('dflt'), 200)}")
        lines.append(f"  what you may do: {INSTRUCTION[dec['kind']]}")
        lines.append(f"  finished when: {wake._short(it.get('done'), 300)}")
        lines.append(f"  token {e['token']}")
    lines.append(f"The executor marks each row on the page relayed (not done) once this message is in your transcript. When the "
                 f"item's finish line lands, write exec = {{state: done, proof, link, by, at}} on walk/<id> at {PAGE} "
                 "(ArtifactData update, pinned), or failed with why. Times in Pacific. No reply to the pass is needed.")
    return "\n".join(lines)


# ---- plan ---------------------------------------------------------------------------------------------

def make_plan(items: list, rows: dict, versions: dict, sessions=None, router_id=None, project="novah estate",
              self_id=None, already_sent=0, max_sends=MAX_SENDS, max_defaults=MAX_DEFAULTS, now=None) -> dict:
    now = now or wake.iso_now()
    when = pacific(now)
    plan = {"at": now, "at_pt": when, "sends": [], "rechecks": [], "stale": [], "cards": [], "refused": [], "no_target": [],
            "deferred": [], "unpinned": [], "running": [], "decisions": {}}
    groups: dict = {}
    defaults = 0
    for it in items:
        iid = it["id"]
        row = rows.get(iid)
        ex = _exec(row)
        if row is not None and ex.get("state") == RUNNING and ex.get("token") and ex.get("by") == BY:
            plan["rechecks"].append({"id": iid, "to": ex.get("to"), "token": ex["token"], "kind": ex.get("kind"),
                                     "started": ex.get("started_utc"), "delivery": ex.get("delivery")})
            continue
        if row is not None and ex.get("state") == RUNNING and ex.get("by") == BY and iid in versions:
            # No token: a card row (or a row whose pass died before it sent). Nothing can be rechecked, so once it
            # is older than the hold limit it goes back to queued: a card write is idempotent (the same answer on
            # the card reads as relayed) and a row that never sent has sent nothing. Unreadable age is unknown.
            age = wake.minutes_between(ex.get("started_utc"), now)
            if age is None:
                plan["stale"].append({"id": iid, "state": UNKNOWN,
                                      "why": "running with no token and no readable start time"})
            elif age > HOLD_LIMIT_MIN:
                plan["stale"].append({"id": iid, "state": QUEUED,
                                      "why": f"running for {int(age)} min with no token: the pass that started it "
                                             "never judged it, so it is queued again"})
            continue
        dec = decide(it, row)
        kind = dec.get("kind")
        if not kind:
            continue
        if row is None:
            if defaults >= max_defaults:
                plan["deferred"].append(iid)
                continue
            defaults += 1
        elif iid not in versions:
            plan["unpinned"].append(iid)   # a write to an existing row needs its version; no version, no act
            continue
        plan["decisions"][iid] = dict(dec, created=row is None)
        if kind == "refuse":
            plan["refused"].append(iid)
            continue
        if wants_card(it, row, kind):
            plan["cards"].append({"id": iid, "card": it["card"], "opt": row.get("opt"),
                                  "note": wake._short(row.get("note") or "", 400), "kind": kind, "at": row.get("at"),
                                  "stated": dec.get("stated") or ""})
            continue
        target, why = resolve_target(it, sessions, router_id, project, self_id)
        plan["decisions"][iid]["target_why"] = why
        if target is None:
            plan["no_target"].append(iid)
            continue
        groups.setdefault(target, []).append(iid)
    budget = max(0, min(max_sends, SEND_BUDGET - int(already_sent or 0)))
    by_id = {it["id"]: it for it in items}
    for n, (target, ids) in enumerate(groups.items()):
        if n >= budget:
            plan["deferred"].extend(ids)
            continue
        chosen: list = []
        for iid in ids:
            trial = [{"item": by_id[c], "row": rows.get(c), "decision": plan["decisions"][c], "token": "WALK-0000000000"}
                     for c in chosen + [iid]]
            if chosen and (len(chosen) >= MAX_ITEMS_PER_SEND or len(compose(trial, when)) > MAX_MESSAGE_CHARS):
                plan["deferred"].append(iid)
            else:
                chosen.append(iid)
        tok = token(chosen[0], rows.get(chosen[0]), target)
        entries = [{"item": by_id[c], "row": rows.get(c), "decision": plan["decisions"][c], "token": tok} for c in chosen]
        plan["sends"].append({"to": target, "ids": chosen, "token": tok, "why": plan["decisions"][chosen[0]]["target_why"],
                              "text": compose(entries, when,
                                              to_router="live router" in plan["decisions"][chosen[0]]["target_why"])})
    # Deferred items were decided but not acted on: they keep no decision, so no row is written for them.
    for iid in plan["deferred"]:
        plan["decisions"].pop(iid, None)
    return plan


def running_writes(plan: dict, items: list, versions: dict) -> list:
    """The batch that marks every acted-on row `running` before anything is sent (EXECUTOR.md step 3). A
    pre-decided item gets its row created here, unpinned: the store refuses a create over a row that exists,
    so an owner's veto that landed meanwhile is never overwritten."""
    by_id = {it["id"]: it for it in items}
    send_of = {iid: s for s in plan["sends"] for iid in s["ids"]}
    writes = []
    for iid, dec in sorted(plan["decisions"].items()):
        if dec["kind"] == "refuse" or iid in plan["no_target"]:
            continue
        s = send_of.get(iid)
        ex = {"state": RUNNING, "by": BY, "at": plan["at_pt"], "started_utc": plan["at"], "kind": dec["kind"]}
        if s:
            ex.update(to=s["to"], token=s["token"])
        elif not any(c["id"] == iid for c in plan["cards"]):
            continue
        if dec.get("created"):
            it = by_id[iid]
            data = {"id": iid, "title": it.get("title"), "state": "answered", "choice": "default", "opt": "",
                    "note": "", "at": plan["at_pt"], "by": BY + ": pre-decided on standing words, not vetoed",
                    "exec": ex}
            writes.append({"op": "set", "collection": "walk", "doc_id": iid, "data": data})
        else:
            writes.append({"op": "update", "collection": "walk", "doc_id": iid, "data": {"exec": ex},
                           "if_version": int(versions[iid])})
    return writes


# ---- cards --------------------------------------------------------------------------------------------

def card_writes(plan: dict, cards: dict, versions: dict, now=None) -> dict:
    """{'writes': [...], 'skipped': {id: why}}. The answer goes on the card only when the card is readable, has
    no answer yet (or the same one), and lists the option the owner clicked."""
    now = now or wake.iso_now()
    out = {"writes": [], "skipped": {}, "same": []}
    for c in plan.get("cards", []):
        card = cards.get(c["card"])
        if not isinstance(card, dict):
            out["skipped"][c["id"]] = (UNKNOWN, f"card {c['card']} could not be read")
            continue
        keys = [str(o.get("key")) for o in card.get("options") or [] if isinstance(o, dict)]
        if c["opt"] not in keys:
            out["skipped"][c["id"]] = (HELD, f"card {c['card']} has no option {c['opt']} (it lists {','.join(keys)})")
            continue
        if card.get("answer") not in (None, "") and card.get("answer") != c["opt"]:
            out["skipped"][c["id"]] = (HELD, f"card {c['card']} already carries answer {card.get('answer')}; not overwritten")
            continue
        if card.get("answer") == c["opt"]:
            out["same"].append(c["id"])
            continue
        if c["card"] not in versions:
            out["skipped"][c["id"]] = (UNKNOWN, f"no version read for card {c['card']}")
            continue
        note = (c["note"] + " " if c["note"] else "") + f"(clicked on the Owner Walk page {c.get('at') or ''}".strip() + ")"
        if c.get("stated"):
            # The amber Yes is limited to what it stated; an asker reading a bare answer would lose the limit.
            note += f" The Yes states, and covers only: {wake._short(c['stated'], 400)}"
        out["writes"].append({"op": "update", "collection": "questions", "doc_id": c["card"],
                              "data": {"answer": c["opt"], "answered_at": now, "note": note, "note_at": now,
                                       "routed": None, "answered_via": "owner-walk"},
                              "if_version": int(versions[c["card"]]), "walk_id": c["id"]})
    return out


def card_written(raw) -> bool | None:
    """True when the batch result names a version and no refusal, False on a refusal, None when unreadable."""
    if not raw:
        return None
    low = str(raw).lower()
    if re.search(r"conflict|refused|rejected|failed|error|not written|nothing (was )?written", low):
        return False
    return True if "version" in low else None


# ---- judge --------------------------------------------------------------------------------------------

def _state_for(kind: str, verdict: str) -> str:
    if verdict == wake.DELIVERED:
        return HELD if kind in FINAL_HELD else RELAYED
    if verdict == wake.UNDELIVERED:
        return FAILED
    if verdict == wake.HELD:
        return RUNNING
    return UNKNOWN


AWAIT = "Not done yet: the owning desk writes done with its finish-line proof when the item lands"

STEP = {
    "price_lookup": "priced lookup asked of {to}; waiting for the cost, then your Yes",
    "typed_step": "decision relayed to {to}; your typed yes in that desk's own chat is the step left",
    "secret_step": "decision relayed to {to}; the key step on the vendor page is yours",
}


def judge(plan: dict, sends: dict, seen_raw: dict, card_result=None, versions=None, now=None) -> dict:
    now = now or wake.iso_now()
    when = pacific(now)
    versions = versions or {}
    final: dict = {}

    def put(iid, state, proof, **extra):
        final[iid] = dict({"state": state, "proof": proof, "link": PAGE, "by": BY, "at": when}, **extra)

    for s in plan.get("sends", []):
        parsed = wake.parse_send(sends.get(s["token"]))
        was = wake.seen(seen_raw.get(s["token"]), s["to"])
        v = wake.verdict(parsed["delivery"], was, wake.minutes_between(plan.get("at"), now), HOLD_LIMIT_MIN)
        for iid in s["ids"]:
            kind = plan["decisions"][iid]["kind"]
            state = _state_for(kind, v)
            proof = (f"send to {s['to']}: delivery {parsed['delivery'] or 'unreadable'}, message_id "
                     f"{parsed['message_id'] or 'none'}; token in the target's transcript: "
                     f"{'yes' if was else 'no' if was is False else 'unreadable'}")
            if state == HELD:
                proof = STEP[kind].format(to=s["to"]) + ". " + proof
            elif state == RELAYED:
                proof += ". " + AWAIT
            extra = {"kind": kind}
            if state == RUNNING:
                extra.update(to=s["to"], token=s["token"], started_utc=plan.get("at"), delivery=parsed["delivery"])
            put(iid, state, proof, **extra)
    for rc in plan.get("rechecks", []):
        was = wake.seen(seen_raw.get(rc["token"]), str(rc.get("to")))
        v = wake.verdict(rc.get("delivery"), was, wake.minutes_between(rc.get("started"), now), HOLD_LIMIT_MIN)
        kind = rc.get("kind") or "carry_out"
        state = _state_for(kind, v)
        proof = (f"recheck of the send to {rc.get('to')}: token in the target's transcript: "
                 f"{'yes' if was else 'no' if was is False else 'unreadable'}")
        if state == HELD:
            proof = STEP[kind].format(to=rc.get("to")) + ". " + proof
        elif state == RELAYED:
            proof += ". " + AWAIT
        extra = {"kind": kind}
        if state == RUNNING:
            extra.update(to=rc.get("to"), token=rc["token"], started_utc=rc.get("started"), delivery=rc.get("delivery"))
        put(rc["id"], state, proof, **extra)
    for iid in plan.get("refused", []):
        put(iid, HELD, "not carried out: " + plan["decisions"][iid]["why"], kind="refuse")
    for iid in plan.get("no_target", []):
        put(iid, FAILED, "not sent: " + plan["decisions"][iid].get("target_why", "no target"),
            kind=plan["decisions"][iid]["kind"])
    cr = card_result or {}
    written = card_written(cr.get("raw"))
    for c in plan.get("cards", []):
        iid = c["id"]
        if iid in cr.get("skipped", {}):
            state, why = cr["skipped"][iid]
            put(iid, state, why, kind="card")
        elif iid in cr.get("same", []):
            put(iid, RELAYED, f"card {c['card']} already carries answer {c['opt']}. {AWAIT}", link=ROUTER_DESK,
                kind="card")
        elif written is True:
            put(iid, RELAYED, f"answer {c['opt']} written on card {c['card']} ({str(cr.get('raw'))[:160]}); the wake "
                f"pass routes it to the asker. {AWAIT}", link=ROUTER_DESK, kind="card")
        elif written is False:
            put(iid, FAILED, f"the card write was refused: {str(cr.get('raw'))[:200]}", link=ROUTER_DESK, kind="card")
        else:
            put(iid, UNKNOWN, f"no readable result for the write on card {c['card']}", link=ROUTER_DESK, kind="card")
    for st in plan.get("stale", []):
        extra = {"requeued": True} if st["state"] == QUEUED else {}
        put(st["id"], st["state"], st["why"], **extra)
    writes, unpinned = [], []
    for iid in sorted(final):
        if iid in versions:
            writes.append({"op": "update", "collection": "walk", "doc_id": iid, "data": {"exec": final[iid]},
                           "if_version": int(versions[iid])})
        else:
            unpinned.append(iid)
    counts = {k: sum(1 for e in final.values() if e["state"] == k)
              for k in (RELAYED, HELD, FAILED, UNKNOWN, RUNNING, QUEUED)}
    summary = ("OWNER-WALK " + " ".join(f"{k}={v}" for k, v in counts.items())
               + f" deferred={len(plan.get('deferred', []))} unpinned={len(unpinned)}")
    return {"exec": final, "writes": writes, "unpinned": unpinned, "summary": summary, "counts": counts}


# ---- command line -------------------------------------------------------------------------------------

def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _versions(path) -> dict:
    try:
        v = _read_json(path)
    except (OSError, ValueError):
        return {}
    return {str(k): int(n) for k, n in v.items()} if isinstance(v, dict) else {}


def _batch_files(writes: list, folder: Path) -> list:
    """The writes with each document's fields in a file of its own, ready for ArtifactData batch `writes`."""
    folder.mkdir(parents=True, exist_ok=True)
    out = []
    for w in writes:
        path = (folder / f"{w['doc_id']}.json").resolve()
        path.write_text(json.dumps(w["data"], indent=2, ensure_ascii=False), encoding="utf-8")
        out.append({k: v for k, v in w.items() if k not in ("data", "walk_id")} | {"file_path": str(path)})
    return out


def cmd_plan(a) -> int:
    try:
        items = _read_json(a.items)
    except (OSError, ValueError) as exc:
        print(f"OWNER-WALK UNKNOWN: cannot read items ({exc.__class__.__name__})")
        return 2
    folder = Path(a.rows) / "walk"
    files = sorted(folder.glob("*.json")) if folder.is_dir() else []
    # The page always has rows; a pass that sees none cannot tell an empty queue from a failed read.
    if not files or len(files) != a.count:
        print(f"OWNER-WALK UNKNOWN: the list reported {a.count} walk rows but {len(files)} files are in {folder}")
        return 2
    rows = {}
    for f in files:
        try:
            d = _read_json(f)
        except ValueError:
            print(f"OWNER-WALK UNKNOWN: row file {f.name} is not JSON")
            return 2
        # Keyed by the document id (the file name the export chose), never by the row's own `id` field: a row is
        # viewer-written, and one document must not speak for another item.
        rows[f.stem] = d if isinstance(d, dict) else {}
    versions = _versions(a.versions)
    router_id = None
    if a.router_current:
        try:
            cur = _read_json(a.router_current)
            router_id = cur.get("session_id") if isinstance(cur, dict) else None
        except (OSError, ValueError):
            router_id = None
    sessions = wake.load_sessions(a.sessions_dir)
    plan = make_plan(items, rows, versions, sessions, router_id, a.project, a.self_id, a.already_sent,
                     a.max_sends, a.max_defaults, a.now)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "plan.json").write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    run = running_writes(plan, items, versions)
    (out / "running.json").write_text(json.dumps(_batch_files(run, out / "running"), indent=2), encoding="utf-8")
    if run:
        print(f"RUNNING rows={','.join(w['doc_id'] for w in run)} batch={out / 'running.json'}")
    for c in plan["cards"]:
        print(f"CARD walk={c['id']} card={c['card']} opt={c['opt']}")
    for s in plan["sends"]:
        msg = out / f"msg-{s['token']}.txt"
        msg.write_text(s["text"], encoding="utf-8")
        print(f"SEND to={s['to']} token={s['token']} items={','.join(s['ids'])} message={msg}")
    for rc in plan["rechecks"]:
        print(f"RECHECK walk={rc['id']} to={rc['to']} token={rc['token']}")
    if sessions is None:
        print("WARNING: no readable session store; every item went to router/current or has no target")
    for st in plan["stale"]:
        print(f"STALE walk={st['id']} -> {st['state']}")
    acted = run or plan["refused"] or plan["no_target"] or plan["rechecks"] or plan["cards"] or plan["stale"]
    if not acted:
        print(f"OWNER-WALK nothing to do: {len(rows)} rows read, none queued"
              + (f"; unpinned {','.join(plan['unpinned'])}" if plan["unpinned"] else ""))
        return 0
    print(f"plan: {len(plan['sends'])} send(s), {len(plan['cards'])} card(s), {len(plan['rechecks'])} recheck(s), "
          f"refused {plan['refused'] or 'none'}, no target {plan['no_target'] or 'none'}, "
          f"deferred {len(plan['deferred'])}, unpinned {plan['unpinned'] or 'none'}")
    return 0


def cmd_cards(a) -> int:
    plan = _read_json(a.plan)
    cards = {}
    for f in sorted(Path(a.cards).glob("*.json")) if Path(a.cards).is_dir() else []:
        try:
            cards[f.stem] = _read_json(f)
        except ValueError:
            continue
    res = card_writes(plan, cards, _versions(a.versions), a.now)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "cards.json").write_text(json.dumps({"skipped": res["skipped"], "same": res["same"]}, indent=2), encoding="utf-8")
    (out / "card_batch.json").write_text(json.dumps(_batch_files(res["writes"], out / "cardfiles"), indent=2), encoding="utf-8")
    for w in res["writes"]:
        print(f"WRITE card={w['doc_id']} answer={w['data']['answer']} (walk {w['walk_id']})")
    for iid, (state, why) in sorted(res["skipped"].items()):
        print(f"SKIP walk={iid} {state}: {why}")
    return 0


def cmd_judge(a) -> int:
    plan = _read_json(a.plan)
    work = Path(a.work)
    sends, seen_raw = {}, {}
    for tok in [s["token"] for s in plan.get("sends", [])]:
        t = _read_text(work / "sent" / f"{tok}.txt")
        if t is not None:
            sends[tok] = t
    for tok in [s["token"] for s in plan.get("sends", [])] + [r["token"] for r in plan.get("rechecks", [])]:
        t = _read_text(work / "seen" / f"{tok}.txt")
        if t is not None:
            seen_raw[tok] = t
    card_result = {"raw": _read_text(work / "card_result.txt"), "skipped": {}, "same": []}
    try:
        c = _read_json(work / "cards.json")
        card_result["skipped"] = {k: tuple(v) for k, v in (c.get("skipped") or {}).items()}
        card_result["same"] = list(c.get("same") or [])
    except (OSError, ValueError):
        if plan.get("cards"):
            card_result["skipped"] = {x["id"]: (UNKNOWN, "the cards step left no cards.json") for x in plan["cards"]}
    res = judge(plan, sends, seen_raw, card_result, _versions(a.versions), a.now)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "batch.json").write_text(json.dumps(_batch_files(res["writes"], out / "rows"), indent=2), encoding="utf-8")
    for iid, e in sorted(res["exec"].items()):
        print(f"{e['state']:<8} {iid}")
    if res["unpinned"]:
        print(f"NOT WRITTEN (no version to pin): {','.join(res['unpinned'])}")
    print(res["summary"])
    if res["counts"][FAILED]:
        return 1
    return 2 if res["counts"][UNKNOWN] or res["counts"][RUNNING] else 0


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--items", required=True, help="the page's items.json")
    p.add_argument("--rows", required=True, help="the out_dir of the ArtifactData list of collection walk")
    p.add_argument("--count", required=True, type=int, help="how many documents the list said it saved")
    p.add_argument("--versions", required=True, help='{"<row id>": <version>} from the list result lines')
    p.add_argument("--sessions-dir", default=None)
    p.add_argument("--router-current", default=None)
    p.add_argument("--project", default="novah estate")
    p.add_argument("--self", dest="self_id", default=None)
    p.add_argument("--already-sent", type=int, default=0, help="sends the wake pass already made this pass")
    p.add_argument("--max-sends", type=int, default=MAX_SENDS)
    p.add_argument("--max-defaults", type=int, default=MAX_DEFAULTS)
    p.add_argument("--now", default=None)
    p.add_argument("--out", required=True)
    c = sub.add_parser("cards")
    c.add_argument("--plan", required=True)
    c.add_argument("--cards", required=True, help="folder of the Router desk cards read with out_dir (…/questions)")
    c.add_argument("--versions", required=True, help='{"<card id>": <version>} from the get result lines')
    c.add_argument("--now", default=None)
    c.add_argument("--out", required=True, help="the pass's work folder")
    j = sub.add_parser("judge")
    j.add_argument("--plan", required=True)
    j.add_argument("--work", required=True, help="sent/, seen/, cards.json, card_result.txt")
    j.add_argument("--versions", required=True, help="the walk row versions after the running batch")
    j.add_argument("--now", default=None)
    j.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    return {"plan": cmd_plan, "cards": cmd_cards, "judge": cmd_judge}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
