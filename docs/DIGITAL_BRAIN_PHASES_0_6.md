# Digital brain, phases 0 to 6: what exists, what done means, the steps

Task K01 (queue item, lane BRAIN). Status: SCOPE, plus the code half of phase 0 as a draft PR. Written 2026-11-23 Pacific by a background desk agent for ROUTER #135.
Source brief: the owner's "NovaOS Digital Brain Build" handoff of 2026-11-18 (phases 0 to 6, ground rules, done tests). Step 1 audit: delivered 2026-11-18 by the INTELLIGENCE desk, summarised in memory note `project_digital_brain_build_audit`; its full report was in a session scratchpad (read here at `C:\Users\novah\AppData\Local\Temp\claude\dbcfc8230e7026ae\37eac687-e418-4382-99b7-aa9d189991d9\scratchpad\digital-brain-audit-report.md`, temporary).

## 1. Verified here, and taken on trust

Verified by me this session, by reading source (nothing executed, no production read):
- Hub `origin/main` c4f7a09a: `spend_approval`, `spend_gate`, `embed_gateway`, `retrieval_status`, `brain.local_embed_enabled`, `brain_events`, `planner_goal.propose_routes`, `_ACTION_CLASS`, `api_app_action`, `_HUB_LOCAL_APP_ACTIONS`.
- novahub-mcp `origin/main` 78a55d7: `tools/apps.py` gate, `tools/today.py`.
- No `episode_id`, `need_relevance`, `novelty` or `urgency` field exists in hub code (grep of non-test source).

Taken on trust (audit, 2026-11-18, hub read at 94e64d48): every live count (262,607 rows, 196,783 embedded, source breakdown), the per-source timestamp table, Lucid and goal planner behaviour, Railway service contents, cost estimates. Re-measure before relying on any of them.

## 2. Where the brief was wrong (from the audit, re-checked where marked)

1. Recall is down because `embed.query` has no standing approval and an emailed one lapses (default 24 h). Re-checked: `spend_approval.TTL_HOURS` defaults to 24, answers may be `1h`, `5h`, `24h` or `inf` (never expires), cap `MAX_TTL_HOURS` 43,800.
2. Reads queue because of the connector's verb prefix gate in novahub-mcp, not the hub catalog. Re-checked. "Reads run directly" is not safe as written: `prospect.find` is classed read and bills a vendor. See PR below.
3. `dedup_key` is identity, not time. No `episode_id`. Re-checked.
4. web_liveness (about 30,130 rows) has no embeddable text; honest coverage was 85.8 percent, not 75.8. Sensors do not all write UTC with a time (audit table).
5. The embedding ceiling `EMBED_DAILY_ITEMS` (1,000 per UTC day) is **shared by every embedding feature, recall queries included**. New finding, verified: `embed_gateway.items_today` sums egress rows by destination and account, and `permitted_now` refuses a query when `already + 1 > ceiling`. A phase 1 backfill that spends the whole ceiling makes recall refuse for the rest of that day.

## 3. Phase table

| Phase | What exists | Done means (owner's test) | Steps and owner | Blocked by |
|---|---|---|---|---|
| 0 Restore recall | `retrieval_status.py` (status ok/degraded/down/unknown, replays the door's rules without sending), lexical fallback, connector `search_brain` reports mode and `connection_status` shows retrieval state (hub #1032, connector #48, merged). Approval windows incl. `inf`. A local embedding leg exists but must match vector width (`VOYAGE_DIM`), so it implies a full re-embed. | Retrieval status healthy, mode semantic, a paraphrased `search_brain` query finds the right memory. | (a) OWNER: answer the pending `embed.query` approval email with `inf` or a long window, or set standing approval (b). (b) DOORS and owner: hub settings `LLM_AUTO_APPROVE_FEATURES` names `embed.query` and `LLM_DAILY_CAP_USD` is above zero; `NEVER_AUTO` holds only `self.dossier`. (c) Connector read gate: BUILT, draft PR below. (d) OWNER or desk with his go: the done test, two connector reads. | (a) or (b) |
| 1 Light up memory | `brain.py` backfill (cron `sync-all`, `EMBED_CORPUS`, newest first, skips location, setting, finance), embed at write time through `intake.accept`, `self.interest_catalog` (free price readout), `corpus_stats` (coverage only when `embedding` is true). | `corpus_stats` shows distilled at 100 percent and overall coverage 95 percent or more, not counting excluded sources. | 1. Owner decides: Voyage (about $0.29 to $2.94 for about 32,650 rows, text goes to Voyage AI, about 33 days at the ceiling) or local re-embed (no ceiling, no vendor, full re-embed of the store, see `docs/DEC2_EMBEDDING_COMPARISON.md`). 2. Exclude `web_liveness` (and other text-free kinds) from selection and the coverage count (queue tasks BRAIN/local_8a8b9ddc-3 and -4: add infra to the non-embeddable kinds, record skip reasons). 3. Reserve headroom for queries: cap the backfill below the shared ceiling. 4. Backfill order: distilled, spoke reports, self_report, fieldy, mailbox. 5. Embed at write time. Fieldy-origin rows stay out of any vendor embedding (queue U10 redline). | Phase 0; owner price and vendor decision |
| 2 Bind episodes | `event_ts` (indexed) and `created_at` on `user_memory`; read-time stitching only (`fieldy_report.stitch`, 240 s; `report_window.resolve`); free read `memory.recent`, `fieldy.window`. | Asking for a known past evening returns one coherent scene (place, transcript, health, calendar, mail). | 1. Owner-authorised read: `SHOW timezone` and one real Fieldy and one Overland timestamp string. 2. Fix zoneless writers (Apple daily, calendar all day, Gmail, QuickBooks dates, the door's silent zoneless to UTC). SENSORS, FIELD, COMMS own these. 3. Add `episode_id`, the binder (shorter window wins), dry run first with a status bar, backfill. 4. A free read action returning a whole episode. Stay detection first: only 4 `stay` rows existed (audit). | Timezone read |
| 3 Attention | Need roots and live weights (`first_principles.py`, `my_needs`). No salience fields. `fieldy_report._episode_salience` is a different, internal thing. | Top three command book items match the owner's own pick on 5 of 7 days. | 1. Add need relevance, novelty, urgency to the spoke report format. 2. Salience is the product, formula only. 3. Prime sorts the command book by salience, grouped under managers. 4. Owner supplies 7 days of his own picks as the test set. | None technical; INTELLIGENCE and ARMS files |
| 4 Working memory | Nothing built. The "Colibri spec" the brief names was not found: Colibri here is an inference engine on overlord. Likely source: queue item W16, tiered memory, a 10-12 spec. Unverified. | Questions about today hit the hot tier first. | 1. Locate the spec (W16) before any code. 2. Hot tier loads today's episodes, active goals, open approvals at each tick. 3. Route "today" questions to it first. | Phase 2 (episodes) |
| 5 Simulate futures | `planner_goal.propose_routes` returns up to 4 routes (`MAX_VECTORS`), behind `GOAL_ROUTES_ENABLED`, one paid step behind `GOAL_ROUTES_MODEL_ENABLED`; need roots; no ranking, no stored prediction. `record_outcome` and `refresh_plan_from_outcomes` exist (audit, agent reported). | Day plan shows two scored options; predictions checked against outcomes weekly. | 1. OWNER sets a spend cap per run and per day before any code. 2. Lucid drafts three plans per goal. 3. Project each against calendar, money, energy; score by need roots. 4. Store the prediction; close the loop weekly. | Owner cap; phase 3 scoring |
| 6 Event driven spokes | `brain_events.py`: append-only table, pull feed `GET /api/brain/events`, metadata only, off by default (`BRAIN_EVENTS`), four event types, design in `docs/BRAIN_EVENTS_DESIGN.md` (merged, PR 14). No call sites wired. Echo polls every 60 s by default (design doc). | A new Fieldy conversation shows in a spoke report within one minute. | 1. Add event types for new sensor signal (the four existing ones are brain changes) and wire publishers after the write commits. 2. Subscribing spokes poll the feed; the poll interval must be well under 60 s or the one-minute test cannot pass. 3. Keep the 15 minute cron as the safety sweep. 4. Pull, not push, keeps Law 9 clean; the brief says "the hub triggers the spoke", pull satisfies it only if the interval is short. | Phase 0 for report generation; `BRAIN_EVENTS` switched on (owner or DOORS) |

## 4. Order

0 first. Then, in parallel: 1 (needs the owner's vendor decision) and 2 (needs one read). 3 can start after 2 is designed. 4 needs 2. 5 needs 3 and the owner's cap. 6 can start after 0 and is independent of 1 to 5 except for the done test.

## 5. Phase 0 build

Draft PR https://github.com/NOVAHGREYWOLF/novahub-mcp/pull/54, branch `brain-p0-connector-reads`, head f8acbe4. Adds an exact-key second allowlist so a connector runs `self.interest_catalog`, `self.goals` and `lucid.today` directly. `prospect.find`, `self.recall`, `self.goal_mail` stay queued. Needs ARMS (owns `tools/apps.py`) and DOORS (Law 9 gate) review before merge. `lucid.today` is not free on a cold day; it is on the list only because `whats_on_today` already makes the same call.

Hub gap found, not fixed (hub file, not mine): `fieldy.window`, `fieldy.get` and `memory.recent` are classed read and advertised in the catalog but are missing from `_HUB_LOCAL_APP_ACTIONS`, so the generic app-action route cannot run them (read in source, not executed). The dedicated connector tools work.

## 6. Owner steps (exact)

1. Answer the pending `embed.query` approval email ("Search your corpus", sends the search words to Voyage AI) with an indefinite or long window. It must be his own tap. Scope: recall query embeddings only, never the corpus backfill, never Fieldy rows. Alternative: standing approval (hub settings `LLM_AUTO_APPROVE_FEATURES`, `LLM_DAILY_CAP_USD`), a production setting.
2. Phase 0 done test, once step 1 is in: call connector `connection_status` and read the retrieval state; then `search_brain` with a paraphrase of a known memory. Two reads of his live brain.
3. Phase 2: one read of the live database, `SHOW timezone`, plus one stored Fieldy and one stored Overland timestamp string.
4. Phase 1: Voyage or local, and yes or no on the price, after reading `self.interest_catalog`.
5. Phase 5: a spend cap per run and per day.

## 7. Not done (left for the next agent or the router)

- Part 16 additions to K01: name the evening routines with schedule and where the last good run shows (CONNECTIONS.md G21), and a one-brain test line (a question in the window answered from the brain in LOCAL and CLOUD mode, G34). Not researched.
- Mail 2 item 3: map the NovahBrain blueprint of 2026-08-13 against the brain as built, and cite the table from the phase steps. Not done.
- The estate RUNBOOK.md BRAIN section: generated by the NODE desk's script; link this file there. Not edited.
- A brain fix desk is not live: ARMS brain fix parts 6 and 7 last active 2026-11-11 (checked in the session list).
