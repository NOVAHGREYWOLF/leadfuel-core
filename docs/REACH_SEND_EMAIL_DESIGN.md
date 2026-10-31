# REACH-SEND-EMAIL-DESIGN: world alerts as feed cards that queue and never send

**Task:** CC-56 (one-interface, part 115, lane ARMS), which is the Conductor task
`REACH-SEND-EMAIL-DESIGN`. **Source:** owner card q808, answered A on 2026-10-30 (evening, Pacific):
"yes, design only", relayed by ROUTER #110.
**Status:** DESIGN ONLY. Nothing in this document is built, switched on or sent. It adds no code
that sends, calls no vendor, and nothing leaves the machine.
**Measured against:** hub `main` at `d45910fa`, read on 2026-10-31.

## 0. The answer in one paragraph

A world alert becomes a **card in the account's own Action Feed on `/command`**: a row in the
existing pending-action queue, of a new kind `world.alert`, carrying no recipient and no send
control. The card can be read, opened on the world page, dismissed, or left to lapse. **Approving
it is impossible**: the feed draws no approve button for the kind, and the server's execute path
refuses the kind even if an approve is forged. That is the default, and it needs no gate, because
nothing leaves. The reach arm's `send_email` verb is designed here as well, but it is built only
after the owner says yes on a card to a **send path** (section 5). Each send path is its own Law 9
card. Until one is answered yes, no alert is emailed, posted, pushed or fanned out to Slack.

## 1. What exists today (verified on hub main `d45910fa`)

| Fact | Where | How I know |
|---|---|---|
| `world_alerts.py` picks alertable brief items (quakes, weather and fires only; severity rank 2 or more; "near an approved place") and writes each as an order to `<reach key>.send_email`, the key derived from the registry | `world_alerts.alertable`, `order`, `channel` | read |
| `dispatch()` raises `AlertPathNotWired` when alerts are on and no transport is supplied. It never falls through to another mailer | `world_alerts.dispatch` | read |
| **Nothing in production calls `dispatch`.** The only importer outside tests is `command_world_intel.alerts_state`, which reads `enabled()` and `channel()` to draw the switch in words | `git grep` over `*.py`, tests excluded | ran |
| **The hub's action catalogue has no `send_email` verb for reach.** It now holds 54 keys (the DOORS review counted 51 on 2026-10-07; the count grew but the conclusion holds). The reach ones are `add_leads`, `build_sequence`, `create_campaign`, `delete_campaign`, `get_campaign`, `list_campaigns` and `start_campaign` | `app._APP_ACTION_CATALOG` | ran (listed every key) |
| The order sets `transactional: True` | `world_alerts.order` | read |
| A transactional send skips the outreach chokepoint, the suppression list and the 200-an-hour per-account rate limit | `send_service._resend_send` | read |
| **Every hub email now crosses `egress.send(destination="email")`** (ATLAS-DOORS, owner card q219 A), with a per-account daily recipient ceiling `EGRESS_EMAIL_DAILY_MAX` that is default-deny (unset means no email leaves) | `send_service.send_email`, `egress.DOORS["email"]` | read |
| The Action Feed on `/command` lists `pending_action` rows for the session's own account. Deciding in place (owner card q360 A) runs the Act page's own server path, `_execute_pending_action` / `_reject_pending_action`, behind session-only, CSRF and compare-and-set guards | `command_panels`, `tests/test_command_feed_decide.py` | read |
| `_enqueue_pending_action` refuses a second row with the same `(account, idempotency_key)`: the queue is already a local dedupe ledger | `app._enqueue_pending_action` | read |
| **`_enqueue_pending_action` defaults to `notify=True`, which fans the row out to a Slack card.** That fan-out is itself a path off the machine | same, its docstring | read (fan-out code not traced) |
| **The approve path for channel `email` does not pass `kind` or `idempotency_key` to `send_service.send_email`.** An alert approved from the feed today would lose its dedupe key and be logged as `marketing` | `app._execute_pending_action`, `channel == "email"` branch | read (new finding, not in the DOORS review) |

### 1a. The four constraints from the DOORS review, re-checked

The review is `one-interface-doors-review-s5-s6.md`, section 2, in the sessions handoff folder.

- **G1, one recipient for every account.** Still true. `recipient()` is the env var `WORLD_ALERTS_TO`
  and `dispatch` takes no account.
- **G2, `transactional: True` skips the send door's brakes.** Still true.
- **G3, no per-send approval and no metering.** **Partly stale.** Metering and the egress ledger now
  apply to any transport that calls `send_service.send_email`, because that function is the door's
  front (q219 A). What is still missing: a per-send approval, and a ceiling of the alerts' own. Today
  alert mail would share the account's general email ceiling with every other send.
- **G4, dedupe rests on the vendor's 24-hour idempotency key.** Still true, and worse than the
  review said: the feed's approve path drops the key (table above). The key also hashes `title`
  and `ts`, so a revised quake gets a new key and alerts again.

## 2. Principles the design keeps

1. **A queue, not a send.** An alert's first and default form is a card. Sending is a later,
   separate act with its own approval.
2. **No recipient until a send path exists.** A card carries no address. G1 cannot happen when no
   address is written.
3. **One door.** Any alert mail goes through `send_service.send_email` and therefore `egress.send`.
   No second mailer, no direct vendor call, no fallback (`world_alerts`' own rule: a vendor path is
   a decision, not a fallback).
4. **Unknown is never quiet.** If the producer cannot read the brief, it writes nothing and says
   `unknown` in `alerts_state`. It never writes "no alerts".
5. **No silent fan-out.** Slack, phone push and email are each a send path, each a card.
6. **Trust cannot creep.** Dismissing alert cards must never teach the skill ledger that the owner
   approves alert mail, and a standing grant can never cover the kind.

## 3. Stage 0, the default: alert cards on `/command` (no gate, nothing leaves)

### 3.1 The producer

A new function beside `dispatch`, for example `world_alerts.queue(account, items)`:

- Takes **one account** and that account's own brief items. It runs `alertable(items)` unchanged:
  the thresholds stay as they are (precision is the product).
- For each pick it enqueues one pending-action row:
  - `kind = "world.alert"`, `channel = None`, `action = None`
  - `source_app` = the world lane's name (`world_layers.LANE_NAME`), so the feed's arm field says
    who proposed it
  - `params` = `summary`, `severity_word`, `layer`, `where` (the brief's `how`), `when`, `source`
    (the link through the same `http(s)`-only rule `order` already uses), `attribution`.
    **No `to`, no subject and no body for a mailer.**
  - `idempotency_key` = the stable key in 3.4
  - `expires_at` = the event's own expiry where the feed gives one (weather alerts), otherwise
    event time plus 24 hours. The feed already draws "lapses in".
  - `notify = False`. **Pinned by a test.** The default `True` would fan the row out to Slack.
- `dispatch()` stays as it is and keeps raising. `queue()` never imports a mailer; the existing test
  that pins `world_alerts`' import list keeps holding.

### 3.2 When the producer runs

**Default: inside the existing world sweep job, server side, after new rows land, for each account
that has at least one approved place.** Never on a GET: the S5 review already flagged a GET that
changes state, and `/command` reads must stay read-only. Writing a row to the hub's own database is
inward and needs no gate.

The alternative is a card derived at read time and never stored, the way the World tab's quest is
in #896. It writes nothing, but it cannot be dismissed, cannot lapse and cannot dedupe, so it does
not meet "queue". It is offered as an option in owner question Q2.

### 3.3 The card, and what it can and cannot do

- **Drawn** with the feed's existing fields: what (`summary` and severity word), where, when, waited
  and lapses, the arm (world), the evidence (`where` already says "N km from <place>"), the price
  (**free: nothing leaves**), and the source credit the data licence needs.
- **Two controls only:** "open on the world page" (a same-origin link) and "dismiss".
- **No approve and no approve-with-edits.** The feed read marks the card `decide: notice` rather than
  `decide: open`, and `decide.js` draws approve only for `open`.
- **The server refuses too.** `_execute_pending_action` gets a branch for `world.alert` beside the
  other special kinds (`signup.invite` and the rest), ahead of every channel branch. It returns
  `{ok: False, error: "notice_only"}`, sends nothing and leaves the row pending. So a forged approve
  POST with a good ref and a good CSRF token still sends nothing.
- **Dismiss** is the existing reject path: it records the decision, sends nothing and closes the row.
- **No trust creep.** The kind is excluded from `skill_ledger` trust steps and from
  `standing_grant`, so dismissals and lapses do not move the world lane toward autonomy. The feed's
  trust field says `not_measured` for the kind, with a fixed reason.
- **Platform view** (the bare admin, or an owner account in PLATFORM scope): counts only, as the feed
  already does for every row.
- **HUD words.** `command_world_intel.alerts_state` changes from "an alert is an order to the email
  door" to: `cards`, "alerts arrive as cards on this screen; nothing is emailed". Its existing states
  `off`, `blocked` and `unknown` stay.

### 3.4 Dedupe without a vendor (closes G4 for stage 0)

- `key = "world-alert:" + sha256(account key | layer | upstream event id)`, with **no title and no
  timestamp**, so a revision of the same event maps to the same key.
- The queue's own uniqueness on `(account, idempotency_key)` is the local ledger. A duplicate is
  caught and dropped.
- **A revision that raises severity updates the open card in place** (new words, its age kept). A
  revision at the same or lower severity is dropped.
- **Unverified, owed by the build desk:** whether every world row carries the upstream event id.
  `world_feeds` uses the feed's own id where there is one and falls back to a key made of title and
  time. For fallback rows a revision cannot be matched, and the design says so (`dedupe: weak` in the
  card's evidence) rather than pretending.

### 3.5 What changes and what does not, at stage 0

Changes (proposed, not made): `world_alerts.py` (new `queue`, new key), the world sweep job (one call
to `queue`), `app._execute_pending_action` (one `notice_only` branch), `command_panels` (the
`notice` decide word, kind excluded from trust and price `free`), `static/command/decide.js` (no
approve for `notice`), `command_world_intel.alerts_state` (words).
Does not change: the thresholds, `dispatch`, the catalogue, `send_service`, `egress`, any env var.
**The env var `WORLD_ALERTS_ENABLED` keeps meaning "may alerts be emailed", which stays off.**
Stage 0 is governed by `WORLD_INTELLIGENCE_PAGE` (the owner's existing flip for the whole world
screen), because cards are part of that screen.
Ownership of each file is checked against the session map by the router before a build desk opens.
This document claims none of them.

## 4. The reach `send_email` verb (designed now, built only after a send-path card says yes)

- **Key:** `<reach key>.send_email`, derived from the registry (`arms.key_for`). The retired spelling
  is never typed.
- **Class:** outward and irreversible, so it lands in `_IRREVERSIBLE_APP_ACTIONS` through
  `_ACTION_CLASS`. Price: metered (the mail vendor bills per email).
- **Carrier, default:** in process, through `send_service.send_email`, so through `egress.send`.
  `calling_app` = the reach key, `kind = "world_alert"`, `transactional = False`, the idempotency key
  passed through, and an unsubscribe link to the world page's alert switch. Not an HTTP hop to the
  reach service and not a second mailer. This matches DOORS-REACH-SEND, which moves reach's own sends
  through the same hub door. The alternative carrier (HTTP to reach, which then posts to the hub's
  door) is owner question Q8.
- **G2 closed:** `transactional = False` puts alert mail back under the suppression list and the rate
  limit. `kind = "world_alert"` gives it provenance at the outreach chokepoint (`kind:world_alert`),
  so turning the chokepoint on does not silence it, and it is not campaign outreach.
- **G1 closed:** the recipient is resolved on the server at send time from the account that owns the
  row: the account's own sign-in address. It is never read from `params`, a query string or an env
  var. `WORLD_ALERTS_TO` is retired. Version 1 serves the owner's account only (Q6).
- **G3 closed:** each send is either one card's approve (send path SP1) or a standing approval the
  owner states on a card (SP2), and is counted against an alert ceiling of its own,
  `WORLD_ALERTS_DAILY_MAX` per account, **default-deny: unset means zero**, on top of the general
  `EGRESS_EMAIL_DAILY_MAX`. It is counted from the egress ledger's own rows, never from memory.
- **G4 closed for mail:** the approve path's `email` branch is fixed to pass `kind` and
  `idempotency_key` through. Without that fix the vendor key is dropped, as it is today.
- **Card to mail:** an approved send path turns a `world.alert` card into a send-capable one by
  enqueuing a separate row (`channel = "email"`, action = the verb) linked to the card. The
  `notice_only` row itself never becomes sendable, so the stage-0 guarantee stays testable on its own.

## 5. Send paths: each one is a Law 9 card, and none is taken

| Path | What leaves, and to whom | Cost | What would turn it on | Default |
|---|---|---|---|---|
| **SP1, per-card send** | one plain-text email to the account's own address, when the person clicks "email me this" on one alert card | metered, per email | the verb in section 4 built, `WORLD_ALERTS_ENABLED=1`, `WORLD_ALERTS_DAILY_MAX` set | **No** |
| **SP2, standing approval** | the same email, sent with no click for every alert card above the thresholds, up to the daily ceiling | metered | SP1, plus the owner saying on a card that the switch is a standing approval | **No** |
| **SP3, Slack fan-out** | a Slack card per alert (`notify=True`) | free, but it transmits | one flag on the producer | **No** |
| **SP4, other accounts** | SP1 or SP2 for a customer account, to that account's own address, with that account's own consent recorded | metered, on that account | per-account consent built, plus the owner's yes | **No** |
| **SP5, daily digest** | one email a day listing that day's alert cards, in place of per-alert mail | metered, at most one a day | SP1's verb, plus a digest job | **No** |

A free path (SP3) is on this list for the same reason as a paid one: it transmits just as far
(Law 9). Phone push is not listed because no push channel exists; it would be a new card when one
does.

## 6. The four constraints, closed

| | At stage 0 (cards) | When a send path is on |
|---|---|---|
| G1 one recipient | no recipient exists | the account's own address, resolved on the server; owner's account only in v1 |
| G2 transactional | no mail | `transactional = False`, `kind = world_alert` |
| G3 approval and metering | nothing leaves, so price is free | per-card approve or a stated standing approval; alert ceiling default-deny; egress ledger row per send |
| G4 dedupe | local key on the queue, revision-stable | the same key passed through to the door and the vendor |

## 7. Guards the build must carry (each written so it fails if the thing it guards is absent)

1. The producer opens no socket and makes no DNS lookup (network refused in the test, with a
   positive control showing the refusal is live).
2. `notify=False` on every alert row (a mutant with `True` fails).
3. An approve POST on a `world.alert` row, with a valid ref and CSRF token, sends nothing, returns
   `notice_only`, and the row stays pending (the send function is stubbed and counted at 0).
4. No alert row's `params` holds a `to`, an address shape, or a body for a mailer.
5. Two revisions of one upstream event give one card, and a severity rise updates it in place.
6. With `WORLD_ALERTS_DAILY_MAX` unset, the verb sends zero (refuses a colour: never fix it to green).
7. The platform view shows counts and no control, for alert cards as for every other row.
8. `alerts_state` says `unknown`, not `cards` or `off`, when the switch cannot be read.

## 8. Verified, and taken on trust

**Verified by me on hub `main` `d45910fa`, by reading code or running read-only `git` commands:**
the `world_alerts.py` behaviour and its `transactional` and key lines; that nothing outside tests
calls `dispatch`; the catalogue's 54 keys with no reach `send_email`; `send_service.send_email`
crossing `egress.send` with a default-deny ceiling; that transactional skips the chokepoint,
suppression and rate limit; the outreach provenance rule accepting a named kind; the queue's
`(account, idempotency_key)` uniqueness and `notify=True` default; the approve path's `email` branch
dropping `kind` and `idempotency_key`; `world_feeds` falling back to a title-and-time key when a feed
gives no id.

**Taken on trust:** the DOORS review's PROVED runs (not re-run); that `notify=True` ends in Slack
(read in the docstring, fan-out code not traced); the task row and its four constraints as written
by conductor 020; PR #896 note 8 as its author wrote it. Nothing was run against production, and no
test was run (this is a document).

## 9. Open decisions for the owner (each with a default)

Each is meant to become one card on the Router desk page. Every card also carries option **X,
"None of these: something else"**.

- **Q1. What do world alerts do by default?**
  A) Cards on `/command` only, nothing emailed. B) Cards, plus per-card "email me this" (SP1).
  X) Something else. **Default: A** (the owner's own default on the task row).
- **Q2. Where are alert cards written?**
  A) By the world sweep job, server side, as queue rows that can be dismissed and lapse.
  B) Derived when the screen reads, never stored (no dismiss, no lapse, no dedupe). X) Something else.
  **Default: A** (it is the only one that queues).
- **Q3. Build the reach `send_email` verb now, held behind the switch?**
  A) Not yet: design only until a send path is approved. B) Build it, dormant and default-deny.
  X) Something else. **Default: A** (q808 said design only).
- **Q4. Is `WORLD_ALERTS_ENABLED` a standing approval for alert mail (SP2)?**
  A) No: every alert email needs its own click. B) Yes, within the daily ceiling. X) Something else.
  **Default: A**.
- **Q5. Daily ceiling for alert mail, per account (`WORLD_ALERTS_DAILY_MAX`)?**
  A) Unset, which means zero. B) 3 a day. C) 10 a day. X) Something else. **Default: A**
  (default-deny, like `EGRESS_EMAIL_DAILY_MAX`).
- **Q6. Who may receive alert mail once a path is on?**
  A) The owner's account only, at its own address. B) Any account, at its own address, after that
  account consents. X) Something else. **Default: A** (G1; customer consent is not built).
- **Q7. Fan alert cards out to Slack (SP3)?**
  A) No (`notify=False`). B) Yes. X) Something else. **Default: A** (Slack is a send path too).
- **Q8. How does the verb carry mail?**
  A) In process through the hub's send door, attributed to reach. B) An HTTP call to the reach
  service, which then posts to the hub's door. X) Something else. **Default: A** (one door, no extra
  hop, matches DOORS-REACH-SEND).
