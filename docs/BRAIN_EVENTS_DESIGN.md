# Brain change events: hub publishes, echo subscribes (design only)

Task D4-design 1/1. Status: PROPOSAL, nothing built. Owner answer: Router card Q50, "Yes, open a design task first".
Written by an INTELLIGENCE desk on Sonnet 5.5 (the router asked for Opus; this was not on it).

## 1. What was checked, and what was taken on trust

Read directly (hub `origin/main` 5556c6b, echo working tree on disk):
- `echo/app/echo_orders.py`: `refresh_twin` calls `brain.notify(..., event_key="echo.voice.refreshed")`.
- `echo/app/brain.py:255`: `notify()` posts to hub `POST /api/notify/event`.
- hub `app.py` `api_notify_event`: forwards to the account's **customer integrations** (Slack plus outbound webhook) via `notify_clients.dispatch_event`, behind a WARDEN `send_message` gate.
- hub `GET /api/orders`, `POST /api/orders/<id>/claim`, `order_ledger.py`: a pull rail, but orders are **projections of GoalPlan steps**, not a general event queue.
- hub brain write routes: `POST /api/model` (`put_model`), `POST /api/knowledge`, `POST /api/knowledge/distill`, `POST /api/memory`, plus `/api/import/<source>`.
- echo `spoke_worker.py`: a poll loop (default 60 s, dormant unless `SPOKE_WORKER_ENABLED` and a service token), a hub-call helper that never raises, and heartbeat.

Not verified (taken on trust from the D4 desk): that no other publisher or subscriber exists in other arms. Also not measured: write volume per account.

## 2. Finding that shapes the design

`brain.notify` is **not** a subscriber signal. It is the customer-facing Slack and webhook fan-out. So the echo "voice refreshed" announcement reaches the owner's Slack, and **no arm hears it**. There is no bus on the hub at all. Reusing `/api/notify/event` for arm-to-arm events would also route internal state changes into customer destinations. That is a Law 9 hazard, so it is rejected.

Orders are the wrong rail too. An order is a command with an owner and a four-status callback. A change event is a fact with many readers and no reply.

## 3. Events

Metadata only, never content. An event carries ids and kinds, so the feed is safe to log and holds nothing the scope wall would have to filter.

| event_type | fired by (hub write) | key fields |
|---|---|---|
| `model.changed` | `put_model` | `kind` (voice, identity, traits, scoped suffix kept), `version` |
| `knowledge.added` | `POST /api/knowledge`, distill | `kind`, `scope`, `count` |
| `memory.recorded` | `POST /api/memory` (opt-in kinds only) | `kind`, `type` |
| `corpus.imported` | import job completion | `source`, `count` |

Envelope: `{id (monotonic), account_email, event_type, ref {kind, scope, version}, source_app, created_at}`.

First consumer need is only `model.changed` where `kind` starts `voice`. Ship that one first and add the rest when a reader exists.

## 4. Who publishes and how (hub, local only)

One append-only table `brain_events` in the hub's own database, written by one helper `brain_events.publish(...)`. The helper is called **after** the write commits, inside a try/except, and never fails the write. A lost event is covered by the reconcile in section 6.

Subscribers do not register with the hub. Echo asks `GET /api/brain/events?since=<cursor>&types=model.changed&limit=100`, with the same mesh auth and subject binding as `/api/orders`. The cursor is the last event id echo has handled.

Why pull and not push:
- no new external service, no webhook URL to protect, no egress (Law 9 clean);
- echo already runs this exact loop and is dormant until switched on;
- a hub or echo restart loses nothing, because the table is the queue.

## 5. Who subscribes (echo)

A second handler in the existing `SpokeWorker` tick. On `model.changed` with kind `voice*` it invalidates its cached model and re-reads `get_model(kind='voice')`. It does not call `brain.notify`, and it must ignore events whose `source_app` is `echo`, so its own `refresh_twin` write does not trigger itself.

The cursor is stored in echo's own database, per account.

## 6. Delivery and failure

- At-least-once. Handlers are idempotent: re-reading a model twice is harmless.
- Ordering is per account by event id.
- Poll fails (hub down, timeout): keep the cursor and retry next tick. Per the standing rule, a failed poll reports **unknown**, not "no changes".
- Echo down for a long time: on start, if the cursor is older than the retention window, do one full re-read instead of replaying.
- Hub publish fails after a write: logged and counted. Echo also does a low-frequency version check on `get_model` (comparing `version`), which catches any missed event.
- Retention: 14 days, pruned by a hub cron (none verified to exist yet). Rows are small.
- Poison event: skip after N tries, advance the cursor, log the id.

## 7. Rollout in small PRs

1. **hub PR A** (migration, flag `BRAIN_EVENTS=0`): the `brain_events` table, the `publish` helper, tests. No call sites.
2. **hub PR B**: call from `put_model` only, behind the flag. Add `GET /api/brain/events`. Observe mode first: write events, nothing reads.
3. **echo PR C**: poll handler for `model.changed`, behind `ECHO_BRAIN_EVENTS=0`. Cursor storage, self-event filter, tests.
4. **hub PR D, later**: `knowledge.added`, `corpus.imported`, retention prune, a `/admin` row for lag (latest event id vs each arm's cursor).
5. Turn flags on one at a time. Flipping them is the owner's decision.

## 8. What it touches

Hub: new module `brain_events.py`, one new model plus migration in `models.py`, one new route, one-line calls in `put_model` and later knowledge and import paths. Echo: `echo_orders.py` or a new `brain_listener.py` plus a cursor table. No change to `leadfuel-core` (archived; this document is the only thing here).

## 9. Owners (from `F:\Claude Sessions\SESSION_MAP.md`; unconfirmed with the sessions themselves)

- hub brain and corpus write paths, the event feed itself: **INTELLIGENCE** (brain/corpus). `app.py` has no single owner and is split by capability block, so PR B needs a block claim.
- `spoke_worker.py` and dispatch contract, spoke conformance: **ARMS**.
- Scope or privacy of what an event may carry: **PRIVACY** should review section 3 (metadata only).
- CI files in either repo: **NODE**.
- echo application code has no single named desk. Recent echo PRs were INTELLIGENCE (reports) and DOORS. The router should name an owner before PR C.
- A new table is a migration; per the map, production migrations are the owner's call (Law 9 does not apply, nothing leaves the machine).

## 10. Law 9 flags (owner approval needed)

None of PRs A to D send data off this machine. Two things would, and are **out of scope** unless asked: a push webhook to a vendor, and any external broker (Redis, NATS, a hosted queue). Both are rejected here.

## 11. Open questions for the router

- Is hub and echo the full subscriber set, or should Lucid and signal (which source voice from echo) get the same feed? Pull works for them unchanged.
- Name the echo owner before PR C.
