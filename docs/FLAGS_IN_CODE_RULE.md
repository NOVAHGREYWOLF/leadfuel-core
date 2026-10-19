# FLAGS-IN-CODE: which switches move into code, which stay variables (proposal, nothing changed)

Task `NODE~FLAGS-IN-CODE-RULE`, queued by conductor 048 on the owner's note on Router desk card
**q577** (2026-10-19): a switch belongs in code, and a Railway variable only "for reason", and that
should be a stated rule. Scope: the CC-35 flags (hub #918 and the five spoke PRs) and the other
Layer 2 switches named on card **q574** (hub #895, #896, #897, #900, #901).

**This is a proposal.** No flag was flipped, no Railway variable was read or changed, no production
row was read, no secret was opened. Variable NAMES only, never values. Written 2026-10-19 (UTC).

Code was read at these `origin/main` heads (fetched 2026-10-19): hub `396b608d`, reach `a48a493e`,
scope `a5d9af58`, signal `1383a7a5`, odyssey `ad58f77e`, orbit `eec60345`. Line numbers are at those
heads. Every PR named below was confirmed MERGED with `gh` / `git branch -r --contains`.

---

## 1. The rule (wording for the owner)

The standing-rules file is the owner's. This is wording a desk proposes; it edits no `CLAUDE.md`.

> **Switches live in code. A variable needs a stated reason.**
>
> 1. **A behaviour switch is decided in code.** Its default is written in the code. If it waits on
>    something, the code checks that thing itself and switches on when it holds: a readiness
>    board that reads `ready`, a table that exists, a token that is present, a reader that has
>    landed. Nobody has to remember to flip it.
> 2. **A deployment variable (Railway or any other) is allowed for one of three stated reasons,
>    written as a comment beside the line that reads it:**
>    - **credential**: a secret, token, key or database URL;
>    - **per-environment value**: something that differs between machines or environments (an
>      address, a host, an identity list, a model a machine serves);
>    - **owner consent**: the switch approves on the owner's behalf, spends, or lets anything leave
>      the machine (Law 9). Its code default is **closed**, and only the owner opens it. It is a
>      variable because a merge to `main` is a production deploy within seconds and desks merge
>      their own PRs on green, so a consent switch written in code could be opened by any merged PR.
>
>    A new variable with none of these reasons is a defect in review.
> 3. **A switch that turns itself on must be able to see its prerequisite.** If the check cannot
>    establish it, the switch stays off: `unknown` is never `ready`. A switch that **takes access
>    away** latches once on, so a later `unknown` (a missed heartbeat) never quietly reopens it; it
>    shows on the board instead.
> 4. **One decision, one place.** A switch shared by the hub and the spokes is read from one place,
>    never copied into each service's variables, so the services cannot disagree.
> 5. **Turning a code switch off is a code change** (a revert PR, which deploys like any merge).

---

## 2. The audit

Column "kind": **credential**, **per-env** (per-environment value), **consent** (approval, spend or
egress), **behaviour** (a pure behaviour switch). "Verified" means read in code by this desk at the
heads above. Lines marked **UNVERIFIED** were not checked and are taken on trust or inferred.

### 2.1 CC-35 flags (hub #918 `ec3eb1f4`; reach `e1f6c77e`, scope `6403d42a`, signal `b5d096df`, odyssey `6d94deba`, orbit `eec60345`)

| Name | Read at | Code default | Kind | Proposal |
|---|---|---|---|---|
| `SPOKE_WORKER_ENABLED` | each spoke `spoke_worker.py:95-97` (`enabled()`), identical in all five (orbit under `apps/<orbit app>/spoke_worker.py`); started at reach `app.py:6710` | off; also off without a token | **two things in one switch**: the heartbeat (which carries the CC-35 level report, `spoke_worker.py:374-389`, whose only caller in all five spokes is the pull loop `:412-422`) and the order pull loop (runs the arm's agents unattended on hub orders) | **Split it.** (a) **Heartbeat + level report: code, on whenever the per-spoke token is present.** It is a call from our service to our own hub on an existing route; no vendor, no spend, no account content. The token is the prerequisite and is already required. (b) **Order pull loop: stays a consent switch, closed,** until each spoke's handler table is audited. Outward capabilities already go to the approval queue (reach `herald_orders.py:216-219`, `outward=True`), but whether any non-outward handler makes a metered model call unattended is **UNVERIFIED** (reach `build_campaign_from_icp` "reads the ICP from the brain"; the other four not read). If the audit shows no unattended spend, the loop moves to code too. |
| Per-spoke tokens `SERVICE_TOKEN_<APP>` | spokes `spoke_worker.py:74-78` (per-spoke, else the shared mesh token); hub `mesh_auth.py:49-64` | none (empty = dormant) | **credential** | **Stays a variable.** Reason: credential. |
| `LEVELS_DATABASE_URL` | spokes `spoke_levels.py:62`, `:148`, `:180` | unset = read the ladder through the spoke's existing shared-database session | **credential** (a database URL) and **per-env** | **Stays a variable**, and it is already the right shape: optional, needed only where the hub's database is not the shared one (an open question in the hub RUNBOOK 0.2, **UNVERIFIED** here; no production read made). The board already names which source each spoke read. |
| `LEVELS_5_8_OPEN` | hub `level_readers.py:54`, `:107`; spokes `spoke_levels.py:59`, `:101` (six services) | off | **behaviour** (opens progress and quests for levels 5-8; takes nothing away, sends nothing, spends nothing: module docstring `level_readers.py:9-15`, `:41-43`) | **Move to code, on.** Its prerequisite (the six rule readers) landed in hub #901. Two ways: **(A, no migration)** replace the variable read with a code constant in `level_readers.py` and the `spoke_levels.py` drop-in; **(B)** use the ladder's own stored `enabled` column, which the spokes already read from the shared table (`quest.py:199-216` seeds 5-8 `enabled: False`; `quest.py:795` honours it). B is one place by construction, but `ensure_seed` never touches an existing row (`quest.py:226-227`), so B needs a data migration on production, which is the owner's. Level 8 stays unmet honestly (no threshold stored). Six variables become none. |
| `LEVEL_GATE_ENFORCE` | hub `level_gate.py:42`, `:66`, `auth.py:395`; spokes `spoke_levels.py:58`, `:96` (six services) | off | **behaviour that takes access away** (not approval, spend or egress). The owner already decided "levels gate access" (card q487 A, cited `level_gate.py:1-4`) | **Move to code, turned on by the readiness board.** The prerequisite already exists as code: `level_surfaces.readiness()` with `ready` false while any blocker stands (`level_surfaces.py:31-34`, the function's docstring at `:326`), and a spoke whose switches differ from the hub's already reads `partial` (`spoke_level_reports.py:36`). Proposal: when `readiness()` first reads `ready`, the hub writes a **one-way latch** to one shared row; the hub and every spoke read that row (spokes already read shared tables) instead of their own variable. `unknown` or `partial` never latches; a stale report after latching shows on the board and does not reopen the gate. Store for the latch **TBD** (a new table would be a production migration, the owner's). Six variables become none. |

### 2.2 Layer 2 switches from card q574

| Name | Read at | Code default | Kind | Proposal |
|---|---|---|---|---|
| `STANDING_GRANT_ENABLED` (hub #895 `917633d1`) | hub `standing_grant.py:66`, `:142`; also read by the readiness board `level_surfaces.py:123`, `:132` | off | **consent**: a standing grant "counts as his Law 9 approval for that skill" (`standing_grant.py:4-8`) | **Stays a variable, closed.** Reason: owner consent. The other two #895 steps are not variables: wiring the `release_due` runner is a code change that would make a scheduled send (owner and VAULT, `standing_grant.py:40-45`), and `alembic stamp 0014` is a production migration step (owner). |
| `WORLD_INTELLIGENCE_PAGE` (hub #896 `1397ea2e`) | hub `world_routes.py:30`; same gate in `command_world_intel.py:262` | off (every route 404) | **behaviour**: draws rows already in the account's store; "NOTHING HERE TRANSMITS" (`world_routes.py:14-17`), globe library served from our own static folder | **Move to code, on.** The page reads the session's own rows only, and says so when there are none. |
| World feed switches `USGS_ENABLED`, `EONET_ENABLED`, `GDACS_ENABLED`, `NWS_ENABLED`, `CELESTRAK_ENABLED`, `WORLD_FEEDS_CRON_ENABLED` ("the feeds you allow" on q574) | hub `usgs_client.py:29`, `eonet_client.py:31`, `gdacs_client.py:30`, `nws_client.py:36`, `celestrak_client.py:40`, `world_feeds.py:54` | all off | **consent** (each is an outbound fetch to a third party, Law 9, even though keyless and free) | **Stay closed by default.** Reason: egress. Optional simplification: one owner allowlist variable naming the allowed feeds instead of six booleans. `NWS_USER_AGENT` (`nws_client.py:41`) is a **per-env** value and stays. |
| Ask local-model switch `COMMAND_ASK_LOCAL_MODEL` (hub #897 `1f8e94e3`) | hub `command_ask_local.py:47`, `:87`, `:92`; decides the route in `command_ask.py` `route_setting()` | off | **behaviour**. The local leg runs only when five environment checks hold: no cloud credential in the process, the open-source provider configured, its address loopback, the named model equal to the served one, the embedder loopback (`command_ask_local.py:100-133`, `local_route` at `:135`). So by construction it spends nothing and sends nothing. Its value must equal `OSS_MODEL` (check 4), so it repeats a value already set. | **Move to code: the local ask turns itself on when all five checks pass,** using the model the local provider serves. On Railway the checks fail (no loopback provider), so it stays off there and says why. Unchanged: a local failure never falls through to a cloud model. Needs one design decision for DOORS/VAULT review: whether an explicitly set cloud `COMMAND_ASK_MODEL` is read at all in a process where the local checks pass (proposed: no, local wins). |
| Cloud ask `COMMAND_ASK_MODEL` (adjacent, not on the card) | hub `command_ask.py:67`, `:108` | unset = off | **consent** (spend and egress) and **per-env** (a model name) | **Stays a variable, closed.** |
| `COMMAND_OWNER_EMAILS` | hub `command_shell.py:100`, `:140`; `scripts/command_owner_rows.py:38`, `:209`; used by `oracle_routes.py` | empty = nobody | **per-env** identity list, personal data, and it widens what a session can read (platform scope) | **Stays a variable.** Reasons: per-environment identity; an address must never sit in a repo (and this repo is public). |
| Node door `NOVAH_LOCAL_AUTHORITY`, `NOVAH_LOCAL_AUTHORITY_TOKEN_SHA256` (hub #900 `a8e18856`) | hub `local_authority.py:82-83`, `:128`, `:135` | off; refuses whenever `RAILWAY_ENVIRONMENT` is set (`:139`) | not Railway at all: set on the owner's PC by the node launcher. The hash is a **credential**; the enable bit opens a login-free door (auth) | **Stays as is.** Not a Railway variable; the four steps on q574 are on the PC. |

### 2.3 What this changes, in count

Counted as places the code reads a name (one per service), not as what is set in Railway today,
which was not read. **Removed: 14 reads** (`LEVELS_5_8_OPEN` in 6 services, `LEVEL_GATE_ENFORCE` in
6, `WORLD_INTELLIGENCE_PAGE` 1, `COMMAND_ASK_LOCAL_MODEL` 1; the last one can only ever pass its
checks on the node, where the provider is loopback). **Narrowed: 5** (`SPOKE_WORKER_ENABLED` keeps only the pull loop, pending the handler
audit; the level report no longer waits on it). **Stays, each with a stated reason:** tokens and
`LEVELS_DATABASE_URL` (credential), `COMMAND_OWNER_EMAILS` and `NWS_USER_AGENT` (per-env),
`STANDING_GRANT_ENABLED`, the feed switches, `COMMAND_ASK_MODEL` and the pull loop (consent).

The wider surface was **not audited**: a name-shape count finds **85** distinct quoted names ending
`_ENABLED`, `_ENFORCE`, `_OPEN` or `_PAGE` in hub non-test code (`git grep` at `396b608d`). Not every
one is confirmed to be an environment read. Applying the rule to them is a separate task.

---

## 3. Suggested build tasks (for the conductor; not started)

Each is a code change in the owning lane's repo and lands closed or behind tests like any other PR.
Lanes are suggestions from the session map; the conductor decides.

1. **ARMS**: split the spoke heartbeat from the pull loop in the `spoke_worker.py` drop-in (all five
   spokes): heartbeat on with a token; pull loop unchanged. Then audit each spoke's handler table
   for unattended metered calls.
2. **DOORS**: `LEVEL_GATE_ENFORCE` becomes the readiness-board latch (hub `level_gate`, `auth`,
   `level_surfaces`; the spoke drop-in reads the latch row). Owner decision needed only if the latch
   needs a new table (production migration).
3. **DOORS or SURFACE**: `LEVELS_5_8_OPEN` becomes code (option A), hub `level_readers.py` and the
   spoke drop-in together.
4. **SURFACE**: `WORLD_INTELLIGENCE_PAGE` removed; the page is on and says when it has nothing.
5. **SURFACE, reviewed by DOORS/VAULT**: the local ask turns itself on from its five checks.
6. **NODE**: a static gate that fails when a new environment read has no `# var-reason:` comment
   naming one of the three reasons (credential, per-env, consent), so the rule is checked, not
   remembered.

---

## 4. What I verified, and what I took on trust

**Verified myself (git/gh at the heads above):** all six CC-35 commits and the five q574 PRs are on
`main` (#895 `917633d1`, #896 `1397ea2e`, #897 `1f8e94e3`, #900 `a8e18856`, #901 `4286e1e6`, #918
`ec3eb1f4`); every file:line above; the code defaults; that the heartbeat (and so the level report)
is only sent from the pull loop; that `ensure_seed` never updates an existing level row; that the
readiness board already compares spoke switches with the hub's; that the local ask's five checks are
environment-only.

**Taken on trust or not checked:** what is set in Railway today (deliberately not read); whether the
hub's `DATABASE_URL` and the shared database are one Postgres (q577's own "taken on trust" line);
whether any spoke handler other than reach's table spends unattended; the store for the latch row;
the owner decisions cited inside module docstrings (q487 A, q358 A, q455 A, pick 291), read as the
code quotes them, not from the cards.
