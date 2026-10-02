# CENSUS-1 (INTELLIGENCE), read-only production counts, 2026-10-02

Authority: owner answered Router card Q55 "SELECT only, nothing printed except counts". Counts only below.
Method: Railway CLI, URL read inside one process only; session forced read-only (default_transaction_read_only=on,
asserted before any query); no rows or text printed; no writes, deploys or migrations. D9 was run through a
count-only wrapper because corpus_composition.py --all prints text previews of repeated rows.

DATABASE: NovaHub's DATABASE_URL is db `novahub` on the Postgres server. The `railway` db on the same server
(shared db) has a different schema (user_memory.deleted_at absent). Counts below are from `novahub`.

## L4 corpus (scripts/corpus_census.py logic)
live 252,737 / retired 132,822 / ever 385,559; 98.0% of live carry event_uid.
Neither 53,079 (stale, 2026-08-14) nor 200,701 matches today. Source of 200,701 not found: unverified.
Top sources live: import 164,404; web_liveness 29,784; webhook:fieldy 16,402; calendar 10,249; distilled 6,218; linkedin 5,866.

## D9 meta (composition)
live 102,053 / retired 63,054; reaction-shaped 19,972 (19.6% of live); unregistered kinds 0; uid collisions 0.
Live by kind: received 42,702; message 29,580; reaction 19,972; relation 6,024; post 2,546; event 677; comment 552.
Text repetition (distinct texts): reaction 1,993 of 19,972 (90.0% repeat); message 26,148 of 29,580 (11.6%); received 4.3%.

## R13-F3 pending approvals (spend_approval, choice IS NULL = unanswered = no)
330 rows total, 311 pending. By feature: guard.semantic 257 (1,020 items); enrich.document 4;
every other feature 1-2 each (self.deep.* x20 features, embed.* x5, frontier:* x5, gateway:odyssey-cron 2, knowledge.distill 1).
pending_action status=pending: master.route 4, app_action 2.
