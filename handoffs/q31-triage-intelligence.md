# Q31 triage, INTELLIGENCE read-only tasks (2026-10-02)

Source: owner answered Router cards Q31, Q18, Q40. Ids/titles/status only (public repo).
Verified myself = origin/main of novahub at 5556c6b3 (git fetch, git grep) and Railway CLI read-only
(service list, deployment commit, build/deploy logs; variable NAMES set/unset only, no values).
Not verified = anything needing prod DB rows, owner artifacts, or other desks' repos.

## DONE (with proof)
- G10: NovaHub, novahub-cron-15min, novahub-cron-daily all SUCCESS on commit 5556c6b3 = origin/main head; deploy logs show clean cron/sync runs. Other arm services run their own repos (not checked here).
- R12-F1: build logs of all three novahub-code services show tzfpy 2.1.0 installed (requirements.txt:95); deploy logs have no tzfpy warning. R12b (fail loud) also shipped, #671.
- J1: ANTHROPIC_ADMIN_KEY is SET on NovaHub (name+set only). The "2 min owner step" is done.
- A15: entitlement gate fix merged (#473, "centralized enforcer was return True"). Reconcile-before-flip ordering not re-verified.
- local_c562c518-1: egress panel merged (#621, #642).
- B5: decided Q18 = embed only, no vendor enrichment. Record as decided; the "no bulk reindex before B4 planned" stays as a rule.

## DOABLE NOW, but not done (needs prod DB read, see QUESTION 1)
- D9: scripts/corpus_composition.py --source meta --all exists on main; needs a prod DB read.
- R13-F3: count pending approvals per feature in prod, read-only SQL; same dependency.
- L4: settle corpus count (53,079 live vs 200,701); same read-only census script (scripts/corpus_census.py).

## NEEDS WRITE ACCESS
- local_d1c5a22e-4: app.py `finance_read` (around line 13531 on main) is still COUNT(*)>0 of qbo_snapshot rows, not recency. Change: also require newest snapshot younger than a freshness window; report "stale" otherwise. Owner of app.py: check SESSION_MAP before editing.
- A17 (local_8e471cfd-2): not confirmed shipped or not; rail-freshness work merged (comms/rail-freshness) but I did not see a consumer of the stale flag. Needs a wall read to confirm.
- Q40: SESSION_MAP.md is ROUTER's file and its checkout has others' uncommitted edits, so I did NOT edit it. Exact change: in the "THE CREDIT CHAIN HAS NO DESK" block replace `UNOWNED   move_credit.py   goal_credit.py` with `BOARDS   move_credit.py   goal_credit.py   (owner agreed, Q40, 2026-10-02)`. Router: name the boards desk session (none found by that name in the map). Note the Q40 text covers move_credit.py (local_d1c5a22e-3); goal_credit.py not stated, so confirm.

## NEEDS OWNER DECISION
1. Prod DB read: may a desk run read-only SELECT-only scripts (corpus_composition, corpus_census, pending-approvals count) against the prod DB, without printing rows? Options: A) yes, SELECT only; B) no, owner runs them. DEFAULT A.
2. E10 (delete brain entries 12503-12505, duplicates of fact 6261; no delete tool exists): delete? Options: A) yes, after a desk confirms they are exact duplicates; B) leave. DEFAULT A.
3. local_c562c518-8: delete two merged local branches in the shared novahub checkout? Options: A) yes (git branch -d only, merged ones); B) leave. DEFAULT A.
4. A18 (local_8e471cfd-5): mesh scope for POST /api/qbo/read (route exists, app.py ~8673). Options: A) finance-read scope only; B) any mesh member. DEFAULT A.
5. B3: embedding model (Dec-2 separate desk, skipped). Dec-1: owner answered 2026-08-23 (replica per node); execution of convergence is open, needs a build task, not a question.

## OWNER-ONLY ACTIONS (no decision, just yours)
- local_d1c5a22e-1: QuickBooks re-auth. local_d1c5a22e-2: revoke leaked key 0b7cf84b (VAULT has procedure).
- local_8e471cfd-6/-7/-8 (G1, F4, share Owner Actions artifact) and local_addebdbe-2 (15 unchecked items on the code-review page): live in artifacts I did not open; unverified.
- A2 (local_8e471cfd-4): needs the phrase the owner wants searched; I have none.
