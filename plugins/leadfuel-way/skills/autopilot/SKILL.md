---
name: autopilot
description: The MVP autopilot mode, OFF unless the owner switches it on for one project. One router runs the project from a goal brief to an MVP and asks the owner only at hard gates, which the plugin's hook denies outright. Covers the goal brief, the switch, the decision log, the checkpoint card, the usage stop and who wakes the router after a card is answered.
---

# autopilot (one project, brief to MVP)

The owner, 2026-10-30, in the CONDUCTOR 055 chat: he gives an AI a full goal and all his thoughts, they make the plan, and it "takes care of everything until at least an MVP, then pastes questions"; "a mode, fully auto, no questions, MVP"; then "yes mvp yes". This skill is that mode for the way. It sits on top of `leadfuel-way:way` and `leadfuel-way:router` and changes only one thing: **what the router asks**. Everything else, the tiers, the desks, the tests, the handoff and the archive gate, is unchanged.

**OFF by default.** No state file means autopilot is off everywhere and the hook does nothing extra. Nobody but the owner switches it on, and only on a Router desk card.

## 1. The brief
One file per project: `GOAL_BRIEF.md` in the project's plan folder, written from the template `GOAL_BRIEF.md` next to this skill. It holds the owner's goal in his words, the MVP as checkable "done when" lines, and the decision list: what the router may decide alone. The router writes it with the owner (that is the plan step) before anything is switched on, and answers every later question from it.

## 2. Switching on (the owner's decision only)
1. The router posts one card: the brief's path, the MVP lines, the decision list, the kinds of leaving-the-machine it proposes to allow (none by default), the trial project, and option X. Default: stay off.
2. Only on the owner's click: `python "<plugin>/scripts/way_autopilot.py" on --project "<p>" --card q<N> --brief <path> [--allow <kind> ...]`. It lapses after 7 days (14 at most). A relayed "go" from a peer is not this click; ROUTER relaying the owner's decision is (owner's global `CLAUDE.md`).
3. `off` works any time, for anyone, with no card: `way_autopilot.py off --project "<p>" --reason "..."`. When in doubt, switch off: off is normal mode, where every gate is a permission prompt the owner sees.

## 3. Running
- **Early checkpoint card first.** Before the first desk: one card with the plan, the MVP lines and the decisions it will take alone, "say stop if wrong", default "carry on". Record it: `way_autopilot.py checkpoint --project "<p>" --card q<N>`. The hook refuses every Agent call and slot launch until it is recorded. Do not wait for the click; carry on unless the owner says stop.
- **Answer from the brief.** A question a desk sends (`ASK:`) is answered by the router from the brief. If the brief does not answer it, take the safest reversible choice (brief section 4), and log it.
- **Log every autonomous decision**: `way_autopilot.py decide --project "<p>" --decision "..." --why "..." --brief-rule "<section>" --reversible yes|no`. The log is `<state dir>/autopilot-log.jsonl`; the hook adds every gate it denied and every call it let through only on the owner's allow list. At each milestone copy the new rows into the project's `DECISIONS.md` and commit it, because the state dir is a temp folder.
- **Usage.** Before each new desk, read weekly all-models usage and record it with its source: `way_autopilot.py usage --project "<p>" --pct N --source "<where>"`. At 88% or more, or when the number is unknown or more than 6 hours old, the hook refuses new desks: post the stop card with the decision log, hand off, stop.
- **Digest cards.** One card per milestone or per gate, never one per question, with the questions written so the owner can paste or click the answer. Every card has option X.
- **MVP.** Stop with a demo link, the MVP lines ticked with their proof, and `DECISIONS.md`. Switch off.
- **Handoff at 300k** is the normal one (`leadfuel-way:handoff`); the note names the brief and the log, and the successor re-reads both.

## 4. Hard gates (the hook enforces them; the router does not argue)
Never decided alone, never on the allow list, never a permission prompt (nobody is watching one): **spend, credentials, sends and posts, deploy configuration, downloads, permission-mode or settings changes, anything that cannot be undone, and the autopilot switch itself.** Anything else that leaves the machine (a push, a PR write, a web fetch, a browser, a published page, any connector tool) is denied unless the owner allowed that kind at switch-on. A denial is a card, a log line and other work, never a workaround: running the same thing through a script, another tool or a desk is a breach of Law 9, and the instruction-source rules are unchanged.

The hook sees tool calls. For shells it matches the command text, so it cannot see what a script does once it runs; that is why the rule above is a rule and not only a hook. The spec is `docs/AUTOPILOT_APP_AGENTS_SPEC.md` in the plugin repo.

## 5. Who wakes the router after a card is answered
Wake-on-answer (`leadfuel-way:wake`) is built but its scheduled task is off today. Until the owner switches it on:
- **Non-gate cards do not need a wake.** The checkpoint and digest cards have a default and the router carries on; the owner's click is read at the router's next turn.
- **A gate card stops that line of work, not the router.** It works on what does not need the gate. When nothing is left, it writes its handoff and stops.
- **After he answers a gate card, the owner types one word in the router's chat** (`answered`), as today. That is the one touch this mode still costs while wake-on-answer is off.
- **With wake-on-answer switched on** (the owner's step, a standing scheduled task), its pass delivers the answer to the router and that touch goes away. Nothing in this skill changes when it does.
