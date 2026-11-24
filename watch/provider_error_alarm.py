"""WATCH webchat-8: raise a LOCAL alarm when model-provider calls start failing.

Why: one dead key silently stopped every model feature for weeks and nothing noticed. The cron
healthchecks watch schedules, not provider errors.

This is READ-ONLY on the hub and SENDS NOTHING (Law 9): no push, no mail, no webhook, no network.
It reads a local export of provider-call outcomes, judges each provider over a trailing window and,
when one is failing, writes ONE alarm row to a local file that the NovahOS shell (or the Router desk
feeder) shows. Any outward send of that row (a push to the owner's phone, say) is a separate step
behind the approval gate; the row records `outward: "held-for-approval"` so nothing reads it as sent.

Input (JSONL, one call per line; ids and classes only, never prompts or keys):
    {"ts": "2026-11-22T10:15:00Z" | epoch seconds, "provider": "anthropic", "ok": true|false,
     "error": "auth" | "rate_limit" | "5xx" | ...  (optional)}

Verdict per provider over the window (default 60 min):
    OK       enough calls and the failure share is at or below the threshold (default 10 percent)
    ALARM    enough calls (default >= 5) and the failure share is above the threshold
    UNKNOWN  too few calls to judge, or no calls at all. Silence is not health: a provider with no
             visible calls is UNKNOWN, never OK. Unreadable lines are counted and, if any exist,
             an otherwise-OK provider degrades to UNKNOWN (the check could not see everything).

Once only: state (a JSON file) remembers which providers are already alarmed. A provider that stays
in ALARM raises no second row; it is re-armed only after a window judged OK. UNKNOWN neither raises
nor re-arms (a check that cannot see must not clear an alarm).

    python watch/provider_error_alarm.py --calls calls.jsonl [--window-min 60] [--threshold 0.10]
        [--min-calls 5] [--now EPOCH] [--alarms alarms.jsonl] [--state state.json] [--dry-run]

Exit 0 = every provider OK, 1 = at least one ALARM, 2 = nothing could be established (UNKNOWN).
Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

DEFAULT_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "provider-alarm")
WINDOW_MIN = 60
THRESHOLD = 0.10
MIN_CALLS = 5


def _epoch(ts):
    """Epoch seconds from a number or an ISO-8601 string, or None when it cannot be read."""
    if isinstance(ts, bool):
        return None
    if isinstance(ts, (int, float)):
        return float(ts)
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return None
    return None


def read_calls(path):
    """Return (events, bad_lines). events = [(epoch, provider, ok, error)]."""
    events, bad = [], 0
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
                t, prov, ok = _epoch(o["ts"]), o["provider"], o["ok"]
                if t is None or not isinstance(prov, str) or not prov or not isinstance(ok, bool):
                    raise ValueError
            except (ValueError, KeyError, TypeError):
                bad += 1
                continue
            err = o.get("error")
            events.append((t, prov, ok, err if isinstance(err, str) else None))
    return events, bad


def judge(events, bad_lines, now, window_min=WINDOW_MIN, threshold=THRESHOLD, min_calls=MIN_CALLS):
    """Per-provider verdicts: {provider: {verdict, calls, failed, share, top_error, reason}}."""
    lo = now - window_min * 60
    per = {}
    for t, prov, ok, err in events:
        if lo <= t <= now:
            per.setdefault(prov, []).append((ok, err))
    out = {}
    for prov, rows in sorted(per.items()):
        n = len(rows)
        failed = [e or "unspecified" for ok, e in rows if not ok]
        share = len(failed) / n
        top = max(set(failed), key=failed.count) if failed else None
        if n < min_calls:
            v, why = "UNKNOWN", "only %d call(s) in the window, need %d" % (n, min_calls)
        elif share > threshold:
            v, why = "ALARM", "%d of %d calls failed (%.0f%%), threshold %.0f%%" % (
                len(failed), n, share * 100, threshold * 100)
        elif bad_lines:
            v, why = "UNKNOWN", "%d unreadable line(s) in the call log" % bad_lines
        else:
            v, why = "OK", "%d of %d calls failed" % (len(failed), n)
        out[prov] = {"verdict": v, "calls": n, "failed": len(failed), "share": round(share, 4),
                     "top_error": top, "reason": why}
    return out


def _load_state(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            s = json.load(fh)
        return s if isinstance(s, dict) else {}
    except (OSError, ValueError):
        return {}


def raise_alarms(verdicts, now, alarms_path, state_path, dry_run=False):
    """Append one local alarm row per newly alarmed provider. Returns the rows raised."""
    state = _load_state(state_path)
    raised = []
    for prov, v in verdicts.items():
        if v["verdict"] == "ALARM":
            if state.get(prov, {}).get("alarmed"):
                continue
            row = {"kind": "provider-errors", "provider": prov,
                   "at": datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "calls": v["calls"], "failed": v["failed"], "share": v["share"],
                   "top_error": v["top_error"], "message": v["reason"],
                   "outward": "held-for-approval"}
            raised.append(row)
            state[prov] = {"alarmed": True, "since": row["at"]}
        elif v["verdict"] == "OK" and state.get(prov, {}).get("alarmed"):
            state[prov] = {"alarmed": False}
    if raised and not dry_run:
        os.makedirs(os.path.dirname(os.path.abspath(alarms_path)), exist_ok=True)
        with open(alarms_path, "a", encoding="utf-8") as fh:
            for r in raised:
                fh.write(json.dumps(r) + "\n")
    if not dry_run:
        os.makedirs(os.path.dirname(os.path.abspath(state_path)), exist_ok=True)
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump(state, fh)
    return raised


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--calls", required=True)
    ap.add_argument("--window-min", type=float, default=WINDOW_MIN)
    ap.add_argument("--threshold", type=float, default=THRESHOLD)
    ap.add_argument("--min-calls", type=int, default=MIN_CALLS)
    ap.add_argument("--now", type=float, default=None)
    ap.add_argument("--alarms", default=os.path.join(DEFAULT_DIR, "alarms.jsonl"))
    ap.add_argument("--state", default=os.path.join(DEFAULT_DIR, "state.json"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    now = a.now if a.now is not None else time.time()
    try:
        events, bad = read_calls(a.calls)
    except OSError as e:
        print("UNKNOWN: call log unreadable (%s)" % e.__class__.__name__)
        return 2
    verdicts = judge(events, bad, now, a.window_min, a.threshold, a.min_calls)
    if not verdicts:
        print("UNKNOWN: no provider calls in the last %g min; silence is not health" % a.window_min)
        return 2
    raised = raise_alarms(verdicts, now, a.alarms, a.state, a.dry_run)
    for prov, v in verdicts.items():
        print("%s %s: %s" % (v["verdict"], prov, v["reason"]))
    for r in raised:
        print("RAISED local alarm for %s (not sent anywhere; outward send needs approval)" % r["provider"])
    if any(v["verdict"] == "ALARM" for v in verdicts.values()):
        return 1
    return 0 if all(v["verdict"] == "OK" for v in verdicts.values()) else 2


if __name__ == "__main__":
    sys.exit(main())
