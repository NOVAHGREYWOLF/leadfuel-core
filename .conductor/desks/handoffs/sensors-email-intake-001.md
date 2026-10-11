# SENSORS · email command intake · handoff 001 (2026-10-02)

Session: `SENSORS · email command intake (research)` [b5dce1]. The owner asked directly: an email he sends with the subject "Use Leadfuel" should make the brain start the task written in the body. He then widened it: any sensor should be able to carry a command. Research only. Nothing was built.

## Done
- Read hub (novahub) on origin/main as of the last fetch, plus three read-only research agents. No code changed.
- Briefed ROUTER #11 by message (queued to its session, 2026-10-02). The full findings are in that message and in this session's transcript. They include a sender-proof weakness, which is kept out of this public repo on purpose.

## What I found
- Every sensor already writes through one door (`intake.accept`). That is where the universal hook belongs.
- Hub tried this twice. `self_capture` sorts mail you send yourself and records an "instruction" but never runs it. It is off and no desk owns it. `master_orders` (reply to the command-book email) was reverted in #322 and never worked.
- Mail coverage has two problems:
  - The regular mail check reads only the Inbox.
  - It takes the newest 50 messages per run and then jumps past the rest, so a burst can lose mail for good. That is a bug, not a policy.
- The owner's rule already exists in hub `docs/BRAIN_SIGNAL_ARCHITECTURE.md` §1 and `mail_sweep.py`: point at every message, and fetch and keep the full text only once there is a reason. A "Use Leadfuel" subject is such a reason.

## Proposed tasks (lane by file)
- T1 COMMS: all mail, all accounts, as pointers. Run the metadata sweep on every connected mailbox and fix the 50-message gap. The owner wants this on its own merits.
- T2 COMMS: prove the owner wrote a message from the mailbox itself, and reply in the same thread.
- T3 SENSORS: a door stage that turns "trigger phrase plus proof" into a command record. It needs a replay guard and must skip mail hub itself sent.
- T4 INTELLIGENCE: the command faculty. Plan with the instruction fenced as data, park questions, report back. It takes over self_capture's instruction path, which needs an owner ruling.
- T5 DOORS: what each level of proof may run without a tap. Outward always queues.
- Order: T1 any time. T2 and T3 before T4. T5 before anything executes.

## Next
ROUTER #11 was asked to put T1-T5 on the Conductor desk page and to post five decision cards with defaults. The owner queues what runs. No desk has been opened.

## State
- Verified myself: the one door; self_capture records but never runs; master_orders is dead; the mail check is inbox-only with the 50 cap; hub never reads sender-authentication results; outward sends default to immediate.
- Taken on trust from the research agents: cron timings, planner and spend-gate behaviour, mail.send lacking thread replies.
- No reply from ROUTER #11 yet.
