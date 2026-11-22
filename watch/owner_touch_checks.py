"""WATCH: the weekly synthetic check and the stuck-session detector for the owner-touch ledger.

Both are READ-ONLY and send nothing (Law 9): no push, no email, no webhook, no network. They judge
evidence that someone else gathered or that already sits in local transcripts, and they say UNKNOWN
wherever the evidence cannot establish a state. A check that cannot see must not report a state.

  python watch/owner_touch_checks.py synthetic --evidence evidence.json
  python watch/owner_touch_checks.py stuck --minutes 30 --cards cards.json

Exit 0 = PASS / nothing stuck, 1 = FAIL / stuck sessions found, 2 = UNKNOWN. Only ids and counts are
printed; no message text is read into the output.

SYNTHETIC. A fake card and a fake guard are raised on purpose by the runner, which writes an evidence
file (JSON, ids and states only):
  card_id            id of the fake card (string)
  push               "confirmed" | "requested" | "failed" | absent. Only the device-side or
                     delivery-receipt confirmation is "confirmed"; "requested" means a send was
                     asked for and nothing proves arrival, which is UNKNOWN.
  answer_delivered   true | false | absent: the answer given on the phone reached the asker
                     (proved from the asker's own transcript by the runner)
  human_touches      number of owner-typed touches in the window, or absent when not counted
PASS needs push confirmed, answer delivered and human_touches == 0. Any definite negative is FAIL.
Anything missing or only "requested" is UNKNOWN, never PASS.

STUCK. A session is stuck when its last transcript event is an assistant question or a permission
wait, it has been idle longer than --minutes, and no card or push is recorded behind it. The record
of cards is --cards (JSON list of session ids that have a card or push). Without it the "nothing
behind it" half cannot be established, so the result is UNKNOWN, not "none stuck".

Stdlib only.
"""
import argparse
import glob
import json
import os
import sys
import time

ROOT = os.path.expanduser("~/.claude/projects")
TAIL_BYTES = 65536


def judge_synthetic(ev):
    """Return (verdict, reasons) for an evidence dict. Verdict is PASS, FAIL or UNKNOWN."""
    if not isinstance(ev, dict) or not ev.get("card_id"):
        return "UNKNOWN", ["no evidence for a raised card (card_id absent)"]
    fails, unknown = [], []
    push = ev.get("push")
    if push == "confirmed":
        pass
    elif push == "failed":
        fails.append("push failed")
    elif push == "requested":
        unknown.append("push was requested but delivery is not confirmed")
    else:
        unknown.append("no push evidence")
    ans = ev.get("answer_delivered")
    if ans is True:
        pass
    elif ans is False:
        fails.append("answer did not reach the asker")
    else:
        unknown.append("answer delivery not established")
    touches = ev.get("human_touches")
    if isinstance(touches, bool) or not isinstance(touches, int) or touches < 0:
        unknown.append("owner touches in the window not counted")
    elif touches > 0:
        fails.append("owner typed %d time(s) during the check" % touches)
    if fails:
        return "FAIL", fails + unknown
    if unknown:
        return "UNKNOWN", unknown
    return "PASS", ["push confirmed, answer delivered, owner typed nothing"]


def _last_event(path):
    """Last JSON object in the file's tail, or None when none can be read."""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as fh:
            fh.seek(max(0, size - TAIL_BYTES))
            tail = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    for line in reversed(tail.splitlines()):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if isinstance(o, dict) and o.get("type") in ("user", "assistant"):
            return o
    return None


def waiting_on_owner(event):
    """True when the last event is an assistant question or a tool request that waits on the owner."""
    if not event or event.get("type") != "assistant":
        return False
    ct = (event.get("message") or {}).get("content")
    if isinstance(ct, str):
        return ct.rstrip().endswith("?")
    if not isinstance(ct, list) or not ct:
        return False
    last = ct[-1]
    if not isinstance(last, dict):
        return False
    if last.get("type") == "tool_use":
        return last.get("name") == "AskUserQuestion"
    if last.get("type") == "text":
        return str(last.get("text", "")).rstrip().endswith("?")
    return False


def find_stuck(root, minutes, cards, now=None):
    """Return (verdict, scanned, stuck_ids, reason). cards is a set of ids, or None when unknown."""
    now = time.time() if now is None else now
    files = glob.glob(os.path.join(root, "*", "*.jsonl"))
    if not files:
        return "UNKNOWN", 0, [], "no transcript files found under the root"
    if cards is None:
        return "UNKNOWN", len(files), [], ("no record of cards or pushes was given, so 'nothing behind "
                                           "it' cannot be established")
    stuck = []
    for f in files:
        if now - os.path.getmtime(f) < minutes * 60:
            continue
        sid = os.path.basename(f)[:-6]
        if sid in cards:
            continue
        if waiting_on_owner(_last_event(f)):
            stuck.append(sid)
    return ("FAIL" if stuck else "PASS"), len(files), sorted(stuck), ""


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("synthetic")
    s.add_argument("--evidence", required=True)
    k = sub.add_parser("stuck")
    k.add_argument("--root", default=ROOT)
    k.add_argument("--minutes", type=float, default=30)
    k.add_argument("--cards", help="JSON list of session ids that have a card or push behind them")
    a = ap.parse_args(argv)
    if a.cmd == "synthetic":
        try:
            with open(a.evidence, encoding="utf-8") as fh:
                ev = json.load(fh)
        except (OSError, ValueError):
            ev = None
        verdict, reasons = judge_synthetic(ev)
        print("OWNER-TOUCH-SYNTHETIC %s: %s" % (verdict, "; ".join(reasons)))
        return {"PASS": 0, "FAIL": 1, "UNKNOWN": 2}[verdict]
    cards = None
    if a.cards:
        try:
            with open(a.cards, encoding="utf-8") as fh:
                data = json.load(fh)
            cards = {str(x) for x in data} if isinstance(data, list) else None
        except (OSError, ValueError):
            cards = None
    verdict, n, ids, why = find_stuck(a.root, a.minutes, cards)
    if verdict == "UNKNOWN":
        print("OWNER-TOUCH-STUCK UNKNOWN: %s. This is not none." % why)
        return 2
    print("OWNER-TOUCH-STUCK %s: %d stuck of %d transcripts idle over %g min%s" %
          (verdict, len(ids), n, a.minutes, ": " + ", ".join(ids) if ids else ""))
    return 1 if ids else 0


if __name__ == "__main__":
    sys.exit(main())
