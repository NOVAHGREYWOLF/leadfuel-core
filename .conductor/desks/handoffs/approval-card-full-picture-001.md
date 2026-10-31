# APPROVAL-CARD-FULL-PICTURE 001 · DOORS · one-interface part · 32

Session `local_dd13dce4-3022-4b90-9651-762613550527`. No router opened it: the owner asked in its own
chat on 2026-10-16 (a question about the approvals card) and on 2026-10-31 ("talk to conductor").

## Done
- Diagnosed the approvals card: hub `app.py` `_approvals_card` (main `d45910fa`, near line 33379)
  renders kind, recipient name, date, summary and body only. It shows no subject, from-account,
  address, attachments or linked items. The mail.send executors already pass `params["attachments"]`.
- Briefed CONDUCTOR 057 (`local_acc328d8-44cd-4180-afc4-4b56434d067f`), message
  `42503ac7-c142-4e84-be11-e64134bbee81`. It filed APPROVAL-CARD-FULL-PICTURE and
  COMMS-OUTREACH-ONE-BUNDLE in Conductor desk doc `desks/doors` v58: both open, neither queued.
  I verified that by reading v58 myself.
- No code, no PR. The only branch is this note's.

## State (verified 2026-10-31, about 12:20 PT)
- Pending actions `1a9d393864584ac9824af2363eda06a5` and `4d01ca19c6194524a3e7aae50bfb18af`
  (linkedin.dm, created 2026-10-05) are still pending.
- The two companion emails are still Outlook drafts outside the queue, still with no attachment.
  Re-checked today through the connector.
- One of the two cards is further superseded by later owner email. The detail went privately to
  the conductor, not into this public note.

## Next
- Nothing for a successor until the owner queues a task. The desk that takes
  APPROVAL-CARD-FULL-PICTURE uses the two pending actions above as test fixtures. The full brief
  is the conductor message above: run `list_events` on this session for its text.

## Owed
- Owner: decide the two live cards on `/approvals/review`. That is his click, not a desk's.

## Gotchas
- The main leadfuel-core checkout is shared and changes branch under you (it was on
  `claude/zealous-heisenberg-tlqil3` when this session started and on `claude/conductor-050` by
  10-31). Use a worktree.
- The Outlook connector drops in and out, so date every finding taken from it.
- CONDUCTOR 057 said this session was past its cap. `get_usage` said 208k of 300k. Checked, not
  taken on trust.
