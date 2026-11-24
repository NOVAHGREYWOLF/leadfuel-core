# Part 205 B-class batch (SURFACE, WATCH, ARMS, DOORS items), 2026-11-23 Pacific

Source: CONDUCTOR 061 relayed the owner's typed words ("code everything you can ... dont stop full bypass mode");
defaults are the `default_if_B` column of CONDUCTOR-061-owner-classification.csv. Each row says what was verified
on live state and what was taken on trust. Nothing was sent, spent, deployed or deleted.

## Already done or overtaken (verified with `gh pr list`, not built again)

| id | state | evidence |
|---|---|---|
| p16-1 walk scoreboard | merged | leadfuel-core #92 |
| p16-2 morning proof read | merged | leadfuel-core #101 (run by hand daily until scheduled: the standing-rule step for a scheduled task is `watch/Register-MorningProof.ps1`, owner's to run) |
| mail2-1 hide Pro and Sending Pack paths | merged plus follow-up draft | hub #1013 (LO-1, merged 2026-10-29); hub #1197 draft (Pro stops granting Reach to strangers). Not duplicated. |
| fold-agents-shared | draft open | hub #1160 |
| p16-10 one model tier map | draft open | hub #1156 |
| fold-a-G40 local model approvals | draft open | hub #1158 |
| fold-s-autonomy scope plus dormant step | draft open | hub #1159 |
| desks-3-9 rows-before-delete page | draft open | leadfuel-core #104 |

Taken on trust: that those drafts match each item's `done_when`. Only titles and states were read.

## Decisions recorded on the owner's standing defaults (reversible, one line each)

- **chats-7 (three August ideas): park all three.** Emoji compression language, OpenExtract for iPhone, taxes from QuickBooks.
  The iPhone one also conflicts with his 2026-10-31 rule not to browse his phone. Parked, not dropped.
- **mail2-44 (machine-level flight recorder): fold into oss-4** (uptime and alarm work). No separate build.
- **sooner-6 (three disabled helper routines): leave disabled, retire the idea of re-enabling at a model cost.**
  Verified with the scheduled-tasks list today: `merge-train-screen-refresh` (last run 2026-11-07), `merge-desk-refresh`
  (2026-10-06) and `sessions-desk-keeper` (never run) are all `enabled:false`. Nothing was deleted or changed.
  Side effect to know: the Merge Train screen's click-carrying (ping, restart check) does not run while disabled.
  Option C in the item (one script that writes state.json with no model session) is the cheap replacement if wanted.
- **webchat-5 (three live cloud routines): stop each until its prompt is fixed.** The routines live on claude.ai,
  not on this machine, so this desk cannot see or stop them. The fix list for each prompt is: ratified arm names
  only (hub, signal, scope, reach, orbit, odyssey), current goals, approvals in the NovahOS Router desk and not Slack,
  and the nightly conductor close-out pointed at the current plan. See OWNER-STEP below.
- **mail2-30 (five-step AI platform self-check):** not built as a table here; it needs a read of the 14 bullets against
  the queue and is carried forward (see handoff note).
- **webchat-10 (one brand): keep the current palette and mark.** `brand/novahos-brand.json` is the one file; the app's
  warm neutral and clay accent, the indigo to violet mark, and the Greywolf navy and red kept as the company brand.
  `tests/test_brand_tokens.py` recomputes contrast from the file (text 4.5:1, accent button 4.5:1). The Greywolf gold
  is `null` because no file read gave its value. Not yet wired into the app, installer or sites: those read their own
  stylesheets (looks.css on branch one-app-b2-looks); wiring is DESIGN's lane (SESSION_MAP: design tokens).
- **own-2 (unlimited levels): approve the rule as proposed.** `game/level_rule.py` is the written rule as pure code
  (source order gap, goal, re-check; pass only on a measured outcome; tier grows every five passes, capped; never
  "game over", it says `nothing_owed` with the next date; decline retires 30 days). `game/` has 15 tests.
  GAME-DESIGN.md section 0 still needs the sentence pointing here (the file is `GAME-DESIGN.md` in the part 13 NODE handoff folder under `F:\Claude Sessions\handoff\`, outside any repo, not in this one).
- **own-3 (payout ledger): count money in, money saved, hours returned, things running.** `game/payout_ledger.py`:
  a line needs a measured source (a click is refused and listed), totals are per kind and never added across kinds,
  an unreadable source reads `unknown` and not zero. The shell room that shows it waits on own-1 (the loop that
  writes measured outcomes); the module gives that room its one function.

## Checked, no code needed

- **desks-1-10 (leadfuel-seo GCP key rotation script): not found, drop the item.** Searched novahub `scripts/` and this
  repo. The only related code is `scripts/gsc.py keyid`, which proves WHICH key a shell resolved after a rotation.
  Rotation itself is a Google Cloud console step. Taken on trust: the searched tree is the hub checkout's working tree,
  not a fresh main (git was not run there).
- **chats-8 (client sites): four rows written privately** to `F:\Claude Sessions\handoff\ROUTER-140\chats-8\`
  (names clients, so not in this repo). Read-only HTTP checks and the private clients repo; details are in the private handoff folder above.
- **chats-16 (temp pages for etg.ai and leadfuel.cloud, four-site report): draft the pages unpublished** is the default.
  Not built here: the four sites' live state was not read except one client site and the client previews above (named in the private handoff).
- **machines-2 (bundle Jarvis from Surface):** the GitHub repo NOVAHGREYWOLF/Jarvis exists and was pushed 2026-10-31,
  after the 2026-11-21 note said 19 commits were missing from GitHub. Whether those 19 commits are now on it was not
  checked (that needs a clone). See OWNER-STEP.

## OWNER-STEPs (nothing here can be done from this desk)

- webchat-5: stop the three claude.ai cloud routines in the claude.ai routines page, owner's account.
- machines-2: on Surface, `git -C <Jarvis checkout on the Surface desktop> status -sb` to see whether it is still ahead of origin;
  if yes, `git push` there or `git bundle create`. This desk did not ssh to Surface.
