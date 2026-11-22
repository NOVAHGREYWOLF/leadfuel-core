"""Fixed-question AI-answer check (WEB-H2).

Asks a fixed list of questions to outside AI assistants and records whether the
expected names appear in each answer. Each LIVE run sends the questions off this
machine, so Law 9 applies: live mode refuses to run unless a local approval file
records the Router desk card id that approved it. DRY-RUN is the default and
never touches the network.

Usage:
  python scripts/ai_visibility/check.py                      # dry run, prints plan
  python scripts/ai_visibility/check.py --store              # dry run, saved locally
  python scripts/ai_visibility/check.py --live --assistant X # needs approval file
  python scripts/ai_visibility/check.py --history

No assistant adapters ship with this tool. A live run needs an adapter that the
owner registers after the card is answered (see ADAPTERS and README.md).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
HOME_DIR = Path(os.environ.get("AI_VISIBILITY_HOME", Path.home() / ".leadfuel" / "ai_visibility"))
DEFAULT_QUESTIONS = HERE / "questions.json"
CARD_RE = re.compile(r"^q\d+$")

# name -> function(question_text) -> answer_text. Empty on purpose.
ADAPTERS: dict[str, Callable[[str], str]] = {}


class ApprovalError(RuntimeError):
    pass


def load_questions(path: Path = DEFAULT_QUESTIONS) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    qs = data.get("questions", [])
    if len(qs) != 10:
        raise ValueError(f"expected 10 fixed questions, found {len(qs)}")
    ids = [q["id"] for q in qs]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate question ids")
    return data


def require_approval(path: Path, assistant: str) -> str:
    """Return the card id, or raise. Missing, malformed or off-scope means refuse."""
    if not path.is_file():
        raise ApprovalError(f"no approval file at {path}; live run refused (Law 9)")
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ApprovalError(f"approval file unreadable: {e}") from e
    card = str(rec.get("card_id", ""))
    if not CARD_RE.match(card):
        raise ApprovalError("approval file has no valid card_id (expected like q123)")
    if rec.get("approved") is not True:
        raise ApprovalError("approval file does not say approved: true")
    allowed = rec.get("assistants")
    if not isinstance(allowed, list) or assistant not in allowed:
        raise ApprovalError(f"assistant {assistant!r} is not listed in the approval file")
    return card


def score(answer: str, expect: list[str]) -> dict:
    low = answer.lower()
    hits = [e for e in expect if e.lower() in low]
    return {"mentioned": bool(hits), "hits": hits}


def run(data: dict, *, live: bool, assistant: str | None, approval: Path | None) -> dict:
    now = dt.datetime.now(dt.timezone.utc)
    card = None
    if live:
        if not assistant:
            raise ApprovalError("--live needs --assistant")
        card = require_approval(approval or HOME_DIR / "approval.json", assistant)
        if assistant not in ADAPTERS:
            raise ApprovalError(f"no adapter registered for {assistant!r}; nothing was sent")
    results = []
    for q in data["questions"]:
        row = {"id": q["id"], "text": q["text"], "expect": q["expect"]}
        if live:
            answer = ADAPTERS[assistant](q["text"])
            row.update(score(answer, q["expect"]))
            row["answer"] = answer
        else:
            row["status"] = "dry-run: not sent"
        results.append(row)
    return {
        "run_id": now.strftime("%Y%m%dT%H%M%SZ") + ("-live" if live else "-dry"),
        "mode": "live" if live else "dry-run",
        "assistant": assistant,
        "card_id": card,
        "questions_status": data.get("status"),
        "created_utc": now.isoformat(),
        "results": results,
    }


def store(record: dict, home: Path = HOME_DIR) -> Path:
    d = home / "runs"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{record['run_id']}.json"
    p.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return p


def history(home: Path = HOME_DIR) -> list[str]:
    d = home / "runs"
    out = []
    for p in sorted(d.glob("*.json")) if d.is_dir() else []:
        r = json.loads(p.read_text(encoding="utf-8"))
        if r["mode"] == "live":
            n = sum(1 for x in r["results"] if x.get("mentioned"))
            out.append(f"{r['run_id']}  {r['assistant']}  card {r['card_id']}  mentioned {n}/10")
        else:
            out.append(f"{r['run_id']}  dry-run")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--live", action="store_true", help="send questions out (needs approval file)")
    ap.add_argument("--assistant")
    ap.add_argument("--approval", type=Path)
    ap.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    ap.add_argument("--store", action="store_true", help="save a dry run too (live runs always save)")
    ap.add_argument("--history", action="store_true")
    a = ap.parse_args(argv)
    if a.history:
        print("\n".join(history()) or "no runs stored")
        return 0
    data = load_questions(a.questions)
    try:
        rec = run(data, live=a.live, assistant=a.assistant, approval=a.approval)
    except ApprovalError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    if a.live or a.store:
        print(f"stored: {store(rec)}")
    print(f"{rec['mode']} | questions {rec['questions_status']} | {len(rec['results'])} questions")
    for r in rec["results"]:
        print(f"  {r['id']} {r['text']}  [{r.get('status') or ('YES' if r['mentioned'] else 'no')}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
