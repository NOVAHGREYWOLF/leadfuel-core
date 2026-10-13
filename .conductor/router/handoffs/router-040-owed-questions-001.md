# Router handoff #040 -> #043 · owed questions, note 001 (2026-10-13 ~01:50Z UTC, at ~320k)

ROUTER #40 = local_c4f9af1e-1c6f-4609-a730-1fe2da39d57a. Ids only. State doc: board router/owed40 (artifact A4uS9xn1emqupohdE4DUfV, always use out_dir; read the update_* keys in order). Router desk page LzmP6QcxmYh9TdvMMjS883. Predecessor #38 handoff 002 is on this branch; read it only for history.

## THE OWNER'S LAST ASK (not done): "the router desk has 26 open questions still showing up. I want an empty list."
Diagnosis, verified by me from the page code and a fresh dump: the page hides a card only if status == "withdrawn" (26 cards already are). A decision card is closed once `answer` is set. A STEP card is closed only when `answer == "done"`, so every step card with answer A/B/not_yet/etc. still counts open. 26 open = 25 step cards (13 old ones have no `id` field; use the document key) + q381 (new, #41's, retire the old connector flag; hub#816 touches the deploy file; not read by me).
Plan: walk the 26 with the owner by clicks. Per card verify first: finished -> `answer: "done"` only on the owner's word or a verified fact; obsolete -> status "withdrawn" + withdrawn_reason; truly open -> ask. NEVER bulk-close, never overwrite his recorded answer without saying so.

## Done and recorded this session (cards carry the detail)
q375 amended B (soft-retire words at 90 days, Law 4; tier_join_review on the card: separate DOORS job, retire words not row, also pending_action.params, 90-day clock for undecided rows). q367 closed. q376, q377, q378, q380 all A, sent to #41. q379 naming answered C. Archive: local_6b8ff456 archived; local_e22bd45b was already; local_7ddb1c08 not found.
Priority from owner: "work on the command fully, anything to do with this; then everything with the reporting."

## Owed / undelivered (re-read, then land)
- Live conductor is local_78314164 (029 local_aac451eb is ARCHIVED). My sends to it were UNDELIVERED twice ("no sign of starting within 20s"). Owed to it: the priority above; file Unipile payment task UNQUEUED (owner said make it a task); pointer to q375 tier_join_review; check 029's four filed tasks (retention desks/doors v26, backup desks/node v65, key-rotate desks/surface v42, Atlas row desks/field v10). Do not change its permission mode; tell the owner.
- SENSORS desk local_786396c4: etg.ai mail. I ran Q8 and Q9 myself on the owner's explicit "do it" (desks still may not). Q8: stored etg.ai mail ends 2026-08-14, zero rows since; mail_index etg.ai never had a received row; connection active, cursor current, last_error None. Cursor-ahead theory REFUTED. It owes a code read and a Q10 script (not run), then a STATUS to me. Owner must say go before Q10 runs.
- Q9: approval_decision exists in prod, 0 rows, no alembic revision table in prod.
- SESSION_MAP rows: owner said a desk wrote them and a check passed; I found nothing. Closed on his word, unverified.

## Gotchas
Bash tool and PowerShell differ: give the owner PowerShell paths. SendMessage by full local_ id. ArtifactData reads need out_dir.
Predecessor #40 stays open until you are live; archive it through the gate (branch claude/router-40 and claude/router-43 pushed, nothing unpushed).
