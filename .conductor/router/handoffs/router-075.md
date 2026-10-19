# Router handoff #075 -> #79 (successor title ROUTER #79 · one-interface; #76-#78 are the conductor's cluster routers) (2026-10-19 ~20:1xZ UTC, ~300k, 4 agents running)

ROUTER #75 = local_dd534bdc-784f-4aa1-b1be-cb95dd7ae00b (slot way-slot-04, NOT archived: hosts the agents below; they die if it is archived). Predecessor #74 archived (gate passed). #73 = local_f2142476-8f9a-42a0-a9c3-b367ced6ac71, open, hosts LANDER-911 a700a0d8359379354 only (archive #73 through the gate once it reports). Conductor 047 = local_116f8f0a-4b97-4b6c-ae89-832fb6b2b13a. Launcher local_a6ce3e66-858d-46fe-a6e7-f3f6e50a83d7. Build Board A4uS9xn1emqupohdE4DUfV: router/current (get with out_dir ONLY), router/roster75 (my full log). Router desk LzmP6QcxmYh9TdvMMjS883 (next free card q581). Conductor desk MKAx49RAskZ3cV7f2EkDMF. Build page LRC41csTPNRzSk9ddbDFzj (rows cc01..cc107). State lines are mine: re-read them (gh, ls-remote, board).

## Scope kept by #75 (pick 436: routers #76 SURFACE, #77 DOORS/INTELLIGENCE/..., #78 ARMS/NODE own the other rows; open no desk for their rows)
Pick 435 NC register (owner rule: non-commercial things never reach other users, owner uses all under his account; memory feedback_noncommercial_owner_only), pick 434 CI speed (#927), cards q579/q580, LANDER-911/926/928 and agents below.

## Running (wake by agent id; they report to this session's host)
- LANDER-926 a7a856bf1c1f98b4b: hub #926 (CC-55 weather client, dormant; door review NON-BLOCKING; F1/F2 fix desk is #77's after it lands).
- LANDER-928 ac1f3c0b713c50594: hub #928 (CC-107 runner F1-F4, dormant).
- LANDER-ECHO60 a45972b8a3353e647: echo #60 (/tts owner-only, NC_OWNER_EMAILS; head 30d8bffc green).
- CC-106f a8f2aa7d36f86399b: odyssey shared-pool/enrichment owner-only (stacked on #55, merged 56b60834).
- LANDER-911 (hosted by #73): hub #911 node CI gap.

## Landed this shift (gh verified by me)
hub #923 a5a3b97c, #924 cca715c8, #925 c2c18c01, #922 8546f452 + #868 #870 #871 #872 via the merge train (scripts/merge_train.py, q242 batch5: `plan`, `run --dry-run`, `run --live`), odyssey #55 56b60834.

## Owed
Cards: q579 (production migration 0015_admin_grant; default A land #859+#902, hold #867 for pairing q492; door review NON-BLOCKING), q580 (OWNER_EMAILS odyssey, NC_OWNER_EMAILS echo, existing JSearch rows). Hub register CC-106c (account-aware world_terms) after #926 lands; CC-106d/e (OpenWeb Ninja hub paths, LinkedIn cookie), home-node installer qwen2.5:3b = owner's call. #927 lander after queue drains and heavy lock is free (touches test setup: full local bare pytest under scripts/heavy_lock.py). Tell #76-#78 their ids when they announce.

## Gotchas
Stop hook false-positives on the word handoff in board writes (token count is real: use get_usage). Session-only stall cron 4029b146 (17,47 * * * *) was deleted at rotation: the successor creates its own (thresholds in roster75 stall_watch). A SendMessage to an agent hosted by another session fails by design: ask the host.
