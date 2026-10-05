# Router handoff #020 -> #021 (2026-10-05 ~18:3x UTC, ROTATING at ~300k)

ROUTER #20 is local_461fe4e9-f058-4b89-820e-a0572ea4a3d6. Ids only. Re-read live state before acting.
Board router/current (A4uS9xn1emqupohdE4DUfV) v133+. Router desk LzmP6QcxmYh9TdvMMjS883, Conductor desk MKAx49RAskZ3cV7f2EkDMF. Conductor: CONDUCTOR 012 local_6247b62d-5a37-42cb-a10e-696b39866996.
PRIVATE detail (trains, wake-on-merge list, archive candidates, owner steps): F:/Claude Sessions/handoff/ROUTER-20-inbox.md. Read it first.

## Owner rule
CLOSE FIRST still in force; held new work is listed in the private file.

## Done by #20
Claimed v105. Cards q259-q277 posted; q259-q276 answered and routed (q276 = #711 held; owner wants 6 AM in his current zone). Train A merged 16:51Z (#709 #749 #750 #751 #758), hub deploy SUCCESS + healthz 200 (verified). Closed core #7, #3. Archived through gate: 10 sessions incl. ROUTER #19 (list in private file).

## Live desks
MERGE-TRAIN 2/2 local_3bac496f (holds ci-novahub; at its send cap; last turn died on a TLS error, resume sent 18:1xZ). ATLAS-DOORS 2/2 local_7f51a9c4 (opened by #20 on q275=A; my side session: detach before archiving me).

## Next
1. Card q277 (open): hub runners crash-looping (restarts 158/84, verified); all hub tests pending since 16:52Z. On A, open a NODE desk.
2. Read MERGE-TRAIN with list_events; wake the desks in the private file as their PRs merge.
3. Archive the archive-ready sessions through the gate.

## Gotchas
- SendMessage: full local_ ids or exact names; 10-send cap per owner message.
- The way hook refuses router edits to SESSION_MAP; give it to a desk.
- A TLS outage ~16:5x-18:1x broke gh and the API for some sessions.

## Late (18:3xZ)
- Owner via CONDUCTOR 012 (~18:25Z): "fix the runners now, it counts as finishing. do run them on git. we will pay if we have to". q277 = A in effect.
- Chip task_9c427e70 "NODE · CI-RUNNER-CRASHLOOP 1/1" posted (Opus) and waits for the owner's click. When it is live: title, file in NODE, set the model, verify.
- NOT opened yet: NODE CI-HUB-HOSTED-TESTS (hub tests on ubuntu-latest with self-hosted fallback; no secrets on the hosted path; passed=true, never steps=0; if minutes run out, an owner card for the billing cap). Open it next.
