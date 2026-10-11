# DOORS-EARNED-ACCESS 001 (DOORS · earned access, local_04d666b8)

## Done
- Owner idea (2026-10-11, this desk's chat): the brain earns permissions as it learns, the way
  a game player or Claude Code does. Wrote it up as a proposal, kept outside the repo:
  `F:/Claude Sessions/handoff/earned-access-proposal.md` (what exists, the gap, levels per skill,
  4-step build order, what was verified and what was not).
- Sent to ROUTER #35 (local_19f89eda): delivered, and it replied. It posted card **q358** on
  the Router desk (A yes standing grant / B no / C talk first; default A); I read q358 back,
  version 1. It asked CONDUCTOR 024 (local_5b6f1dd2) to file **DOORS~EARNED-ACCESS** unqueued:
  delivered to that session, read not confirmed.

## State
- No code, no hub branch, no PR. Nothing is queued.
- Verified by me on hub origin/main 54825f60: `autonomy.py` moves the asking, not the acting;
  `action_tier.py` makes outward red and is off unless `AUTONOMY_TIER_ENABLED`;
  `what_can_you_do` `locked` means plan; an edit overwrites the draft in
  `app.py` `approvals_review_act` and in the Slack edit path.
- Not checked: production env, real approval counts, whether the conductor filed the task.

## Next
Nothing until the owner answers q358 and queues DOORS~EARNED-ACCESS. Then the router opens one
DOORS desk for step 1, which is the same under A or B: record whether each approval was sent
untouched, edited (and how much) or rejected, and keep the original draft beside the sent
version.

## Owed / not delivered
- Owner: q358.
- Conductor: confirm DOORS~EARNED-ACCESS is filed (read not confirmed).

## Gotchas
- The board doc `router/current` is about 60 KB: read it with `out_dir`.
- This is the main leadfuel-core checkout on a branch shared with other desks' handoffs. Commit
  only your own file.
