# Router handoff #015 -> #016 (2026-10-03 ~18:45 UTC)

ROUTER #15 is local_8e21f892-8f9f-4a18-9624-bef6418d1cd4 (Opus), ~230k tokens. Ids only. Re-read live state; do not trust these lines.
Router desk LzmP6QcxmYh9TdvMMjS883, Conductor desk MKAx49RAskZ3cV7f2EkDMF, board router/current (A4uS9xn1emqupohdE4DUfV) v18. Conductor 009 local_e8701502.

## Priority: owner's ATLAS-GREEN order. Never paint green; unknown -> measured.

## ci-novahub (UTC)
- #739 merged 8df6327 18:11Z. ATLAS-B1 local_70fae0d7 (#740, on Fable xhigh) took the lock 18:14Z, pushed main-merge head 331d5be, CI running.
- Next offers, in order: SENSORS QBO-REAUTH local_6343c1fa (#726, ATLAS-QBO, told it's next), then INTELLIGENCE ATLAS-B2 local_b0fbc21c (#728, main merged locally, unpushed), then the oldest green tickets.

## ATLAS desks (all woken 18:20Z after ECONNRESET at ~16:27Z)
- DOORS ATLAS-DOORS local_3f2e7535 (Opus): has 2 queued relays of arm send paths (reach, signal, lucid, odyssey).
- COMMS local_90bbf62d: draft hub #749 (Teams manual), waits on q211.
- BRAIN-MEASURE local_261fb941, SENSOR-REG local_85ca338f: no report since wake.
- ARM-SENDS local_adf52fcb: send paths -> DOORS; measuring scope write path.
- VAULT-RAW local_6b8ff456: waits on q210 (owner must type yes in its chat).
- DATA-REFRESH 2/2 local_1ba6b145: batches 1-3 sent; forward every ATLAS DONE to it.
- ARMS PRIME-BRIEFING-LIVE local_109425cd: NovahPrime #14 draft, CI pending; wake it to merge on green. Deploy to live novah serve is an owner step.
- Archived DONE: INFRA-MEASURE, PRIME, FLAGS, ATLAS-ACT 2/2, DATA-REFRESH 1/1.

## Other desks
- NODE RAILWAY-SET-A 2/2 local_1137441b (Opus): orbit #30 first, hub #699 last (q200 go).
- NODE WIP-CAP 2/2 local_eafd9b01: merging unowned green drafts (q207 cap 25).
- NODE CI-STARVATION local_5bc2f56b: building heavy-job lock (q205 A).
- MONEY 2/2 local_4e1440cc (#727), and #14/#13 inherited desks: see router-014.md.

## Open owner cards
q208 server, q209 budget-kit PRs, q210 vault prod read, q211 comms, q212-q216 flags. Next free id q217.

## Held
CLOUD-LOCAL 198-204, WAY-POSITIVE-CONTROL 206, Q201-SYNC-STATUS-POST 208: open as CPU frees (q202 A), under the WIP cap of 25.

## Archive owed
- ROUTER #14 local_34998bfa: gate holds (handoff 4c189f7 pushed, worktree clean), but its chip children (the ATLAS desks) are nested under it and an idle one would be archived with it. Archive it once those children are done. #13 local_21748811: only when none of its desks is unfinished.
- Gotcha: chips are owner-placed, so detach_session refuses.
