# Reports rebuild: one command email, every report attached

Decided 2026-09-29 with Novah. Work happens in `NOVAHGREYWOLF/novahub` (report code lives there; this repo is only the plan record).
Each step below is one session: finish, open a draft PR, retire.

## The design (fixed, do not re-litigate)
1. **One sender.** Every report reaches the owner through a single daily email from the command desk (NovahPrime, `prime@mail.leadfuel.cloud`). No other report mail.
2. **Branding sticks.** Each report keeps its own look (Lucid, Echo, Fieldy, Reach, etc.). Branding is rendering, not a delivery channel.
3. **Pull model.** Prime asks each spoke for its report. The spoke asks the hub for its data (`spoke_ask.py`), assembles its report, and returns it. Prime combines them into the briefing.
4. **Briefing + attachments.** The email body is the combined briefing. The full documentation of every report is attached, one file per report.
5. **Nothing silent.** A spoke that is late, dark or errored appears in the briefing as such. Never a quietly missing section.

## Current state (from code read 2026-09-29)
- Briefing built in `novahub/command_book.py`, `master_report.py`, sent at `app.py` (~26715, `service="novahprime"`).
- Attachments off since 2026-08-24: nine `.html` files got the 08-22 book junked by Defender. `MASTER_ATTACH_REPORTS` (unset) restores them.
- Side senders to remove: `app.py` ~25869 (`service="lucid"`, "Your day, in review"), ~2485 (`service="echo"`), `todo.py` ("Today: nothing open", `hello@`).
- Spokes push to the hub today (`_master_store_spoke`, `spoke_authority.py`, `SPOKE_SUBMIT_AUTHORITY` off). The hub reconstructs lucid/echo/orbit/signal/reach/odyssey from its own data.
- Railway on 2026-09-29: `Postgres` (16:55 UTC) and `novahub-cron-15min` (18:38 UTC) crashed; builds failed 09-24/25.

## Roster
Core, daily, one attachment each: Mail, Calendar, Finance, Location, Fieldy, Body, Odyssey, Reach, Orbit, Signal.
Ops, daily, attached every day (one combined PDF): System health, Spend, Coverage, Deliverability (DMARC digest).
Weekly / on demand: Estate, Echo, Scope, Trait check, Dossier.
Lucid's day-plan-vs-actual stays as a spoke report inside the briefing.

## Attachment format
One PDF per report, rendered server-side (HTML attachments caused the junking). Ops combined into one PDF. Must be proven by a real send landing in the etg.ai inbox, not assumed.
An allow-rule for `mail.leadfuel.cloud` in Microsoft 365 is a fallback, not the plan.

## Steps (one session each)
1. **Stabilize.** Diagnose and fix the crashed `Postgres` and `novahub-cron-15min` Railway services and the recent build failures. Done when both stay up and the next cron run succeeds.
2. **Inventory (read-only).** For every sensor and spoke: is it in today's fused briefing, does it have an attachable renderer, when did it last report. Read the Build Board (https://claude.ai/artifact/A4uS9xn1emqupohdE4DUfV) report tasks first so nothing is redone. Output: a ledger, no code changes.
3. **Kill the side senders.** Lucid, Echo and the `hello@` todo mail stop sending on their own. Their content becomes spoke reports in the briefing, branding kept.
4. **Pull model.** Prime requests each spoke on a schedule; spokes gather and return; late or missing spokes are shown in the briefing.
5. **Attachments.** One PDF per report, Ops combined, deliverability test to etg.ai.
6. **Verify end to end.** One real briefing lands with all attachments; DMARC and spam-folder checks pass.

Steps 1 and 2 are independent. 3 to 6 run in order.

## Rules for every step session
- One step only; anything else found goes on the Build Board as a task.
- Confirm the problem still exists before changing anything.
- Branch, tests and lint, draft PR, then stop. Never merge or deploy.
- Spend approvals stay a separate immediate email but must be sent from Prime.

## Completion status (reconciled 2026-10-02 UTC, task PR-leadfuel-core-7)
Public repo: ids, titles and status only. "Verified" = read with `gh` against `NOVAHGREYWOLF/novahub` on this date; "reported" = taken from the named desk's session, not re-checked. Statuses move; re-read before acting.

The plan's steps 1 to 6 above map to the conductor tasks below. Steps 3 and 4 shipped before this reconciliation (novahub #672, #680, #683). The old `.conductor/` state branch (leadfuel-core PR 7) is stale: it still lists P6 as in review and P7 as in progress.

| Task | What | State | Basis |
|---|---|---|---|
| P5-F4 | auto-archive line in the briefing (novahub#692) | merged | verified |
| P6 | Scope and Core daily reports (novahub#694) | merged | verified; the "dormant" test failure noted earlier is moot, ask the reports desk only if it recurs |
| P7 | Estate weekly report (novahub#696) | merged | verified; do not redo |
| P8 | DMARC parser and Deliverability report (novahub#695) | open draft, checks green | verified. Still owed: an ingest that delivers the report mail; where reports land (Router card Q23) is unanswered. P8 desk owns #695 |
| P5-F5 | scan source coverage once per pull (novahub#700) | open draft | verified state; the citation-mislabel half is reported as not yet reproduced |
| P9 | attach every report as a PDF | no PR | verified (none open). PDF look and engine is an owner decision (Router card Q33) |
| P10 | end-to-end check, briefing lands with every attachment | closed as links-only | reported by its desk: the briefing sends signed links, no attachments; PDF check unbuilt; live-inbox send not run (needs owner approval). Re-open after P9 |

## What is left, in order
1. **P8 ingest** (blocked on Q23): land #695 once the owner says where reports arrive, then build the ingest.
2. **Q33**: owner picks the PDF engine and look. Nothing in P9 starts before this.
3. **P9**: one PDF per report, Ops combined, built on the chosen engine. The HTML attachments stay off (#513, junked by the mail filter).
4. **P10 re-open**: one real briefing to the owner's inbox with every attachment. This leaves the machine, so it needs the owner's approval first.
5. **P5-F5**: finish #700 and say what the gates mean on its head before merge.

Rules that still hold: draft PRs, bare `pytest` plus the repo gate script, never merge on a stale base, nothing transmits without the owner.
