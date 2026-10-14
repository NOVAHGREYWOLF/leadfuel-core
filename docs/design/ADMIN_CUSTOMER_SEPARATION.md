# The wall between the customer account and the admin

Task **VAULT~ADMIN-CUSTOMER-SEPARATION** (queued pick rank 307, owner card q461 = A, recorded by
CONDUCTOR 040). Project one-interface, lane VAULT, part 9. Written by a background desk of ROUTER #59.
**Design only: no product code, no production read, no secret, no setting changed.** PRIVACY reviews
this note before any build is filed. Closes the design half of point 12 of the /command checklist
(`docs/COMMAND_COMPLETION_PLAN.md`, section 3 point 12).

Code facts were read on 2026-10-14 from a read-only snapshot of hub `origin/main` at **1dae531b**
(`git archive`, nothing run, no database touched). Every claim about what a route reads today is marked:

- **VERIFIED**: I read the code; `file:line` given (hub repository, that commit).
- **NOT VERIFIED**: I did not read it, or reading the code cannot settle it (above all, anything about
  production). It is never read as done.

## 1. What the owner asked for

His ruling (ROUTER #38 chat, 2026-10-12, quoted on the Conductor desk task; spelling cleaned by #38):
"my ordinary account should see the whole estate because that is part of my life ... If I log in just
as admin it shows no customer setting but has admin control of the full application ... the admin
shouldn't have any rights to my information, only admin rights." Card q369 (Q2) added: "the platform
is mine so we should have a connector to it. I should be able to access it through my customer view".
The reading "estate = his own data plus a connector to the platform" was confirmed: q369 = B
(leadfuel-core commit d22ce8a, branch `claude/zealous-heisenberg-tlqil3`; I read the commit subject,
not the chat turn).

Three things, as ROUTER #38 restated them:

1. **Customer view**: a person's own data, the whole of it.
2. **Admin login alone**: platform controls only. No customer content, no customer settings.
3. **A link**: one customer account can also hold admin rights and switch to an admin view. The admin
   side **never** reads customer content, the owner's own included.

## 2. Words (the naming problem)

In the code "estate" has meant the **platform** (the scope control once read MINE | ESTATE). The owner
means **his own life** (his domains, devices, accounts, as a customer). Desks also say "estate" for the
repositories and sessions. Three meanings, one word.

**State today.** SURFACE~ESTATE-WORD-RENAME (owner card q398 = A) already renamed the scope's platform
side: the words are now `mine` and `platform`, and a posted or held `estate` is read as `platform` and
never written (VERIFIED, `command_shell.py:101-109`). The rail label "scope: the estate" is gone from
`templates/command_screen.html` (VERIFIED by search: no such string at 1dae531b). The word survives
elsewhere: the zoom level "Z1 estate" (`templates/command_screen.html:193,198`), the admin TODAY
reader `_estate()` and its `estate` key (`command_shell.py:488-510, 635`), `_estate_say` in
`command_ask.py:113`, and the observability docstrings ("the whole estate"). A search found 24 hits in
`templates/` and `static/` and hits in six `command_*.py` files (VERIFIED, counts only).

**The words this design uses, and proposes for code and screen:**

| Word | Means | Never means |
|---|---|---|
| **customer** (code), **Mine** (screen) | one person's own account: their content and their settings | the platform |
| **platform** (code and screen) | the application itself: services, registries, health, billing, entitlements, its own settings | any one person's data |
| **customer content** | rows a person's use of the product produced (section 4) | counts across everyone |
| **customer settings** | a person's own choices and connections (section 4) | platform settings |
| **admin** | a role that operates the platform | a person; a view of anyone's data |
| **estate** | not used in code or on the screen (owner question Q7) | |

## 3. Who is admin today (all VERIFIED unless marked)

There are **four** doors to admin power in the hub today, not one.

| # | Door | How it is decided | Where |
|---|---|---|---|
| D1 | **Bare admin login** | Username and password compared with two environment settings; on success the session gets `is_admin` and loses `invite_id` and any impersonation. No account, no email. | `app.py:40395-40443`; `auth.py:308-318` |
| D2 | **Impersonation** ("start as client") | Any admin session may set `impersonate_invite_id`; from then on `current_account` returns that customer's email **with `is_admin` still true**, so the rest of the suite treats the admin as that customer. Audited. | `app.py:40458-40481`; `auth.py:313-328` |
| D3 | **Admin address allowlist** | An account whose identity emails meet an environment allowlist counts as admin on a handful of routes (landing analytics, the self report's invite minting, admin flags on whoami, entitlement and campaign pages). | `self_paywall.py:431-447`; e.g. `app.py:4280-4305, 4638` |
| D4 | **The owner rule** (hub #803, dormant) | An account named in `COMMAND_OWNER_EMAILS` reads the platform on the Command screen through `PLATFORM_SUBJECT`, the bare admin's shape. Empty means nobody. Whether it is set in production: **NOT VERIFIED** (card q368 = B says it stays unset; the conductor's note, not read by me). | `command_shell.py:62-185`; `app.py:17491-17501` |

`_require_bare_admin` passes only a session with `is_admin` and **no** email (`app.py:15899-15903`), so
it refuses D2, D3 and D4. `_require_admin_session` passes any `is_admin` session, impersonating or not
(used by `/admin/workspace/<email>`, `/admin/scheduling*`, the impersonation routes; `app.py:19698,
36957-37132, 40471, 40494`).

**Count.** A scan of `app.py` found 628 route functions; 86 of them carry an admin check of some kind
(VERIFIED by a scratch script that reads decorators and bodies; it is a substring scan, not a call graph,
so the number is a floor for gating and a ceiling for nothing). Routes in `oauth_as.py`,
`studio_routes.py` and `world_routes.py` were **NOT** scanned.

## 4. What counts as customer content (proposed classification)

`models.py` declares 70 model classes; **57** of them carry an account-address column (VERIFIED, scratch
script). The build adds one registry that puts every table in exactly one class; an unclassified table
fails a test (W4 below). The proposal, for PRIVACY to correct:

- **Customer content (C).** `user_memory`, `knowledge`, `document`, `mail_index`, `mail_peer`,
  `brain_events`, `user_model`, `user_profile`, `user_goal`, `goal_reading`, `goal_node`,
  `user_aspiration`, `plan`, `plan_block`, `contact`, `contact_link`, `todo_item`, `pending_action`,
  `approval_decision`, `self_claim`, `claim_evidence`, `quest_answer`, `daily_digest`, `scheduled_post`,
  `campaign_state`, `booking`, `import_job`, `ingest_log`, `egress_log`, `vault_spool`, `store_order`,
  `self_report_share`, `progression`, `reward_events`, `retune_event`, the shared `email_log` (its
  recipient and subject columns).
- **Customer settings (S).** `account_setting`, `calendar_connection`, `event_type`,
  `customer_integration`, `mcp_connection`, `connected_identity`, `customer_credential`,
  `notification_subscriber`, `ingest_token`, `llm_spend_key`, `team`, `team_member`.
- **Account administration (P), visible to admin.** Invites (identity), `app_entitlement`,
  `self_report_entitlement`, `billing_plan`, `credit_balance`, `credit_ledger`, `credit_accrual`,
  `usage_debit_seen`, `reward_credits_ledger`, `spend_approval` (amount and feature only, never its
  reason text), `lucid_waitlist`, `admin_workspace_nudge`, the admin audit log.
- **Platform (P).** Everything with no account column: registries, sensors, cron heartbeats, arms
  state, system settings, landing analytics.

Whether the admin may see the **address** and plan of each account (P above) is owner question Q3.
Whether counts over C tables are platform data is Q4.

## 5. What admin routes read today (the gap)

Read against the rule in section 1: **no route reachable by an admin may read C or S rows of any account.**

| Route (admin door) | What it reads | Mark |
|---|---|---|
| `/admin/start-as-client/<id>` then any customer route (D2) | The whole of that customer's content and settings, as that customer. The direct opposite of the rule. | VERIFIED `app.py:40458-40481`, `auth.py:315-328` |
| `/admin/wall` and `/api/observability/wall`, goal lens with a named account (D1) | That account's active goal plans (intent, steps), its measures, lane readings and queued orders: `goal_plan.list_active`, `goal_progress.status`, `lanes.hydrate`, `order_ledger.queued_for_goal`. | VERIFIED `app.py:17287-17296, 17166-17174`; `wall_lenses.py:387-425, 442, 500, 619` |
| `/api/observability/wall` with a **service token** instead of a session | The same goal reads; `allow_personal=False` only withholds personal-family arms, it does not refuse a named account. | VERIFIED `app.py:17158-17171`; `wall_lenses.py:387-400` |
| `/admin/emails` (D1) | Recipient and subject of the newest 200 rows of the suite's outbound mail log, searchable. Whether customer-authored sends land in that log: NOT VERIFIED. | VERIFIED `app.py:40691-40707`; `email_log.py:183-234` |
| `/admin/actions/bulk-reject` (D1) | Rejects any account's waiting proposals by id, age or expiry. A write on C rows; it returns ids, not content. Its docstring says choosing ids is "a human judgment call", which needs the content. | VERIFIED `app.py:19463-19512` (body past 19512 not read) |
| Command rail, `memory` feed, platform side (D1, D4) | The newest memory rows across **every** account: stored time, event time, source, kind, privacy tier. No text, no address, but row-level traces of each person's activity. | VERIFIED `command_rail.py:82-88, 135-156` |
| Command rail, `pending` and `corpus` feeds, platform side | Counts only (by kind, source, privacy tier); rows set to `None` for the platform. | VERIFIED `command_rail.py:93-120, 207-251` |
| Command `act` view and `today` view, admin mode | Counts only for the queue; the platform census; the ME lens with `allow_personal=True`. | VERIFIED `command_shell.py:399-424, 488-534, 627-642, 677-684` |
| ME lens (`allow_personal=True`) | Registries (needs, instruments, arms) and the base wall's nodes. Whether any rung under a need is a per-person measurement: NOT VERIFIED (`_subtree` not traced). | Partly VERIFIED `wall_lenses.py:210-325` |
| `/admin/workspace/<email>` (`_require_admin_session`) | Identity, intake session id, billing plan, AI spend for that address, audit rows naming it; tiles link to each arm's own admin. Account administration (P), no content seen. What each arm's own admin page reads: NOT VERIFIED. | VERIFIED `app.py:19692-19723`; `workspace.py:1-29` |
| `/admin/identity` | An address's linked aliases and person id. Account administration (P). | VERIFIED `app.py:38188-38212` |
| Command `ask` as the platform | Refused: "the platform holds no brain of its own". | VERIFIED `command_ask.py:113-119` |
| Deciding a proposal in place | Refused for the platform and for any admin acting as an account (approve is person-only, hub #815). | VERIFIED `command_panels.py:321-334` |
| Every other admin route (billing, credits, invites, audit, costs, finance, system settings, blog, GDPR purge, scheduling, LinkedIn, mesh callers, prospect verify, store orders, the admin launcher into every arm) | NOT VERIFIED one by one. The launcher marks every app "owned" for an admin (`app.py:16376-16395`; `auth.py:410-413`); what an admin reads inside each arm is in other repositories and NOT VERIFIED. | |

Two code comments now contradict the owner's rule and must change with the build: "Bare admin is the
owner" (`app.py:17126`) and "the only person who can open it is the owner" (`wall_lenses.py:324`). One
comment contradicts its own code: the admin login's comment says a customer who borrows admin keeps
their `invite_id`, and the next lines remove it (`app.py:40429-40434`).

**Not known:** whether the owner's customer view shows empty data (ROUTER #32's 10-08 analysis said so,
cause unknown). Not investigated here: it needs a production read, which this task may not make.

## 6. The design

### 6.1 Two views, one rule

- A **customer session** (an account signed in, view = customer) reads that account's content and
  settings, as today. Its screen may show the **platform connector** (6.4).
- An **admin context** is either a bare admin login (D1) or a linked account switched to the admin view
  (6.3). In an admin context **every reader receives the platform subject** (`PLATFORM_SUBJECT`, no
  email), never the person's account. So the linked owner in the admin view sees exactly what the bare
  admin sees, and no more: the admin view is not a way into his own content either.
- **The wall:** no code path reached from an admin context reads a C or S row of any account, or writes
  one in a way that returns its content. Allowed in an admin context: platform data, account
  administration (subject to Q3), and counts (subject to Q4).

### 6.2 The link (account to admin)

A new table, `admin_grant`: `person_id` (from `identity_link`, never an address string, so an alias
change cannot drop or move the grant), `granted_at`, `granted_by` (`bare_admin` or a grant id),
`revoked_at`, `last_used_at`. One active row per person.

- **Created** by a pairing step (default of Q5): a signed-in customer opens "link admin", enters the
  admin credentials once, and the grant is written for that person. Both halves are proven in one
  request: the account by its session, the admin by its password. Audited (`admin_grant_created`).
- **Revoked** from the admin side (bare admin or any grant holder) or by the person; takes effect on the
  next request, because every request re-checks the grant (as the owner rule re-checks its list today,
  `command_shell.py:82-85`).
- **Replaces** D3 and D4: the address allowlist and `COMMAND_OWNER_EMAILS` become seeds at most (Q2, Q5),
  then are removed. One mechanism, not four.
- **D2 (impersonation) is retired**: the routes return 410 and `current_account` stops honouring
  `impersonate_invite_id` (Q1).

### 6.3 The view switch

- The session holds `view`: `customer` (default) or `admin`. It is set **only** by `POST /view`, which
  refuses any session without an active grant (403, session unchanged). No query string, header or page
  control decides the view; this follows the owner rule's "the session decides, not the request"
  (`command_shell.py:82-85`).
- Switching to admin asks for the admin credentials once per sign-in session (default of Q6), and the
  admin view ends when the grant is revoked, at sign-out, or after the session cap.
- In the admin view, `current_account` (or one wrapper above it) returns the platform subject, so
  `_require_bare_admin` and every reader take the path the bare admin takes. The switch back to the
  customer view needs no credentials.
- The screen always says which view it is in, in words; switching never mixes the two on one page.

### 6.4 The platform connector in the customer view (q369 = B)

The customer view lists the platform as one connected source, the way it lists any other connection.
It shows **platform data only** (health, census, counts if Q4 allows them), which by the wall holds no
customer content, so it is safe to show in a customer view, and one control: "switch to admin". Admin
controls themselves (billing, invites, settings, purges) are never drawn in the customer view.

### 6.5 Admin writes on customer rows

Some platform duties write customer rows without needing to read them: the GDPR purge, the expiry sweep,
bulk-reject of an aged backlog. They stay only if **content-blind**: the selector is age, expiry or a
platform rule, never a list of ids chosen by reading the rows, and the response carries counts, not
content (Q8).

## 7. The testable wall (test SPEC, for the build desk)

A spec, not code. Hub file names are proposals. Every part must be able to **fail**, and must say
`unknown` (error, not pass) when it cannot see what it checks.

**W0: inventory, the vacuity guard.** Enumerate `app.url_map` and classify every endpoint as
*admin*, *customer*, *service*, or *public*, by a transitive AST call graph from the route body to the
gate functions (`_require_bare_admin`, `_require_admin_session`, the new admin-view gate, the address
allowlist), the way `scripts/check_subject_binding.py` computes binders transitively. Fail if any route
is unclassified, if the admin set is empty, or if it is smaller than a checked-in floor (today's scan
found 86 candidates in `app.py`; the build measures the real number and pins it). Include
`oauth_as.py`, `studio_routes.py`, `world_routes.py`.

**W1: static reach.** For every admin route, walk the call graph into hub modules. Fail when it reaches a
model class or raw-SQL table in class C or S, or a reader on a named list (`goal_plan.list_active`,
`lanes.hydrate`, `order_ledger.queued_for_goal`, `brain.retrieve`, `email_log.recent`, and so on). An
edge the walker cannot resolve is reported as `unknown` and fails unless W2 covers that route.
Aggregate reads are allowed only through one module (`platform_counts`, say) whose functions return
integers keyed by platform vocabularies (kind, source app, privacy tier) and are tested for that shape.

**W2: dynamic canary.** A fixture seeds two accounts: A, a plain customer, and B, a customer holding an
`admin_grant` (the owner's case). Into every string column of every C and S table it writes a unique
canary, `CANARY-<table>-<column>-<A|B>`. Then, for every admin route in W0 (GET always; POST only where
the route is listed as side-effect free or runs in a dry-run fixture):

- call it as (i) the bare admin, (ii) B in the admin view, (iii) a service token where the route takes
  one;
- fill path parameters from the seed (A's and B's addresses and ids), and also try the generic query
  parameters admin routes read today (`email`, `lens` in `system|me|goal`, `goal_id`, `q`);
- **assert** no canary appears in the body, headers or redirect target;
- **assert**, through a SQLAlchemy `before_cursor_execute` hook on every engine (hub and shared), that no
  statement selects from a C or S table except inside the aggregate module.

Two **positive controls**, or the run errors: A's own customer session **does** see A's canaries on a
customer route that shows content, and the SQL hook records at least one statement per request. A
canary test that cannot see a canary has not passed.

**W3: link and switch.** Each is a separate test that fails on its own:
a session with no grant cannot set `view=admin`; a grant revoked mid-session ends the admin view on the
next request; a query string or header naming a view changes nothing; in the admin view every reader
receives a subject with no email (a spy on the readers); the impersonation routes answer 410 and a
leftover `impersonate_invite_id` in a cookie makes `current_account` return the plain admin, not the
customer; the admin view cannot decide a proposal (`may_decide` false).

**W4: classification is total.** Every model class and every raw-SQL table named in hub code is in
exactly one class of the registry. A new table with no class fails.

**The ratchet.** Today's code fails W1 and W2 on the rows of section 5. The build lands the tests with
a baseline file naming each known violator and its reason. The test fails if a violator **not** in the
baseline appears, and also fails if a baseline entry **no longer** violates (so the baseline can only
shrink, as `check_subject_binding.py` does). The build is done when the baseline is empty. The baseline
is never edited to make a red run green; an entry leaves only when its route is fixed.

## 8. Order of work (after PRIVACY's review and the owner's answers)

1. Registry of table classes (W4) and the inventory (W0). Tests only. Lane VAULT, DOORS review.
2. W1, W2, W3 with the ratchet baseline. Tests only.
3. Retire impersonation (Q1); fix the wall and observability goal reads, `/admin/emails`, the memory
   rail's platform rows, bulk-reject's selectors. Each fix removes a baseline entry. DOORS owns the routes.
4. `admin_grant`, the pairing step, `POST /view`. VAULT.
5. Fold D3 and D4 into grants and remove them (Q2, Q5).
6. The platform connector card in the customer view. SURFACE, after the screen-file chain in the plan's
   section 4.
7. Each arm's own admin pages get the same W0-W2 run in their repositories (not designed here).

Point 12 of the plan touches `app.py`, `auth.py` and the platform connector in the MCP repository; it
must not run beside the screen build without the plan's file locks.

## 9. Owner questions (for the Router desk; not asked in chat)

```
ASK: ADMIN-CUSTOMER-SEPARATION Q1 | Impersonation ("start as client") lets admin act AS any customer and read everything. Retire it?
OPTIONS: A) Retire it: routes answer 410, nobody can act as a customer. B) Replace with customer-granted support access: the customer opens a time-boxed window, sees it, can close it. C) Keep as is.
DEFAULT: A (your rule: admin has no rights to customer information; B can be added later if a support need appears)

ASK: ADMIN-CUSTOMER-SEPARATION Q2 | The dormant owner rule (COMMAND_OWNER_EMAILS, hub #803, unset) lets a named account read the platform on /command. Keep it?
OPTIONS: A) Remove it when the admin link lands (one way in, not two). B) Keep it dormant as a fallback. C) Remove it now.
DEFAULT: A (the link does the same job with a grant you can revoke; removing it now leaves no path until then, and it reads nothing while unset)

ASK: ADMIN-CUSTOMER-SEPARATION Q3 | What may the admin see about each account to run the platform?
OPTIONS: A) The account record only: address, plan, entitlements, billing, credits. Never content or settings. B) An opaque id per account, no addresses (billing handled in the payment console). C) Counts only, no per-account view.
DEFAULT: A (billing and entitlements cannot be run without knowing whose they are; it is the account record, not the account's information)

ASK: ADMIN-CUSTOMER-SEPARATION Q4 | May the admin view count customer rows (e.g. "91 proposals wait platform-wide", memory rows by kind)? With one customer, a platform count is that customer's count.
OPTIONS: A) Counts allowed, never rows, never split by account. B) Counts only when 5 or more accounts contribute, else "too few to show". C) No counts over customer rows.
DEFAULT: A (queue and pipeline health need counts; rows and per-account splits stay walled)

ASK: ADMIN-CUSTOMER-SEPARATION Q5 | How does a customer account get admin rights?
OPTIONS: A) Pairing: signed in as yourself, enter the admin password once; the grant is stored and revocable. B) An address list in a setting (as today's admin list). C) Both: the list seeds grants once, then only grants count.
DEFAULT: A (proves both halves in one step, needs no setting change, and can be revoked without a deploy)

ASK: ADMIN-CUSTOMER-SEPARATION Q6 | Switching your account to the admin view: ask for the admin password when?
OPTIONS: A) Once per sign-in session. B) Every switch. C) Never after the link is made.
DEFAULT: A (one entry per session; a stolen customer session alone does not become admin)

ASK: ADMIN-CUSTOMER-SEPARATION Q7 | Words. "Estate" means the platform in old code and your own life in your words. Which words?
OPTIONS: A) Code says customer and platform; the screen says Mine and Platform; "estate" is used in neither. B) As A, but the customer view is called "My estate" on the screen.
DEFAULT: A (Mine and Platform are already the scope words since q398; one meaning per word)

ASK: ADMIN-CUSTOMER-SEPARATION Q8 | Admin jobs that change customer rows without reading them (privacy purge, expiry sweep, clearing an aged queue). Keep them?
OPTIONS: A) Keep, content-blind only: select by age, expiry or rule, never by picking rows; return counts. B) Keep as they are today (bulk reject by id list included). C) Remove them from admin.
DEFAULT: A (the platform must still purge and expire; picking rows to reject needs their content)
```

## 10. What I verified and what I took on trust

- **Verified by me:** the task text (Conductor desk doc `desks/vault`, version 27, the one task only);
  plan section 3 point 12 and section 5 (leadfuel-core main 2524db4); every `file:line` above, read in a
  snapshot of hub `origin/main` 1dae531b; the q369 = B and q398 commit subjects in leadfuel-core history.
- **Taken on trust:** the owner's quoted words (ROUTER #38's cleaned transcription, via the conductor);
  card q368 = B (`COMMAND_OWNER_EMAILS` left unset); ROUTER #32's empty-view observation.
- **Unknown:** every production value and row (no production read was allowed); the arms' own admin
  pages; the admin routes marked NOT VERIFIED in section 5.
