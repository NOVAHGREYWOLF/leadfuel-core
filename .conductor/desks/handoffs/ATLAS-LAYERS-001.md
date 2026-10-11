# DESIGN · ATLAS-LAYERS 1/1 · handoff 001 (2026-10-06)

Desk local_1fb48586-dd83-4345-a7db-5e2a4fcf32dd (Opus). Router: ROUTER #22 local_09dd8448 (rotating to #23). Handed off at the 300k guard before any build.

## Done
- Duplicate check: SURFACE · CC-ROUTE-MOVE local_e137f345 is not building layers. Its one commit 5c1f3fd on novahub `claude/affectionate-sammet-a9c442` moves /goal routes only (read with git show). No other desk is building layers.
- Read the live Atlas Live (artifact 6LEvF7K9u9qnSxh68VWsfA, version 1791062377-1d32 = v10). Verified: still 10 layers; v10 added only the part drill-down.
- Read all 55 picks (G6HiaFgajgX6FSvAhfyMQz, collection picks): all build. Read the catalog definitions from that page's source.
- Read each brain connector read tool once to learn result shapes. Keys only were kept.
- Wrote the build spec: which picks can draw from the connector today (30: 17 layers, 13 views), which stay unknown (25), the new tool manifest, the UI plan, and a line map of the page. It is private build material on this PC: `F:/Claude Sessions/handoff/ATLAS-LAYERS-001-spec.md`.

## State
- Nothing published. Atlas Live is unchanged at v10.
- Branch `claude/hopeful-lewin-b9e3e3` in leadfuel-core, this note only.

## Next
ATLAS-LAYERS 2/2 (DESIGN, Opus): read the spec file above, re-read Atlas Live with the Artifact tool, then build and publish in place with the new capabilities set.

## Owed
- Nothing for the owner. Viewers must allow the wider connector manifest once after the publish.

## Gotchas
- Connector reads return private content (message text, goal intents, mail previews, coordinates). Read with small limits, and never put values on the page.
- Line 2573 of the page is one 145 KB JSON line. Never edit it.
- The Bash tool needs `MSYS_NO_PATHCONV=1` for `git show <ref>:<path>`.
- DESIGN · ATLAS-DATA-REFRESH 2/2 (local_1ba6b145) also publishes Atlas Live. It is idle and says it re-reads before any write. Build on the live version at publish time.
