# DESIGN · spatial views catalog · handoff 001 (2026-10-02)

Session: local_e5337961-1753-4b8f-8165-20a25c22b63e. Owner's direct request: make the Flow Atlas always on, add a live "data going in" layer, research map-style layers, and find every other place a spatial graphic (with a watchdog) would help, then ask what he wants.

## Done
- Published the private page **Spatial Views Menu**: https://claude.ai/artifact/G6HiaFgajgX6FSvAhfyMQz (version 1). It offers 4 always-on options for the atlas, 18 atlas layers (L01-L18) and 37 views (V01-V37), each with a reason, a watchdog, its data source, a live path and the owning desk. Build / Later / Skip picks save to the page's db, collection `picks` (doc id = L01 / V01 / `atlas-live`).
- Functional check: wrote, read (also at `view` level) and deleted one probe doc in `picks`. The store is empty now.

## State
- **Verified by this desk:** hub origin/main 073f802 has `/api/registry/spokes`, `/api/observability/wall`, 40 entries in `cron_heartbeat.CRONS`; `/healthz` returns only the worst cron; `check_all` keeps ages only for silent accounts; `health_watchdog` treats `empty` as ok; `networkx` is not in requirements. Through the brain connector: `recent_memory` returns stored time, authored time, source and privacy tier per row (so L01 live arrivals needs no hub change); `pending_actions`, `current_spend` and `corpus_stats` work; `quickbooks_freshness` answers "not available, nothing is wrong".
- **Taken on trust** from three survey agents: everything else marked "From a survey reading" on the page.
- The page's sources are inside the published HTML; `Artifact read` on the URL recovers them.

## Next
When the owner says his picks are in: `ArtifactData list` collection `picks`, then write each Build as a task on the Conductor desk page naming the owning desk. Do not start building before that.

## Owed / not delivered
- No message sent to ROUTER or CONDUCTOR from this session.
- Findings for owning desks, not acted on here: `/healthz` drops the never-ran count (WATCH); `check_all` discards healthy ages (SENSORS); health "empty" counted ok (FIELD); `quickbooks_freshness` reports fine while blind (SENSORS); ci-novahub hold ~2 h with 15 waiting and ci-odyssey ~6.5 h, survey reading at 12:28 UTC (WATCH).
