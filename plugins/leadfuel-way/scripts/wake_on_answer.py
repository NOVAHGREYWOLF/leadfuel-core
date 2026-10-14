#!/usr/bin/env python
"""Wake on answer: route an answered Router desk card to the session that asked, and say whether it landed.

    python wake_on_answer.py plan  --cards DIR --count N --router-current FILE [--self ID] [--only q1,q2]
                                   [--now ISO] [--max-sends 5] --out PLAN.json
    python wake_on_answer.py judge --plan PLAN.json --work DIR [--now ISO] --out DIR

The script does everything that does not need a Claude tool. The session that runs a pass (the
`leadfuel-way:wake` skill) does the tool calls in between: it reads the cards with ArtifactData, sends
each planned message, searches the target's transcript for the message's token, and writes the
results back. Nothing here touches the network.

A card is pending when the owner has answered it (`answer` set; a step card's `not_yet` is not an
answer) and `routed` is empty (the page writes `routed: null` on every click and every note). Its
target is `asker_session` when that is a full `local_` id, else a full `local_` id inside the `asker`
text, else the live router from the Build Board's `router/current`.

Four states, and only one of them is a pass:
    DELIVERED    the TARGET's own transcript holds the card's token. Nothing else counts: a send is
                 not delivered because it was sent, and a tool that says "delivered" is a claim.
    HELD         the send was queued behind a turn, or held for approval, and the token is not in the
                 target's transcript yet. Rechecked on the next pass, never resent.
    UNDELIVERED  the send failed, or it stayed HELD/UNKNOWN past HOLD_LIMIT_MIN. A durable note goes
                 on the Build Board (router/wake_undelivered) so the next router finds it.
    UNKNOWN      the pass could not establish either (no send result, no readable search).
The card never carries the token: a router reading the card would otherwise put it in its own
transcript and a message that never arrived would read as delivered.

Exit codes: 0 nothing to do or every card DELIVERED, 1 any UNDELIVERED, 2 any HELD or UNKNOWN, or a
plan that could not read its inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

DELIVERED, HELD, UNDELIVERED, UNKNOWN = "DELIVERED", "HELD", "UNDELIVERED", "UNKNOWN"
STATES = (DELIVERED, HELD, UNDELIVERED, UNKNOWN)
HOLD_LIMIT_MIN = 120   # a HELD or UNKNOWN card becomes UNDELIVERED (with a durable note) after this long
MAX_SENDS = 5          # messaging pauses after 10 sends until the owner types: spend few per pass
BY = "wake-on-answer"

SID = re.compile(r"(?<![\w-])local_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?![\w-])")
DELIVERY = re.compile(r"delivery:\s*([a-z_]+)", re.I)
MESSAGE_ID = re.compile(r"message_id:\s*([0-9A-Za-z-]+)")


# ---- reading what the tools said -----------------------------------------------------------------

def parse_send(text) -> dict:
    """{'delivery': delivered|queued|held|undelivered|None, 'message_id'} from a send tool's result text.

    A cross-session notice that the message is held for approval wins over any delivery word: the
    session has it, its Claude has not read it. None means the text did not say (not a pass)."""
    if not text:
        return {"delivery": None, "message_id": None}
    text = str(text)
    low = text.lower()
    mid = MESSAGE_ID.search(text)
    out = {"delivery": None, "message_id": mid.group(1) if mid else None}
    notice = "delivery notice" in low
    if "approval" in low or (notice and re.search(r"\bheld\b|\bholding\b", low)):
        out["delivery"] = "held"
        if notice and re.search(r"\bexpired\b|\brefused\b|\brejected\b", low):
            out["delivery"] = "undelivered"
        return out
    m = DELIVERY.search(text)
    word = m.group(1).lower() if m else ""
    if word in ("delivered", "queued", "undelivered"):
        out["delivery"] = word
    elif "not delivered" in low:
        out["delivery"] = "undelivered"
    return out


def _json_array(raw: str):
    """The first JSON array that starts a line (search_session_transcripts prints a warning line first)."""
    dec = json.JSONDecoder()
    for m in re.finditer(r"(?m)^\s*\[", raw):
        try:
            value, _ = dec.raw_decode(raw[m.end() - 1:])
        except ValueError:
            continue
        if isinstance(value, list):
            return value
    return None


def seen(raw, target: str):
    """True when the search hits include the target session itself, False when the search read cleanly
    and the target is not among its hits, None when the search output cannot be read."""
    if not raw:
        return None
    rows = _json_array(str(raw))
    if rows is None:
        return None
    return any(isinstance(r, dict) and r.get("sessionId") == target for r in rows)


def verdict(delivery, was_seen, minutes, limit: int = HOLD_LIMIT_MIN) -> str:
    """The state of one card. DELIVERED needs the target's transcript as evidence; nothing else gives it."""
    if was_seen is True:
        return DELIVERED
    if delivery == "undelivered":
        return UNDELIVERED
    over = minutes is not None and minutes > limit
    if delivery in ("queued", "held"):
        return UNDELIVERED if over else HELD
    return UNDELIVERED if over else UNKNOWN


# ---- cards -----------------------------------------------------------------------------------------

def valid_sid(value) -> bool:
    return bool(value) and bool(SID.fullmatch(str(value).strip()))


def resolve_target(card: dict, router_id) -> tuple:
    """(session id or None, why). A row id like `intelligence/local_8e471cfd-1` is not a session."""
    own = card.get("asker_session")
    if valid_sid(own):
        return str(own).strip(), "asker_session"
    m = SID.search(str(card.get("asker") or ""))
    if m:
        return m.group(0), "the asker text names this session"
    if valid_sid(router_id):
        return str(router_id).strip(), "the asker names no session, so the live router (router/current)"
    return None, "the asker names no session and router/current has no session id"


def answered(card: dict) -> bool:
    ans = card.get("answer")
    if ans is None:
        return False
    return not (card.get("kind") == "step" and ans == "not_yet")


def unrouted(card: dict) -> bool:
    routed = card.get("routed")
    return not (isinstance(routed, dict) and routed.get("at"))


def same_answer(card: dict, wake: dict) -> bool:
    return wake.get("answered_at") == card.get("answered_at") and wake.get("note_at") == card.get("note_at")


def pending(cards: dict, only=None) -> list:
    """[(card id, 'send' | 'recheck')] in card-id order."""
    out = []
    for cid in sorted(cards):
        card = cards[cid] or {}
        if only and cid not in only:
            continue
        if not only and card.get("status") == "withdrawn":
            continue
        if not answered(card) or not unrouted(card):
            continue
        wake = card.get("wake") if isinstance(card.get("wake"), dict) else {}
        if wake.get("state") and same_answer(card, wake):
            if wake["state"] in (HELD, UNKNOWN):
                out.append((cid, "recheck"))
            continue  # DELIVERED or UNDELIVERED for this very answer: finished
        out.append((cid, "send"))
    return out


def card_token(cid: str, card: dict, target: str) -> str:
    seed = f"{cid}|{card.get('answered_at')}|{card.get('note_at')}|{target}"
    return "WAKE-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:10]


def _label(card: dict) -> str:
    for opt in card.get("options") or []:
        if isinstance(opt, dict) and opt.get("key") == card.get("answer"):
            return str(opt.get("label") or "")
    return ""


def _short(text, n: int) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def compose(items: list, to_router: bool) -> str:
    """One message for one target. items: [(card id, card, token)]."""
    pairs = ", ".join(f"{cid} = {card.get('answer')}" for cid, card, _ in items)
    who = ("You get these as the live router: the asker text names no session." if to_router
           else "You are the session that asked.")
    lines = [f"WAKE-ON-ANSWER: the owner answered {len(items)} card(s) on the Router desk page: {pairs}. {who}"]
    for cid, card, token in items:
        label = _label(card)
        head = f"- {cid} = {card.get('answer')}" + (f" ({_short(label, 80)})" if label else "")
        if card.get("by_default"):
            head += " [recorded as the default]"
        lines.append(f"{head}: {_short(card.get('title'), 140)}")
        if card.get("note"):
            lines.append(f"  the owner's note: {_short(card.get('note'), 500)}")
        lines.append(f"  asker: {_short(card.get('asker'), 160)}")
        lines.append(f"  token {token}")
    lines.append("The watcher records the delivery on each card under `wake`, and once it has seen this message in "
                 "your transcript it writes `routed` (by wake-on-answer). When you act on a card, put what you did in "
                 "its routed.note. No reply to the watcher is needed.")
    return "\n".join(lines)


def _card_view(card: dict) -> dict:
    keep = ("answer", "answered_at", "note_at", "title", "asker", "kind", "by_default")
    view = {k: card.get(k) for k in keep}
    view["prior_sends"] = (card.get("wake") or {}).get("sends", 0) if isinstance(card.get("wake"), dict) else 0
    return view


def make_plan(cards: dict, router_id, self_id=None, only=None, max_sends: int = MAX_SENDS, now=None) -> dict:
    now = now or iso_now()
    plan = {"at": now, "router_id": router_id, "self_id": self_id, "sends": [], "rechecks": [],
            "deferred": [], "self": [], "no_target": [], "cards": {}, "why": {}}
    groups: dict = {}
    for cid, action in pending(cards, only=only):
        card = cards[cid]
        plan["cards"][cid] = _card_view(card)
        if action == "recheck":
            wake = card["wake"]
            to = wake.get("to")
            plan["rechecks"].append({"card": cid, "to": to, "search_token": card_token(cid, card, str(to)),
                                     "delivery": wake.get("delivery"), "first_sent_at": wake.get("first_sent_at"),
                                     "sends": wake.get("sends", 1), "why": wake.get("why"),
                                     "message_id": wake.get("message_id")})
            continue
        target, why = resolve_target(card, router_id)
        plan["why"][cid] = why
        if target is None:
            plan["no_target"].append(cid)
        elif self_id and target == self_id:
            plan["self"].append(cid)
        else:
            groups.setdefault(target, []).append(cid)
    for n, (target, cids) in enumerate(groups.items()):
        if n >= max_sends:
            plan["deferred"].extend(cids)
            continue
        items = [(cid, cards[cid], card_token(cid, cards[cid], target)) for cid in cids]
        as_router = all(plan["why"][c].startswith("the asker names no session") for c in cids)
        plan["sends"].append({"to": target, "why": plan["why"][cids[0]], "cards": cids,
                              "search_token": items[0][2], "tokens": {cid: tok for cid, _, tok in items},
                              "text": compose(items, to_router=as_router)})
    return plan


# ---- judging a pass --------------------------------------------------------------------------------

def parse_time(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def minutes_between(start, end):
    a, b = parse_time(start), parse_time(end)
    if a is None or b is None:
        return None
    if a.tzinfo is None:
        a = a.replace(tzinfo=timezone.utc)
    if b.tzinfo is None:
        b = b.replace(tzinfo=timezone.utc)
    return (b - a).total_seconds() / 60


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def judge(plan: dict, send_results: dict, seen_raw: dict, now=None, versions=None) -> dict:
    """States, the card writes (an ArtifactData batch for the Router desk) and the durable notes for the
    Build Board. send_results and seen_raw are keyed by search_token; versions by card id."""
    now = now or iso_now()
    versions = versions or {}
    states, wakes = {}, {}
    for send in plan.get("sends", []):
        tok, to = send["search_token"], send["to"]
        parsed = parse_send(send_results.get(tok))
        was_seen = seen(seen_raw.get(tok), to)
        minutes = minutes_between(plan.get("at"), now)
        for cid in send["cards"]:
            state = verdict(parsed["delivery"], was_seen, minutes)
            states[cid] = state
            wakes[cid] = {"state": state, "at": now, "to": to, "why": send.get("why"),
                          "delivery": parsed["delivery"], "message_id": parsed["message_id"],
                          "first_sent_at": plan.get("at"), "sends": int(plan["cards"][cid].get("prior_sends") or 0) + 1}
    for rc in plan.get("rechecks", []):
        cid, to = rc["card"], rc["to"]
        was_seen = seen(seen_raw.get(rc["search_token"]), str(to))
        state = verdict(rc.get("delivery"), was_seen, minutes_between(rc.get("first_sent_at"), now))
        states[cid] = state
        wakes[cid] = {"state": state, "at": now, "to": to, "why": rc.get("why"), "delivery": rc.get("delivery"),
                      "message_id": rc.get("message_id"), "first_sent_at": rc.get("first_sent_at"),
                      "sends": rc.get("sends", 1)}
    for cid in plan.get("no_target", []):
        states[cid] = UNDELIVERED
        wakes[cid] = {"state": UNDELIVERED, "at": now, "to": None, "why": plan.get("why", {}).get(cid),
                      "delivery": None, "message_id": None, "first_sent_at": None, "sends": 0}

    writes, fallback, unpinned = [], {}, []
    for cid in sorted(wakes):
        view = plan["cards"][cid]
        wake = dict(wakes[cid], by=BY, answered_at=view.get("answered_at"), note_at=view.get("note_at"))
        data = {"wake": wake}
        if wake["state"] == DELIVERED:
            whom = "the live router" if wake["to"] == plan.get("router_id") else "the session that asked"
            data["routed"] = {"at": now, "by": BY, "to": wake["to"],
                              "note": f"Delivered by wake-on-answer to {whom}; its transcript shows the message. It acts next."}
        if wake["state"] == UNDELIVERED:
            fallback[cid] = {"card": cid, "title": _short(view.get("title"), 140), "answer": view.get("answer"),
                             "answered_at": view.get("answered_at"), "to": wake["to"], "state": UNDELIVERED,
                             "at": now, "delivery": wake["delivery"], "why": wake.get("why"),
                             "next": "the live router reads this card and acts on it; the watcher will not resend this answer"}
        if cid in versions:
            writes.append({"op": "update", "collection": "questions", "doc_id": cid, "data": data,
                           "if_version": int(versions[cid])})
        else:
            unpinned.append(cid)
    counts = {s: sum(1 for v in states.values() if v == s) for s in STATES}
    summary = (f"WAKE-PASS DELIVERED={counts[DELIVERED]} HELD={counts[HELD]} UNDELIVERED={counts[UNDELIVERED]} "
               f"UNKNOWN={counts[UNKNOWN]} self={len(plan.get('self', []))} deferred={len(plan.get('deferred', []))} "
               f"unpinned={len(unpinned)}")
    return {"states": states, "writes": writes, "fallback": fallback, "unpinned": unpinned, "summary": summary}


# ---- command line ----------------------------------------------------------------------------------

def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def cmd_plan(args) -> int:
    try:
        current = _read_json(Path(args.router_current))
    except (OSError, ValueError) as exc:
        print(f"WAKE-PASS UNKNOWN: cannot read router/current ({args.router_current}: {exc.__class__.__name__})")
        return 2
    router_id = current.get("session_id") if isinstance(current, dict) else None
    cards_dir = Path(args.cards)
    files = sorted(cards_dir.glob("*.json")) if cards_dir.is_dir() else []
    if len(files) != args.count:  # a read the files do not confirm is not a read
        print(f"WAKE-PASS UNKNOWN: the query reported {args.count} cards but {len(files)} files are in {cards_dir}")
        return 2
    cards = {}
    for f in files:
        try:
            cards[f.stem] = _read_json(f)
        except ValueError:
            print(f"WAKE-PASS UNKNOWN: card file {f.name} is not JSON")
            return 2
    only = {c.strip() for c in args.only.split(",") if c.strip()} if args.only else None
    plan = make_plan(cards, router_id, self_id=args.self_id, only=only, max_sends=args.max_sends, now=args.now)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    for send in plan["sends"]:
        msg = out.parent / f"msg-{send['search_token']}.txt"
        msg.write_text(send["text"], encoding="utf-8")
        print(f"SEND to={send['to']} token={send['search_token']} cards={','.join(send['cards'])} message={msg}")
    for rc in plan["rechecks"]:
        print(f"RECHECK card={rc['card']} to={rc['to']} token={rc['search_token']}")
    if not valid_sid(router_id):
        print(f"WARNING: router/current session_id is not a session id ({router_id!r}); cards with no asker id have no target")
    if not plan["sends"] and not plan["rechecks"] and not plan["no_target"]:
        print(f"WAKE-PASS nothing to deliver: {len(cards)} unrouted cards read, none answered and pending"
              + (f"; for the runner itself: {','.join(plan['self'])}" if plan["self"] else ""))
        return 0
    print(f"plan: {len(plan['sends'])} send(s), {len(plan['rechecks'])} recheck(s), self {plan['self'] or 'none'}, "
          f"no target {plan['no_target'] or 'none'}, deferred {plan['deferred'] or 'none'}")
    return 0


def cmd_judge(args) -> int:
    plan = _read_json(Path(args.plan))
    work = Path(args.work)
    sends, seen_raw = {}, {}
    for tok in [s["search_token"] for s in plan.get("sends", [])]:
        text = _read_text(work / "sent" / f"{tok}.txt")
        if text is not None:
            sends[tok] = text
    for tok in [s["search_token"] for s in plan.get("sends", [])] + [r["search_token"] for r in plan.get("rechecks", [])]:
        raw = _read_text(work / "seen" / f"{tok}.txt")
        if raw is not None:
            seen_raw[tok] = raw
    try:
        versions = _read_json(work / "versions.json")
    except (OSError, ValueError):
        versions = {}
    result = judge(plan, sends, seen_raw, now=args.now, versions=versions)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "writes.json").write_text(json.dumps(result["writes"], indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "fallback.json").write_text(json.dumps(result["fallback"], indent=2, ensure_ascii=False), encoding="utf-8")
    for cid, state in sorted(result["states"].items()):
        print(f"{state:<11} {cid}")
    if result["unpinned"]:
        print(f"NOT WRITTEN (no version to pin): {','.join(result['unpinned'])}")
    print(result["summary"])
    states = set(result["states"].values())
    if UNDELIVERED in states:
        return 1
    if states & {HELD, UNKNOWN}:
        return 2
    return 0


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan", help="pick the pending cards and write one message per target")
    p.add_argument("--cards", required=True, help="the folder of card files ArtifactData wrote (<out_dir>/questions)")
    p.add_argument("--count", required=True, type=int, help="how many documents the query said it returned")
    p.add_argument("--router-current", required=True, help="router/current from the Build Board, saved with out_dir")
    p.add_argument("--self", dest="self_id", default=None, help="the session running this pass; never sent to")
    p.add_argument("--only", default=None, help="comma list of card ids; reaches a withdrawn card (the proof card)")
    p.add_argument("--max-sends", type=int, default=MAX_SENDS)
    p.add_argument("--now", default=None)
    p.add_argument("--out", required=True)
    j = sub.add_parser("judge", help="turn the send results and searches into states and writes")
    j.add_argument("--plan", required=True)
    j.add_argument("--work", required=True, help="folder with sent/<token>.txt, seen/<token>.txt, versions.json")
    j.add_argument("--now", default=None)
    j.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    return cmd_plan(args) if args.cmd == "plan" else cmd_judge(args)


if __name__ == "__main__":
    sys.exit(main())
