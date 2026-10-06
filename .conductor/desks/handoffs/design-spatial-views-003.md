# DESIGN · spatial views · handoff 003 (2026-10-02): two builds the owner asked for

Session local_e5337961-1753-4b8f-8165-20a25c22b63e, stopped at ~390k. Follows 001 and 002 (read 002 first).
Owner, in that session, about Atlas Live (https://claude.ai/artifact/6LEvF7K9u9qnSxh68VWsfA, v4): "this is 2d, we also want it in 3d mode. Also make sure this is sitting with the rest of the surface stuff so we can see it anytime both local and online."

## Build A · DESIGN · 3D mode (Opus, route.py: effort high)
- Merge Atlas Live's ten layers (arrivals, travel time, volume, privacy zones, cost, blind spots, borders, claimed vs measured, your trail, permission routes) and its two pools into the 3D Flow Atlas (https://claude.ai/artifact/UCCG9zfCDWeveQMuT1MFZ5, three.js 0.147, data in its `DATA` object). Add a 2D/3D switch; 2D is today's Atlas Live drawing.
- Read the atlas fully with `Artifact read` before republishing (1,428 lines). Keep the Tufte rule: colour is for state only; each layer owns one channel.
- **Make the data source an adapter**: one `connector` adapter (the `mcp` capability on "novahub brain": recent_memory, corpus_stats, pending_actions, current_spend, quickbooks_freshness) and one `hub` adapter that reads the same facts from the hub's own JSON routes. Build B needs this so one page runs in both places.
- Done when: the 3D atlas shows the layers live, the switch works, and it is checked once on phone width.

## Build B · INTELLIGENCE (command center lane) · the atlas inside the hub (Opus)
- Owner of the files: SESSION_MAP.md:272 gives `wall_lenses.py` and the lens templates to INTELLIGENCE · command center. Its old session id is not live, so a new desk in the INTELLIGENCE group takes it.
- Serve the atlas page from the hub beside the command wall (`/admin/wall`), signed-in owner only, so it is at the local hub on the home node (local-hub :8080) and on the production hub.
- Feed it from the hub's own routes. The connector's tools map to these routes (novahub-mcp `mesh_client.py`): `/api/actions/pending`, `/api/spend/current`, `/api/registry/spokes`, `/api/observability/wall`. A route for recent arrivals may need adding.
- No new outbound call from the server (Law 9). The browser loading three.js from a CDN is a separate question: vendor it under static/ if the hub's CSP or policy requires it.
- Rules: take a worktree in the hub repo, run `sh scripts/gates.sh` and bare `pytest`, take the `ci-<repo>` hold, and merge on green. A merge to main deploys to production in about 5 s.
- Depends on Build A's adapter. B can start on the route and the template shell in parallel.

## Owed
- Neither build was started here. Start cards: Build A task_5266e378, Build B task_9e9c7a2d (each starts when the owner clicks).
- Conductor 007 (local_da515743) is archived; the send to it bounced. Re-sent to the most recently active CONDUCTOR session, local_b666d711: delivered, its turn started on it, not confirmed read.
- Still two sessions titled CONDUCTOR · system build (local_b666d711, local_083bdfe0); the rule is exactly one.

## Status read 2026-10-03 ~02:15 UTC
- Build B stood down (ATLAS-HUB-001.md on hub branch claude/nice-rhodes-c5c334 @ 8d79a3d): on ROUTER #13's relay of owner answer q177, the atlas lives in the hub as the map view, hub PR #730 (/goal/atlas) and #736 (/goal/atlas/live). Verified here with gh: #730 open draft, CLEAN; #719 open draft. #713, #720 and #736 not read (gh timed out). Follow-up link from /admin/wall went to ROUTER #13.
- Build A: ATLAS-3D 1/1 (local_0f7bb7a2) settled the design and published nothing; handed off at 300k (atlas-3d-001.md) and asks ROUTER #13 first whether 3D still goes ahead beside the hub map view. No successor seen in the DESIGN group at this read.

## 2026-10-05 final
- Owner: "we should have 55 layers". All 55 picks (L01-L18, V01-V37) become atlas layers. Relayed to ROUTER #20 local_461fe4e9: delivered, not confirmed read.
- On the atlas as of Atlas Live v5: 10 layers plus part of L03. v10 is reported published and was not read here.
- This session is at its hard cap. Next: a SPATIAL-LAYERS desk opened by ROUTER #20 (ATLAS-VIEWS / SPATIAL-1), after it checks for duplicates.
