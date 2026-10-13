# Router handoff #044 -> #046 · owed questions, note 001 (2026-10-13 ~02:5xZ UTC; guard said ~301k)

ROUTER #44 = local_f3879197-5288-4c9d-a46d-1ae6f1cb2484 (Fable). Ids only. State doc: board router/owed44 (artifact A4uS9xn1emqupohdE4DUfV; read with out_dir). Router desk LzmP6QcxmYh9TdvMMjS883. Conductor desk MKAx49RAskZ3cV7f2EkDMF. Predecessor #43 local_849c57ad ARCHIVED by me. Live: ROUTER #45 one-interface local_c9518c71 (router numbers are global, so the successor here is #46); CONDUCTOR 032 local_8c82c09f said it is rotating: address the board as for_conductor_033 keys.

## Done
- Claimed, #43 archived. q382 = A: Q10 ran read-only, hypothesis confirmed, counts on the card. q148 closed done (all seven PRs merged and checkSuites live, seven read-only plans by me). q246: owner cleared Odyssey Cron and novahub-cron-15min himself (new deployments building 02:09Z, verified); novahub-cron-daily on HOLD.
- Found: a hub `railway config plan` would delete six live NovaHub variables and shows cron-daily live `0 12 * * *` vs file `50 * * * *` (hub#789 never applied). Filed NODE HUB-RAILWAY-TS-DRIFT; conductor confirmed filed.
- Posted q386 (Unipile) and q392-q396 (conductor 032's five). Owner answered in chat: q383 A, q384 B, q385 B; written on the cards, relayed to #45 (queued). Filed INFRA-DOOR candidate (owner's words) and the ATLAS section-6 gaps; conductor filed T22 and T30 tasks.

## State (re-read; do not trust these lines)
Branch claude/router-44, this note is the last commit. Open cards of mine: q246 (later, cron-daily held), q386, q392-q396. #45's: q387-q391. hub#818 draft CLEAN (#45's). Railway dashboard shows a subscription PAST DUE banner; owner told.

## Next
The owner is walking the open cards one by one in my chat and was at card 5 = q386 (Unipile). Continue: explain q386 (why, what not), take his letter, then q392..q396 in order; write each answer on the card (answer, answered_via, relayed_by) and relay to the asker's router or the conductor. Then read the two cron build outcomes (`railway deployment list --service <name> --json --limit 1`) and note them on q246.

## Owed / not delivered
Three sends to #45 and one to conductor 032 were QUEUED, not confirmed read. Owner decisions: q246 cron-daily (after the hub apply), q386, q392-q396, the Railway bill.

## Gotchas
router/current moves every minute (three routers write): re-pin on mismatch; never write session_id. Query n >= last before posting a card (#45 took q383-q385 and q387-q391 under me). The harness classifier refuses dashboard clicks in Chrome (Modify Shared Resources): the owner clicks himself. Chrome tab 450498491 is open on Railway. Use `date -u` for time labels.
