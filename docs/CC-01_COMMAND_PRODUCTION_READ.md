# CC-01: one counts-only read of /command on production

Task CC-01 (Command Center Build page, task `cc01`). Done by DOORS one-interface part 114.
**Read only. No code, no flag, no write, nothing sent.** All times UTC; the read ran 2026-11-23 about
20:46 to 20:50 UTC (12:46 pm to 12:50 pm Pacific).

**True source of the go.** The owner typed `go` in this session's own chat after Router desk card q802
was answered A (relayed by ROUTER #110). Until that go nothing was read from production.

## How it was read

- Production host: `leadfuel.cloud` (the NovaHub service's custom domain in Railway, read by name only).
- The owner's own signed-in Chrome, no password typed, no sign-in page touched. Every endpoint answered
  `mode: user`, `scope: mine`, so the read was the account's own map.
- Only the page's own GET reads were called: `/api/command/atlas`, `/layers`, `/views`, `/rail/{memory,
  pending,spend,corpus}`, plus the `/command` page source fetched as text. **No POST was sent.** The
  Ask route is POST-only, so whether `COMMAND_ASK_MODEL` is set was NOT read (see "unknown").
- Output was reduced in the page to state words and counts. This note carries cell counts only: no row
  counts, no source figures, no spend figures, no names, no text a person wrote.
- Finding on the way: loading `/command` in the browser **never reached idle** (three tool calls timed
  out at 45 s and the tab had to be closed), while every JSON read answered at once. Cause not
  established. Likely the screen's own render loop, but that is a guess.

## The counts

| Part of the screen | Total | Live | Dark |
|---|---|---|---|
| Atlas parts | 90 | 18 live, 5 idle, 3 stale | **62 unknown**, 2 planned |
| Layers | 18 | 16 built; 13 read live | 3 built but `unknown` (L09, L11, L18), 2 `later` (L08, L14) |
| Views | 37 | 16 built; 13 read live | 3 built but `unknown` (V02, V08, V32), **21 `later`** |
| Rail feeds (memory, pending, spend, corpus) | 4 | 4 live | 0 |
| Wall | 1 | | `unknown` (one input, "connections", unread) |

Layer note: L02 reads live. L03 is live with one of its four pools (the CI queue) `unknown`.
View note: V08 and V32 say `unknown`; the page's own reason codes are `your_map` (V08) and `owner_only`
(V02, V32).

## The dark cells, by cause

The two causes the card asked for, plus the two the read turned up that fit neither.

**A. Dark because a switch is off (q574): the page states it for one switch only.**
- The place views are "built and off, behind the world page switch" (page text). That is
  `WORLD_INTELLIGENCE_PAGE`. The page does not list which cells those are. **Count: unknown.**
- 2 atlas parts read `planned` ("dormant, gated off, or locked until a level"). The reader does not say
  which switch, so these are **counted here as switch-or-level gated, not proved off.**
- Studio (`STUDIO_GENERATE`), Ask (`COMMAND_ASK_MODEL`), the oracle (`ORACLE_MODEL`) and `COMMAND_HOME`:
  **unknown**. No GET shows their values and the one route that would (Ask) is a POST.
  `COMMAND_HOME` being on is implied only by the page answering at `/command` (taken as a hint, not a read).

**B. Dark because no reader exists.**
- Atlas: **47** of the 62 unknown parts say `no reader yet`.
- Layers: **L08 and L14** are `later` (the plan says each needs data nobody stores yet); L03's CI pool
  says `no_reader`.
- Views: **21** are `later`: V03, V13 to V19, V21 to V24, V26 to V31, V33 to V35.

**C. Reader exists, but the account side is not given it (owner-only or "your map").**
- Layers **L09, L11, L18**: `owner_only` ("the owner's platform view only").
- Views **V02, V32**: `owner_only`. **V08**: `your_map` (no account-side reader).
- Whether the owner's own login sees the platform view (the "bare admin" mode) is not decided by this
  read: every answer was `mode: user`. That is the thing to check before calling these three layers and
  two views dark: they may be lit under the owner's platform sign-in. **Unverified.**

**D. Rows exist, but the source declares no freshness budget.**
- Atlas: **15** unknown parts say `no budget`. A reader exists and rows exist; the part declares no
  budget, so nothing can say when it is late (`account_atlas.py`, "unknown, no budget, with the numbers").
  This is neither a switch nor a missing reader. It is a missing declaration, cheap to close.

Arithmetic: 47 + 15 = 62 unknown atlas parts. Cells with a named cause: 62 + 2 + 3 + 2 + 3 + 21 = 93
across atlas, layers and views, plus the wall and one pool. Nothing is counted twice.

## What this changes in the plan (`docs/COMMAND_COMPLETION_PLAN.md`)

- Point 7 ("no cell says stage N or not wired yet") is **partly met on production**: the page text has no
  "stage N" and no "not wired yet" (0 matches each). The remaining dark cells say `later` or `unknown`
  instead. The plan's section 2 list of dead strings is out of date against production.
- Point 8: production shows **16 of 18 layers** built (the plan says 13: L09, L11 and L18 now answer, as
  `owner_only`) and 16 of 37 views built, with 21 views still `later`.
- Point 1: the screen answers signed in with the owner's own map and live rail feeds, so the "not
  loading my info" worry is **not reproduced for the rails or layers** on this account. The atlas still
  leaves 62 of 90 parts dark.

## Verified and not verified

**Verified by me, on production, 2026-11-23:** every state word and count in the tables above, from the
JSON the page itself reads, answered `ok` with `mode: user`.

**Taken on trust:**
- That the Chrome session is the owner's own account (the read did not call an identity endpoint; the
  route's rule is that the session is the only subject, and the task said the owner's own account).
- The meaning of `planned`, `no budget` and `owner_only`: read from hub source on this PC
  (`account_atlas.py`, `command_layers.py`), not from the deployed commit. Production may differ.

**Unknown:** every flag value (section A), which views the world switch hides, whether the owner's
platform sign-in lights the owner-only cells, why `/command` never reaches idle in the browser.
