# leadfuel-way

The way every session works, as a Claude Code plugin. A skill is advice a session may forget;
the hooks in this plugin are the part that happens anyway.

**What it does**
- **Every session start** gets a `THE WAY` banner: its role (read from its title: conductor, router, or a desk lane), its model's handoff caps, and an instruction to load the right skill. No banner means the hooks are not live.
- **The handoff guard** measures the session's real context from its transcript and tells it to hand off at the cap for its model (Opus and Sonnet 300k soft / 450k hard; Haiku 120k / 150k). Past the soft cap, the **Stop hook** sends a session back to write the handoff once before it may end a turn.
- **A conductor or router may not edit inside a git checkout** (handoff notes and `.conductor/` state excepted). Work goes to desks. A session is a coordinator if its title starts with `CONDUCTOR` or `ROUTER` (upper case, whatever follows); ROUTER and CONDUCTOR are tiers, never desk lanes, so a desk's lane is one of the owner's desk lanes (NODE, DOORS, ...). Only the four edit tools are covered, not shell commands.
- **Desks are grouped by project** (owner, 2026-10-07; 0.1.8, reworded 0.1.9). A desk is titled `LANE · <project> part · n` (the lane, the project's name followed by the word `part`, then n; for example `INTELLIGENCE · world intel part · 3`) and filed in its project's sidebar group (`world intel`); the lane stays in the title, and CONDUCTOR and ROUTER keep their tier groups. The older titles (`LANE · <task id> n/m · topic`, `LANE · topic`, `ROUTER #N`, `CONDUCTOR · topic`) are still read by every hook, so sessions migrate one at a time. The `new-project` skill makes a project's group; nothing falls back to the lane's group.
- **No self-archive before a live successor.** `archive_session` on `self` is refused until the session has read its successor back with `list_sessions` / `get_session`, live in the right group. A project-form desk's group is its own, read with `get_session` on `self`.
- **No bulk moves.** A `move_sessions` call that names more than one session is refused: sessions move one at a time, never in bulk. The plugin itself never moves or retitles a session.
- **The test rule is taught in `way`, `desk` and `router`** (owner, 2026-10-11, card q354 A; 0.1.10): static gates plus the test files for what you changed, locally; the full suite once, in CI, on the exact head you merge; a full local bare `pytest` only when the test setup itself changes. No hook enforces it.
- **Starting a session with no click** (owner, 2026-10-13; 0.1.11). `start_session` is switched off for the owner's account and a `spawn_task` chip needs a click, so the `launch` skill starts a session by running a scheduled-task launch slot (`way-slot-01` to `way-slot-06`): `run_scheduled_task` returns the new session's id, `update_scheduled_task` swaps the brief and title between runs. Measured: it starts, retitles, takes a model change and a message, and can be archived from outside. It can never be filed in a sidebar group (the app refuses), and its routine's permission mode is the owner's to set to Bypass, once. The archive guard counts a successor launched into a slot by its `way-slot-NN` `scheduledTaskId` in place of a group. What was measured and what was taken on trust is in `docs/SLOT-LAUNCH.md`.
- **A click on a card wakes the asker** (owner's queued pick NODE~WAKE-ON-ANSWER; 0.1.12). The `wake` skill is one pass of a watcher run by a scheduled task (`wake-on-answer`, Haiku): it sends each answered, unrouted Router desk card to the session that asked (or to the live router), and records `DELIVERED` only when the message shows in that session's own transcript; queued or held is `HELD`, a failed send is `UNDELIVERED` with a durable note on the Build Board, and a pass that cannot see is `UNKNOWN`. Logic in `scripts/wake_on_answer.py`. The task is the owner's to switch on (and to set to Bypass, as the slots are).
- **Eight skills**: `way` (every session), `handoff` (every tier), `conductor`, `router`, `desk`, `new-project`, `launch`, `wake`. Invoked as `leadfuel-way:<name>`.

**Install (owner step, once).** Installing writes `~/.claude/settings.json`, which sessions may not edit.
```
claude plugin marketplace add NOVAHGREYWOLF/leadfuel-core
claude plugin install leadfuel-way@leadfuel
```
The marketplace is this repo (`.claude-plugin/marketplace.json`, name `leadfuel`). Until this reaches the default branch, add a local checkout of the branch instead: `claude plugin marketplace add <path to the checkout>`. Start a fresh session afterwards: hooks load at session start.

**Prove it is live.**
```
python scripts/way_doctor.py          # LIVE only if every piece was seen working; UNKNOWN is never a pass
python scripts/way_pilot.py           # one small Haiku run with a low cap; needs `claude auth login` first
python scripts/way_caps.py set 40000 90000 --minutes 90   # force a low cap on every session, for a desktop pilot
python scripts/way_caps.py clear
```

**Switches (environment).** `SESSION_SOFT_TOKENS` / `SESSION_HARD_TOKENS` override the caps; `SESSION_GUARD_OFF=1` disables the guard and the Stop gate; `WAY_ENFORCE_ROLES=0` disables the coordinator edit rule, the background-agent rules and the bulk-move rule; `WAY_ARCHIVE_GUARD=0` disables the self-archive guard; `WAY_STATE_DIR` moves the per-session state (default: a `leadfuel-way` folder under the temp directory).

**Tests.** CI runs the full suite on every PR (workflow `test`, job `pytest`: a bare `pytest` from the repo root, which collects `plugins/`; see `pyproject.toml` for why). Locally, run the test files for what you changed, for example `pytest plugins/leadfuel-way/tests/test_plugin_layout.py`. A change to `pytest.ini`, the pytest config in `pyproject.toml`, a `conftest.py` or the test workflow still gets a full local bare `pytest` (0.1.10; owner, 2026-10-11, card q354 A).

The repo is public: this plugin carries ids, titles, status and PR numbers only.
