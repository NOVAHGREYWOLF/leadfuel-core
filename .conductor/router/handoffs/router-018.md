# Router handoff #018 -> #019 (2026-10-05 ~01:45 UTC, ROTATING)

ROUTER #18 is local_55805a7f-0523-4375-9741-5244a0ee29ec (Opus), at the 300k cap. Ids only. Re-read live state before acting.
Board router/current (A4uS9xn1emqupohdE4DUfV) v87+ carries the detail. Router desk LzmP6QcxmYh9TdvMMjS883, Conductor desk MKAx49RAskZ3cV7f2EkDMF, Merge desk 745Gwx8qyNNTkhA7SSg6Bo, Sessions desk 4kc5BBHaEb9gLzjMGe7R8A. Conductor 011 local_495986b8. No start_session: desks are chips. Owner: "keep going, fully auto".

## Done (gh verified by #18)
leadfuel-core #25 #26; hub #755 #759 #763 #764 #745 #717 #715 #706 #693 #699 #742 #744 #760; novahub-mcp #43 #44; 9 WIP-CAP kits. ICP 26 created (desk read-back). Archived: #17, #16, CI-STARVATION, PART-SCHEMA, PUSH-AUDIT, CI-OVERFLOW, WIP-CAP, CAMPAIGN13, ORPHAN-REVIEW, PRICE-SHEET, SESSIONS-DESK-PAGE, ICP-STORE, STORE-CATALOG, ICP-UNMATCHED.

## Live desks
APPROVAL-CONFIRM-HARDEN local_d5ed3ca3 (slot ruling: skip offline tickets >24h); HUB738-PLACES-FIX local_189795a4 (then open SUITE PLACES-GATE-LAND); AI-STORE-RETIRED-KEYS local_465ce636 (BLOCKED on q258, hub #766 in train); AI-STORE-ERROR-HYGIENE local_c436d656 DONE (#44 merged; archive when idle); MERGE-TRAIN local_ed6ea561; REPORTS-VISUAL-REBUILD local_b9254a83; MERGE-DESK-PAGE local_aeeca517 (waits q249); RAILWAY-SET-A local_1137441b (waits q246 + DOORS signal #13/#28); ORPHAN-FIELDY-ASK-FIX and STORE-CHECKOUT started from chips, ids not read yet. Chip waiting: HUB727-LAND task_c38e78b7.

## Next
Route desk reports. As slots free: SURFACE STORE-FRONT (after checkout), ATLAS-OPS-BRIDGE (design), SURFACE /goal/atlas (after #736). Pass STORE-CATALOG flags to conductor (Radeon sizes as CPU-ONLY; tier ladder restated in 3 places).

## Owner items
q246, q249, q257 (owner steps), q258 (ICP rename; D = name 'Hub'), q237, q208. Next free card q259.

## Gotchas
- SendMessage needs the FULL local_ id; short ids fail.
- 10-send cap resets only when the owner types.
- set_session_model on chip desks is refused by the classifier; chips open on Opus.
- Chip desks I opened are MY side sessions: archiving me sweeps finished idle ones. Archive done desks first.
- ATLAS-B1 local_70fae0d7 past 300k: archive through the gate once its handoff is pushed. ROUTER #14 waits on INVENTORY-ARMS local_197a5c5c / MCP-MAP local_bf111dae (running since 10-03, possibly hung).
