# ATLAS-DOORS 2/2 handoff (DOORS)

Session: DOORS · ATLAS-DOORS 2/2. Router: ROUTER #20. Source: Router desk q275 = A.
Written 2026-10-05 ~13:55 UTC. Re-read state before acting; these lines go stale.

## hub #752 (atlas-doors)
- Head f4b82c7: main 46d1a47 merged in, plus the test fix (tests/test_hub_post_door.py reads source through tests._source.source_of; the guard was not touched).
- CI on f4b82c7: pytest pass, hosted gates pass, hosted pip-audit pass. CLEAN. Marked ready.
- Handed to MERGE-TRAIN 2/2 (local_3bac496f) ~11:50 UTC. Delivered, but not merged as of 13:54 UTC.
- Train holds .locks/ci-novahub (claimed 08:46Z, last updated 09:19Z). The session is idle and hub has had no merges since 04:40Z.
- Worktree: novahub/.claude/worktrees/atlas-doors-2 (detached; pushed as HEAD:atlas-doors).

## hub #754 (doors/send-email-carries-reply-to-idempotency)
- Fix committed LOCALLY ONLY: 5b1f2aa in novahub/.claude/worktrees/doors-resend-2 (detached on 83a3d0b).
  - api_send_application binds account_email via _subject_or_refuse.
  - Two tests: an odyssey caller naming the account without the acting header gets 403; with the header, the acting person binds.
  - Local run: tests/test_send_email_carries_reply_to_and_key.py and tests/test_subject_binding.py, 24 passed.
- Next: after #752 lands, rebase 5b1f2aa onto main, push HEAD:doors/send-email-carries-reply-to-idempotency, wait for green and CLEAN, then send to MERGE-TRAIN.
- Counterpart: odyssey #52 head 2b2df82 sends X-Acting-Email (ARM-SENDS-DOORS 2/2 owns it; I verified line 145 myself).
</content>
</invoke>
