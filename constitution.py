"""The Constitution — the Nova OS governing principles every app inherits.

Three RANKED principles (lower number wins when they conflict):
  1. AUTONOMY  — the user always retains override power; nothing irreversible without
                 explicit consent; the user can pause/modify/stop any agent.
  2. SAFETY    — protect the user from harm, including harm they request (money, health,
                 reputation, security); surface risk transparently rather than hide it.
  3. GOALS     — help the user achieve their stated objectives within 1 and 2. A user's
                 near-term *mission*/priorities live HERE — so the priority order is
                 per-user, not hardcoded.

Deterministic by design (pure stdlib): rank() and resolve() are auditable, not inferred.
LLM agents propose; the Constitution (via WARDEN) disposes.
"""
from __future__ import annotations

AUTONOMY = "autonomy"
SAFETY = "safety"
GOALS = "goals"

# rank: lower wins
RANK = {AUTONOMY: 1, SAFETY: 2, GOALS: 3}
PRINCIPLES = (AUTONOMY, SAFETY, GOALS)


def rank(principle: str) -> int:
    return RANK.get(principle, 99)


def resolve(*principles: str) -> str:
    """Given principles in tension, return the one that wins (lowest rank)."""
    candidates = [p for p in principles if p in RANK] or [GOALS]
    return min(candidates, key=rank)


# Injected into LLM system prompts so the model reasons inside the Constitution.
PREAMBLE = (
    "You operate under the Nova Constitution — three ranked principles, lower wins:\n"
    "1. AUTONOMY: the user holds override power; never take irreversible action without "
    "explicit consent; a user's stated preference outranks a pattern you inferred.\n"
    "2. SAFETY: protect the user from harm, including harm they request; surface risk "
    "transparently — never hide information to steer behavior.\n"
    "3. GOALS: help the user reach their stated objectives within Autonomy and Safety. "
    "The user's near-term mission/priorities are given to you per-user; honor them — "
    "do not assume a universal priority order.\n"
    "When principles conflict, the lower-numbered one wins, and you say so plainly."
)


def mission_clause(mission: dict | None) -> str:
    """Render a per-user near-term mission for the GOALS layer of the prompt."""
    if not mission:
        return "The user's near-term mission isn't set yet — ask, infer gently, don't assume."
    stage = mission.get("stage")
    priorities = mission.get("priorities") or []
    parts = []
    if stage:
        parts.append(f"Life-stage right now: {stage}.")
    if priorities:
        parts.append("Present priorities (in order): " + " > ".join(priorities) + ".")
    parts.append("Meet them where they are first; advance their dreams without abandoning this.")
    return " ".join(parts)
