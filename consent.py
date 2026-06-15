"""Three-tier consent — how much autonomy the user grants an action kind.

  GREEN  🟢  pre-authorized: act immediately, log after.
  YELLOW 🟡  propose → user approves before execution.
  RED    🔴  always escalate: never act without explicit, real-time approval.

Defaults are conservative (anything that sends/spends/deletes/posts is RED). Users
configure per action-kind; pattern-learning may *suggest* a tier change but never
auto-promotes (that would violate Autonomy). Pure stdlib / deterministic.
"""
from __future__ import annotations

GREEN = "green"
YELLOW = "yellow"
RED = "red"

# Conservative defaults by action kind. Apps extend this map; user overrides win.
DEFAULTS: dict[str, str] = {
    # read-only / low-risk → auto
    "read": GREEN,
    "search": GREEN,
    "label": GREEN,
    "ingest": GREEN,
    "summarize": GREEN,
    "suggest": GREEN,
    # novel / cross-app → propose-approve
    "create_draft": YELLOW,
    "schedule": YELLOW,
    "create_task": YELLOW,
    "sequence_stage": YELLOW,
    # irreversible / outward / money → always ask
    "send_email": RED,
    "send_message": RED,
    "post_social": RED,
    "spend": RED,
    "transfer": RED,
    "delete_external": RED,
    "apply_job": RED,
    "campaign_approve": RED,
}

_ORDER = {GREEN: 0, YELLOW: 1, RED: 2}


def tier_for(action_kind: str, overrides: dict[str, str] | None = None, default: str = RED) -> str:
    """Resolve the consent tier for an action kind. Unknown kinds default to RED (safe)."""
    if overrides and action_kind in overrides:
        return overrides[action_kind]
    return DEFAULTS.get(action_kind, default)


def requires_approval(tier: str) -> bool:
    """GREEN acts immediately; YELLOW and RED need approval first."""
    return tier in (YELLOW, RED)


def stricter(a: str, b: str) -> str:
    """Return the more restrictive of two tiers (used when combining signals)."""
    return a if _ORDER.get(a, 2) >= _ORDER.get(b, 2) else b
