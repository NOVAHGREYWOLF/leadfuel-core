# ONE-PLACE-DESIGN 2/2 → 3/3 handoff (DESIGN desk, 2026-10-07)

Session: `DESIGN · ONE-PLACE-DESIGN 2/2 · one-interface mock-up`, local_94485af5-fea9-4e57-b53a-9d7de684766d,
model Fable 5.1 (switched by ROUTER #25 at the owner's pin q180). Router: ROUTER #25
local_447575ed-7d43-46a1-9189-5723397c433f. Reason: context guard crossed 300k mid-task. No PR: design only.

## Done (verify, do not trust)
- Design artifact **https://claude.ai/artifact/TL21cZ8Bh5GnKixuQFjwaM** (Design canvas, private; owner opens it).
  Index `project/canvas.json` lists 10 artboards and carries one build note per screen as stickies
  (n1–n10) plus the title note. **6 of 10 artboard files are published**: Main (Home), Map (overlays,
  layer rows toggle real overlays), Focus (HUD at QuickBooks balances), Act (the door), Ask (cited,
  over the map), Search (jump palette). Clickable: every screen links to the others.
- Sources copied to `one-place-design-002/project/` beside this note (same bytes as published).
- Verified myself: hub origin/main fd6b0fd holds the #772 tokens (`--lf-state-*`, depth, grid,
  glow, selected); hub `static/atlas/topology.json` = 11 layers, 90 nodes with angle `a` and
  `regionDividers` [27,78,112,160,210,262,333]: the mock's map is that polar layout. Taken on trust
  (subagent read of Atlas Live v11, LeadFuel Command, the review page, the Conductor desk):
  the 55 picks L01–L18 / V01–V37 and their names, used verbatim in Map.dc.html.

## Next (one step)
Write and publish the 4 missing artboards, one Write then one publish each, same `url`, `root` =
a folder holding `project/`, chrome copied from Main.dc.html: `Quests.dc.html` (quest log over the
world: goals + campaigns, worst first, next step with disposition), `Owner.dc.html` (whole estate:
amber scope pill "whole estate", Mine/Estate toggle, all 90 places lit, estate census pane in
Today, owner powers under a menu divider: Estate, Desks, Train, Spend, Runners), `Phone.dc.html`
(390×844: world fills, Today/Act bottom sheet, tab bar Home·Map·Quests·Act·Ask, no fake status
bar), `Hud.dc.html` (the same Home in the LeadFuel Command cyan HUD skin: Barlow Condensed /
Barlow / JetBrains Mono via one Google Fonts link, hex pips, bracket panels; option B for the
owner). Then report STATUS: DONE to ROUTER #25 with the artifact url.

## Owed / not delivered
- Owner choice, via a Router desk card: skin A (Novah tokens, gated q176 C2=B, screens 1–9) or
  skin B (Command HUD, screen 10). Default A; B implies a tokens PR and a CSP font change.
- No message to the router sent yet from this session; the STATUS: CONTINUING goes with this note.

## Gotchas
- Design type rules: canvas.json first; one artboard Write then publish; never verify by rendering.
- The agent list cannot name arms: the mock types the six ratified names; the build note says
  `arms.keys()`.
- `git show origin/x:path` under Git Bash needs `MSYS_NO_PATHCONV=1`.
