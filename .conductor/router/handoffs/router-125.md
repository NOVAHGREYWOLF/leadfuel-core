# ROUTER #125 · novah estate · handoff (2026-11-18 ~13:10 PST, ~305k tokens)
Session local_b62e2a02-a00f-4a64-bddb-0870632a9e81, slot way-slot-05. Predecessor #124 archived. router/current v684 names #125 (router field fixed). Re-read live state; these lines are agent reports unless marked verified.

## Done (verified by me unless noted)
- Cards routed: q9274-6, q9280, q9228, q9229, q9281, q9299 (routed written). Part 10 archived (handoff F:\novah-estate\HANDOFF-one-app-part-010.md, estate repo local-only).
- Hub PR 1111 merged (f1d315c5, verified gh). hub#1099 (ARMS brain fix 6, local_cc5e1d51-8811-4b88-898c-f9cbf205b122) waits on CI run 42925014471: when green and main unmoved, ping it to squash. Not re-checked since.
- Draft PRs from agents (none merged): hub 1112 (q9229), reach 49 (q9228, stacked on 48), hub 1114 (local Fieldy, q9438), hub 1115 (web_fetch door, stacked on 1012, q9434), hub 1116 (model_pull door, on 1012, q9441), hub 1117 DOORS memjobs scope, 1118 VAULT node check, 1119 INTELLIGENCE W3-02 stack (q9440). 1117/1118/1119 pytest red: all three fail tests/test_command_rungs.py::test_no_test_names_it_is_an_empty_list (probably already broken on main, unchecked; main's last green tests run 2026-11-11); 1119 also fails price-table, GDPR guard (PRIVACY q961, deliberate), retired-knowledge tests. CI runners are up on ci-vm (VM 102); heavy_lock.py reads local docker (known, only blocks local full runs).
- Estate-repo local branches (push disabled): one-app/files-everywhere 3d59fff (Files v1, card q9299 A = wait), node/q9442-q9443-fetch-hooks eeea708, node/q9443-review2-fixes d616399 (review 3: enable ok with conditions), doors/model-pull-q9441 0a19de8, node/p10-memjob 392534b (held).
- Private mockup (PRODUCT onboarding): https://claude.ai/artifact/UH4h3VSm16FiFhZuriUU1T. PRODUCT part 4 PR leadfuel-core#76 (handoff only).

## Running when written
Agent aa5a5b287311b0a40 (hooks review-3 fixes F1,F2,F4,F5,F3 on a new branch from d616399): it dies with this session; if no report arrives, reopen from the review notes in the scratchpad (r3_probe_a/b).

## Owed
- Hub: sort the shared red test; merge order 1012 -> 1115/1116; 1117 -> 1118 -> 1119; then NODE merges 392534b. own_node egress door needs the owner's P1 answer (docs/NODE_RELAY_CONTRACT.md s10). PRIVACY must list memory tables.
- Unrouted owner answers with no desk: q9223 B, q9224 X, q9225 B, q9226 X, q9227 A (blocks hub#1105). Unanswered: q9321 (retire 15 sessions), q9306-q9320. IDENTITY desk (q9286 A) needs a SESSION_MAP lane. Design-note copies in scratchpad product-multi-user-ans-11-10 need a diff and copy into F:\Claude Sessions\product-multi-user\. Reach brief B (19 group B routes) owed. Wake-pass finding: 71 cards UNDELIVERED, 16 HELD (NODE part 11 reported; unchecked).
- Part 11 (local_674b6e47) is at about 334k and has a pending successor proposal task_9aa1ec8a; do not wake. q9438 (Railway flag) must NOT be set. Unopened picks: REP-R0/R2/R3/R6/R7, TAILSCALE, EVERYTHING-ON other-lane pieces, phone Files panel.

## Gotchas
ArtifactData get only, with out_dir; a background agent cannot message the router (its final notice is the report); start_session absent in a slot run.
