#!/usr/bin/env python
"""Send a session a message and say whether it landed: DELIVERED, HELD, UNDELIVERED or UNKNOWN.

    python send_confirm.py prepare --from ID --to ID --subject TEXT --body-file FILE --out DIR
                                   [--sends-so-far N] [--now ISO]
    python send_confirm.py judge   --plan DIR/plan.json --sent FILE --seen FILE [--attempts N] [--now ISO]
                                   [--out DIR]

The script does everything that does not need a Claude tool. The session that sends (the
`leadfuel-way:message` skill) does the two tool calls in between: it sends the prepared text with
`mcp__ccd_session_mgmt__send_message` to the target's `local_` id, writes the tool's whole result to a
file, and only after the send has returned searches the target's transcript for the token and writes
the whole output to a second file. Nothing here touches the network and nothing changes any session's
permission mode.

The four states are the same four `wake_on_answer.py` uses, and the reading of the send result, the
transcript search and the verdict are that script's own functions (imported, not copied), so a desk and
the wake watcher can never disagree about what "delivered" means:

    DELIVERED    the TARGET's own transcript holds the token. Nothing else counts. A send is not
                 delivered because it was sent, and a tool that says "delivered" is a claim.
    HELD         the send was queued behind a turn, or held for approval, and the token is not in the
                 target's transcript yet. Check again later with the same plan; never resend.
    UNDELIVERED  the send failed, or it stayed HELD/UNKNOWN past the hold limit. A durable fallback
                 record is written (fallback.json, pr-comment.txt).
    UNKNOWN      the send said nothing readable, or said delivered/queued and the search could not
                 confirm it. Never a pass.

`next` says what to do, in one word: DONE, RECHECK, RESEND (once, with the same file, so the same
token: a receiver drops a token it has already seen), or FALLBACK. A resend is offered only when it can
help: a missing target or a message to yourself will not get better, and a send the tool called
delivered or queued is never repeated.

Exit codes: 0 DELIVERED, 1 UNDELIVERED, 2 HELD or UNKNOWN, or inputs that could not be read.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def _wake():
    """The wake watcher's classifier. Loaded by path so this script runs from any folder."""
    name = "wake_on_answer_for_send_confirm"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / "wake_on_answer.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


W = _wake()
DELIVERED, HELD, UNDELIVERED, UNKNOWN = W.DELIVERED, W.HELD, W.UNDELIVERED, W.UNKNOWN
STATES = W.STATES
HOLD_LIMIT_MIN = W.HOLD_LIMIT_MIN
MAX_ATTEMPTS = 2           # the first send and one resend
SEND_WARN_AT = 8           # messaging pauses after 10 sends until the owner types
LONG_BODY = 1500           # a message that must land is a pointer to a pushed note, not the note
SUBJECT_MAX = 120
BY = "send-confirm"

# Reasons a resend cannot fix. Measured on 2026-10-13 (see tests/test_wake_on_answer.py).
PERMANENT = re.compile(r"not found|current session|no such session|refusing to send", re.I)


def valid_sid(value) -> bool:
    return W.valid_sid(value)


def message_token(sender: str, target: str, subject: str, body: str, now: str) -> str:
    seed = f"{sender}|{target}|{subject}|{body}|{now}"
    return "MSG-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:10]


def compose(token: str, sender: str, subject: str, body: str) -> str:
    """The text that is sent. The token is in it, so the target's transcript can prove arrival."""
    return (f"MSG {token} from {sender} | {subject}\n\n{body.strip()}\n\n"
            f"(token {token}: if you have already seen this token, ignore this copy. A reply is only "
            f"needed if the message asks a question.)")


def make_plan(sender, target, subject, body, now=None, sends_so_far=0) -> dict:
    """{'errors': [...]} when the send must not go out; else the plan with the text to send."""
    now = now or W.iso_now()
    errors, warnings = [], []
    if not valid_sid(sender):
        errors.append(f"--from must be your own full local_ session id (get_session self), got {sender!r}")
    if not valid_sid(target):
        errors.append("--to must be the target's full local_ session id: a name-addressed send is held "
                      f"for approval when the receiver is in another permission mode, got {target!r}")
    if valid_sid(sender) and sender == target:
        errors.append("a session cannot message itself (the app refuses it)")
    subject = " ".join(str(subject or "").split())
    if not subject:
        errors.append("--subject is required: it is the one line a fallback record may carry")
    elif len(subject) > SUBJECT_MAX:
        errors.append(f"--subject is {len(subject)} characters; keep it to {SUBJECT_MAX} (ids and status only)")
    if not str(body or "").strip():
        errors.append("the body is empty")
    if errors:
        return {"errors": errors}
    token = message_token(sender, target, subject, body, now)
    if len(body) > LONG_BODY:
        warnings.append(f"the body is {len(body)} characters: for a message that must land, push a note and "
                        "send its path")
    if sends_so_far >= SEND_WARN_AT:
        warnings.append(f"{sends_so_far} sends so far: messaging pauses after 10 until the owner types; "
                        "fold items into one message and spend what is left on the sends that must land")
    return {"errors": [], "warnings": warnings, "token": token, "from": sender, "to": target,
            "subject": subject, "at": now, "text": compose(token, sender, subject, body),
            "sends_so_far": sends_so_far}


def reason(delivery, sent_text) -> str:
    """'permanent' when a resend cannot help, 'transient' when the tool refused for another reason,
    'silent' when the send said nothing readable, 'accepted' when the tool took it (delivered, queued, held)."""
    if delivery in ("delivered", "queued", "held"):
        return "accepted"
    if delivery == "undelivered":
        return "permanent" if PERMANENT.search(str(sent_text or "")) else "transient"
    return "silent"


def next_step(state: str, why: str, attempts: int) -> str:
    if state == DELIVERED:
        return "DONE"
    if state == HELD:
        return "RECHECK"
    if state == UNDELIVERED:
        if why in ("transient", "silent") and attempts < MAX_ATTEMPTS:
            return "RESEND"
        return "FALLBACK"
    # UNKNOWN: the tool took it but the search could not confirm yet -> look again; the tool said nothing -> one resend.
    if why == "accepted":
        return "RECHECK"
    return "RESEND" if attempts < MAX_ATTEMPTS else "FALLBACK"


def judge(plan: dict, sent_text, seen_raw, attempts: int = 1, now=None) -> dict:
    now = now or W.iso_now()
    parsed = W.parse_send(sent_text)
    was_seen = W.seen(seen_raw, plan["to"])
    minutes = W.minutes_between(plan.get("at"), now)
    state = W.verdict(parsed["delivery"], was_seen, minutes, HOLD_LIMIT_MIN)
    why = reason(parsed["delivery"], sent_text)
    step = next_step(state, why, attempts)
    if state == UNDELIVERED and parsed["delivery"] != "undelivered":
        # Held, silent or unconfirmed past the limit: no resend (it may still arrive; the token lets the
        # receiver drop a second copy), the record goes to a durable channel.
        step = "FALLBACK"
    out = {"state": state, "next": step, "delivery": parsed["delivery"], "message_id": parsed["message_id"],
           "seen": was_seen, "token": plan["token"], "to": plan["to"], "attempts": attempts, "reason": why}
    if step == "FALLBACK":
        out["fallback"] = {plan["token"]: {
            "token": plan["token"], "from": plan["from"], "to": plan["to"], "subject": plan["subject"],
            "state": state, "delivery": parsed["delivery"], "reason": why, "attempts": attempts,
            "first_sent_at": plan.get("at"), "at": now, "by": BY,
            "next": "the receiving session, or the live router, reads this record and acts on it; "
                    "the sender will not resend, and the message may still arrive late (it carries a token)"}}
        out["pr_comment"] = (f"Undelivered session message {plan['token']} from {plan['from']} to {plan['to']}: "
                             f"{plan['subject']} (state {state}, {attempts} attempt(s), {now}). "
                             "The sender's note holds the detail; ids and status only here.")
    out["summary"] = (f"SEND-CONFIRM {state} next={step} token={plan['token']} to={plan['to']} "
                      f"delivery={parsed['delivery']} seen={was_seen} attempts={attempts}")
    return out


# ---- command line ----------------------------------------------------------------------------------

def _read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def cmd_prepare(args) -> int:
    body = _read_text(args.body_file)
    if body is None:
        print(f"SEND-CONFIRM UNKNOWN: cannot read the body file {args.body_file}")
        return 2
    plan = make_plan(args.sender, args.to, args.subject, body, now=args.now, sends_so_far=args.sends_so_far)
    if plan["errors"]:
        for e in plan["errors"]:
            print(f"REFUSED: {e}")
        return 2
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    msg = out / f"msg-{plan['token']}.txt"
    msg.write_text(plan["text"], encoding="utf-8")
    (out / "plan.json").write_text(json.dumps({k: v for k, v in plan.items() if k != "text"},
                                              indent=2, ensure_ascii=False), encoding="utf-8")
    for w in plan["warnings"]:
        print(f"WARNING: {w}")
    print(f"SEND to={plan['to']} token={plan['token']} message={msg}")
    return 0


def cmd_judge(args) -> int:
    try:
        plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
        plan["token"], plan["to"], plan["from"], plan["subject"]
    except (OSError, ValueError, KeyError):
        print(f"SEND-CONFIRM UNKNOWN: cannot read a plan from {args.plan}")
        return 2
    res = judge(plan, _read_text(args.sent), _read_text(args.seen), attempts=args.attempts, now=args.now)
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "verdict.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
        if "fallback" in res:
            (out / "fallback.json").write_text(json.dumps(res["fallback"], indent=2, ensure_ascii=False),
                                               encoding="utf-8")
            (out / "pr-comment.txt").write_text(res["pr_comment"], encoding="utf-8")
    print(res["summary"])
    return {DELIVERED: 0, UNDELIVERED: 1}.get(res["state"], 2)


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare", help="stamp a message with a token and write the text to send")
    p.add_argument("--from", dest="sender", required=True, help="your own local_ session id")
    p.add_argument("--to", required=True, help="the target's local_ session id (never a name)")
    p.add_argument("--subject", required=True, help="one line, ids and status only; a fallback record may carry it")
    p.add_argument("--body-file", required=True)
    p.add_argument("--sends-so-far", type=int, default=0)
    p.add_argument("--now", default=None)
    p.add_argument("--out", required=True)
    j = sub.add_parser("judge", help="turn the send result and the transcript search into a state and a next step")
    j.add_argument("--plan", required=True)
    j.add_argument("--sent", required=True, help="the send tool's whole result, saved as text")
    j.add_argument("--seen", required=True, help="search_session_transcripts for the token, whole output")
    j.add_argument("--attempts", type=int, default=1, help="1 after the first send, 2 after a resend")
    j.add_argument("--now", default=None)
    j.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    return cmd_prepare(args) if args.cmd == "prepare" else cmd_judge(args)


if __name__ == "__main__":
    sys.exit(main())
