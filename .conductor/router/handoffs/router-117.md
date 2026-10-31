# Router rotation #117 -> #118 (title ROUTER #N · one-interface), 2026-10-31 PT

ROUTER #117 = local_4345342f-9040-4bc4-8a1f-04a6e22ac69e (way-slot-04), holds router/current (Build Board A4uS9xn1emqupohdE4DUfV; roster router/roster117; ArtifactData with out_dir). Conductor 057 local_acc328d8-44cd-4180-afc4-4b56434d067f. #112 archived. Part numbers from 177. Stop opening desks at weekly all-models >= 88% (resets 2 pm PT).

## Done
Claimed; cards q996-q1007, q1009 answered and routed; follow-ups q1022 q1023 answered and routed; #112/#110 cards q869 q870 q896 q933-q950 q975 q976 q981 q995 routed. Pushed hub drafts #1093 (Q8) #1094 (G6+D2) #1095 (D5). Board rows cc77 cc50 cc68 cc91 name their PRs. Files in F:\Claude Sessions\handoff\one-interface-research: TRAIN5-LIST.md, AUDIT-CC-PAGE-2026-10-31.md, P160-CHECK-2026-10-31.md (if written).

## Agents running at handoff (die if I am archived; keep #117 open until they report)
DOORS p166, SURFACE p168, NODE p170, SURFACE p171, SURFACE p172 (mockup), INTELLIGENCE p173 (Market), ARMS p174, SURFACE p175, DOORS p176, check agent a86516662d3da6125. Local branches only, nothing pushed except the three above.

## Next (orders from 057, owner-relayed; verify each)
1. Board rows: flip cc23 (#938 merged) and cc55 (#926 merged); cc04 note #859 #902 merged, #867 OPEN, stays doing; refresh stale detail of cc40 cc105 cc50 from the audit.
2. Train 5: land the 9 "ready" PRs in TRAIN5-LIST.md one at a time inside the ci-novahub hold (mkdir F:/Claude Sessions/.locks/ci-novahub): before each re-read head SHA, test.yml pytest job on it, main unmoved. Skip migrations, deploy config, secrets, outward sends, #958. Do not touch the 52 needing main merged until the 9 are done.
3. Push local branches one at a time as drafts: surface-p160 last (guard test breaks other L2 CSS; add "built from items 1-2 of one-skin-spec.md" and a browser render first).
4. Wake-on-answer sent 212 answers; only mine (#112 #110 #117 askers) are routed; the other ~150 belong to other routers and conductors, tell 057.

## Owed
Owner: q997 deploy setting EGRESS_DEDUP_WINDOW_HOURS; q947 scheduled task approval; q943 crypto question; q1000 needs named Ninja calls. A user question on which desk sent "Proof: Body and Places" mail: sender prime@mail.leadfuel.cloud (NovahPrime), not one of my desks.

## Gotchas
The hook warns on the word handoff; ignore unless no note exists. Card ids race: set without if_version, bump on error. Worktree isolation sometimes fails transiently: retry once. SKIP_TESTS=1 must be set as $env:SKIP_TESTS in PowerShell.
