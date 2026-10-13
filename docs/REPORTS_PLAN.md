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

## Completion status (reconciled 2026-10-06 UTC, task GRP-reports-finish)
Public repo: ids, titles and status only. "Verified" = read with `gh` against `NOVAHGREYWOLF/novahub` on this date; "reported" = taken from the named desk's session or board task, not re-checked. Statuses move; re-read before acting.

The plan's steps 1 to 6 above map to the tasks below. The previous reconciliation (2026-10-02) is superseded: it listed #695 and #700 as open and P9 as having no PR, and all three have since merged.

| Task | What | State | Basis |
|---|---|---|---|
| Steps 3, 4 | side senders folded in, Prime pulls each spoke (novahub#672, #680, #683) | merged 2026-09-29/30 | verified |
| P5-F1, P5-F3 | spoke authority and the contested-source guard (board tasks, both done) | done, nothing to build | reported (board) |
| P5-F4 | auto-archive line in the briefing (novahub#692) | merged | verified |
| P5 | CONDUCTOR block in the briefing (novahub#697) | merged | verified. Reported: no conductor report has ever reached the hub in production, so the block never renders; the writer sits outside the hub |
| P6, P7 | Scope and Core daily reports (#694), Estate weekly (#696) | merged | verified |
| P8 | DMARC parser, ingest and Deliverability report (#695) | merged 2026-10-02 | verified. Dormant until `DMARC_MAILBOX` is set (owner step) |
| P5-F5 | scan source coverage once per pull (#700) | merged 2026-10-02 | verified |
| P9 | attach every report as a PDF (#701), WeasyPrint libs in the build (#714), print CSS (#722) | merged | verified. In production the PDF engine reported itself missing at boot (reported, from a deploy log); fix is deploy configuration, an owner step |
| Desk Log | daily Desk Log (#742) | merged | verified |
| Spend | metered LLM spend, gate and fixed floor, as the `spend` spoke; ops roster is core + spend + deliverability (novahub#775) | draft | verified (this PR). `health_ops` and `coverage` were not built: `core` already reports system health and source coverage |
| Visual rebuild | every report as one offline interactive HTML file (novahub#774) | open draft | verified state; owned by the reports visual desk |
| P10 | end-to-end check, briefing lands with every attachment | not run | needs a real send, which leaves the machine: owner approval first |

## What is left, in order
1. **Land the Spend report** (novahub#775) and the visual rebuild (#774) through the merge train.
2. **PDF engine in production**: a deploy-configuration change so the boot line reads ready (owner step). Check after any fix that the engine reports ready at boot.
3. **DMARC_MAILBOX** (owner step): until it is set the Deliverability report stays dormant.
4. **Proof send (P10)**: one real briefing to the owner's inbox through the proof-send gate, with every attachment. Leaves the machine, so the owner runs it, after item 2.
5. **Master report storage**: reported as not stored since 2026-09-24 while the briefing still goes out; a reports-desk investigation, not started.

Rules that still hold: draft PRs, bare `pytest` plus the repo gate script, never merge on a stale base, nothing transmits without the owner.
