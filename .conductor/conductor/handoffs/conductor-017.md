# Handoff: CONDUCTOR · system build, 017 (2026-10-07 ~05:50Z, rotating at ~300k)

Ids only (public repo). This session: local_51008c82, branch claude/conductor-017. Pages: Conductor desk MKAx49RAskZ3cV7f2EkDMF, Router desk LzmP6QcxmYh9TdvMMjS883, Build Board A4uS9xn1emqupohdE4DUfV (router/current). The 30-min tick cron is DELETED. Re-create it at minutes 13,43 with the prompt in 013's note; query picks with `decided_at >=` the last tick and cards with `n >= 325`.

## Done (verified by me)
- Archived 016 local_8594cdf2 through the gate.
- Picks filed: 220 NODE WAY-SCRIPT-TOOLKIT (q322), 221 VAULT HUB-ANON-KNOWLEDGE-DOCS (q323; desk local_6eb9de30 running at 05:44Z), 222 SURFACE CC-GAME-SHELL ("one-interface" project, started by the owner). q324 = A noted on picks 204 AUTO-DESKS and 220.
- One-interface runs under the ESTATE router: the owner overrode my separate router at ~05:39Z. Its 21 picks are listed in claude/router-one-interface-1 @ b3ccb9e, .conductor/projects/one-interface/. ROUTER #25 was told.
- Filed UNQUEUED: NODE CORE-PR8-DEAD-HOOKS. Core #8 (DIRTY) is checked out in the shared main folder and still carries the python3 hooks that #31 removed.
- Picks 213-218 updated with ROUTER #25's routing.
- Book project "resonance" is a separate estate. It has its own router, ROUTER #1 · resonance local_73406e4f (I set it to Sonnet), its own pages (Conductor 66JYwW5GPc5HMcFdqD7iHj, Router WHPPzczLHLzjCPiP4kuCCd) and one sidebar group, "Resonance Effect". Its plan files stay local. Nothing is queued there yet.

## State (trust; re-read)
- Live estate router: ROUTER #25 local_447575ed (claimed 04:48Z). #24 local_17705746 not archived yet (that is #25's claim step).
- Hub tests on main were pending at 05:22Z.
- Unused worktree router-resonance-1 (no commits): safe to remove.
- Keep #11, #12, #13 and conductor 005 local_083bdfe0.

## Next
Re-create the tick, then file owner answers that create work. Open cards: q208, q294, q315-q318, q325, q326.

## Arrived after the handoff (for 018)
- From ROUTER #25 (~06:0xZ): it runs one-interface, and its first desk is chip task_4762696b, DESIGN · ONE-PLACE-DESIGN 2/2 (Fable pin from q180), rescoped to the CC-GAME-SHELL spec. Note that on picks DESIGN~ONE-PLACE-DESIGN (189) and SURFACE~CC-GAME-SHELL (222). #25 also reports, unverified by me, that hub #776 /command merged 04:53Z and train F landed. I told #25 that CC-PHONE-READY (pick 212) is still queued and is its to open.

## Gotchas
- With MSYS_NO_PATHCONV=1, `git -C /f/...` fails: use F:/ paths.
- Estate work goes to the estate router. Only a separate estate gets its own router (owner, 05:39Z).
- A router opened from a chip nests under its opener. Use a paste prompt.
