# DESIGN · 3D system flow map · handoff 001 (2026-10-02)

Session: local_d235ebbb-8ed8-4968-8979-bdbba357eedc. Owner's direct request: a 3D spatial view of how the whole system flows.

## Done
- Published the private artifact **LeadFuel Flow Atlas**: https://claude.ai/artifact/UCCG9zfCDWeveQMuT1MFZ5 (version 2). It runs on three.js 0.147 and is a single HTML file.
- It maps 90 parts and 167 flows across 11 layers: world, sensors, stores, core, faculties, meaning, doors, arms, surfaces, Novah, machine. Each part cites a file and line or a desk doc, marked as read in code or stated in a doc.
- The page puts the answer first: 3 breaks (embedding gateway, master report citations, the local NovahPrime briefing) and 5 paths around a gate (reach, odyssey, the hub sender, echo, scope).
- Features: four tours, a text index, search, click-to-trace (direct neighbours bright, the rest of the chain faint), and a "show only where it breaks" view.
- Styling follows Tufte R1-R15 on the Novah tokens: colour marks exceptions only. CONDUCTOR approved the plan.

## State
- **Verified:** arms.py on main keys the hub as `core` since 2026-09-29 (alias `hub`); echo, scope and orbit are FACULTY tier; the page renders with no console errors at 1440×900.
- **Taken on trust** from three survey agents reading hub main @ 4c54132: every count and every state.
- **Not checked:** phone layout on the live page.
- The build sources were in this session's scratchpad. To edit, use `Artifact read` on the URL and work from the saved HTML. The data is the `DATA` object; the engine follows it.

## Next
Open the artifact on a phone and fix what is broken. Correct any part a desk disputes; the owning desk owns those facts.

## Owed / not delivered
- The published link reached CONDUCTOR. The copy for ROUTER #9 bounced ("not reachable"); its earlier status copy did land.
- No owner decision is pending.

## Gotchas
- The browser pane cannot inspect file:// pages or private artifacts without a sign-in. Serve the file locally to check it.
