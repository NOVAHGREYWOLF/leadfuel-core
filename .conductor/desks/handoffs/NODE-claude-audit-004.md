# Handoff: NODE · claude audit part · 3 (desk), 2026-10-13 ~02:05Z UTC, at the 300k guard

Session local_53c020d0-79f8-45c3-8279-23d5d6e3b144, group `claude audit`, Fable 5.1. Opened by the owner (no router). Public repo: ids only. Note 003 on this branch records the structure page and the 17 archives.

## Owner instruction, 2026-10-13 ~01:55Z (this chat)
"do the 26 fix then archive": the audit's FIX_THEN_ARCHIVE bucket (`F:/Claude Sessions/handoff/claude-audit-001/buckets.md`, ids; per-session fix text in `rows.json`, bucket FIX_THEN_ARCHIVE). Nothing archived yet; state below was gathered 01:58-02:03Z.

## State (verified by me)
- 3 of 26 already archived by others: 6b8ff456, e68e1e68, 083bdfe0. 23 remain.
- gh: every "merged" PR in the bucket is merged. Still open drafts: hub #711 (close as superseded by #789), hub #737 (not ours), novahos #26-#32 #34 #38, site #1 #6 #8, mcp #39.
- App worktrees of the 23: all clean, ahead-of-upstream 0. be232c9f's a920053d is already on origin/report-desk-log. 84568eb5 holds nested hub worktrees mt2-736 (6a302080, 10 commits not on origin/main) and mt2-trainA (a61f81f7, 26): make local branches `keep/mt2-736`, `keep/mt2-trainA` in novahub before archiving, then remove them.
- Hub worktrees not removed by archiving: cc-per-user (37 ahead, remote branch gone, check against origin/main), atlas-act-threats (25 ahead, 1 dirty file, read it first), lucid-day-hub-accept and book-time-utc (clean, on remote).
- `F:/Claude Sessions` push is DISABLED by design (sync via VAULT); 3037c6b, 71dbab0, 2ca9ae9 live there. Not a push job. Untracked there: desks/handoffs/* notes incl. the REPORT-DESK-LOG final note.
- Scratchpads survive archiving: e68e1e68's Fieldy dump still exists at `...\F--Leadfuel-repos-leadfuel-core\48ff980c-495b-469b-87e7-616446859545\scratchpad`.
- `detach_session` refuses chip-placed children (tool doc). So archiving a parent sweeps idle children with no open PR.
- Stale tickets of the 23 in `F:/Claude Sessions/.locks/ci-novahub.wait`: ...LUCID-DAY-HUB-ACCEPT-pr761, ...command-center-per-user-pr713, ...ATLAS-ACT-THREATS-pr747, ...WATCH-MERGE-ALL-GREEN, ...WORLD-LANE-2-open-pr; `full-suite.wait`: ...LUCID-DAY-HUB-ACCEPT--gates-then-pytest. The owner's instruction is the ruling for these; pull them as each session goes.

## Next
1. Archive, one call each, after the fix named: aaafc9b9, 18e77f32, 4e487d91, 189795a4, b43f0db0, 087f843b, 421a0f65, 0538771b, be232c9f, 84568eb5 (branches first), 7f8c732a (close #711 first), b7756f1c, 678d9904, 874ae11a, d91ea972, ae41c845. Then ROUTER #11 99c30023 (its children be232c9f, 874ae11a gone), then ROUTER #21 d51bda2e (children d91ea972, 0538771b, 84568eb5 gone; e137f345, 50f531b4 already archived).
2. Hold, children owe work and cannot be detached by a tool: 250be6e6 (child ce416a80), ROUTER #13 21748811 (4e1440cc, 96e507d3, and #14), ROUTER #14 34998bfa (85ca338f, 90bbf62d), ROUTER #24 17705746 (5caa5279, c6e0da09, and #25), ROUTER #25 447575ed (99adadec). Owner step: sidebar, each child, "Detach to top level"; then archive.
3. One message to the live conductor with the cards the fixes name: CI-runner leftovers (4e487d91), backup -Verify/-RestoreTest after 10-18 (b43f0db0), novahos stack land-or-close (b7756f1c), SIDEBAR-SWEEP superseded (678d9904), world lane items 3-4 (d91ea972), out-door remedy (b) + gate ownership (ae41c845), Kismet routine (678d9904).

## Owed
- Owner: the detach step in 2; "revive" build; lock fossil ruling for tickets outside the 23.
- Sends this part: 4 to conductor 030 (all delivered, none confirmed read); 0 undelivered.

## Gotchas
- Scripts and gh loops in one Bash call; `list_sessions` at limit 200 is ~25k tokens, avoid. `rows.json` field `id` is the full session id.
