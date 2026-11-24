"""WATCH: sensor silence alarm. Say when a feed stops, once.

LOCAL ONLY (Law 9): reads local JSON files, writes local JSON files, prints. No network, no push,
no mail, no webhook. The NovahOS shell shows `alarms.json` (a room or an alarm list).

  python watch/sensor_silence.py --seen seen.json [--feeds feeds.json] [--state state.json]
                                 [--alarms alarms.json] [--now 2026-11-22T10:00:00+00:00]

FEEDS (feeds.json): {"location": {"max_quiet_minutes": 180}, ...}. The built-in default covers
location, the first feed. Every feed has a maximum quiet time.

SEEN (seen.json): {"location": "2026-11-22T09:15:00+00:00", ...}, the last time each feed delivered
anything, gathered by whoever can read the feed. This module judges it and does not fetch it.

VERDICT per feed: ok | stale | unknown. Silence is never ok.
  ok       last delivery is inside the maximum quiet time
  stale    last delivery is older than the maximum quiet time
  unknown  no entry, unparseable, no timezone, or in the future beyond clock skew: the age cannot be
           established, so no state is claimed. Unknown is alarmed too (a feed we cannot see is not a
           feed that is fine) and says so.

ONCE: the owner is told when a feed enters stale/unknown, not on every run. The state file remembers
which feeds were already told; a feed that returns to ok is re-armed. A state file that cannot be
read is treated as "nothing told yet" (a repeat alarm is safer than a missed one).

Exit 0 = all ok, 1 = something stale, 2 = nothing stale but something unknown. Stdlib only.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

DEFAULT_FEEDS = {"location": {"max_quiet_minutes": 180}}
CLOCK_SKEW_SECONDS = 300


def _parse(ts):
    """Aware UTC datetime, or None when the value cannot establish a time."""
    if not isinstance(ts, str):
        return None
    try:
        dt = datetime.fromisoformat(ts.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def judge_feed(last_seen, max_quiet_minutes, now):
    """Return (verdict, age_minutes or None, reason)."""
    if (isinstance(max_quiet_minutes, bool) or not isinstance(max_quiet_minutes, (int, float))
            or max_quiet_minutes <= 0):
        return "unknown", None, "no valid maximum quiet time configured"
    seen = _parse(last_seen)
    if seen is None:
        return "unknown", None, "no usable last-delivery time (missing, unparseable or no timezone)"
    delta = (now - seen).total_seconds()
    if delta < -CLOCK_SKEW_SECONDS:
        return "unknown", None, "last delivery is in the future; clock or feed is wrong"
    age = max(delta, 0) / 60.0
    if age > max_quiet_minutes:
        return "stale", round(age, 1), "quiet %.0f min, limit %s min" % (age, max_quiet_minutes)
    return "ok", round(age, 1), "quiet %.0f min, limit %s min" % (age, max_quiet_minutes)


def evaluate(feeds, seen, now):
    """Verdict dict per configured feed. A feed absent from `seen` is unknown, never ok."""
    seen = seen if isinstance(seen, dict) else {}
    out = {}
    for name, cfg in (feeds or {}).items():
        mq = cfg.get("max_quiet_minutes") if isinstance(cfg, dict) else None
        verdict, age, reason = judge_feed(seen.get(name), mq, now)
        out[name] = {"verdict": verdict, "age_minutes": age, "reason": reason,
                     "last_seen": seen.get(name) if isinstance(seen.get(name), str) else None}
    return out


def new_alarms(results, told):
    """Return (fresh, still): feeds to tell the owner about now, and all feeds not ok."""
    told = set(told or [])
    still = sorted(n for n, r in results.items() if r["verdict"] != "ok")
    fresh = [n for n in still if n not in told]
    return fresh, still


def _load(path, default):
    if not path:
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1)
    os.replace(tmp, path)


def run(feeds, seen, state_path, alarms_path, now):
    results = evaluate(feeds, seen, now)
    state = _load(state_path, {})
    told = state.get("told") if isinstance(state, dict) else []
    fresh, still = new_alarms(results, told if isinstance(told, list) else [])
    if alarms_path:
        _write(alarms_path, {"checked_at": now.isoformat(), "feeds": results,
                             "new_alarms": fresh, "active": still})
    if state_path:
        _write(state_path, {"told": still})
    return results, fresh


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seen", help="JSON of last delivery time per feed")
    ap.add_argument("--feeds", help="JSON of max quiet minutes per feed (default: location only)")
    ap.add_argument("--state", help="JSON remembering which feeds were already told")
    ap.add_argument("--alarms", help="JSON the NovahOS shell reads")
    ap.add_argument("--now", help="ISO time with timezone (default: now)")
    args = ap.parse_args(argv)
    now = _parse(args.now) if args.now else datetime.now(timezone.utc)
    if now is None:
        print("--now needs an ISO time with a timezone", file=sys.stderr)
        return 2
    feeds = _load(args.feeds, DEFAULT_FEEDS) if args.feeds else DEFAULT_FEEDS
    seen = _load(args.seen, {})
    results, fresh = run(feeds, seen, args.state, args.alarms, now)
    for name in fresh:
        r = results[name]
        print("ALARM %s %s: %s" % (name, r["verdict"].upper(), r["reason"]))
    for name, r in results.items():
        if name not in fresh:
            print("%s %s: %s" % (name, r["verdict"], r["reason"]))
    verdicts = {r["verdict"] for r in results.values()}
    if "stale" in verdicts:
        return 1
    if "unknown" in verdicts or not results:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
