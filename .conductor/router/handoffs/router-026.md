# Router handoff #026 -> #027 (2026-10-07 ~08:3xZ, at the 300k guard)

ROUTER #26 is local_0185d288-2c99-49e5-8c15-5412aecd8eaf. Ids only. Re-read live state before acting.
Board router/current (A4uS9xn1emqupohdE4DUfV) v233+. Router desk LzmP6QcxmYh9TdvMMjS883. Conductor desk MKAx49RAskZ3cV7f2EkDMF.
PRIVATE detail: F:/Claude Sessions/handoff/ROUTER-26-inbox.md. Read it first.

## Done by #26
Claimed v220. Two MERGE-TRAIN 5/5 sessions were racing: the stamp holder local_0a111962 kept the train; the duplicate stood down and was archived. Train landed hub #782 (0d43b03c28); #786 is out on #783's guard (SURFACE CC-ROUTE-MOVE 2/2 agent fixing). Archived through the gate: MERGE-TRAIN 4/4, PHOTO-PRICE-SHEET, ARM-SENDS-DOORS 2/2, the duplicate 5/5. Agents finished: ARM-SENDS-DOORS 3/3 (signal #33), CC-PHONE-READY 2/2 (#784 tests), HERO-COUNCIL 1/2 (hub #787 docs). Rulings: BOOK-TIME-LOCAL lands via the train on q298=A; LAB video rename visible-only. Cards q329-q341 posted.

## Open owner cards
q208, q294, q315-q318, q329-q341. next_free_card q342.

## Chips waiting
task_ffa4ddc2 NODE MERGE-TRAIN 6/6 (Opus xhigh on click; 5/5 at cap stays open until 6/6 holds the stamp).

## Agents of #26 still running (they die if #26 is archived)
SURFACE CC-ROUTE-MOVE 2/2 (Opus, hub #786 branch). MONEY PHOTO-REVENUE-EXCLUDE 1/1 (Sonnet, hub money/photo-revenue-exclude). #26 stays open and copies their reports into router/current agent_reports_26. Do NOT archive #26 before both are there (or 3h pass).

## Next
1. On the owner's clicks: route q329 (RUNNER-WAIT 3/3), q334 (PHOTO-CLIENT-STORE 2/2), q335 (merge signal #33 or hold), q336-q339 (HERO-COUNCIL 2/2, Opus), q340-q341 (LAB video desk local_a2905088).
2. When 6/6 reports it holds the stamp: archive 5/5 through the gate. When CC-ROUTE-MOVE 2/2 reports: ask VAULT HUB-ANON local_6eb9de30 to review the guard change, then tell 6/6 #786 is ready.
3. Hold #24 and #25 (side sessions without PRs; see board hold_archive_24/25).

## Gotchas
- The board is written by other sessions mid-turn: pin every write and diff on mismatch (out_dir works in #26).
- FETCH_HEAD in the shared novahub checkout is overwritten by other sessions; use the commit sha.
- A chip desk takes the router's model: set the routed model, then stop + continue.
- 9 of 10 sends used since the owner last typed.
