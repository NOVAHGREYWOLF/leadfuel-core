# Router handoff #033 -> #034 (2026-10-11 ~09:40Z UTC, soft cap)

ROUTER #33 is local_62d2f0c7-2aa1-4238-90ab-c6e6d9cb5144. Ids only. Board router/current (A4uS9xn1emqupohdE4DUfV) keys log_33*, agents_33*, agent_reports_33* supersede this note. Router desk LzmP6QcxmYh9TdvMMjS883, Conductor desk MKAx49RAskZ3cV7f2EkDMF. Live conductor local_15c2bd8f-1b42-4107-a41f-3e4121f62c57.

## Done by #33 (each re-read by me)
- Archived #32 and #30. Routed q348-q352 (q352 = A). Hub main 4a9c3c28 at 09:16Z.
- Running background agents (mine; they die if #33 is archived, reports come to #33): DOORS D1 part 2 a341a8af4280a6cd2 (branch doors/owner-sees-estate), SURFACE D2 part 5 aae9e1196a1382a66 (surface/camera-universe), ATLAS-INVENTORY-HUB 3/3 abe493da287de0d78, HOME-BETA-BUTTON affceef82a799e649, repo/PR/CI sweep a24d6b4b973c14392 (report F:/Claude Sessions/handoff/router-33-repo-sweep.md).
- Session sweep DONE: F:/Claude Sessions/handoff/router-33-session-sweep.md (read sections 0 and 9).

## Next
1. #33 stays open until its agents report. Then read the repo sweep, decide capacity (the bottleneck is the single heavy slot, not desk count).
2. Open desks only for queued picks (choice now, not done: 314; my name match: 75 look done under merged PRs, 8 open-only, 231 no PR). Send the 75 to the conductor to confirm.
3. D3 (rail, top bar) is NOT queued: the conductor asks the owner. VAULT review agent when D1 has a PR. Land PRs inside the ci-novahub hold.
4. 19 sessions wait on owner decisions (sweep section 6): one batch of cards.

## Owed
Cards q208, q294 open. Time-critical: the LeadfuelBackup task runs 03:30 local 10-11; last result 0x80070002, C:\LeadfuelBackup holds only the script (read 02:32 local); owner and NODE desk local_b43f0db0.

## Gotchas
ArtifactData list without out_dir floods context (picks = 336 docs): use out_dir then python. Git paths with a colon need MSYS_NO_PATHCONV=1. Sends since owner typed: 1 of 10.

## Board and context (added ~10:05Z, owner: 'make the router bigger or put this context down')
- Board router/current was 228 KB and 432 keys; it is now 49 KB and 139 keys. 294 history keys (incarnations up to 31) were MOVED, intact, to router/archive_pre33 (read back identical). See key board_note_33.
- What filled #33 fast: the Artifact tool schema loaded twice by ToolSearch (use ArtifactData only), printing the 336-pick list, whole-board key dumps, whole sweep reports. Rules for #34: read board keys by name with python; send any read wider than one page to a read-only agent that writes a file and returns 12 lines; never print directories.

