# leadfuel-core

Shared library for the **LeadFuel Business Suite** apps (novahawk · novahub · icp · campaign).
No app, no domain — just the common code each service imports so the suite behaves uniformly.

Install it in any app (add to that app's `requirements.txt`):
```
leadfuel-core @ git+https://github.com/NOVAHGREYWOLF/leadfuel-core.git@main
```
Local dev: `pip install -e .` from a clone, or `pip install git+https://github.com/NOVAHGREYWOLF/leadfuel-core.git`.

## What's in it
- **`service_auth`** — validate inbound `X-Service-Token` (the producer half of the mesh).
  503 until `LEADFUEL_SERVICE_TOKEN` is set, 403 on a bad/missing token.
- **`service_client`** — call other apps' token-authed APIs (the consumer half). Base URLs from
  per-app env (`NOVAHAWK_API_URL`, `ICP_API_URL`, `CAMPAIGN_API_URL`, `HUB_API_URL`). Stdlib only.
- **`knowledge`** — read/write the one shared Knowledge System + document store at the hub
  (`get_knowledge` / `add_knowledge` / `add_document`).

Two-way comms: every app gets both halves (serve + call), so any app can talk to any other.

## Usage
```python
from leadfuel_core import service_auth as SA, service_client as SC, knowledge as K

# guard an endpoint
if not SA.is_enabled():               return 503
if not SA.header_authed(req.headers): return 403

# call another app
leads = SC.get_leads("cust@acme.com", priority="High")
icp   = SC.get_icp("cust@acme.com")

# write to the shared knowledge store
K.add_knowledge("cust@acme.com", "learning", "Replies fastest Tue AM", source="icp")
```

Dependency-free by design (stdlib only). Public repo — contains no secrets.
