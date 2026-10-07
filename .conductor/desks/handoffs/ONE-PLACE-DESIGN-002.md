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

## Owner reaction (typed in this session, 2026-10-07 ~06:5xZ; true source: local_94485af5)
"okay great. but we are missing the spacial atlas. this is good but i think it could be better.
write the hand off. DOes this seem like a video game? its getting there."
Read: the world must be the SPATIAL atlas (the 3D crystal of Atlas Live v11 / hub
`goal_atlas.html`), not the flat ring; and the whole thing must feel more like a game.
Second message, same session: "i dont really see any of the command prompt or all the different
types of command prompt screens like developer... as also mentioned before it should go in as far
and out as far as can. micro macro. also where is the live?" Read, three gaps the 2/2 screens have:
1. The registers are missing: plain / operator / developer (1/1 and the hub /command have them)
   and the developer screens (Engineering tree, source rows, ids, citations by id); also a real
   command prompt: the Ask box doubles as a console (`/` jumps, `>` runs a command, `?` asks).
2. Zoom is only two levels. It must go out to the whole estate and in to the smallest thing:
   estate → region → part → "Made of" (376 parts: module, route, table, cron, setting) → the code
   line, commit, test and row it is calculated from (Atlas v11's detail panel has this chain).
   One continuous zoom, the trail and minimap showing the depth.
3. "The live" is absent: the mock is example data. Show the Live rail (status, arrivals every
   30 s, waiting pools, snapshot age) as a HUD element; and consider making the mock itself live
   the way Atlas Live v11 is (a plain artifact reading the brain connector), since a Design-type
   artboard cannot call the network.

## Next (one step)
First, replace the stage with the spatial atlas: the crystal (hex prism, pyramid caps, lattice
cross-sections, parts placed by region and row as Atlas v11 does; sensors on the lower faces,
arms on the upper, Core at the origin, Novah above), drawn so you move THROUGH it: selecting a
part flies the camera to it (~1.6 s ease), the HUD panels overlay the crystal, Home is the
character at the core looking out, overlays are the live layers (comets, fog, routes) on the
crystal. Cheapest sure path: an isometric SVG crystal in `Main.dc.html` and `Map.dc.html` with
the HUD over it. Better: one 3D artboard, three.js uploaded as a .js asset (Design type step 3),
orbit + fly-to + click a part → Focus. The 2D ring becomes the minimap and the no-WebGL /
reduced-motion fallback. Then the 4 missing artboards, one Write then one publish each:
`Quests.dc.html`, `Owner.dc.html` (whole estate, amber scope pill, owner powers under a menu
divider), `Phone.dc.html` (390×844, no fake status bar), `Hud.dc.html` (same Home in the
LeadFuel Command cyan HUD skin; option B). Game feel to add everywhere: things are summoned,
not always shown (a menu pick pulls its panel up with a short dolly); motion on arrivals and
state changes; a sense of place (region name and depth when you enter one). Then STATUS: DONE
to ROUTER #25 with the artifact url.

## Owed / not delivered
- Owner choice, via a Router desk card: skin A (Novah tokens, gated q176 C2=B, screens 1–9) or
  skin B (Command HUD, screen 10). Default A; B implies a tokens PR and a CSP font change.
- No message to the router sent yet from this session; the STATUS: CONTINUING goes with this note.

## Gotchas
- Design type rules: canvas.json first; one artboard Write then publish; never verify by rendering.
- The agent list cannot name arms: the mock types the six ratified names; the build note says
  `arms.keys()`.
- `git show origin/x:path` under Git Bash needs `MSYS_NO_PATHCONV=1`.
