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

## UPDATE ~02:1xZ UTC 10-13: THE ETG.AI MAIL ROOT CAUSE (SENSORS desk local_786396c4, STATUS NEEDS-NOVAH)
Desk says: envelope.uid_from_legacy cuts the event uid to 96 chars ("mailbox:" + Graph id, ids are 152 chars and share their first ~141); event_uid is VARCHAR(96); so after the first etg.ai message every later one is deduped by the door as already held, while the cursor still advances. Gmail ids are short, so Gmail flows. VERIFIED BY ME on hub origin/main: envelope.py lines 101 and 103 return key[:96] and f"{src}:{key}"[:96]; models.py event_uid String(96). NOT verified by me: the 152-char shared-prefix claim (desk read it from the live Inbox), that prod shows it, the timing (door switch B3.3 a74ad5bc, 2026-08-14 06:39Z, desk's git read).
OPEN, owner's calls, in order:
1. Q10 (read-only, counts and lengths, file book_inbox_q10.py in that desk's scratchpad): needs his go. The desk asks; default yes. Read the script first as with Q8/Q9, then give him the PowerShell command with the real path, or run it on his explicit "do it".
2. Who owns envelope.py and intake.py (door/ingestion owner, not the SENSORS rail files)? Check F:\Claude Sessions\SESSION_MAP.md, name the owner, route the fix there: hash any key over 96 chars, leave short keys untouched. Fix applies to every rail, not just mail.
3. Recovery is a PRODUCTION WRITE (re-pull Aug 14 to now, or reset the cursor; check backfill_uids did not stamp truncated uids): a card for the owner, his yes only.
4. Other long-id rails may be hit the same way: a count, separate from this.
