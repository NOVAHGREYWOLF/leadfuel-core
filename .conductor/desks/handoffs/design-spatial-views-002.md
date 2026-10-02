# DESIGN · spatial views catalog · handoff 002 (2026-10-02)

Session local_e5337961-1753-4b8f-8165-20a25c22b63e, stopped at ~312k. Follows design-spatial-views-001.md.

## Done
- Read the owner's picks (`ArtifactData list`, page G6HiaFgajgX6FSvAhfyMQz, collection `picks`): **all 55 are Build** (L01-L18, V01-V37), clicked 21:45-21:49 UTC, no notes. `atlas-live` (where the always-on atlas lives) has **no pick**.

## Proposed grouping (not yet filed anywhere)
1. DESIGN, Opus (route.py: effort high): the live atlas page with a layer drawer, polling the brain connector. L01 L03 L04 L05 L06 L10 L11 L12 L13 L16 L18, plus the live-now parts of V07 V09 V10 V19.
2. SURFACE: read-only connector tools for hub JSON that already exists (fleet `/api/registry/spokes`, wall, cron heartbeats, egress panel, orders, memory catalog). Unlocks V02 V04 V08 V11 V12 L07 L09.
3. Hub truth fixes, each to its owning desk: SENSORS check_all keeps ages (V01 L17) and QuickBooks freshness says unknown (V23); WATCH /healthz never-ran count (V02); FIELD health "empty" and location "delivered" (V21 V22); SENSORS/DOORS per-stop times (L02); INTELLIGENCE state history (L08) and projection job (V03 V25 V24 V15 V05 V06).
4. ARMS, per arm: V13-V20.
5. NODE/WATCH local collectors: V26-V35, L14.
6. Customer: V36 (DESIGN), V37 (SURFACE).

## Next
Hand the pick list and this grouping to the conductor so it files them as tasks on the Conductor desk page (it writes that page itself through its add scripts in `leadfuel-conductor/data`). Do not write the conductor's page from a desk.

## Owed / not delivered
- No message was sent. **Two live sessions are titled `CONDUCTOR · system build`** (local_4de240e1, local_083bdfe0); the rule is exactly one, so the owner or the router decides which one gets this before anything is sent.
- `atlas-live` is unpicked. Default A (live page) so item 1 can start.
