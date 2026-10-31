# ROUTER #103 · one-app handoff (ids and status only, 2026-10-30 PT)
Predecessor: router-097.md (#97 local_4faaba43-2587-4976-bf91-f01441277662, archive refused "live work", retry). #103 session: local_e68a7075-052e-4ef6-80f7-e07952ff1411 (slot way-slot-05). Conductors: 054 local_6751ce61-7c3e-45f1-8470-4d404e395fa2, 055 local_113a1094-db34-4ab5-b217-b7ea88dd659e. Code LOCAL ONLY in private estate F:\Leadfuel (never push one-app/*). Owner orders: do everything without questions, stay busy, max parallel, no download without his install-time yes. Re-read live state before acting.

## Owner decisions this session
- q685 B, q686 A (done: User-scope var unset, Machine needs admin), q727 A (v4 approved as MVP base, written by router from his chat), q728 A (Hermes qwen3-64k:4b), q730-q740 answered (workstream under project; panes split side by side overrides q735), q791 A (downloads allowed at install time, answered by owner 21:30Z), q729 open (what looks wrong).
- Two products: chat app first (v4 MVP), a store selling tools/skills later (memory project-two-products). One app, not two: v4 is the design the real app converts to. Hub sign-in block and dark/light toggle of the real app stay.

## Desk branches (worktrees under F:\Leadfuel\.claude\worktrees\one-app-<name>)
int5 05ad79c (merge desk: full suite 2897/23 OK x2, selftest 'hostile' terminal-fixture failure, bisect pending); int6 train (stacking term1 9b91e52, ctx1 40e8425, herm1 84e03a2, cat1 74de636, ren1 0aa8527, cmd1 52f8270, cd1 0bc6a0e), asm1 fb764fb, instrep 552c9c3, gap1 4c1e77a (doc 38), store1 9ebd1aa (doc 39), proof1 007023a, base1 20189fb (doc 41 baseline + convergence waves 0-5), mock4 (mockup v4).
Running at write time (die with this session): v4 update a ae4e14eb2f944f0d4 (hub sign-in footer, theme toggle, hub pane), train a44231cc30aa16c6a, merge/bisect a487b122f456eb694, fix1 a144dadf0a2574186 (CB-29 + search_all), envbk1 a2999839d3c38cab7 (.env backup before write).
## Artifacts
Mockup v4 https://claude.ai/artifact/8H5t8SjFw8bhhjw6uNAzZK (base layer), v3 7j9QGbQDFcE13jBFG92ime, v1 EFT8RRPXxdbPeRrFShpPDL, App Build page WXb79XUAzLZ6GUgKmJEkpw (86 tasks, queue collection), Router desk LzmP6QcxmYh9TdvMMjS883.
## Owed / next
1. Conversion waves from doc 41 to make the real app v4 (UI desks by disjoint files), after int6 is green.
2. After int6: rebuild frozen NovahOS.exe + Setup exe from int6; update ONE-INSTALL-READY with NovahOS name, .env backup (envbk1), upgrade over old Assistant.exe install (open choice: default in-place upgrade), q791 A.
3. Hub / Command Center pane in v4 (ordered); ONE-4 hub MCP entry is built in installer code, never run on this PC, window has no Sign in wiring.
4. LAB owes services.json studio entry (cd1 has a built-in fallback). Core login mockup NOT found (nearest: novahub templates/login.html; owner liked a login 'for core'); ask owner or search chat.
5. Card to post: default look (v1 vs Claude-like); today's app look is neither (navy/cyan/Barlow skin-mockup3.css).
6. Pester installer tests show 4 failures seen on asm1/ren1 (herm1 saw 0): train desk to name them. #97 archive retry.
Rotate only after running desks finish.

## UPDATE 2 (2026-10-30 ~21:00 PT, ids and status only) FOR SUCCESSOR ROUTER #107 (slot 02, 9:50 pm PT)
- DONE since note: int6 5c8920c (2998/23 OK, selftest 140/140, frozen 128/128); int7 cf9ea33 (+envbk1 +dl1 +instrep, suite 2998/23, selftest 140/140, frozen 128/128, Pester 82/0). INSTALL READY, not started: owner runs in ADMIN PowerShell `powershell -NoProfile -ExecutionPolicy Bypass -File F:\Leadfuel\.claude\worktrees\one-app-int7\home-node\RUN-INSTALL.ps1`, types yes once (q792 = A). Mockup v5 published https://claude.ai/artifact/NgpytVzLiRoYMKvGBujuA2 (q729 = C; copy in Document Library). App Build page refreshed (46%, 85.5/187).
- WAVE 1 desks opened (background agents of #103; DIE if #103 is archived: do not archive #103 until they report; their branches are from int7 cf9ea33, worktrees one-app-<branch>): conv1 a0f87c08248226d03 (BP-01, BP-04), conv2 a3d6c6a388ce0ff29 (BP-02, BP-03), ctx2 a858d732b706c0561 (GAP-01,02,03,04,06,07,08,09,10,14,15), shell1 a615a438eae9f7764 (GAP-05,12,13,16,18,19,21,22,23,25,26), shell2 a18585f122e53237a (GAP-24,27,30,31,32,33,55,56,57), code1 aac996f88284bfabd (GAP-11,38,42,43,44,45,46,47), agt1 a17d4887d4f2a954c (GAP-29,50,51,54,20,39,28,40, TP-02), sto1 a5c1ef72b7faa58ab (ST0,ST3,ST5,GAP-35,36,ST9,GAP-37,VO-02,IN-04,IN-05).
- NOT opened (need owner yes or a door): GAP-17 images, GAP-34, GAP-48/49/52/53, IN-02/06/07/08, ST4, ST6, ST7, ST8, ST10, TP-03, VO-01, BP owner yes already given. Wave 2 = merge TRAIN int8 of the 8 branches (conflicts likely in ui/*.js, status.js, panes), one full suite under the heavy lock, then rebuild NovahOS.exe + Setup exe, update install report.
- Open: ROUTER #97 archive refused (live work). Conductor 056 holds router/current. Owner: install run, look feedback on v5.
