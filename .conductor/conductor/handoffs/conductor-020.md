# Handoff: CONDUCTOR · system build, 020 (2026-10-07 ~19:50Z UTC, rotating at ~300k)

Ids only (public repo). This session: local_042c7286-d308-454d-8efb-acbde8deb52e, branch claude/conductor-020. Pages: Conductor desk MKAx49RAskZ3cV7f2EkDMF, Router desk LzmP6QcxmYh9TdvMMjS883, Build Board A4uS9xn1emqupohdE4DUfV (router/current). Tick cron cd4f8b1b was CANCELLED by 020 before rotating (so two conductors never tick at once): re-create at minutes 13,43 (prompt as in 013's note). 020 stays open, does nothing, until 021 is titled and filed and archives it. Cards: start at n >= 347 (q346 open); picks: decided_at > 2026-10-07T18:16:55Z.

## Done (verified by me unless marked)
- Archived 019 (local_1a4942ec) through the gate. Kept conductor 005 (local_083bdfe0) and ROUTER #11, #12, #13.
- Owner note on q344 ("HAVE A DESK DO THIS", 18:16:55Z): filed NODE WAY-INSTALL-0.1.8 + pick rank 235. ROUTER #29 ran it; I read installed_plugins.json: leadfuel-way 0.1.8, sha b92f65c57. Pick marked done. Live behaviour of 0.1.8 in a new session: unverified by anyone.
- Filed UNQUEUED from #29's relay, after reading the DOORS review file F:/Claude Sessions/handoff/one-interface-doors-review-s5-s6.md in full (PROVED lines are the reviewer's, not re-run by me): INTELLIGENCE WORLD-FLAG-ON-PREREQS, DOORS STUDIO-GENERATE-PREREQS, ARMS REACH-SEND-EMAIL-DESIGN. Task counts read back: +1 each, none else changed. Did NOT read the s3-fixes review file.

## State (re-read before acting)
- Router #29 local_46ddffce was status "rotating" (hit 300k ~19:31Z): handoff router-029.md pushed 6270c21 on claude/router-29; branch claude/router-30 exists at 6270c21. No ROUTER #30 was live in the ROUTER group at 19:4xZ (owner pastes). #28 local_efc92f9b and #27 local_dc4fea43 still open for their agents.
- Per #29 (gh/ls-remote-verified by it, taken on trust by me): hub #793 S1 landed 82513aea65, #791 S5 landed 3e428cd915, #794 S2 landed 8a2ffa9b; #792 and #795 in fixes (S6 3/3, S3 4/4 agents).
- q344 routed; q345 routed (B); q346 (title wording A/B) open. GROUP-BY-PROJECT stays open until q346 is answered.

## Next
Run the tick. When ROUTER #30 is live (router/current session_id and the ROUTER group), brief it only if something is new. File only owner answers that create new work.

## Owed
- Owner: queue SUITE TEST-ISOLATION? Asked three times; "KEEP GOING" is not a yes. Flake keeps reddening hub PRs. On yes: pick SUITE~TEST-ISOLATION (re-get desks/suite first), brief the live router.
- Owner: queue COUNSEL PHOTO-STORE-WORDING? Same. Owner: q346.
- Sends to #29 this turn: 2, both delivered (read receipts unconfirmed).

## Gotchas
- Bash tool halves backslashes: use Write for files; os.path.basename in python.
- router/current is ~150 KB: get with out_dir, then extract with python. ArtifactData update merges nested keys; pin if_version; compare counts afterward.
- PowerShell cd persists: return to the main checkout before archiving a worktree. Use PowerShell for git/gh.
