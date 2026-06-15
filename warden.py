"""WARDEN — the deterministic enforcement gate.

Every consequential action is evaluated here BEFORE it runs. WARDEN is pure, auditable
code (never an LLM) so it can't be jailbroken or talked around: LLM agents propose,
WARDEN disposes. It checks, in order:

  1. authentication        (no identity → block)
  2. privacy transition    (PRIVATE data → third party → block; Safety)
  3. consent tier          (YELLOW/RED without approval → escalate)
  4. resource limits       (over budget/quota → block)
  -> else approve. Every path returns an audit record for the log.

WARDEN can block / escalate / throttle an action; it cannot act on the user's behalf,
override the user, or modify the Constitution.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import consent as _consent
from . import constitution as _con
from . import privacy as _privacy

APPROVE = "approve"
ESCALATE = "escalate"   # needs explicit user approval first
BLOCK = "block"


@dataclass
class Action:
    kind: str                              # see consent.DEFAULTS keys
    authed: bool = True
    approved: bool = False                 # did the user explicitly approve THIS instance?
    consent_overrides: dict | None = None  # per-user tier overrides
    privacy_tier: str | None = None        # privacy tier of data involved (privacy.classify)
    destination: str = "internal"          # internal | trusted | third_party
    resource_ok: bool = True
    meta: dict = field(default_factory=dict)


@dataclass
class Decision:
    verdict: str                  # approve | escalate | block
    reason: str
    principle: str | None = None  # which Constitution principle drove a block/escalate
    consent_tier: str | None = None
    audit: dict = field(default_factory=dict)


def evaluate(action: Action) -> Decision:
    tier = _consent.tier_for(action.kind, action.consent_overrides)

    def _audit(verdict: str, reason: str, principle: str | None) -> dict:
        return {
            "kind": action.kind, "verdict": verdict, "reason": reason,
            "principle": principle, "consent_tier": tier,
            "privacy_tier": action.privacy_tier, "destination": action.destination,
        }

    # 1. authentication
    if not action.authed:
        return Decision(BLOCK, "no authenticated identity", _con.AUTONOMY, tier,
                        _audit(BLOCK, "unauthenticated", _con.AUTONOMY))
    # 2. privacy transition (Safety): PRIVATE data must never leave to third parties
    if action.privacy_tier == _privacy.PRIVATE and action.destination == "third_party":
        return Decision(BLOCK, "PRIVATE data cannot go to a third party", _con.SAFETY, tier,
                        _audit(BLOCK, "private->third_party", _con.SAFETY))
    # 3. consent tier (Autonomy): YELLOW/RED need explicit approval
    if _consent.requires_approval(tier) and not action.approved:
        return Decision(ESCALATE, f"consent tier {tier} requires approval", _con.AUTONOMY, tier,
                        _audit(ESCALATE, "needs_approval", _con.AUTONOMY))
    # 4. resource limits (Safety)
    if not action.resource_ok:
        return Decision(BLOCK, "resource/quota limit exceeded", _con.SAFETY, tier,
                        _audit(BLOCK, "resource_limit", _con.SAFETY))
    # approve
    return Decision(APPROVE, "ok", None, tier, _audit(APPROVE, "ok", None))
