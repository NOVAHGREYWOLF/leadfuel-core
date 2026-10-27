# ROUTER #96 · one-app handoff (ids and status only, 2026-10-26 22:30 PT)
Predecessor note: router-095.md. Router #96 session: local_c71b620c-37c5-4c58-bb3b-9545175ee8d8 (stays open until its 3 background agents finish; do NOT archive it before). Conductor: local_6fc9e01a-601e-4c47-bb30-815437069049 (one STATUS sent, queued). #95 archived. Code is in the private estate F:\Leadfuel, LOCAL ONLY, never push one-app/*. Integration worktree F:\Leadfuel\.claude\worktrees\one-app-int (branch one-app/int). Sidebar group `one-app` = cg-f7545554-2b6e-490d-8f68-c8de4a9a9c87 (I created it; no desk is filed there, my desks are background agents).

## RUNNING background agents (belong to #96, die if #96 is archived; read their state from git, their reports come to #96)
- ad478e00feee4e719 finished (part 1, hit cap). a49892062b5c24a39 = ONE-INT part 2 (NODE one-app part 2): merges in int; at 22:30 PT cn1 cn26 cn7 a2 c2 d e2 code cd2 are IN, int head 5596597; left: one-app/remote (ONE-REMOTE, added by me as phase 3), full suite runs (one after the six, one after remote), handoff ONE-INT.md. I told it (queued) to remove the duplicate 'Character Design' nav entry (cause: `merge(true)` left off, rail from morepanes.js + chardesign.js both register); verify it did.
- a24b9fa9d0469889b = ONE-G1 voice UX resume (NODE one-app part 3, Sonnet), worktree one-app-g1, own branch, told: voice LOCAL only, no cloud TTS door.
- aae83352363b38919 = ONE-MANIFEST (NODE one-app part 4, Opus): doc home-node/35-Node-Model-Manifest.md, design only, branch one-app/manifest.

## Owner answers (cards q649 later, q650 resume, q651 leave; q648 superseded). Memory files written.
Owner rules: connections made once, usable from desktop and online like Claude (offline case open); voice local, never edge-tts; installer preloads everything per tier.

## NEXT (top priority, owner's last words): the UI must look like the approved NovahOS mockup and like Claude: easy, expandable, easy to navigate. Seen on mock host (snapshot of int 52b58af): TWO navs (legacy left rail + side nav), 13 items, duplicate Character Design. Approved mockup nav = New chat, Search, Archive, Character Design, Catalogue, System, history by date, account block (docs 31, 32 s.2). The mockup's visual file was NOT found (only its description): ask the owner which artifact or find it. Open a UI desk AFTER part 2 reports (branch from int), brief = one sidebar, six core items, groups collapse, Settings in account block, Home = New chat empty state, Voice/Terminal/Files as System tabs. ui/app.js now free (chunk A merged).
Then the rest of the next wave (router-095.md list) plus: CN desks carry 'one account connection' rule, S installer last using doc 35.
Cards pending on the Router desk page: q617 only.
Gotchas: start_session refuses on automated-event turns, use Agent; mock bridge lacks clarify_pending and prime_display (mock-only toasts).
