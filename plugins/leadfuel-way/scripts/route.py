#!/usr/bin/env python3
"""Pick the cheapest model that is safe for a board task. Deterministic, stdlib-only.

    python route.py '{"title": "...", "effort": "small", "envelope": "production"}'
    python route.py --backtest <dir of board task JSON files>

Rules, first match wins:
  1. task["model_pin"] ("fable"|"opus"|"sonnet"|"haiku", or that model's full id) is obeyed.
     FABLE is reached ONLY by a pin: it is the owner's choice, never a rule's. A pin that names
     no known model is an error, not a silent fall-through to the rules below.
  2. OPUS   envelope critical/door, effort high/xhigh, or a risk word in the TITLE
            (security, auth, migration, architecture, rewrite).
  3. HAIKU  effort small/low AND a mechanical word in the TITLE (sweep, typo, docs,
            copy, display text, changelog, readme, lint, format, bump) AND not Opus-risky.
  4. SONNET everything else. Sonnet is the default: it is the model that did most of the work.

Words are matched on the TITLE only. Briefs mention "security" and "privacy" in passing all
the time; matching them would send everything to Opus.

task["model_effort"] (low|medium|high|xhigh|max), when given, is passed through as "model_effort"
for the router's set_session_effort. It is the model's thinking effort, not the board's task
"effort" (small/high/...), which only feeds rule 2.

IDs come from novahos.model_tiers when importable, else the fallback below. Keep them in step.
model_tiers has no Fable tier, so the Fable id lives here alone.

Copied into the leadfuel-way plugin from novahos .claude/skills/route-and-spawn/route.py (cb94eb0);
this copy is the one the router runs when it opens a desk. Only the fallback Haiku id changed.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:  # one place for model IDs, when the kernel is installed
    from novahos.model_tiers import model_for

    IDS = {"opus": model_for("reason"), "sonnet": model_for("write"), "haiku": model_for("classify")}
except Exception:  # noqa: BLE001
    IDS = {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5", "haiku": "claude-haiku-4-5-20251001"}
IDS["fable"] = "claude-fable-5-1"
NAME_FOR_ID = {model_id: name for name, model_id in IDS.items()}

MODEL_EFFORTS = ("low", "medium", "high", "xhigh", "max")
OPUS_ENVELOPES = {"critical", "door"}
OPUS_EFFORT = {"high", "xhigh"}
CHEAP_EFFORT = {"small", "low"}
OPUS_WORDS = re.compile(r"\b(security|auth(?:entication|orization)?|migration|architecture|rewrite)\b", re.I)
MECHANICAL_WORDS = re.compile(
    r"\b(sweep|typo|docs?|documentation|copy|display[- ]text|changelog|readme|lint|format|bump)\b",
    re.I,
)


class BadTask(ValueError):
    """A model_pin or model_effort that names nothing this router knows."""


def route(task: dict) -> dict:
    model_effort = str(task.get("model_effort") or "").lower()
    if model_effort and model_effort not in MODEL_EFFORTS:
        raise BadTask(f"unknown model_effort {model_effort!r}; expected one of {list(MODEL_EFFORTS)}")
    out = _route(task)
    if model_effort:
        out["model_effort"] = model_effort
    return out


def _route(task: dict) -> dict:
    title = str(task.get("title") or "")
    effort = str(task.get("effort") or "").lower()
    envelope = str(task.get("envelope") or "").lower()

    pin = str(task.get("model_pin") or "").strip().lower()
    if pin:
        name = pin if pin in IDS else NAME_FOR_ID.get(pin)
        if name is None:
            raise BadTask(f"unknown model_pin {pin!r}; expected one of {sorted(IDS)} or their ids")
        return _out(name, f"pinned to {name}")
    risky = envelope in OPUS_ENVELOPES or effort in OPUS_EFFORT or bool(OPUS_WORDS.search(title))
    if risky:
        why = (
            f"envelope={envelope}" if envelope in OPUS_ENVELOPES
            else f"effort={effort}" if effort in OPUS_EFFORT
            else "risk word in title"
        )
        return _out("opus", why)
    if effort in CHEAP_EFFORT and MECHANICAL_WORDS.search(title):
        return _out("haiku", f"effort={effort}, mechanical title")
    return _out("sonnet", "default")


def _out(name: str, why: str) -> dict:
    return {"model": name, "model_id": IDS[name], "reason": why}


def backtest(directory: str) -> None:
    """Compare what the board actually used with what this router would pick."""
    actual_cost: dict[str, float] = {}
    moves: list[tuple[str, str, str, float]] = []
    for f in sorted(Path(directory).glob("*.json")):
        doc = json.loads(f.read_text())
        t = doc.get("data", doc)
        cost = t.get("cost_usd")
        if cost is None or not t.get("model"):
            continue
        was = str(t["model"]).split()[0].lower()
        now = route({**t, "title": t.get("title", "")})["model"]
        actual_cost[was] = actual_cost.get(was, 0.0) + float(cost)
        if now != was:
            moves.append((f.stem, was, now, float(cost)))
    print("actual spend by model:", {k: round(v, 2) for k, v in actual_cost.items()})
    print(f"{len(moves)} tasks would route differently:")
    for tid, was, now, cost in moves:
        print(f"  {tid:38} {was:6} -> {now:6} (was ${cost:.2f})")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--backtest":
        backtest(sys.argv[2])
    elif len(sys.argv) == 2:
        try:
            print(json.dumps(route(json.loads(sys.argv[1]))))
        except BadTask as exc:
            sys.exit(f"route.py: {exc}")
    else:
        sys.exit(__doc__)
