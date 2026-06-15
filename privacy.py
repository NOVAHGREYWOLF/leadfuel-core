"""Three-tier privacy — classify a data point at ingestion.

  PRIVATE 🔴  health, identity, financial credentials, intimate communications.
              Minimized; never sent to third parties; local-only in the sovereign tier.
  SEMI    🟡  email, files, business comms — self-hosted/own DB; may be processed by a
              trusted model with consent.
  PUBLIC  🟢  published/marketing content — free to flow.

Classification is a deterministic heuristic over (source, type, content keywords). It errs
toward PRIVATE on ambiguity — safer to over-protect. Apps can override per data point.
"""
from __future__ import annotations

PRIVATE = "private"
SEMI = "semi"
PUBLIC = "public"

_PRIVATE_SOURCES = {"applehealth", "health", "fitbit", "strava", "bank", "finance", "messages", "imessage", "whatsapp"}
_PRIVATE_TYPES = {"health", "vitals", "credential", "secret", "medical", "intimate", "financial"}
_PRIVATE_KEYWORDS = (
    "diagnos", "medication", "therapy", "depress", "anxiet", "ssn", "password", "account number",
    "routing number", "salary", "net worth", "intimate", "sexual", "suicid",
)
_PUBLIC_SOURCES = {"published", "blog", "marketing", "website"}
_PUBLIC_TYPES = {"published_post", "marketing", "press"}


def classify(source: str = "", type_: str = "", content: str | None = None) -> str:
    """Return PRIVATE / SEMI / PUBLIC for a data point. Defaults to SEMI; ambiguity → PRIVATE."""
    s, t = (source or "").lower(), (type_ or "").lower()
    if s in _PRIVATE_SOURCES or t in _PRIVATE_TYPES:
        return PRIVATE
    if content:
        c = content.lower()
        if any(k in c for k in _PRIVATE_KEYWORDS):
            return PRIVATE
    if s in _PUBLIC_SOURCES or t in _PUBLIC_TYPES:
        return PUBLIC
    return SEMI


def may_send_to_third_party(tier: str) -> bool:
    """PRIVATE data never leaves to third parties (e.g., external/non-trusted services)."""
    return tier != PRIVATE


def may_use_cloud_model(tier: str) -> bool:
    """PRIVATE may use a cloud model only behind an explicit consent gate; default deny here."""
    return tier in (SEMI, PUBLIC)
