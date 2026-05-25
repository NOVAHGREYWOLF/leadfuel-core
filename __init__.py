"""leadfuel_core — shared layer for the LeadFuel app suite.

SHIPPED (Phase 1, in progress):
  - service_auth    validate inbound X-Service-Token  (producer half of the mesh)
  - service_client  call other apps' APIs             (consumer half of the mesh)
  - knowledge       read/write the shared Knowledge System + document store (at the hub)

STILL TO EXTRACT from apps/novahawk/ri/ (couple to a per-app DB — needs the
packaging/deploy decision first; see docs/ROADMAP.md Phase 1):
  - leadfuel_auth   SSO / account-email / has_access entitlement
  - leadfuel_icp    get_icp / list_icps
  - spend           per-app spend reporting (feeds the hub rollup)
  - db mirrors      read-only models of leadfuel-owned tables

See docs/ROADMAP.md (Phase 1) and docs/ICP_INTEGRATION_PLAN.md.
"""
from . import knowledge, service_auth, service_client

__all__ = ["service_auth", "service_client", "knowledge"]
