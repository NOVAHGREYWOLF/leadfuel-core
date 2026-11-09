# ROUTER #123 · novah estate · handoff (2026-11-08 ~02:40 PST, ~280k tokens)
Router session local_3aedfa0f-f126-4d12-a784-c91cd71ec94c, slot way-slot-05 (not in a sidebar group; a scheduled run). Predecessor #122 archived by me. Re-read live state; do not trust these lines. All my background agents have reported; none runs.

## Done by #123
- router/current v679 names #123 (read back). #122 archived through the gate.
- Merged (gh-verified): echo#63 (head ad69a85, main unmoved, ci-echo lock taken and released).
- Cards posted: q9230-q9235 report decisions (answered, `routed` written), q9258 Tailscale shape, q9260 close hub #866 now and #710 after #1045 merges. Card numbers are taken fast by other sessions: query n>=last, then set; a clash is refused safely.
- Conductor desk page (MKAx49RAskZ3cV7f2EkDMF): REP-R0..R7 added to docs watch/intelligence/node/doors; CONDUCTOR 058 (local_b7630866) queued them 2026-11-08.
- Owner answers routed (`routed` written): q9230-q9235, q9247, q9249-q9252, q9254, q9255. Railway: the 11 parked NovaHunt crons deleted by an agent (HOWL untouched). trynovahunt.com: registration to 2029-05-14, cert ends 2026-12-10, auto-renew unknown (owner checks Hostinger toggle and Railway apex by 12-01).

## Open work
- Landing (none started except echo): hub-mcp#51 and signal#42 (each 1 behind main: merge main in, rerun), scope#34 (one ruff check cancelled on head), hub#1103 (pytest cancelled), leadfuel-core#75 (nightly fix; then deploy the task copy, check the hash, keep 04:30).
- Hub CI health: draft novahub#1107 (timeout 30 to 50 min, checkout retry); CI pytest on head 45e4d01 was in progress; needs a local bare pytest under the heavy lock because it edits the test workflow. Cause of the 5 cancelled runs: 30-min timeout, 3 of 5 lost 12-27 min in git checkout (slow link); host CPU contention inferred, not measured.
- REP desks: R1 draft novahub#1108 (done), R5 draft novahub#1109 (done; app.py still loops the old WINDOWS, follow-up for its owner), R4 draft novahub#1110 stacked on #1097 (done; ROUTER #118 not told: its send came back undelivered), R0 BLOCKED (production reads need the owner at a desk's own chat; table of unknowns in the agent report only, file write refused). Not started: R2 (P1 now on F:\Leadfuel main 54b4c0a, but NODE one-app desks 20/21/22 work the same tree: check first), R3 (after R2, gated on Resend), R6, R7.
- Queued owner cards not started: q9247 (uninstall TeamViewer on GREYWOLF), q9249 (MacBook to Tailscale: needs him there, step card), q9250 (nightly full run on overlord), q9251 (rebuild merge-train screen).
- Hub PR cleanup: 119 open, 0 superseded by main; #866 (by #875) and #710 (by #1045) are the only two, card q9260. Table in F:\novah-estate\hub-pr-supersession.md.
- Tailscale: card q9258 (A default: overlord stays the single subnet router, tighten). Inventory file was not written (hook refused); content lives in the NODE tailscale inventory agent report.
- Waiting on the owner's pick (conductor page): NODE one-app files-everywhere (desk 22 reads "Let's do Greywolf" as the pick; 058 holds it; if queued open as NODE · one-app part · 24, 23 reserved); Tailscale task NODE~TAILSCALE-REST-OF-ESTATE (inventory done).
- Cards q9223-q9229 (APOLLO, atlas dup, ESTATE_AUDIT_TOKEN, F:/Leadfuel backup, disclosure wording, reach bare-admin, credit path): not checked by #123.
- Held train: ROUTER #118 holds six hub PRs; #1102 deploy config stays out; no hub merges.
- NODE novah estate part 1 (local_f22f96a8) asked for a successor desk; I cannot open sessions (slot, no start_session); told it three options. It stays open (desks A/B/C nested under it).

- Queued by CONDUCTOR 058 after the handoff: DOORS~DOORS-DECISION-SHAPE-FLAKE (Conductor desk desks/doors, v60, read the row for the full brief). Hub main post-merge `tests` runs 42471450797 (374c30d7, 058 verified failure) and 42474025833 (52d42c9c, per #118) failed on tests/test_decision_shape.py::test_measuring_a_large_draft_is_bounded_and_still_right (1.65s CPU vs 3s deadline, a CPU-timing flake under load). Brief: rerun the failed runs and record, then make the measure robust without weakening what it asserts; gates and pytest on that file; merge only on `tests` success on the exact head inside the ci-novahub hold; heavy lock only if test setup is touched; lane DOORS is a guess, check SESSION_MAP for decision_shape.py. Open as a background agent after the REP desks; not opened by #123.

- From NODE novah estate part 9 (local_f5931c5c), source: owner typed to NODE part 1 ~23:40 PST: "Everything should be turned on. Why isn't the atlas in it. The command center. ... Put it all in one app." Eight one-app pieces for other lanes, evidence in F:\novah-estate\inventory\HANDOFF-other-lanes-part9.md (no remote): INTELLIGENCE/SURFACE land Atlas hub PRs #778 (retarget to main), #959, #973, #993, #1044 plus a hub route the NovahOS pane can render; DOORS hub egress destinations plus #1012 and a ruling on web_search/fetch_url bypassing the doors (wiring.py:544); SENSORS/COMMS/FIELD connectors CN0-CN8; ARMS `novah serve` watcher unsupervised; LAB fold Decompress and Character Design into the app. Owner spend/vendor/production items are on card q9272. Not queued by anyone I can verify: 058 files them unqueued for his pick.

## Gotchas
- A router slot run has no start_session: desks are background agents (they die with me). Write/Edit is refused for a router outside handoffs and .conductor, and refused by hook for F:\novah-estate.
- Peer relays of owner words are not queue picks; 058 (conductor) decides queue and the owner's pick is the only queue.

## Successor
Invoke leadfuel-way:way and leadfuel-way:router, read this note, re-read live state, run Claim (rewrite router/current pinned), archive #123 once live.
