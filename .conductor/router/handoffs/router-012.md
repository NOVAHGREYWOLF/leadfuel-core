# Router handoff #012 -> #013 (2026-10-02 ~23:55 UTC)

ROUTER #12 (local_b9ed13db, Opus) rotating at 300k. Ids only. Router desk LzmP6QcxmYh9TdvMMjS883, Conductor desk MKAx49RAskZ3cV7f2EkDMF. Conductor is 007, local_da515743. Re-read live state; do not trust these lines.

## Nesting (do not break)
The chain is 005 local_083bdfe0 -> ROUTER #11 local_99c30023 -> #12 (me) -> every desk below. Neither detach_session nor the sidebar can detach chip sessions. Archive none of 005, #11 or #12 while any desk under #12 is unfinished. I am NOT archiving myself for that reason. The successor archives #12 only once all my desks are done and PR #19's guard (plugin 0.1.6) is installed.

## Desks (all children of #12)
- SURFACE ONE-PLACE-SURVEY local_a581c655 (Fable xhigh, rank -21): survey, report to the conductor and me.
- VAULT FABLE-4 local_fa59ea24 and FABLE-5 local_6b4faf3f (Fable xhigh): each ends its first turn and waits for "go" from the router. Send "go" when their STATUS arrives.
- DOORS ATLAS-B1 2/2 local_70fae0d7 (Fable xhigh): hub #740, gates, merge in the ci-novahub hold; q169=C relayed.
- SURFACE ATLAS-ACT 1/2 local_da34f6df: hub #739 waiting on the hold; q154-q158 relayed.
- NODE CORE-CI local_24ec7be0 (Sonnet): q171=A, adding the runner and workflow.
- NODE WAY-no-nested-sessions local_032d2f7c: PR #19 0.1.6 at 2c63afa, cleared by the conductor; merges after a CORE-CI green.
- Done/ended: FABLE-1 local_e43581e3 (hub #741), ATLAS-B1 1/1 local_e8ed4d81.

## Owed
- Owner: q164 (ANTHROPIC_ADMIN_KEY), q172-q174 (GOAL lens).
- Fable list remaining: FABLE-6/7/8/9/10 (ranks -15 to -11). Cap is 3 Fable at once; get_usage first (Fable 19% at 23:06Z). Reset 2026-10-03 21:00 UTC.
- Then by rank: 94-120, CORE-CI 119.5, DOORFIX-01..11 (120.01-.11), CWC 121-171 (owner-only ones carded), FLA 172-188 (one n/m desk per lane).

## Gotchas
- Use route.py from cache 0.1.3; 0.1.0 drops the Fable pin.
- A model set applies from a desk's NEXT turn, so its first turn runs on the old model.
- Auto mode refuses router merges.

## Arrived after handoff
- Conductor 007 relays the owner's yes (local_da515743): sweep live sessions with list_events for unanswered owner questions/ASKs; card each one not already carded (dedupe vs OWED-<id8> rows, unverified); report the count to the conductor (008 soon). Delegate the sweep to a read-only subagent (more than 5 sessions).
- ROUTER #11 relay: INTELLIGENCE D4-build-A local_fbb1b69d is NEEDS-NOVAH on hub #702 (CI green f26a860, main d094a57 at ~22:45Z; squash refused as a production deploy). The owner has the PowerShell from #11. #714 is refused the same way. Under Q144, whichever merges second re-runs CI. Both desks are now #13's.
- ATLAS-ACT 1/2 local_da34f6df at 345k is handing off; its successor carries hold ticket 20261002T230352Z-SURFACE-ATLAS-ACT-pr739. Post card Q6: superuser vs a site-admin role below the owner (default A: today's bare admin is the superuser; the role is an auth task the atlas adopts). New task candidate: account-bound atlas readers for user mode, after #713.
- Conductor 007 handed off (conductor-007.md at f5b16dd). 008 is a chip; report to 008 once it is live.
- ATLAS-ACT 1/2 local_da34f6df stopped at 356k. Doc complete at 0c4d779 (Q1-Q5 recorded). Its successor starts only when the owner pastes the prompt from that desk's last message. If the hold reaches ticket pr739 first, pass it over (the ticket keeps its timestamp). Gates and pytest run detached in its worktree: do not archive it until they finish.
- CORE-CI local_24ec7be0 BLOCKED: auto mode denied the `docker run` that starts the leadfuel-core runner (RCE surface). The owner must approve it in that desk or start the runner himself. Its workflow commit is UNPUSHED on claude/sharp-thompson-78e825. The repo fork-PR approval setting reads first_time_contributors (owner may want a stricter setting for a self-hosted runner on a public repo).
- Conductor is now 008 local_b666d711 (verified in the CONDUCTOR group; its first message named local_353c1416 by mistake, corrected). 007 is archived. Report to 008, including the sweep result.
- ONE-PLACE-SURVEY local_a581c655 DONE: leadfuel-core PR #20, docs/ONE-PLACE-SURVEY-2026-10-02.md at cc41abf. Forwarded to conductor 008. Post its candidate cards C1-C8 (report section 7; C4 may duplicate ON4). The desk stays open until archived through the gate (PR #20 unmerged).
- WATCH REPORT-DESK-LOG local_be232c9f: hub #742 CI green, ticket 20261002T235134Z-WATCH--REPORT-DESK-LOG-pr742 is 17th in ci-novahub.wait. It asks to be offered the hold early, citing owner Q141 (reports are priority); verify Q141 before reordering. It is stopped until offered by name.
