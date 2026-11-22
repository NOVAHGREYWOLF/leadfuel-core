"""WATCH: count how often the owner had to type into a session, and what the touch was for.

Read-only. Reads the local Claude Code transcripts (*.jsonl) and keeps only counts: no message
text is written anywhere. A touch is a user-role message whose origin.kind is "human" (the
transcript field the app sets for text typed or pasted by a person).

The categories are HEURISTIC, read off the shape of the message, not its meaning. They exist to
show which touches a machine could have made, not to settle any one case. Treat the totals as
solid and the split as indicative.

  python watch/owner_touch_ledger.py --days 3
  python watch/owner_touch_ledger.py --days 1 --line      # the single line for the Conductor desk
  python watch/owner_touch_ledger.py --selftest

Exit 0 = counted. Exit 2 = UNKNOWN: the ledger could not see, and says so instead of printing 0.
A check that cannot establish a state must not report one, so UNKNOWN covers three cases:
  * no transcript file under the root was touched in the window (nothing to read),
  * fewer transcript files than --min-transcripts were in the window, or
  * transcripts were read and held user messages, but none of those carried an `origin` field at
    all (the app stopped writing it, or renamed it): every count would otherwise read as zero.
Exit 1 = the self-test failed.

Stdlib only.
"""
import argparse
import collections
import datetime as dt
import contextlib
import glob
import io
import json
import os
import re
import sys
import tempfile
import time

ROOT = os.path.expanduser("~/.claude/projects")

GO = re.compile(r"^(ok(ay)?[ ,.]*)?(go|go on|do it|yes|yes do it|yes a do it|keep going|continue|move forward|"
                r"answered|done|sure|a|b|c|a\.|b\.|c\.|yes\.?)[ .!]*$")
POLL = re.compile(r"(what'?s ?n?e?x?t|whats? ?n[a-z]*xt|what ?s?n[a-z]*xt|what else|what needs|are you done|"
                  r"hows? it go|how's it go|did we answer|what we got through)")
RELAY = re.compile(r"(router|conductor)")
RELAY_VERB = re.compile(r"(tell|talk|ask|send|comm|check with|make sure|let .* know|knows)")


def classify(text):
    t = text.strip()
    low = re.sub(r"\s+", " ", t.lower())
    words = len(low.split())
    if "<pasted_content" in t or t.startswith("You are ") or words > 150:
        return "paste: starts or hands over a session"
    if GO.match(low):
        return "go / approve / click-answer"
    if words <= 12 and POLL.search(low):
        return "status poll (nothing pushed it to me)"
    if words <= 20 and RELAY.search(low) and RELAY_VERB.search(low):
        return "relay between sessions"
    if words <= 12 and re.match(r"^(queue|archive|open|leave|set|send|ask) ", low):
        return "command a session could have taken from a rule"
    return "other (new input or a real decision)"


def read_touches(root, since):
    """Return (transcripts_seen, touches, user_msgs, user_msgs_with_origin).

    The last two let the caller tell "the owner typed nothing" from "the origin field is gone".
    """
    files = [f for f in glob.glob(os.path.join(root, "*", "*.jsonl")) if os.path.getmtime(f) >= since]
    since_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(since))
    touches, sessions_seen, user_msgs, with_origin = [], 0, 0, 0
    for f in files:
        sessions_seen += 1
        sid = os.path.basename(f)[:-6]
        with open(f, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"type":"user"' not in line and '"type": "user"' not in line:  # cheap prefilter
                    continue
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                if o.get("type") != "user" or o.get("isMeta") or o.get("isSidechain"):
                    continue
                ts = o.get("timestamp", "")
                if ts[:19] < since_iso:
                    continue  # the file is recent; this line may not be
                user_msgs += 1
                origin = o.get("origin")
                if isinstance(origin, dict) and "kind" in origin:
                    with_origin += 1
                if (origin or {}).get("kind") != "human":
                    continue
                ct = o.get("message", {}).get("content")
                if isinstance(ct, list):
                    if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in ct):
                        continue
                    ct = " ".join(b.get("text", "") for b in ct if isinstance(b, dict))
                if not isinstance(ct, str) or not ct.strip():
                    continue
                touches.append((ts[:10], sid, classify(ct)))
    return sessions_seen, touches, user_msgs, with_origin


def unknown_reason(root, days, sessions_seen, user_msgs, with_origin, min_transcripts=1):
    """None when the ledger could see; otherwise the reason it cannot count."""
    if sessions_seen == 0:
        return "no transcript files found under %s in the last %g days" % (root, days)
    if sessions_seen < min_transcripts:
        return ("only %d transcript file(s) under %s in the last %g days, fewer than the %d expected "
                "(a run inside a Claude session always sees its own transcript)" %
                (sessions_seen, root, days, min_transcripts))
    if user_msgs > 0 and with_origin == 0:
        return ("%d transcripts and %d user messages were read but none carried an origin.kind field, "
                "so a human touch cannot be told from any other" % (sessions_seen, user_msgs))
    return None


def report(sessions_seen, touches, days, user_msgs, with_origin, root=ROOT, line=False, today=None,
           min_transcripts=1):
    stamp = today or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    why = unknown_reason(root, days, sessions_seen, user_msgs, with_origin, min_transcripts)
    if why:
        if line:
            print("OWNER-TOUCH-LEDGER %s UNKNOWN: %s. This is not zero." % (stamp, why))
        else:
            print("UNKNOWN: %s. This is not zero." % why)
        return 2
    by_day = collections.Counter(d for d, _, _ in touches)
    by_cat = collections.Counter(c for _, _, c in touches)
    sessions_touched = len({s for _, s, _ in touches})
    if line:
        top = ", ".join("%d %s" % (n, c.split(" ")[0].strip(":/")) for c, n in by_cat.most_common(3))
        print("OWNER-TOUCH-LEDGER %s last %gd (UTC): %d owner touches in %d sessions, %d transcripts scanned%s" %
              (stamp, days, len(touches), sessions_touched, sessions_seen,
               "; top: " + top if top else ""))
        return 0
    print("transcripts scanned: %d   owner touches: %d   in %d sessions" %
          (sessions_seen, len(touches), sessions_touched))
    print("per day (UTC):", ", ".join("%s=%d" % kv for kv in sorted(by_day.items())))
    for c, n in by_cat.most_common():
        print("  %4d  %s" % (n, c))
    return 0


def selftest():
    cases = {
        "go": "go / approve / click-answer",
        "whats next": "status poll (nothing pushed it to me)",
        "so what snext": "status poll (nothing pushed it to me)",
        "talk to router on your findings": "relay between sessions",
        "queue the three test flake fixes": "command a session could have taken from a rule",
        "You are CONDUCTOR system build 035. Invoke the skill": "paste: starts or hands over a session",
        "the seed bank is what i was talking about": "other (new input or a real decision)",
    }
    bad = [(k, classify(k), v) for k, v in cases.items() if classify(k) != v]
    for b in bad:
        print("SELFTEST FAIL: %r -> %r, wanted %r" % b)
    # positive control: an empty root must say UNKNOWN (exit 2), never "0 touches".
    with tempfile.TemporaryDirectory() as empty:
        seen, t, um, wo = read_touches(empty, 0)
        if seen != 0 or t:
            print("SELFTEST FAIL: empty root was not empty")
            return 1
        with contextlib.redirect_stdout(io.StringIO()):
            code = report(seen, t, 1, um, wo, root=empty)
        if code != 2:
            print("SELFTEST FAIL: empty root did not exit 2")
            return 1
    print("selftest:", "FAIL" if bad else "ok")
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=3)
    ap.add_argument("--root", default=ROOT, help="transcripts root (default ~/.claude/projects)")
    ap.add_argument("--min-transcripts", type=int, default=1,
                    help="UNKNOWN if fewer transcript files than this were in the window (default 1; "
                         "a run inside a Claude session sees its own transcript, so use 2 there)")
    ap.add_argument("--line", action="store_true", help="print the single Conductor desk line")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if a.selftest:
        return selftest()
    since = time.time() - a.days * 86400
    seen, touches, user_msgs, with_origin = read_touches(a.root, since)
    return report(seen, touches, a.days, user_msgs, with_origin, root=a.root, line=a.line,
                  min_transcripts=a.min_transcripts)


if __name__ == "__main__":
    sys.exit(main())
