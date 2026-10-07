# Handoff 001: SURFACE · command center nav button (desk, opened directly by the owner, no router brief)

Session `local_9c29f80c-c0d6-4274-9b81-b09af65a7741` (short ref changed on resume). Model Sonnet. Group SURFACE.

## Done
- novahub #707 merged as `073f802` (2026-10-02, deploy success per GitHub deployment 6803523697). Nav link "Command Center" in `templates/base.html` (desktop nav + mobile drawer), pointing at `/goal` (`goal_workspace_page`), shown when `account.logged_in`, hidden from anonymous. `tests/test_nav_command_center_link.py`, 9 tests.
- Owner, direct (2026-10-02): leave `/goal` alone until the real command center exists; the real one is ONE page, customers scoped to their own estate, owner as admin gets the same page plus superuser powers. Build handed to ROUTER #8; desk `INTELLIGENCE · command center per user` (1/1 handed off; 2/2 live 2026-10-05).

## UPDATE 2026-10-07 03:50Z: STOOD DOWN, the repoint is carried by CC-ROUTE-MOVE (supersedes everything below)
Successor session `local_9ec7acd5-fe31-4f8b-af7f-0610e6348c35` (Opus). It archived the predecessor (handoff 17d0fcc pushed and verified, checkout clean).
- **Do NOT build the "Next" below.** `SURFACE · CC-ROUTE-MOVE 1/1` (`local_e137f345-6bd6-47cb-8e18-e6ae2a4fffcc`, ROUTER #22's task, owner q263 = B) already has it in commit `5c1f3fd`. Its branch `claude/affectionate-sammet-a9c442` is at `93d1c7f`, which I verified on the remote with ls-remote. I read the diff myself. Both `base.html` links now go to `url_for('command_center')` with `nav_active == 'command_center'`. In the test, `GOAL` is now `href="/command-center"`, and the anonymous-hidden, nav-saw-the-account and bare-admin tests are kept. A customer GET of `/command-center` asserts 200 through `_get`. It also adds tests that `/goal` is gone from the nav and that a bare admin goes 302 to `/admin/wall`.
- A second nav-only PR would change the same lines and the same test file. That is exactly the duplicate work the standing rules forbid.
- Live state at 03:50Z, verified by me: novahub main `5c2218f`; main `base.html` still points at `goal_workspace_page` (lines 62, 103); endpoint `command_center` is on main (app.py ~16703). CC-ROUTE-MOVE has no PR yet. It is waiting on the heavy slot for its full run and on whether to open the draft PR on targeted tests (73 green).
- **This task is done when CC-ROUTE-MOVE's PR lands on main.** Nothing else is owed by this desk. ONE-PLACE-SHELL (#776, `one-place-shell` at `7354660`) also touches the base.html nav. Per that desk's note, whichever lands second rebases.

## UPDATE 2026-10-06 21:30Z (superseded by the one above)
- **#713 IS MERGED**: `7d0c8347ecea264f3ff5abe05a1223832b55ab54`, mergedAt 2026-10-06T00:58:18Z (verified by me with gh). Main was `5c2218f` at 21:27Z. The build desk's promised message never reached me; do not wait for it. So the blocker is gone and the repoint is now the live task.
- **No successor was ever opened.** I have no start_session tool; the owner has the paste prompt.
- **CAUTION, read first:** a SURFACE desk `CC-ROUTE-MOVE 1/1` (session `local_e137f345-6bd6-47cb-8e18-e6ae2a4fffcc`, novahub worktree `affectionate-sammet-a9c442`, branch `claude/affectionate-sammet-a9c442`) exists and its task moves a command center route. I did NOT read its brief or scope. Before editing `templates/base.html`, confirm on current main that endpoint `command_center` still exists (a route move may rename it) and ask that desk whether it touches the nav links or my test. SendMessage by `local_` session id delivers; by name it may be held.
- Heavy jobs now seem to use a "heavy slot" (see that desk's transcript, COMMS held it 2026-10-06). Re-read the CURRENT lock protocol in `F:/Claude Sessions/.locks/README.md` and `WORK_QUEUE.md` before taking or queuing anything.

## State (re-read before acting) -- as of 2026-10-05, partly stale
- Verified 2026-10-05 08:23Z: novahub #713 (`feat/command-center-per-user`, `GET /command-center`, endpoint `command_center`) OPEN, draft, last updated 2026-10-02T17:24Z. Main was `46d1a47`.
- Read: VAULT reviewed, no blocking finding, all findings closed. PRIVACY pass is second-hand (recorded in a PR comment by that desk). Its red checks are cancelled unlocked runs; it still needs one full CI run inside the `ci-novahub` hold.

## Next (one step)
When #713 is on main: take a worktree on novahub from fresh `origin/main`; change both links in `templates/base.html` from `url_for('goal_workspace_page')` to `url_for('command_center')`, `nav_active == 'command_center'`; update the test (GOAL constant -> `href="/command-center"`, keep anonymous-hidden, the "nav saw the account" proof, bare admin sees it) and add a real GET as a customer returning 200. File a wait ticket in `F:/Claude Sessions/.locks/ci-novahub.wait` BEFORE opening the PR. Then `gates.sh --fast`, CI green on that tree, re-check main, squash, release, message the build desk and the owner.

## Owed
- A message from `INTELLIGENCE · command center per user 2/2` when #713 merges, with the merge commit. CONFIRMED by their reply on 2026-10-05: they will not touch the nav block or my test file; #713 waits only for the `ci-novahub` slot (3rd in queue, WATCH holding it then); main merged in locally, unpushed. No owner decision pending for me.

## Gotchas
- Do NOT repoint before #713 merges: `url_for` on a missing endpoint 500s every console page.
- `/pricing` passes no `account=` to `base.html`; test the nav on `/knowledge`. A bare admin has no email: gate on `account.logged_in`.
- `gh`/`git` in the shared novahub checkout can take over 100s under load: run backgrounded, read the output file.
- Opening a PR or pushing fires CI: take the lock first (I did not, on #707).
