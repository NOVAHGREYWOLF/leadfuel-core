# Wave 3 partition: the unbuilt memory / brain / connector / vault / sync / search / consent work

Read-only mapper for ROUTER #109, 2026-10-31 (Pacific). True source: owner via CONDUCTOR 056, 2026-10-31,
"burn code ... all the code ... to the memory". Nothing here is built or queued by this file. Public repo:
ids, titles and status only.

**Refs read (read-only):** hub `origin/main` d45910fa (2026-10-30); hub branches `tiered-memory-phase1`
39fa463, `brain-fix-t3` e41e3c5, `arms/hub-todo-token` e9744a9, `arms/hub-todo-add` 8131ed5; MCP
`origin/main` ac534a8, `arms/mcp-todo-tool` 2d43aa1, `arms/mcp-fieldy-day-report` (same head); app
`one-app/int9` ab53b88 and `one-app/hl1..hl7`. **`one-app/hl8` and `one-app/hl9` do not exist as branches**
(HL-9/HL-10 work is on the hub `arms/*` branches).
**Docs read:** Tiered Memory Developer Specification (7zLfapyDzCTC1ubk8H4U3v, whole); hub
`docs/specs/TIERED_MEMORY_SPEC_V2.md` on `tiered-memory-phase1` (whole; it REPLACES the v1 build plan:
no second store, features on the existing hub tables); novahub-brain fix brief (9QBQq1j1TNAxs76nQooTjE,
whole) and handoffs BRAIN-FIX-001..004; Master Plan (KsFUsB4R89dkVe5WMQdYeb: Part V roadmap and build
spec read, Parts I-IV skimmed by heading only); Own Your Data (3oWoo4krvs9duNLa39ijgs: pitch only, every
build section is an empty placeholder); Fix Ledger todos (50 docs); home-node 31, 37, 38, 39 (status,
matrix and task sections), handoffs ONE-HL1..HL7, ONE-W3A/B/D, ONE-INT-9.
**Not done:** no test run, no hub call, no production read. "BUILT" below means code seen on the named
ref, not proven working.

## 1. Item table

| # | Item | Source | Built? (ref: evidence) | Repo | Lane |
|---|---|---|---|---|---|
| 1 | Retrieval degrades to keyword search, reports its state | fix brief Task 1 | BUILT, main: `retrieval_status.py`, `ask.py` lexical_fallback (#1032); MCP #48 | hub+MCP | ARMS (done) |
| 2 | `fieldy_window`, `fieldy_get`, time-ranged `recent_memory` | fix brief Task 2 | BUILT, main: `fieldy_read.py` (#1033); MCP `ac534a8` (#49) | hub+MCP | ARMS (done) |
| 3 | Fieldy API pull: retry 401/403 with backoff, 90 s timeout, arrival-path log | fix brief Task 3 item 1 | UNBUILT, main: `api_connectors.py:31` `_HTTP_TIMEOUT = 30` | hub | FIELD |
| 4 | Digest `window_covered`, `conversation_count_covered`, day_part/cursor | fix brief Task 3 item 4 | UNBUILT, main: no match for either field | hub (+MCP tool param) | FIELD (+ARMS reports desk for MCP) |
| 5 | Digest extraction "returned nothing": retrieval or model call? | fix brief Task 3 item 3 | UNKNOWN (static trace owed) | hub | FIELD |
| 6 | Daily Fieldy brief silent since 10-04: restart + backfill | fix brief Task 3 item 2 | UNBUILT; needs prod logs: owner's go, not in wave 3 | hub | FIELD |
| 7 | Brain-fix 8 acceptance tests from the Claude MCP client | fix brief "Acceptance" | UNKNOWN (owed to owner, BRAIN-FIX-004) | - | owner |
| 8 | v1 SQLite tiered store (MemoryItem, warm store, migrator) | spec v1 phase 1 | BUILT on `tiered-memory-phase1` only (`tiered_memory/*`); SUPERSEDED by spec v2 §13: lift redaction, fixture, report format; never merge | hub | INTELLIGENCE |
| 9 | Phase 0 brain count | spec v2 §11 | BUILT on `tiered-memory-phase1` (`docs/specs/TIERED_MEMORY_PHASE0.md`), not on main; prompt-site list still owed | hub | INTELLIGENCE |
| 10 | Columns heat/used/presented/embedding_model/confirmation; tables `memory_pack`, `memory_job` | spec v2 §4 | UNBUILT, main: zero matches | hub | INTELLIGENCE |
| 11 | Context packs (budgeted, cite `[t:id]`, ids-only record) | spec v2 §5, v1 alg 4 | UNBUILT, main: zero matches | hub | INTELLIGENCE |
| 12 | Route policy local/claude, `MEMORY_ROUTE_ENFORCE`, job queue, Claude leg through spend+egress | spec v2 §6 | UNBUILT, main: zero matches | hub | INTELLIGENCE+DOORS |
| 13 | Node relay contract `node-relay/1` | DOORS doc | DOCS ONLY on main (`docs/NODE_RELAY_CONTRACT.md`, #860); no code. **Conflict: it says no long-poll; spec v2 §6 says long-poll** | hub | DOORS |
| 14 | Feedback, nightly heat, ranking meaning+keyword+heat | spec v2 phase 3 | UNBUILT | hub | INTELLIGENCE |
| 15 | Prefetch from arm signals | spec v2 phase 4 | UNBUILT; deferred by the spec until phase 3 has a baseline | hub | INTELLIGENCE+ARMS |
| 16 | Forget an item or subject everywhere, ordered tombstones | spec v2 §7, §12.5 | UNBUILT (main has account-wide purge only: `data_rights.purge_everywhere`) | hub | PRIVACY |
| 17 | Forget reaches this PC's seed copy | spec v2 §7 finding | UNBUILT; PRIVACY decision owed | app | NODE |
| 18 | Other arms (reach, signal, orbit, Echo) on packs; "what the brain is using" page | spec v2 phase 6 | UNBUILT; after phases 1-3 | hub+arms | each arm + SURFACE |
| 19 | HNSW ANN index on the three vector columns | spec v2 §2.6 | Migration BUILT on main (`migrations/versions/0002_vector_ann_index.py`, 2026-08-10); live state UNKNOWN (phase 0 found none, so likely never applied; not re-checked) | hub | INTELLIGENCE |
| 20 | Archive / summarise cold rows | spec v2 §5 | UNBUILT by design until a written trigger | hub | INTELLIGENCE |
| 21 | Export/import a whole brain; hosted/local identical | spec v1 cap 9-10 | UNBUILT; spec v2 §8 makes it the later local-node product | hub+app | later |
| 22 | Embedding switch Voyage to mxbai | spec v2 §9, q363=C | UNBUILT on purpose ("C for now") | hub | owner |
| 23 | Crossover: local system writes, synced twin | spec v2 §12, doc 18 | PARTIAL: app `lfdesk/sync/*` (identity, lease, tombstones, peers, shipper) BUILT on int9 for `history.db`; `StoreSink` only, no HTTPS sink, no hub receiver, no caller outside `lfdesk/sync` | app+hub | NODE (crossover task filed, unqueued) |
| 24 | Local brain search over the hub tables | doc 37 Brain | BUILT on int9: `lfdesk/brain/*` (search, tiers, status, stdlib pg) | app | NODE |
| 25 | Hub brain hits on the Sources card | doc 38 GAP-31 | BUILT on hl2, merged in int9 (`searchgate.brain_source_row`, `ui/sources.js`) | app | NODE |
| 26 | RAG caller (document answers) | doc 38 GAP-31, 39 ST8 | BUILT on int9 (w3e merge 82bb2c3: `rag/caller.py`, `ragdocsgate.py`) | app | NODE |
| 27 | Past chats as a model read tool | doc 38 GAP-33 | BUILT on int9 (`lfdesk/tools/pastchats.py`, `wiring.py:759`) | app | NODE |
| 28 | Memory topics + sensitive-topics switch; incognito | doc 38 GAP-30, GAP-23 | BUILT (code) on int9: `lfdesk/memory/topics.py`, `memorygate.py`, `ui/hubmemory.js`; working UNKNOWN | app | NODE |
| 29 | End-to-end proof of memory, projects, artifacts, routines | doc 38 GAP-28, doc 37 | UNBUILT (doc 37: "working UNKNOWN"; no e2e test found) | app | NODE |
| 30 | Decompress archive tools: sources, remove source, chunk preview, compact, stats, OCR opt-in | doc 31 chunk E2 (D6, D7, D9, D14, D16, D20-D23) | UNBUILT on int9: no `get_archive_chunk`; `remove_source`/`compact` only in vendored `memstore/store.py` | app | NODE |
| 31 | Obsidian-like Markdown vault (links, graph) | doc 37 Brain, doc 39 ST10 | NOT STARTED (int9: zero hits). App `lfdesk/vault` is the KeePassXC password bridge, a different thing | app | NODE (owner choice first) |
| 32 | Hub-backed Projects view; first-run Core link; connector rows | HL6, HL1, HL4 | BUILT, merged in int9 | app | NODE (done) |
| 33 | Live brain proof runner | HL7 | BUILT, merged in int9 (command line only); 3 owner questions open in ONE-HL7 | app | NODE |
| 34 | To-dos from the connector (N10) | Fix Ledger n10-todo | BUILT ON BRANCHES, unmerged: hub `arms/hub-todo-token`, `arms/hub-todo-add`; MCP `arms/mcp-todo-tool`; app int9 `modes.py` pre-registration | hub+MCP+app | ARMS / NODE |
| 35 | Node worker that answers local memory jobs | spec v2 §6 local leg | UNBUILT (int9: no match) | app | NODE |
| 36 | Per-node credential for the job protocol | spec v2 §12.4 (VAULT~NODE-CREDENTIAL-DESIGN) | UNKNOWN / UNBUILT (hub main: no match) | hub+app | VAULT |
| 37 | Confirmed-facts guard works on single words (false contradictions) | Fix Ledger n13 | UNBUILT; owner decision pending on the ledger | hub | INTELLIGENCE |
| 38 | Invented citations removed but the claim stays unmarked | Fix Ledger n18 | UNBUILT; owner decision pending; packs (item 11) are the structural fix | hub | INTELLIGENCE |
| 39 | Market consent: opt-ins per category, disclosure record, deals | Master Plan Part V Market spoke | UNBUILT, main: no `opt_ins`, no `market_deal`. Roadmap places it in phase 3 (2027) | hub | not this wave |
| 40 | Quest progression (levels, rewards, earn-only credits) | Master Plan Quest spoke | BUILT on main (`quest.py`, migration 0013, `/api/quest/*` in `app.py:3777-3861`) | hub | INTELLIGENCE (done) |
| 41 | Own Your Data build sections | 3oWoo4krvs9duNLa39ijgs | NOTHING TO BUILD: every section is an unfilled placeholder | - | - |

## 2. Desk briefs (W3-01 .. W3-12)

**Rules for every brief (LAW 9 limits):** local branch only, never pushed unless the router says so, no
PR merge; migrations are WRITTEN and tested against a throwaway local database, NEVER applied to any
shared or production database; nothing leaves the PC (no hub call, no vendor call, no model download;
tests use fakes); no production read; no `.env` or credential read; the novahub checkout is shared, so
take a worktree. Narrow tests on touched files plus `SKIP_TESTS=1 sh scripts/gates.sh` in the hub;
no local full pytest. A file listed under one brief is touched by no other brief.

**Hot spots and their single owner:** hub `app.py` -> W3-02; hub `models.py`, `data_places.py`,
`docs/THE_PLACES.md` and the one new migration -> W3-01; hub `ask.py` -> W3-02; hub `brain.py` -> W3-04;
MCP `tools/__init__.py` (one line) -> W3-06; app `assistant/gate_list.py`, `assistant/pagebridge.py`,
`assistant/tests/mockbridge.js`, `build/NovahOS.spec`, `lfdesk/tools/modes.py`, `assistant/wiring.py`,
`assistant/ui/index.html`, `assistant/ui/panes.js` -> W3-12.
**Held by other desks, given to no brief:** MCP `tools/fieldy.py`, `mesh_client.py`, `tools/guide.py`,
`tests/test_fieldy_day_report.py` (ARMS reports part 1, `arms/mcp-fieldy-day-report`); MCP
`tools/todo.py`, `.github/workflows/test.yml` (HL-8). Hub `source_watchdog.py` (WATCH) is not touched.

### W3-01 Hub: memory columns, pack/job/tombstone tables, packs (spec v2 phase 1)
- **Repo:** novahub. **Model:** Opus (migration, data model). **Lane:** INTELLIGENCE.
- **Owns:** new `memory_pack.py`; new `memory_redact.py` (lifted from `tiered_memory/` on
  `tiered-memory-phase1`); new `migrations/versions/00NN_memory_tiering.py` (next free number at build
  time, one head); `models.py` (append columns and three models only); `data_places.py`;
  `docs/THE_PLACES.md`; new `docs/specs/TIERED_MEMORY_SPEC_V2.md` and `TIERED_MEMORY_PHASE0.md` (copied
  from the phase 1 branch, plus the owed prompt-site list); new `tests/test_memory_pack.py`,
  `tests/test_memory_migration.py`, `tests/fixtures/planted_answer/*` (lifted fixture).
- **Goal:** spec v2 §4 columns on `user_memory`, `knowledge`, `document`; tables `memory_pack`,
  `memory_job` and an ordered `memory_tombstone` (stable ref: table, row id or `event_uid`, seq; never
  content), all declared as places; `memory_pack.build(account, feature, task, budget, required_ids)`
  per §5 (15% reserve, rank 0.6 cosine + 0.4 heat, full-text rank when no vector, no `deleted_at`
  rows, summary de-dup, `[t:id]` format, ids-only row, secrets stripped).
- **Done:** migration up/down on a scratch Postgres+pgvector; places gate green; pack rows hold no
  content (test asserts); p95 pack build measured on a phase-0-shaped synthetic copy and written in the
  PR; ULIDs for new ids; PR says how each §12 crossover rule was kept.
- **Tests:** the new test files; gates.sh static.
- **Stack on:** `arms/hub-todo-add` (8131ed5); read `tiered-memory-phase1` (39fa463) for the lift.

### W3-02 Hub: route policy, job queue, `ask` on packs, hub registration (spec v2 phase 2)
- **Repo:** novahub. **Model:** Opus (auth, egress, Law 9). **Lane:** INTELLIGENCE + DOORS.
- **Owns:** new `memory_route.py`; new `memory_jobs_api.py` (Blueprint: node take/fetch/answer);
  `ask.py`; `app.py` (exactly: its own blueprint line, the W3-04 and W3-05 blueprint lines, and the
  `/api/fieldy/digest` pass-through of `day_part`/`cursor` for W3-03, app.py ~31706); new
  `tests/test_memory_route.py`, `tests/test_memory_jobs_api.py`, `tests/test_ask_packs.py`.
- **Goal:** per-account policy in `AccountSetting` (`reader_route_default`, `claude_features`,
  `claude_cap_usd_day`, `embed_route`); `local` unless named; no fallback either way (node off, job
  expired, local error -> visible refusal); Claude leg only via `llm_client.call_claude_with_cost` +
  `egress.send` with ids/counts; `MEMORY_ROUTE_ENFORCE` defaults off; `ask` builds packs on its current
  route. Reconcile the job protocol with `docs/NODE_RELAY_CONTRACT.md` (`node-relay/1`, short requests,
  no long-poll) and say which wins in the PR.
- **Done:** `ask` answers byte-identical with and without packs on the fixture; with enforcement on in
  tests, node off = refusal, never Claude; a mutation that removes the refusal turns a test red; job
  rows live 24 h; node auth uses a per-node credential seam (fake in tests; no shared token in `.env`).
- **Stack on:** W3-01; at the end merge W3-03, W3-04, W3-05 branches locally and add their lines.

### W3-03 Hub: Fieldy pipeline health (brain-fix Task 3, code half)
- **Repo:** novahub. **Model:** Sonnet. **Lane:** FIELD (flag WATCH; do not edit `source_watchdog.py`).
- **Owns:** `api_connectors.py` (`_fieldy_fetch` retry/backoff with ceiling, 90 s Fieldy timeout,
  arrival-path log line); `fieldy_digest.py` (`conversation_count_covered`, `window_covered`,
  `day_part`/`cursor` params with defaults so it works before W3-02's app.py hunk); `fieldy_report.py`
  (only if the static trace of item 3 finds a defect); new `tests/test_fieldy_fetch_retry.py`,
  `tests/test_fieldy_digest_window.py`.
- **Goal:** items 1, 3 (static trace, written finding), 4 of Task 3. Item 2 (brief restart, backfill)
  is excluded: it needs production logs and the owner's go.
- **Done:** 401/403 retried then surfaced, never silent; whole day reachable by cursor in tests; trace
  result written in the PR. The MCP `fieldy_digest` param exposure is NOT here: it lives in
  `tools/fieldy.py`, held by ARMS reports part 1; hand it there.
- **Stack on:** `brain-fix-t3` (e41e3c5, carries BRAIN-FIX-004) rebased onto `arms/hub-todo-add`.

### W3-04 Hub: feedback, heat, ranking (spec v2 phase 3)
- **Repo:** novahub. **Model:** Sonnet. **Lane:** INTELLIGENCE.
- **Owns:** new `memory_heat.py` (citation parse, feedback, 24 h unused rule, nightly set-based SQL
  recompute); new `memory_feedback_api.py` (Blueprint, registered by W3-02); new
  `scripts/memory_heat_nightly.py` (not scheduled); `brain.py` (ranking hook only: meaning + keyword +
  heat, one embedding model per search); new `tests/test_memory_heat.py`, `tests/test_brain_heat_rank.py`.
- **Done:** on the planted-answer fixture, cited rows rise and uncited fall over a replayed week;
  `rejected` rows score 0 and are never packed; no scheduler entry added.
- **Stack on:** W3-01. Prefetch (phase 4) is NOT in wave 3: the spec forbids it before this baseline.

### W3-05 Hub: forget an item or a subject everywhere (spec v2 phase 5, hub half)
- **Repo:** novahub. **Model:** Opus (irreversible deletes, privacy). **Lane:** PRIVACY.
- **Owns:** new `memory_forget.py`; new `memory_forget_api.py` (Blueprint, registered by W3-02;
  person-only, no mesh token may forget); new `tests/test_memory_forget.py`.
- **Goal:** hard-delete rows (vector goes with the row); delete derived `knowledge` by provenance and
  report the untraced count (never zero by default); strip ids from `memory_pack`; drop queued
  `memory_job`s; write ordered tombstones into W3-01's table; status `pending` until complete. Separate
  verb from `deleted_at`. Does not change `data_rights.py` (PRIVACY's enumerated list): if the place
  list needs a new entry, list it in the PR instead.
- **Done:** a forgotten subject leaves zero hits in rows, vectors, derived knowledge, pack refs and
  jobs in tests; mutation removing the knowledge step turns a test red.
- **Stack on:** W3-01.

### W3-06 MCP: forget and "what the brain is using" tools
- **Repo:** novahub-mcp. **Model:** Opus (a destructive tool). **Lane:** ARMS.
- **Owns:** new `tools/brain_memory.py` (`memory_forget` that QUEUES a pending action by default,
  `brain_using` read-only: pack counts and refs, ids only); new `tests/test_brain_memory_tools.py`;
  ONE registration line in `tools/__init__.py` (the only wave-3 edit there).
- **Must not touch:** `mesh_client.py` (use its existing request helper; if a new helper is needed,
  name the conflict spot "new function beside fieldy_get" and ask ARMS reports part 1),
  `tools/guide.py` (listing in `what_can_you_do` is handed to its holder), `tools/fieldy.py`,
  `tools/todo.py`, `.github/workflows/test.yml`.
- **Done:** tool descriptions short and literal; identity from the session token only; tests against
  a fake hub. **Stack on:** `arms/mcp-todo-tool` (2d43aa1); needs W3-01/W3-05 route shapes (fake until
  then).

### W3-07 App: node memory-job worker (spec v2 §6 local leg)
- **Repo:** F:\Leadfuel home-node. **Model:** Opus (auth, outbound connection). **Lane:** NODE.
- **Owns:** new `app/lfdesk/memjobs/__init__.py`, `client.py`, `worker.py`,
  `app/lfdesk/memjobs/tests/test_memjobs.py`; new `app/assistant/memjobsgate.py` (start/stop/status,
  OFF by default) and `app/assistant/tests/test_memjobsgate.py`.
- **Goal:** take a job, fetch the pack once, answer with the local Ollama model, post the answer; node
  id from `lfdesk/sync/identity.py` (import only, no edit); per-node credential seam; refusal on
  timeout, never a cloud call.
- **Done:** tests against an in-process fake hub only; a mutation that adds a cloud fallback turns a
  test red. **Stack on:** `one-app/int9` (ab53b88); contract from W3-02.

### W3-08 App: forgets reach this PC's seed copy
- **Repo:** F:\Leadfuel home-node. **Model:** Opus (deletes). **Lane:** NODE (PRIVACY decides).
- **Owns:** new `app/lfdesk/brain/forget_apply.py`, new `app/lfdesk/brain/tests/test_forget_apply.py`.
- **Goal:** replay ordered tombstones (W3-05) against the local seed copy through the narrow writer in
  `lfdesk/brain/pg.py` (import only, no edit), idempotent, watermark kept beside the node identity.
- **Done:** tests on a scratch local Postgres only; never run against the real seed until the owner
  answers question 1. **Stack on:** `one-app/int9`; W3-05 tombstone shape.

### W3-09 App: Markdown vault of the brain (Obsidian-like), local only
- **Repo:** F:\Leadfuel home-node. **Model:** Sonnet. **Lane:** NODE.
- **Owns:** new `app/lfdesk/notes/__init__.py`, `export.py`, `links.py`, `app/lfdesk/notes/tests/*`;
  new `app/assistant/notesgate.py`, `app/assistant/tests/test_notesgate.py`; new
  `app/assistant/ui/notes.js`, `notes.css`.
- **Goal:** owner's own Markdown folder (one note per item, backlinks, private tier kept, no AGPL code
  imported); read from `lfdesk/brain` and history; writes only inside the chosen folder.
- **Done:** jail test, no network, round-trip of links. **Depends:** owner question 5 (default: own
  vault). **Stack on:** `one-app/int9`.

### W3-10 App: Decompress archive tools and pane (doc 31 chunks E/E2)
- **Repo:** F:\Leadfuel home-node. **Model:** Opus (deletes, subprocess spawning). **Lane:** NODE.
- **Owns:** `app/lfdesk/tools/memstore_tools.py`, `app/assistant/archivegate.py`,
  `app/assistant/ui/archive.js` and their existing tests (`lfdesk/tools/tests/test_memstore_tools.py`,
  `assistant/tests/test_archivegate.py` if present, else new).
- **Goal:** D6 sources table, D7 remove source (manual in every mode), D9 `get_archive_chunk`, D14
  structured stats, D16 compact, D23 tool status probe, D20 OCR/transcribe as an explicit per-ingest
  opt-in, one worker (D22 stays 1). Vendored `memstore/` is LAB's and is not edited.
- **Done:** no subprocess without the opt-in (test); jail checks. **Depends:** owner question 6.
  **Stack on:** `one-app/int9`.

### W3-11 App: end-to-end proof of memory, projects, artifacts, routines (GAP-28)
- **Repo:** F:\Leadfuel home-node. **Model:** Sonnet. **Lane:** NODE.
- **Owns:** new `app/assistant/tests/test_e2e_knowledge_proof.py` only.
- **Goal:** drive memory (propose, approve, topics, incognito), projects, artifacts and routines
  through `realbridge.py` (hl5, import only) against fakes; each feature reads `working` or names the
  step that fails. A check that cannot see a feature must say `unknown`, not pass.
- **Done:** a missing gate makes the test fail (checked by removing one in a scratch copy).
  **Stack on:** `one-app/int9`.

### W3-12 App: registration and bundling for W3-07, W3-09, W3-10 (last)
- **Repo:** F:\Leadfuel home-node. **Model:** Opus (`modes.py` is a guardrail file). **Lane:** NODE.
- **Owns:** `app/assistant/gate_list.py`, `app/assistant/pagebridge.py`,
  `app/assistant/tests/mockbridge.js`, `build/NovahOS.spec`, `app/lfdesk/tools/modes.py`,
  `app/assistant/wiring.py`, `app/assistant/ui/index.html`, `app/assistant/ui/panes.js`.
- **Goal:** one line each to register `memjobsgate`, `notesgate`, new archive bridge methods; bundle
  them (the `test_every_gate_list_module_is_bundled` guard must stay green); classify W3-06's
  `memory_forget` in `modes.HUB_WRITES` (asks in every mode) and `brain_using` in
  `HUB_REACHES_OUT`.
- **Done:** `gate_list`, spec and modes tests green; selftest notes it cannot see a missing gate.
  **Stack on:** W3-07, W3-09, W3-10 branches merged locally onto `one-app/int9`.

## 3. Owner questions (defaults in brackets)

1. This PC holds a copy of the brain: should forgets be applied to it, or the copy dropped? [apply]
2. When you ask Claude to forget something, delete at once or queue it for your tap? [queue]
3. Node worker sign-in: wait for the per-node credential design, or build against a fake now? [fake now, off]
4. The relay contract says short requests; the memory spec says long-poll. Which? [short requests]
5. Notes vault: our own Markdown folder, or Basic Memory (AGPL)? [our own]
6. Archive: OCR and transcription only when you tick it per ingest, one worker? [yes]
7. Restart the silent daily Fieldy brief and backfill from Oct 5 (needs server logs)? [later, in that desk]
8. Build the market consent screens (opt-ins, disclosures) now, or on the 2027 roadmap? [roadmap]
9. Run the Voyage-vs-mxbai quality test before revisiting embeddings? [not now]
10. Which features may Claude read your memory for? [ask when W3-02 is green]
