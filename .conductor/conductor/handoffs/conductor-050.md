# Handoff: CONDUCTOR system build, 050 -> 051, 2026-10-20 ~18:45Z

050 = local_2b680341-cac4-42d0-a405-13ae04b665a6 (slot way-slot-01). 049 (local_4b77bcc9) archived. Ids only; public repo.

## Done (050)
- Board A4uS9xn1emqupohdE4DUfV router/current: conductor key names 050 (051 sets its own: pin if_version, out_dir, never print the ~134 KB doc). Live router = ROUTER #87 local_b72e16fa-83bc-4f9c-aaa9-ecf91a31f527 (way-slot-06), at ~345k of 450k, note origin/claude/router-87 @085bd796; its successor ROUTER #88 requested from launcher local_1c9b1829 (my LAUNCH-REQUEST sent 18:3xZ; #87's earlier one got no LAUNCHED). Check `get_session` on the launcher and for a live ROUTER #88 before asking again.
- Owner order (typed in my chat): as much code as possible, then wait for checks. Relayed to #86 then #87.
- Owner answers routed: q611 C, q612 A, q613 B, q619 A, q620 A (q614 A, q615 B, q616 B, q618 A read by routers). Open owner cards: q617 (spare machines), q492 (blocks q620 A work), q619/q620 follow-ups.
- Rows filed: desks/intelligence WORLD-GLOBE-POINTS-DARK (queued, read-only report done by INTELLIGENCE part 118: likely admin login has no account email, feed cron flags, pick-303 fixes landed in hub #938); desks/doors R86-linkedin-send-no-queue-law9 (unqueued, owner picks).
- Tick cron 9e672fa8 (:03 :13 :23 :33 :43 :53) = stall check first (wakes an idle router once an hour), then cards and merges. Dies with this session: 051 re-creates it.

## State (re-read, do not trust)
Last hub merge by mergedAt: #966 11:07:23Z; main 966129ba per #87. All open hub PRs are drafts; hub pytest skips drafts (#949), so landers undraft first. Wall stack #875 #951 #946 #952 #960 waits on q492.

## Next
Set board conductor key; re-create tick; confirm ROUTER #88 is live (else ask launcher once, or give owner the paste prompt); route q492 to the owner and relay answers; archive 050 only after 051 is live.

## Owed
Owner: q492, q617; typed go in NODE Railway desk chat for any production read or variable (WORLD flags, COMMAND_HOME are his paste). Launcher reply for ROUTER #88 and CONDUCTOR 051 not yet received.

## Gotchas
Stop hook misreads start notes as a rotation. Idle routers do not wake themselves: check isRunning. Messages to a mid-turn session queue. ArtifactData query with n>=617 on questions works; list floods.
