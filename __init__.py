"""leadfuel_core — shared layer + Nova OS kernel for the LeadFuel/Nova app suite.

MESH (Phase 1):
  - service_auth    validate inbound X-Service-Token  (producer half of the mesh)
  - service_client  call other apps' APIs             (consumer half of the mesh)
  - knowledge       read/write the shared Knowledge System + document store (at the hub)

NOVA OS KERNEL (Phase O — governance every app inherits; pure stdlib, additive):
  - constitution    ranked principles: Autonomy > Safety > Goals (+ prompt preamble)
  - consent         three-tier consent (green/yellow/red) per action kind
  - privacy         three-tier privacy classifier (private/semi/public) at ingestion
  - warden          deterministic action gate (approve/escalate/block + audit)
  - mcp             in-process tool registry (MCP-shaped integration substrate)

Adopt incrementally and opt-in per app — existing functions are untouched, so this
release is backward-compatible.

STILL TO EXTRACT from apps/novahawk/ri/ (see docs/ROADMAP.md Phase 1):
  - leadfuel_auth, leadfuel_icp, spend, db mirrors.
"""
from . import (
    consent,
    constitution,
    knowledge,
    mcp,
    privacy,
    service_auth,
    service_client,
    warden,
)

__all__ = [
    "service_auth",
    "service_client",
    "knowledge",
    "constitution",
    "consent",
    "privacy",
    "warden",
    "mcp",
]
