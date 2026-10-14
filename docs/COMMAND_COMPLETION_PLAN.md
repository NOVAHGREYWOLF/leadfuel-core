# /command: the plan from today to fully operational

Task SURFACE~COMMAND-COMPLETION-PLAN (pick 286). Written by SURFACE one-interface part 20, a background
desk of ROUTER #56. **Plan only: no product code, no flag, no spend.** Facts read 2026-10-14 about
04:00-04:20 UTC. Hub main at that time: **a4371688**. All times are UTC.

True source of the goal: the owner, in the Conductor chat, 2026-10-14: "i want to finish as much of the
command with my allowance and everything that we have written about it and get that fully operational."
The completion test is the 12-point checklist he agreed on Router desk card **q454 = A** ("agree to all 12
as written", so point 8 is not cut). Card **q452 = C** started the held tasks now. This plan refreshes the
earlier draft by SURFACE part 15 against hub main as it is now; the differences are listed in section 7.

## How to read the marks

- **verified**: I read it myself this session (`gh`, `git` on the hub's `origin/main`, the card or pick
  documents, the review files, the code).
- **unverified**: taken from a note or from another desk's report. The source is named.
- **unknown**: the check cannot see its subject (above all, anything in production). It is never read as done.

The Conductor desk's `done` flags lag the real merges (for example picks 265, 279 and 282 show no
done flag, though hub #833, #826 and #827 are merged). **No `done` flag was used here.**
Merge state below comes from `gh` only.

## 1. The short note

Most of the groundwork is merged: the screen, focus HUD, rail, console, camera and universe, 13 of 18
layers, the Ask console (landed OFF), quest progression in the hub, the read-only Action Feed and Character
panels, the platform rename, the person-only approve rule, and the decision record. **What is left is three
bands.**

1. **Finish the panels** (points 2 to 6). Mostly already filed and queued. Seven hub PRs are open as
   drafts right now, so the work is landing, not starting. Deciding in place (pick 287) is the big one and
   has not started.
2. **Fill the dead menu, strip and panes** (points 7, 8, 11, 12). The live page still says "stage N", "not
   wired yet" or "later" in many places. After card q369 = B moved the old "regions" plan into panels, **no
   queued task builds these**: the old D3/D4/D5 picks are marked superseded and were never re-queued. This is
   the largest unplanned piece and q454 = A keeps the 37 views and Follow in scope.
3. **The gates only the owner opens** (points 1, 6, 9, 10): `COMMAND_HOME`, `COMMAND_ASK_MODEL`,
   `STUDIO_GENERATE`, `WORLD_INTELLIGENCE_PAGE`, `ORACLE_MODEL`, the approval-link secret, plus any spend and
   send. Each has prerequisite desks that are cheap and do not need him.

## 2. What is live on hub main a4371688 (verified in code)

- **Ask:** `POST /api/command/ask`, session plus CSRF, signed-out 401 (app.py:17340-17368). Off until
  `COMMAND_ASK_MODEL` is set, one model, no fallback (the route's own docstring; the model name is read from
  the environment, so whether it is set in production is **unknown**).
- **Quest routes:** GET progression, log, rewards, credits; POST recompute, accept, decline, rewards/seen,
  all through `_quest_caller` (app.py:3583-3687). The POSTs are not called by any page yet (PR #829 adds the
  calls and is open).
- **Panels:** `GET /api/command/feed` and `GET /api/command/character` (app.py:17458, 17481). The panel
  script's own header says nothing there approves, rejects, sends or recomputes
  (static/command/panels.js:13). The feed's one action is a link to the Act page. Trust rings read
  `unknown`, earned access reads `not_built`, the likeness reads `not_made` (command_panels.py:94-113).
- **Level 2 cannot be reached by anyone** until the hub can prove who measured the voice
  (quest.py:9-17, `_voice_measurer`). PR #828 is the fix and is open.
- **Layers:** 13 built (L01 L03 L04 L05 L06 L07 L10 L11 L12 L13 L15 L16 L17), 5 `later` (L02 track, L08
  replay, L09 scheduled, L14 weather, L18 claimed vs measured) (command_layers.py:111-160).
- **Still dead on the page** (templates/command_screen.html): LEADS "not wired yet" (:96); WORLD "not read
  here yet" (:98); Needs "not wired yet" (:138-139); menu Quests, Party, Studio, Crew, Machine as stage or
  "not wired yet" spans (:154-155); Views "arrive in stage 4" (:262); Follow "stage 4" (:263); the mic label
  "local only" (:327); the five `later` layer rows (:276-278).
- **Approve race:** `_execute_pending_action` (app.py:12536) reads the row with a plain select, checks
  `status == "pending"`, then writes `approved`. I saw no row lock or compare-and-set in it. Two clicks at the
  same instant could both pass the check. (Read by me; I did not run a concurrent test.)
- **Flags:** `COMMAND_HOME` defaults off (app.py:17056-17060). `.railway/railway.ts` on main declares none of
  `COMMAND_HOME`, `COMMAND_ASK_MODEL`, `STUDIO_GENERATE`, `WORLD_INTELLIGENCE_PAGE`, `ORACLE_MODEL` or the
  approval-link secret (grep, verified). Their production values are therefore **unknown** to every reader
  that is not Railway itself.
- **Phone width:** `screen.css` has two breakpoints (1100 and 700 px), `console.css` two, `focus.css` one;
  `panels.css`, `layers.css` and `rail.css` have **none** (grep, verified). Whether the panels work at phone
  width is **unknown**: no test or measurement of it was found.

### Merged hub PRs that carry the command (verified with `gh`)

| PR | What | Merged (UTC) |
|---|---|---|
| #793, #794, #795 | Screen, focus HUD and live rail, console | 10-07 |
| #797 | Layers batch 1 | 10-08 |
| #796 | Home fixes: TODAY counts held spend asks, an unread view never reads clear | 10-08 |
| #791, #792 | World intelligence lane (dormant), studio lane (generate off) | 10-07 |
| #799 | Home (beta) button on the old home, Old home link on /command (q349 = B) | 10-11 |
| #801 | Camera Z0-Z4 and the universe | 10-11 |
| #803 | Owner rule for the screen (`COMMAND_OWNER_EMAILS`, default nobody) and MINE or ESTATE scope | 10-11 |
| #814 | Earned access step 1: the shape of every approval decision is recorded (migration 0012) | 10-12 |
| #815 | Approve is person-only; no service token may approve | 10-12 |
| #816 | The retired connector approve switch removed from code | 10-13 |
| #817 | Known wins; the self-model pass runs on them (q376) | 10-13 |
| #819 | Layers batches 2 and 3 | 10-13 |
| #820 | Ask console over the map (D7), off until the model is named | 10-13 |
| #821 | Platform rename (the other side of the scope control is the platform) | 10-13 |
| #822 | Quest progression: levels 1-4, payoffs, gap quests, earn-only credits at 0 | 10-13 |
| #823 | Action Feed and Character panels, read-only (q369 = B) | 10-13 |
| #824 | Ask phone path drops local-only rows (q401 = A) | 10-14 |
| #826 | Hub engine hides bound parameters in database errors (pick 279) | 10-14 |
| #827 | Watchtower board flake fix (pick 282) | 10-14 |
| #833 | `ask.answer` drops local-only rows for every caller (pick 265) | 10-14 |

### Open draft PRs on the hub (verified: state and check results from `gh`, 04:0x UTC)

| PR | Pick or task | CI `pytest` on its head | Notes |
|---|---|---|---|
| #829 | 280 Character panel recompute and "mark as seen" on a click | success (f2aa6d6d) | Touches app.py, command_panels.py, panels.js, screen.js, levels.js, command_screen.html. A DOORS review (head 40b3a21c) found one low item, a log line carrying an account address in the rate-limit key; the head has since changed (unverified that it was fixed). |
| #828 | 281 Hub stamps who wrote the voice row; level 2 reads only Echo's stamped measurement | success (3d814d19) | DOORS review: PASS with follow-ups (a test for the update path, a token-uniqueness check, a statement that Echo's number is dropped if it uses the shared token, and a product question: Echo's spoken-only seed would count toward level 2). The reviewer's word, unverified by me. |
| #825 | 278 Layers route docstring, log and blank-address pins | **failure** (17b29fbd) | Needs a rerun or rebase; cause not read by me. |
| #830 | 284 Five more cloud paths drop local-only rows | in progress (fbfb14bb); the earlier head failed | DOORS review: PASS with follow-ups (unverified, reviewer's word). |
| #831 | 285 Day summaries carry their tier | **failure** (36ea6a84) | DOORS review: lands only after #833 (now merged); needs main merged in. |
| #832 | 301 Birth statements rule in the privacy register (E0) | success (b7f66933) | Docs only. |
| #834 | Hub main timing flake fix (pick 304, inferred from the title and card q456) | success (6ae8f06c) | Changes one test file. |
| #818 | Approval links signed by their own secret, one item, once | success (6f45ff2d) | Draft since 10-13; also edits `.railway/railway.ts`, so it is a deploy-configuration PR. Waits on the owner (section 5). |
| leadfuel-core #44 | 300 Oracle terms-line wording (E9) | not read | Docs only; card q458 = A says merge it. |
| (branch only) | 295 `intelligence/oracle-birth-statements` | no PR yet | Last commit 04:00 UTC says gates and the draft PR are owed. |

No branch exists on the hub for picks 287, 288, 289, 290, 291, 292, 293, 294, 296, 297, 298, 302, 303 (branch
names searched, verified). A desk that started and has pushed nothing would not show: **unknown**.

## 3. The 12 points: where each stands

Status words: **DONE**, **PARTLY**, **OPEN**, **UNKNOWN**. The "files" line lists what the work touches so two
desks never edit the same screen file at once (section 4).

### 1. /command is the signed-in home and shows his own data. Status: OPEN (his flip), UNKNOWN in production
- **Done (verified):** the home flag and the beta button (#799); the owner rule (#803); the data readers.
- **Open:** `COMMAND_HOME` is off by default in code; its production value is unknown. The "it is not loading my
  info" question (rows read as zero) has no answer: it needs a counts-only production read per address, and a
  fix if it is an address alias (task not filed; step C13 below). The home should be honest before it is
  flipped, so the flip waits on points 2 and 3.
- **Only the owner:** the `COMMAND_HOME` flip; allowing the counts-only production read; setting
  `COMMAND_OWNER_EMAILS` if it is not set (unknown).
- **Files:** none for the flip; the read fix would touch the command readers in `app.py`.

### 2. Every number is a real reading or a sentence saying why not. Status: PARTLY
- **Done (verified):** #796 (TODAY counts held spend asks; unread never reads clear), #819 and the layers
  (each layer says why it is later), quest `unknown` handling (#822).
- **Open:** pick 288 HELD-ASK-NOTES (held asks and unknown levels stop reading green or absent; six
  findings, N1 N5 N9 N10 F1 F2, taken from the DOORS reviews, which I did not read in full: unverified); the
  spend gate failing open when an account cap is unreadable (task DOORS~SPEND-GATE-ACCOUNT-CAP-FAILOPEN,
  exists, unqueued); the Needs ladder as an honest reader (not filed); the Resources strip and Radar (not
  filed).
- **Only the owner:** queue the spend-gate task; a card on which credits count (Resources).
- **Files:** `command_panels.py`, `command_layers.py`, `app.py` read helpers, `templates/command_screen.html`;
  the spend gate touches `llm_client.py`, `settings_store.py`.

### 3. Action Feed approves, edits and rejects in place; every decision recorded; no double run. Status: PARTLY
- **Done (verified):** the read-only feed (#823); the decision record (#814); approve is person-only (#815).
- **Open:** deciding in place (pick 287, not started); the atomic status change in `_execute_pending_action`
  (today a plain check then write, section 2). The planned home for the atomic change is the follow-up task
  after #818 (VAULT~APPROVAL-LINK-REVIEW-FOLLOWUPS, exists, unqueued), but #818 waits on a secret, so **287
  should carry the compare-and-set itself**. Approval links (#818) are a separate, owner-gated path.
- **Only the owner:** the approval-link secret (credential) for #818; nothing for 287 (card q360 = A allows
  approving on the screen).
- **Files:** `app.py` (`_execute_pending_action` and a new write route), `command_panels.py`,
  `static/command/panels.js`, `templates/command_screen.html`, `static/command/screen.js`. **Screen-file lock.**

### 4. Character: name, computed level, reachable level 2, real trust rings, earned access he can revoke. Status: PARTLY
- **Done (verified):** the Character panel and quest progression (#822, #823).
- **Open:** the recompute and "seen" calls (#829, open, CI green); who measured the voice so level 2 can be met
  (#828, open, CI green); the skill ledger and trust steps so rings stop reading `unknown`
  (INTELLIGENCE~LEVELS-AND-TRUST, pick 253, not started); the rings, regression reason and unlock card on the
  screen (not filed); the standing grant with revoke and a delayed-send hold (DOORS~EARNED-ACCESS, pick 259,
  not started; its hold length is now decided, **10 minutes, card q455 = A**); the retention rule
  (DOORS~EARNED-ACCESS-RETENTION, exists, unqueued); the expiry sweeper check (not filed).
- **Only the owner:** allow a counts-only production read to confirm the expiry sweeper fires (nothing else).
- **Files:** `quest.py`, `model_provenance.py`, `command_panels.py`, `models.py` and a migration for the grant
  table, `static/command/panels.js`, `levels.js`. The skill ledger is a hub-side module and can run beside the
  screen work.

### 5. Every inference about him on a known win is asked on the screen. Status: OPEN
- **Done (verified):** the backend rule and the self-model pass on known wins (#817, q376 = A).
- **Open:** the guesses-to-check panel with confirm, "not me" and skip (pick 289, not started).
- **Only the owner:** nothing.
- **Files:** `command_panels.py`, `panels.js`, `command_screen.html`. **Screen-file lock.**

### 6. Ask answers with citations from a local model or one he names, and never sends local-only rows. Status: PARTLY
- **Done (verified):** the Ask console (#820, off); local-only rows dropped on the phone path (#824) and for
  every caller of `ask.answer` (#833).
- **Open:** five more cloud paths (#830, open) and day summaries' tier (#831, open, red, needs main merged in);
  a model picker (pick 290) and a local model for Ask with a proof that nothing leaves (pick 291, which needs
  the home node's local tier: unverified that it exists). **Cards to post** (not found by a keyword scan of
  q340-q460 in the part-15 draft; I did not re-scan): who may ask (his account or every account), and whether
  the gateway may answer with another model or host.
- **Only the owner:** `COMMAND_ASK_MODEL` (a local name, or a frontier model, which is hub API spend: card
  q383 = A chose a named frontier model, spend-gated, each question sending up to 8 of his brain rows).
- **Files:** `command_ask.py`, `command_console.py`, `static/command/console.js`, `ask.py` and the cloud-path
  modules (`goal_infer.py`, `self_infer.py`, `day_tier.py`, report modules).

### 7. No menu item, strip cell or pane says "stage N" or "not wired yet". Status: OPEN (largest gap)
- **Done (verified):** nothing; the strings listed in section 2 are still on main.
- **Open (no queued task covers these):** shell parity (re-queue the old D3: brain counts on the card, menu
  items that act in place, LEADS reader, Today and Act always on); the Needs ladder; Board (today's plan, goals,
  plans); Crews or Party (one station per arm from `arms.keys()`); Radar; Resources; Log; a Lucid quests
  reader; Studio and World regions.
- **Only the owner:** queue them (the Conductor desk shows D3, D4, D5 as superseded; they need re-queuing or
  replacing); cards for the Crew push from this PC (Law 9) and the credits question.
- **Files:** `templates/command_screen.html`, `static/command/screen.js`, `screen.css`, new reader modules.
  **Screen-file lock; the longest serial chain in the plan.**

### 8. The world keeps his 10-02 picks: globe, all 18 layers, 37 views, Follow. Status: PARTLY
- **Done (verified):** globe, camera and universe (#801); 13 of 18 layers (#797, #819).
- **Open:** the 37 views and Follow with tours (old D5, superseded, large); the last five layers. L02, L08 and
  L18 each need data nobody stores yet (a per-item record, a state history, a ledger of claims); L09 needs a
  decision on which job runs on which line; L14 needs a load baseline (command_layers.py:115-158, verified).
  Because q454 = A did not cut this, it stays in scope. Option B on that card (13 layers, no views) is still
  the cheap path if the week runs short; only he can take it.
- **Only the owner:** decide whether to cut it later; the decisions L09 needs.
- **Files:** `command_layers.py`, `static/command/layers.js`, `screen.js`, new view modules.

### 9. The oracle room works with free readings, the terms line is in place, and it can be switched off. Status: PARTLY
- **Done (verified):** the plan merged (leadfuel-core #39). Cards answered: q387-q391, q457 (the teller's
  name is chosen), q458 = A (use the drafted words), q459 = B (download the larger city list once, with
  credit).
- **Open:** E0 privacy rule (#832, open, green); E9 terms line (leadfuel-core #44, open, docs only); E1 birth
  statements (branch pushed, PR owed); E2 numerology (294), E3 astrology (293), E5 reading faculty (292), E6
  gateway and review (298), E7 the room (296), E4 character families (297), E8 teller and deck art (299, started
  by DESIGN, no PR found). Order is in section 4.
- **Only the owner:** place the terms paragraph in his own terms outline (q458); `ORACLE_MODEL` and the local
  model plus per-reading ceiling (q388 A deferred that to a later card, not yet posted: unverified); the
  commissioned deck spend (later, q390).
- **Files:** E1 to E3 and E5 are new hub modules; E4 and E7 edit the Character panel and the screen
  (**screen-file lock**); E6 touches the spend tables.

### 10. Studio and world intelligence are ready to switch on. Status: OPEN (prerequisites, then his switches)
- **Done (verified):** both lanes are on main and dormant (#791, #792).
- **Open:** Studio findings S6-F1 to F4 (pick 302, not started); World findings S5-F1 to F3 (pick 303, not
  started); declaring the studio door and metering each run into the spend ceiling (not filed); the world
  alerts transport design (ARMS~REACH-SEND-EMAIL-DESIGN, exists, unqueued). Studio and World notes S6-N1, S6-N2
  and S5-N2 are in or beside those tasks.
- **Only the owner:** `STUDIO_GENERATE` with a spend ceiling and the generation platform account and key
  (credential and spend); `WORLD_INTELLIGENCE_PAGE`; cards for alert mail (standing approval, daily ceiling,
  recipient) before any send.
- **Files:** `app.py` (studio and world blocks near :43035-43046), studio and world modules, the door tables.

### 11. Every panel works at phone width. Status: UNKNOWN
- **Done:** nothing found that tests or measures it. The panels' own stylesheet has no breakpoint (verified).
- **Open:** a pass at 375 px wide once the panels are final: render, fix, and add a layout test (not filed).
- **Only the owner:** nothing.
- **Files:** `screen.css`, `panels.css`, `layers.css`, `console.css`. **Screen-file lock; run last.**

### 12. The admin login reads no customer content; his customer view reaches the platform through a connector. Status: OPEN
- **Done (verified):** the rule is decided (q369, the estate reading confirmed 10-13); #803 and the rename
  #821 prepared the words; approve is person-only (#815).
- **Open:** the design task (VAULT~ADMIN-CUSTOMER-SEPARATION: one link, one view switch, a test that admin
  routes read no customer content; exists, unqueued, design only), then a build (not filed).
- **Only the owner:** queue the design; answer its cards.
- **Files:** `app.py` admin and customer routes, `auth.py`, the platform connector code in the MCP repo. Touches
  almost every route; **do not run beside the screen build** without a plan.

## 4. Order, and who may edit which file

**One editor at a time** on `templates/command_screen.html`, `static/command/panels.js`,
`static/command/screen.js`, `static/command/levels.js` and `static/command/panels.css`. The chain, in order:

1. #829 (pick 280, open, green) lands first. It already holds these files.
2. Pick 287, decide in place.
3. Pick 288, held-ask notes.
4. Pick 289, guesses to check.
5. Rings on the screen (new, after the skill ledger and #829).
6. Pick 297, Numbers and Sky families on the character pane (after the oracle engines).
7. Shell parity (re-queue the old D3), then the other dead-menu panes.
8. Pick 296, the oracle room (after the terms line #44 and the privacy rule are merged).
9. Character sheet overlay, regions, the 37 views and Follow, then the phone pass last.

`app.py` is shared by everything (43,000 lines); changes there are small and merged with main first, so it is
not a lock. Everything outside the chain runs in parallel: the skill ledger, earned access, the spend gate, the
cloud paths, the oracle engines, the Studio and World prerequisites, the model picker.

**CI and deploy.** One hub pytest at a time estate-wide; landings queue inside the ci-novahub hold. A merge to
main deploys in about five seconds, so the honesty fixes (points 2 and 3) land before the home flip.

**Waves (rough).**

| Wave | In parallel | On the screen chain |
|---|---|---|
| now | land the open PRs (#825, #828, #830, #831, #832, #834); the E1 PR; leadfuel-core #44; pick 253; the spend-gate task; pick 287 starts once #829 is merged | #829 then 287 |
| next | 288 after 287; 302, 303; 290; E2 and E3 engines; earned access (259) after 287 and 253 | 288, 289 |
| after | E5, E6; rings; retention; sweeper check; Needs, Radar, Resources, Board, Crews, Lucid quests reader | rings, 297, shell parity |
| last | the large items: 37 views and Follow, last five layers, admin and customer build, the phone pass | oracle room, regions, views, phone pass |

## 5. What only the owner can do (collected)

| Step | Kind | Notes |
|---|---|---|
| Set the approval-link secret on NovaHub | credential | Card q384 = B asked a desk to generate and pipe it; a background desk was refused by the worktree guard, so he must say it in the live router's own chat, or set it himself. Whether it is set now: **unknown** (a desk found it absent on 10-13 at 03:0x UTC; unverified since). Unblocks #818 and its follow-ups. |
| Flip `COMMAND_HOME` | production setting | After points 2 and 3. Current value unknown. |
| Name `COMMAND_ASK_MODEL` | production setting, spend if a frontier model | After the cloud-path PRs land. |
| Allow counts-only production reads | production read | The zero-rows question; the expiry sweeper check. |
| `STUDIO_GENERATE`, spend ceiling, platform account and key | credential, spend | After pick 302 and the door-and-meter task. |
| `WORLD_INTELLIGENCE_PAGE` | production setting | After pick 303. |
| `ORACLE_MODEL`, local model, per-reading ceiling | production setting, card | The card is not yet posted (unverified). |
| Place the oracle terms paragraph in his terms outline | his own edit | Card q458. |
| Remove the retired connector switch on Railway | deploy configuration | Card q381; the code part (#816) is merged. |
| Queue the unqueued tasks listed in section 6 | Conductor desk click | Q414 = A covers non-owner tasks in waves. |
| Crew push from this PC, alert mail, commissioned deck | cards | Law 9: each leaves the machine or spends. |

Cards the earlier audit wrote and that I did not find posted (a keyword scan, not re-run by me): the likeness
maker (Q-R1-2), his spoken voice and earcons (Q-R1-3, Q-R1-4), Market and Contracts (Q-R3-1), and which credits
the Resources strip counts (Q-R2-6 with Q-R3-2). Q-R2-3 (undo hold) has since been answered (q455 = A).

## 6. Queue changes: the next 12 tasks to open, ranked

Weight: small, medium, large (estimates, not measurements). "Queued" means a Conductor desk pick exists; it
still needs a desk. "New" means no task exists and one must be filed and queued first.

| Rank | Task | Lane | Why now | Depends on | Weight |
|---|---|---|---|---|---|
| 1 | ONE-INTERFACE-PANELS-DECIDE-IN-PLACE (287, queued) | SURFACE, DOORS review | The biggest piece of point 3 and the owner's most visible gap; carry the compare-and-set itself | #829 merged; #814 (merged) | large |
| 2 | LEVELS-AND-TRUST skill ledger and trust steps (253, queued) | INTELLIGENCE | Makes the trust rings real (point 4); hub-side, runs beside the screen chain | #814 (merged) | medium |
| 3 | SPEND-GATE-ACCOUNT-CAP-FAILOPEN (exists, **queue it**) | DOORS | A gate that fails open is a defect, not polish; blocks Resources honesty and the home flip | none | medium |
| 4 | ONE-INTERFACE-HELD-ASK-NOTES (288, queued) | SURFACE | Held asks and unknown levels must not read green before the home flip (point 2) | 287 (same screen files) | small-medium |
| 5 | STUDIO-GENERATE-PREREQS (302, queued) | DOORS | Cheap and independent; makes half of point 10 closeable | none | medium |
| 6 | WORLD-FLAG-ON-PREREQS (303, queued) | INTELLIGENCE | The other half of point 10; different modules from 302 | none | medium |
| 7 | GUESSES-TO-CHECK-SCREEN (289, queued) | SURFACE, PRIVACY review | Point 5; the backend is merged (#817) | 288 (screen files) | medium |
| 8 | ASK-MODEL-PICKER (290, queued) | INTELLIGENCE | Point 6; lets him name a model without editing config | #833 merged, #830 landed | medium |
| 9 | EARNED-ACCESS steps 2-4 (259, queued) | DOORS, VAULT review | Point 4 revoke and undo hold; hold length now decided (q455 = A) | 287, 253 | large |
| 10 | ORACLE-NUMEROLOGY (294, queued); ORACLE-ASTROLOGY (293) follows | INTELLIGENCE | Pure modules that run beside the screen chain; unblock 297, 292, 296 | the birth-statements PR (295) | medium (astrology large) |
| 11 | NEW: re-queue shell parity (the old D3) as the first dead-menu desk; then LEADS, Needs, Board, Crews, Radar, Resources and Log as separate desks | SURFACE with INTELLIGENCE, DOORS, SENSORS, ARMS | Point 7 has no queued work at all; this is the largest unplanned piece | 288 and 289 landed on the screen files | large (several desks) |
| 12 | ADMIN-CUSTOMER-SEPARATION design (exists, **queue it**) | VAULT | Point 12 needs a design before any build, and the build touches routes the rest touches | none | medium |

Also new and not yet filed, in the order they are needed: the counts-only "not loading my info" read (point 1;
needs his go), the rings on the screen, the expiry-sweeper check (needs his go), and the phone-width pass
(point 11, last).

Already moving and needing a lander, not a new desk: #829, #828, #825, #830, #831, #832, #834, leadfuel-core
#44, and the birth-statements PR. Also not ranked above: the approval-link follow-ups (wait on the secret), the
earned-access retention task (after the decision record), VOICE-PROVENANCE-FOLLOWUPS (small, from the review of
#828), the oracle band E4 to E8 (wait on the engines), D2 ASK-LOCAL-MODEL (waits on the local tier), and the
five `later` layers (large, data nobody stores yet).

## 7. What changed since the part-15 draft

- Merged since then (verified): #826, #827, #833.
- Opened since then (verified): #828, #829, #830, #831, #832, #834; leadfuel-core #44; a pushed branch for
  pick 295.
- Cards answered since then: q455 = A (undo hold 10 minutes), q456 = A (the timing flake), q457 = A (the
  teller's name), q458 = A (terms words), q459 = B (bigger city list), q452 = C and q454 = A (the cards above).
- Two wave-1 PRs (#825, #831) now show a red `pytest` and need a rerun or a rebase; one (#830) is still running.
- The Character write calls (#829) and the voice stamp (#828) are written and green, so the first rank of the
  screen chain is a lander's job, not a build.

## 8. What I verified and what I took on trust

**Verified (read myself):**
- Hub `origin/main` a4371688: `git` history since 0985656e; `gh` for every PR number, state, check result,
  file list and merge time in sections 2 and 6; `gh run list` for the main and branch runs.
- The code at a4371688 for every file and line cited in section 2 (app.py, quest.py, command_panels.py,
  command_layers.py, command_screen.html, panels.js, the stylesheets); the branch names on the hub.
- The Conductor desk picks 250-304 and the task documents named here (existence, status field, source note),
  and the titles, options and answers of Router desk cards q349, q358-q360, q369, q376-q377, q381-q391, q414, q435, q451-q460.
- The part-15 plan and its handoff, and the DOORS review files for #828, #829, #830, #831 (their verdict
  lines and the follow-up lists only).

**Taken on trust or unknown:**
- The DOORS review findings are the reviewers' words. I did not re-run their probes or read the older
  stage reviews (S1 to S6), so the HELD-ASK-NOTES findings are counted from the task text only.
- The oracle plan (leadfuel-core #39) and the audit's STEPS, DECISIONS and OWNER-QUESTIONS files: read by the
  part-15 desk, not re-read by me.
- Every production state: flag values, whether the approval-link secret is set, whether migrations 0012 and
  0013 created their tables, whether the expiry cron fires, whether `COMMAND_OWNER_EMAILS` is set. **unknown.**
- Whether any desk is running on a pick without having pushed a branch. **unknown.**
- Whether the home node has a local model tier that pick 291 can use. **unknown.**
- Phone-width behaviour of every panel. **unknown.**
- Sizes and weights are estimates.

This file changes no behaviour and is covered by no test in this repository (checked: no test or script
references `docs/`). The full suite is CI's.
