# Router handoff #041 -> #042 · one-interface (2026-10-13 ~00:45Z UTC, ~300k)

ROUTER #41 is local_c17aaac6-253f-4e7a-b175-be8d6b56e131. Ids only. Board router/current (A4uS9xn1emqupohdE4DUfV; ALWAYS out_dir; v460 at last read) and doc router/log41 (e01-e08). Router desk LzmP6QcxmYh9TdvMMjS883. Conductor desk MKAx49RAskZ3cV7f2EkDMF. Conductor 030 = local_78314164-79ea-488f-a8b0-9ffb6fb74d40 (live; 029 archived). ROUTER #40 owed questions = local_c4f9af1e (live; the owner clicks cards there).

## Done (verified by me with gh / ls-remote / get_session)
- #39 and VAULT part 3 (local_0510ec9a) archived through the gate. hub#815 MERGED 23:57:36Z, 6a30af20 = hub main, deploy 7026639320 success 00:00:49Z.
- Cards read by me and acted on: q375 amended B, q376/q377/q378/q380 all A (clicks in #40's chat 00:08Z), q367 closed, q374 A, q368 B, q369 C. Posted q378, q380, q381.
- hub main push run 38324828013 on 6a30af20 was RED (3 flaky tests); sent to conductor 030 as a candidate task, queued not read.

## Running — #41 STAYS OPEN until the agent reports (it reports to #41 only)
- Agent a17a26a46817df85e (VAULT one-interface part 6, Opus): finishes VAULT~APPROVAL-LINK-HARDENING from hub branch vault/approval-link-hardening (ed5e9a58, notes APPROVAL-LINK-HARDENING-001/002). Ends NEEDS-NOVAH, DRAFT PR, never merges. Owner sets APPROVAL_LINK_SECRET in Railway FIRST, then merge.
- Session SURFACE one-interface part 13 (local_4a06afda): owner's q369 talk-through.
- CHIP waiting for a click: task_4129fa97 INTELLIGENCE one-interface part 1 (Opus, q376; needs his typed go in its chat for a counts-only production read).

## Next
1. Claim (title ROUTER #42 · one-interface, router/current). Re-read live state.
2. q381 (merge hub#816, default A): on his A land it inside the ci-novahub hold (merge main in, pytest job success on that SHA, main unmoved, squash); he then deletes CONNECTOR_APPROVE_ENABLED in Railway. Verified: #816 draft CLEAN, head e18881dd, pytest success; refusals unchanged is the desk's word.
3. When part 6 reports: verify its PR with gh; card for the secret name and the spend links (per-ask link unsigned; digest approve-all signed with SECRET_KEY).
4. Then archive #41 through the gate (it has the agent's report; handoff pushed).

## Gotchas
Card numbers collide with #40 (read the page; next free q382). router/current writes collide (pin if_version). The Bash cwd drifts after cd. Sends used about 8 of 10; the owner has not typed in #41's chat. PRs 816 and part 6 both edit .railway/railway.ts.
