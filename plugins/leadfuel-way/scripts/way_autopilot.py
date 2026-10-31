#!/usr/bin/env python
"""The autopilot switch, its checkpoint and usage records, and its audit log (WAY-AUTOPILOT-1).

    python way_autopilot.py status
    python way_autopilot.py on --project "<p>" --card q<N> --brief <path> [--days 7] [--allow git-push --allow gh-pr ...]
    python way_autopilot.py off --project "<p>" [--reason "..."]
    python way_autopilot.py checkpoint --project "<p>" --card q<N>
    python way_autopilot.py usage --project "<p>" --pct <weekly all-models %> --source "<where it was read>"
    python way_autopilot.py decide --project "<p>" --decision "..." --why "..." [--brief-rule "..."] [--reversible yes|no]
    python way_autopilot.py log [--project "<p>"] [--last 20]

OFF by default: with no state file there is no autopilot anywhere. `on` is the owner's decision only,
taken on a Router desk card whose id is recorded here; this script cannot verify the card, so the rule
is in the skill and the hook refuses `on` and `allow` from inside an autopilot session. `off` always
works and never needs a card. Hard gates cannot be put in `--allow`; only kinds that leave the machine
can (git-push, gh-pr, gh-write, web, browser, artifact-publish, mcp:<tool>).

State: <state dir>/autopilot.json (WAY_STATE_DIR overrides the dir, as for the hook).
Log:   <state dir>/autopilot-log.jsonl, one JSON object per line, append-only.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
_spec = importlib.util.spec_from_file_location("way_autopilot_gate_cli", HOOKS / "autopilot.py")
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

CARD = re.compile(r"^q\d+$")
MAX_DAYS = 14


class Refused(Exception):
    pass


def _read() -> dict:
    status, data = gate.load()
    if status == "unreadable":
        raise Refused(f"{gate.state_path()} is unreadable: fix or remove it (while it is, every session is gated)")
    data.setdefault("projects", {})
    return data


def _write(data: dict) -> None:
    p = gate.state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(p)


def _project(data: dict, name: str, create: bool = False) -> dict:
    for k, v in data["projects"].items():
        if k.casefold() == name.casefold():
            return v
    if not create:
        raise Refused(f"no autopilot record for project {name!r}")
    data["projects"][name] = {}
    return data["projects"][name]


def _allowable(kind: str) -> bool:
    return kind in gate.EGRESS_KINDS or (kind.startswith("mcp:") and len(kind) > 4)


def cmd_on(a, now: float) -> str:
    if not CARD.match(a.card or ""):
        raise Refused("`on` needs the owner's Router desk card id (--card q<N>): switching on is his decision only")
    if not Path(a.brief).is_file():
        raise Refused(f"the goal brief {a.brief!r} is not a file: write it from skills/autopilot/GOAL_BRIEF.md first")
    bad = [k for k in a.allow if not _allowable(k)]
    if bad:
        raise Refused(f"cannot allow {bad}: hard gates are never allowable; allowable kinds are "
                      f"{', '.join(gate.EGRESS_KINDS)} and mcp:<tool>")
    if not 0 < a.days <= MAX_DAYS:
        raise Refused(f"--days must be 1..{MAX_DAYS}: the switch lapses by itself")
    data = _read()
    cfg = _project(data, a.project, create=True)
    cfg.clear()
    cfg.update(on=True, approved_card=a.card, approved_at=now, brief=str(Path(a.brief).resolve()),
               allow=sorted(set(a.allow)), expires=now + a.days * 86400, checkpoint_card=None, usage=None)
    _write(data)
    gate.log({"project": a.project, "decision": "autopilot-on", "card": a.card, "allow": cfg["allow"], "days": a.days})
    return f"autopilot ON for {a.project!r} (card {a.card}, lapses in {a.days} days, allow {cfg['allow'] or 'nothing'})"


def cmd_off(a, now: float) -> str:
    data = _read()
    try:
        cfg = _project(data, a.project)
    except Refused:
        return f"autopilot already off for {a.project!r} (no record)"
    cfg.update(on=False, off_at=now, off_reason=a.reason or "")
    _write(data)
    gate.log({"project": a.project, "decision": "autopilot-off", "reason": a.reason or ""})
    return f"autopilot OFF for {a.project!r}"


def cmd_checkpoint(a, now: float) -> str:
    if not CARD.match(a.card or ""):
        raise Refused("--card must be the checkpoint card's id, q<N>")
    data = _read()
    cfg = _project(data, a.project)
    cfg.update(checkpoint_card=a.card, checkpoint_at=now)
    _write(data)
    gate.log({"project": a.project, "decision": "checkpoint-posted", "card": a.card})
    return f"checkpoint card {a.card} recorded for {a.project!r}"


def cmd_usage(a, now: float) -> str:
    if not 0 <= a.pct <= 100:
        raise Refused("--pct is a percentage, 0..100")
    if not (a.source or "").strip():
        raise Refused("--source must say where the number was read: an unsourced number is not a measurement")
    data = _read()
    cfg = _project(data, a.project)
    cfg["usage"] = {"weekly_pct": a.pct, "at": now, "source": a.source}
    _write(data)
    gate.log({"project": a.project, "decision": "usage-recorded", "weekly_pct": a.pct, "source": a.source})
    stop = " STOP: at or past 88%, start nothing" if a.pct >= gate.USAGE_STOP_PCT else ""
    return f"weekly usage {a.pct:g}% recorded for {a.project!r}{stop}"


def cmd_decide(a, now: float) -> str:
    if not a.decision.strip() or not a.why.strip():
        raise Refused("a logged decision needs both --decision and --why")
    gate.log({"project": a.project, "decision": "autonomous", "what": a.decision, "why": a.why,
              "brief_rule": a.brief_rule or "", "reversible": a.reversible})
    return "logged"


def cmd_status(a, now: float) -> str:
    status, data = gate.load()
    if status != "ok":
        return f"autopilot state: {status}" + (" (off everywhere)" if status == "absent" else " (every session gated)")
    lines = []
    for name, cfg in data.get("projects", {}).items():
        live = cfg.get("on") is True and float(cfg.get("expires") or 0) > now
        lines.append(f"{name}: {'ON' if live else 'off'} card={cfg.get('approved_card')} allow={cfg.get('allow')} "
                     f"checkpoint={cfg.get('checkpoint_card')} usage={cfg.get('usage')}")
    return "\n".join(lines) or "autopilot state: no projects (off everywhere)"


def cmd_log(a, now: float) -> str:
    p = gate.state_dir() / gate.LOG_FILE
    if not p.exists():
        return "no autopilot log yet"
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    if a.project:
        rows = [r for r in rows if str(r.get("project", "")).casefold() == a.project.casefold()]
    return "\n".join(json.dumps(r) for r in rows[-a.last:])


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    p = sub.add_parser("on"); p.add_argument("--project", required=True); p.add_argument("--card", required=True)
    p.add_argument("--brief", required=True); p.add_argument("--days", type=int, default=7)
    p.add_argument("--allow", action="append", default=[])
    p = sub.add_parser("off"); p.add_argument("--project", required=True); p.add_argument("--reason")
    p = sub.add_parser("checkpoint"); p.add_argument("--project", required=True); p.add_argument("--card", required=True)
    p = sub.add_parser("usage"); p.add_argument("--project", required=True); p.add_argument("--pct", type=float, required=True)
    p.add_argument("--source", required=True)
    p = sub.add_parser("decide"); p.add_argument("--project", required=True); p.add_argument("--decision", required=True)
    p.add_argument("--why", required=True); p.add_argument("--brief-rule"); p.add_argument("--reversible", default="yes", choices=["yes", "no"])
    p = sub.add_parser("log"); p.add_argument("--project"); p.add_argument("--last", type=int, default=20)
    return ap


def main(argv: list[str] | None = None, now: float | None = None) -> int:
    a = parser().parse_args(argv)
    try:
        print(globals()[f"cmd_{a.cmd}"](a, time.time() if now is None else now))
    except Refused as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
