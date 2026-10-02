# DESIGN · spatial views catalog · handoff 002 (2026-10-02)

Session local_e5337961-1753-4b8f-8165-20a25c22b63e, stopped at ~312k. Follows design-spatial-views-001.md.

## Done
- Read the owner's picks (`ArtifactData list`, page G6HiaFgajgX6FSvAhfyMQz, collection `picks`): **all 55 are Build** (L01-L18, V01-V37), clicked 21:45-21:49 UTC, no notes. `atlas-live` (where the always-on atlas lives) has **no pick**.

- Conductor 007 (local_da515743) filed the 55 picks (its transcript cites "55 build picks on G6HiaFgajgX6FSvAhfyMQz, ranks 109-119"); not re-read on the Conductor page.
- Owner said "keep going": published **Atlas Live** https://claude.ai/artifact/6LEvF7K9u9qnSxh68VWsfA (v1), the first slice of item 1 = L01 live arrivals + L03 waiting pools. It declares `mcp` on "novahub brain" (recent_memory, corpus_stats, pending_actions, current_spend), polls 30-300 s, and shows times, sources, kinds and counts only, never item content. Result shapes were learned from real calls this session; the page's own calls run as the viewer and were NOT exercised here. Pools for embeddings and CI are drawn dashed as unknown. inbound_today (drafted replies) is left out because its result shape was never seen.

## Proposed grouping (filed by the conductor)
1. DESIGN, Opus (route.py: effort high): the live atlas page with a layer drawer, polling the brain connector. L01 L03 L04 L05 L06 L10 L11 L12 L13 L16 L18, plus the live-now parts of V07 V09 V10 V19.
2. SURFACE: read-only connector tools for hub JSON that already exists (fleet `/api/registry/spokes`, wall, cron heartbeats, egress panel, orders, memory catalog). Unlocks V02 V04 V08 V11 V12 L07 L09.
3. Hub truth fixes, each to its owning desk: SENSORS check_all keeps ages (V01 L17) and QuickBooks freshness says unknown (V23); WATCH /healthz never-ran count (V02); FIELD health "empty" and location "delivered" (V21 V22); SENSORS/DOORS per-stop times (L02); INTELLIGENCE state history (L08) and projection job (V03 V25 V24 V15 V05 V06).
4. ARMS, per arm: V13-V20.
5. NODE/WATCH local collectors: V26-V35, L14.
6. Customer: V36 (DESIGN), V37 (SURFACE).

## Next
Hand the pick list and this grouping to the conductor so it files them as tasks on the Conductor desk page (it writes that page itself through its add scripts in `leadfuel-conductor/data`). Do not write the conductor's page from a desk.

## Owed / not delivered
- **Two live sessions are titled `CONDUCTOR · system build`** (local_4de240e1, local_083bdfe0); the rule is exactly one. The owner said "use the newer conductor, send it the list". The list went to local_4de240e1 (created 20:16 UTC, child of local_083bdfe0) at about 22:05 UTC: delivery **queued, not confirmed read** (message_id 9040794a). The successor checks with `list_events` on local_4de240e1 that it was filed, and re-sends if not.
- `atlas-live` is unpicked. Default A (live page) so item 1 can start.
