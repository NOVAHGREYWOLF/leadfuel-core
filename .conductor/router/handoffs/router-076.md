# router-076 handoff (ROUTER #76 · one-interface, SURFACE cluster), 2026-10-19

Ids only. The successor re-reads state (gh, pages, locks) before acting; nothing below is trusted.

## Who I am
Cluster router for conductor 047/048 (owner picks 421/431/432/433/436). Slot run local_a2da990c-7249-4a15-ba50-ae31b55abcb4. Board: router/current routers.76; roster router/roster76 (Build Board A4uS9xn1emqupohdE4DUfV). Build rows (page LRC41csTPNRzSk9ddbDFzj, collection tasks): cc05 cc16 cc37 cc38 cc57 cc75 cc77 cc78 cc79 cc82 cc83 cc87 cc88 cc89 cc90 cc91 cc92 cc93 cc95 cc96 cc98 cc100 cc101 cc103. `stage` is progress 0-4 only (048).

## Done
cc05 done (#916). PRs open (all drafts, door-reviewed, landers queued on ci-novahub): #929 cc98, #933 cc96+cc87, #934 cc103, #936 cc90, #941 cc16 tests, #939 cc37 (head f4cee820, lander a648f659e45421310), #932 cc38 (head 746abe2b, held), #930 cc57 (no lib; needs owner download go), q581 desk a6a31b1475f26f726 (counts-only rail/views, report to #80/#81).

## Agents I started (die if this session is archived; hold it open until they report)
Landers: a6fecc03a6e1e5461 (934), ac506dc14a9edcb60 (929), a99051525897fc053 (933), a2211684586fe29c9 (941), abe50bdb83cd2de3f (936), a648f659e45421310 (939). Desks: ae8742ac52a0be1c2 (cc38, waiting for my message to push once), a6a31b1475f26f726 (q581).

## Next
1. #932: owner card on X "base subscription" (asked #79); on answer, message ae8742ac52a0be1c2 to fold + push once, then lander (needs a short re-look).
2. Not yet opened (hold for CI queue ~22 runs; push once per PR): cc77 (after #942 lands), cc79, cc78, cc83, cc82+cc89, cc91, cc92 (after cc38+cc90), cc93, cc95, cc100 (after #934), cc101 last, cc75 idle until readers land; cc88 decision-only (take plan default), cc57 follows owner download go; 4 layout fixes from cc16 (CC-16-verification-001.md). Serial: screen.js CC-83>CC-82; command_screen.html CC-90>CC-92>CC-82>CC-93 (#943 CC-20 first); command_focus.py CC-103>CC-100; command_layers.py CC-77>CC-79>CC-78.
3. Rows set done only from gh. Tell #80 when command_layers/views chains move.

## Owed
Owner cards: q586/q587 (answered), X sentence card, q591 (#79). Needs-Novah: LEVEL_GATE_ENFORCE flip (#79 owns), cesium download (#930). A DOORS finding on dossier auto-approve is #79's desk.

## Gotchas
Spokes doc F:\Leadfuel\Important Documents\01 The Spokes (2026-10-17).md is base layer: differences stop and ask. Landers exit BLOCKED on queue waits unless told to use a Monitor. Agent isolation:worktree fails here (cwd not a git repo for the Agent tool); omit it. Stop hook misfires on the word handoff.
