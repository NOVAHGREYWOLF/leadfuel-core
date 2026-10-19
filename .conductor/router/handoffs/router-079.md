# Router handoff #079 -> #80 (successor title ROUTER #80 · one-interface) (2026-10-19 ~22:4xZ UTC, ~315k, 6 desk agents running)

ROUTER #79 = local_ace81e74-8551-4bf2-966d-5c3a42acfae9 (slot way-slot-06, NOT archived: hosts the agents below, they die if it is archived). Predecessor #75 = local_dd534bdc (open: hosts LANDER-926, LANDER-928; archive through the gate when both report; its cron is gone). #73 archived. Conductor 048 = local_a3a6cdcb-1d6c-49bc-a604-89c3451e3942. Launcher local_a6ce3e66-858d-46fe-a6e7-f3f6e50a83d7. Cluster routers: #76 local_a2da990c (SURFACE rows), #77 local_073551bc (DOORS/INTELLIGENCE rows), #78 not launched. Board A4uS9xn1emqupohdE4DUfV: router/current (get with out_dir ONLY, key base_layer_doc), router/roster79 (my full log, v26+), router/spoke_audit_79 (private gap list). Router desk LzmP6QcxmYh9TdvMMjS883 (cards in `questions`, owner items in `needs`; next free card q593). State lines are mine: re-read them.

## Running (background agents hosted by #79; wake by agent id; do not rotate-archive while they run)
SIGNAL-FIX af354e8ac2fe49988 (ARMS 71), REACH-FIX aa1ed9ba5126673b2 (72), SCOPE-FIX aa55f18325e122bfe (73), ORBIT-FIX a8fd1b1a443cbcb5d (74), ODYSSEY-FIX a633f48e12cef2919 (75), DOSSIER-AUTOAPPROVE-FIX ad860e466ec0e9a89 (DOORS 76). Each opens a DRAFT PR and does not merge. LANDER-944 a5cafd8bb93944a0f (hub #944, gunicorn access log; CONTINUING, ticket last in ci-novahub.wait: RESUME it when its ticket nears the head).

## Owner answered (cards read by me, routed notes written)
q583 A, q584 A, q585 A, q591 A, q592 A = picks conductor records. q586 B, q587 A, q589 B, q590 A sent to #76 (hub #932, #939). q580 A: odyssey #56 merged 24dbe3e; odyssey #58 draft adds OWNER_EMAILS preserve() (deploy config: not merged, owner looks). Needs items all clicked Go (intent only per conductor ruling: no typed go): echo-nc-owner-emails, hub-929-level-gate-enforce, hub-930-cesium-download, hub-939-dossier-ask, odyssey-owner-emails, read-live-auto-approve-list.

## Next
1. As each fix desk reports: verify the PR with gh, send a DOORS read-only re-review (Opus) per fix, then a lander (ci-<repo> hold, merge main in, CI green on exact head, squash).
2. Open when a slot frees: q585 desk (code-only check of four safety switches); after #944 merges: q592 DOORS desk; after the q591 fix lands: q583 INTELLIGENCE wiring desk.
3. LEVEL_GATE_ENFORCE: after hub #929 merged and deployed (#76 tells me), confirm card, NODE railway desk, owner types go in that desk's chat.
4. Archive #75 through the gate when LANDER-926 and LANDER-928 report. Tell the conductor/launcher when you claim.

## Owed / gotchas
ARMS/NODE rows cc56 cc60-65 cc15 cc24 cc32 cc50 cc70 cc99 are held by me (conductor ruling); start only owner-queued rows. Session cron 353405e9 (19,49 * * * *) is MINE and session-only: CronDelete it from my session before I am archived; create your own. Hub test queue is the bottleneck (one pytest at a time; ci-novahub.wait 24 tickets, 13 old no-PR tickets unconfirmed, I moved 12 moot ones to ci-novahub.pruned). Doc folder F:\Leadfuel\Important Documents is PRIVATE: path only, doc 01 The Spokes is the base layer. Stop hook false-positives on the word handoff in board writes; real size by get_usage.
