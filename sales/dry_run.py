#!/usr/bin/env python3
"""SALES K06 first slice: a dry-run harness for outbound drafts. No model call, no send, no network.

THE BUG CLASS IT TESTS (SALES desk, 2026-09): an em-dash, the single character the copy rules call the number one
giveaway, was reaching outgoing mail because the verifier scored the draft at WRITE time and the token fill ran at
SEND time, from a file none of the guards scanned. A guard that reads a different string from the one that leaves
passes everything.

So the harness has one rule and builds the whole pipeline around it: the string the guards read is the string that
would be handed to the sender, produced once, by one function (`outbound`), after EVERY send-time stage has run.

    drafts -> render (token fill, from the outbound app) -> extra send-time stages -> outbound text
                                                                      |-> guards read exactly this
                                                                      '-> this is what would be handed to the sender

For each draft the row reports:
  * `renderable`        the outbound app's own verdict (an unreadable lead is NOT renderable, never "clean")
  * `tells_written`     what the guard finds in the draft as written
  * `tells_outbound`    what the guard finds in the text that would leave
  * `injected_at_send`  tells present outbound and absent as written: the em-dash class, caught without sending
  * `verdict`           blocked | tells | unverified | clean_by_this_guard. Never "good": an empty tell list means
                        nothing the guard knows was present, not that the copy is fine (the guard says so itself).
  * `outbound_sha`      sha256 of the exact string the guard read and the sender would get

The outbound app is passed in (a module with `render_with_report` and `assessment`, e.g. a checkout of reach loaded
with `load_reach(path)`); nothing from it is called except those two pure functions. The sender is never imported.
A model call, and the owner's yes for it, are experiment 1 and are NOT here.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Callable, Iterable

Stage = Callable[[str, str, object], "tuple[str, str]"]

BLOCKED, TELLS, UNVERIFIED, CLEAN = "blocked", "tells", "unverified", "clean_by_this_guard"


class _Lead:
    """A plain stand-in for the outbound app's lead row: attributes from a dict."""
    def __init__(self, d: dict):
        self.name, self.company, self.title = d.get("name"), d.get("company"), d.get("title")
        self.email = d.get("email")


def load_reach(path: str | Path):
    """Load `render` and `voice_verify` from a reach checkout, and return a namespace with the two functions we use.

    Raises FileNotFoundError when the checkout is absent: a harness that cannot see its subject must not run empty.
    """
    root = Path(path)
    for need in ("render.py", "voice_verify.py"):
        if not (root / need).is_file():
            raise FileNotFoundError(f"{need} not found in {root}")
    sys.path.insert(0, str(root))
    try:
        mods = {}
        for name in ("render", "voice_verify"):
            spec = importlib.util.spec_from_file_location(f"_reach_{name}", root / f"{name}.py")
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            mods[name] = m
    finally:
        sys.path.remove(str(root))

    class _Reach:
        render_with_report = staticmethod(mods["render"].render_with_report)
        assessment = staticmethod(mods["voice_verify"].assessment)
    return _Reach


def outbound(reach, draft: dict, stages: Iterable[Stage] = ()) -> tuple[str, str, dict]:
    """The one place the outgoing text is made. Returns (subject, body, report). Guards must read this, not the draft."""
    lead = _Lead(draft.get("lead") or {})
    subject, body, report = reach.render_with_report(
        draft.get("subject"), draft.get("body"), lead, draft.get("sender") or {}, draft.get("extra") or {})
    for stage in stages:
        subject, body = stage(subject, body, lead)
    return subject, body, report


def _text(subject: str, body: str) -> str:
    return f"{subject}\n\n{body}" if subject else body


def _keys(assessment: dict) -> set:
    return {(t.get("kind"), t.get("term")) for t in assessment.get("tells", [])}


def dry_run(reach, drafts: list[dict], stages: Iterable[Stage] = ()) -> list[dict]:
    stages = tuple(stages)
    rows = []
    for i, d in enumerate(drafts):
        subject, body, report = outbound(reach, d, stages)
        final = _text(subject, body)
        written = _text(d.get("subject") or "", d.get("body") or "")
        a_final = reach.assessment(final)            # the guard reads exactly `final`
        a_written = reach.assessment(written)
        injected = sorted(_keys(a_final) - _keys(a_written))
        if not report.get("renderable"):
            verdict = BLOCKED
        elif a_final.get("tells"):
            verdict = TELLS
        elif not a_final.get("confident"):
            verdict = UNVERIFIED
        else:
            verdict = CLEAN
        rows.append({
            "id": d.get("id", i), "verdict": verdict, "renderable": bool(report.get("renderable")),
            "reason": report.get("reason", ""),
            "tells_written": sorted(map(str, _keys(a_written))), "tells_outbound": sorted(map(str, _keys(a_final))),
            "injected_at_send": [list(k) for k in injected],
            "outbound_sha": hashlib.sha256(final.encode("utf-8")).hexdigest(),
            "outbound_text": final,
        })
    return rows


def render_table(rows: list[dict]) -> str:
    if not rows:
        return "nothing to show: no drafts given\n"
    out = ["| id | verdict | injected at send | tells outbound | reason |", "| --- | --- | --- | --- | --- |"]
    for r in rows:
        inj = ", ".join(f"{k}:{t}" for k, t in r["injected_at_send"]) or "-"
        out.append(f"| {r['id']} | {r['verdict']} | {inj} | {len(r['tells_outbound'])} | {r['reason']} |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="SALES K06 dry-run harness: no model, no send, no network")
    ap.add_argument("--reach", required=True, help="path to a reach checkout")
    ap.add_argument("--drafts", required=True, help="JSON list of {id, subject, body, lead, sender, extra}")
    a = ap.parse_args(argv)
    try:
        reach = load_reach(a.reach)
    except FileNotFoundError as e:
        print(f"UNKNOWN: {e}", file=sys.stderr)
        return 2
    drafts = json.loads(Path(a.drafts).read_text(encoding="utf-8"))
    sys.stdout.write(render_table(dry_run(reach, drafts)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
