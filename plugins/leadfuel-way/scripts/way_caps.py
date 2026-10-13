#!/usr/bin/env python
"""Force a low handoff cap for a pilot, on every session on this machine, for a short while.

    python way_caps.py set SOFT HARD [--minutes 60]     e.g. set 40000 90000 --minutes 90
    python way_caps.py show
    python way_caps.py clear

Desktop sessions cannot set environment variables and sessions may not edit the owner's settings
file, so the hook also reads <state dir>/caps-override.json. The override EXPIRES (default 60
minutes) and the hook ignores it afterwards, so a forgotten one cannot leave the whole machine
handing off early. SESSION_SOFT_TOKENS / SESSION_HARD_TOKENS in a session's environment still win.
Remember to `clear` when the pilot is over: way_doctor.py reports an active override.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path


def override_path() -> Path:
    return Path(os.environ.get("WAY_STATE_DIR") or Path(tempfile.gettempdir()) / "leadfuel-way") / "caps-override.json"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("set")
    s.add_argument("soft", type=int)
    s.add_argument("hard", type=int)
    s.add_argument("--minutes", type=float, default=60.0)
    sub.add_parser("show")
    sub.add_parser("clear")
    args = ap.parse_args(argv)
    path = override_path()
    if args.cmd == "set":
        if args.soft <= 0 or args.hard < args.soft or args.minutes <= 0:
            print("need 0 < SOFT <= HARD and minutes > 0", file=sys.stderr)
            return 2
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"soft": args.soft, "hard": args.hard, "expires": time.time() + args.minutes * 60}), encoding="utf-8")
        print(f"forced caps: handoff at {args.soft // 1000}k, hard stop at {args.hard // 1000}k, for {args.minutes:g} minutes ({path})")
    elif args.cmd == "clear":
        try:
            path.unlink()
            print("override cleared")
        except FileNotFoundError:
            print("no override was set")
    else:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            left = (float(data["expires"]) - time.time()) / 60
            print(f"override: soft {data['soft']}, hard {data['hard']}, " + (f"{left:.0f} minutes left" if left > 0 else "EXPIRED (ignored by the hook)"))
        except (OSError, ValueError, KeyError):
            print("no override set")
    return 0


if __name__ == "__main__":
    sys.exit(main())
