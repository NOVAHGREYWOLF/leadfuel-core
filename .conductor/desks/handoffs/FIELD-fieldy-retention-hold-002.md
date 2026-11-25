# FIELD · fieldy retention hold on hub — handoff 002

Session `local_e68e1e68-3da1-4054-bc6f-74ad569ec2cb` (FIELD, Sonnet), 2026-10-07 ~09:30Z. Successor to `local_ccbb8afd-09ad-49fe-ab48-86bf5cde9405` (handoff 001, same folder). Branch `claude/zealous-heisenberg-tlqil3` (leadfuel-core, core PR #8). No PR of its own. Nothing here is private.

## Done in 2/2
- Titled `FIELD · fieldy retention hold on hub 2/2` and filed in FIELD (get_session shows the group).
- Re-read live state: 001's commit `16fa443` is on origin (ls-remote) and equals local HEAD; tree clean; no stash. Predecessor archived through the gate (handoff pushed, nothing unpushed, nothing owed to other sessions).
- **Correction to 001:** it names ROUTER #26. The Build Board doc `router/current` says incarnation 27, `session_id` `local_dc4fea43-2246-4e1d-a042-b376ad61bdc5` (ROUTER #27, claimed 08:40Z); #26 hands off and forwards nothing. The brief therefore went to #27.
- Code citations in 001 re-read myself and hold: `fieldy_report.py:496` (empty extraction pass message) and `fieldy_retention.py:64-69` (hold contradicts the data_policy 30-day promise; "whoever turns this on owns updating that page").
- Sent the ASK to ROUTER #27 by session id: queue (1) FIELD digest-extraction diagnosis with the owner's report-quality bar as acceptance, (2) WATCH fieldy watchdog false "down", (3) PRIVACY/COUNSEL wording for `data_policy.html` while the hold is on. Options A) card them for the owner to queue (default), B) hold. Message id `4ee0fc3a-bde3-40b6-b3bc-99fee2d6d007`.

## Delivery state, stated plainly
The app first reported the send as **queued** (ROUTER #27 was mid-turn). **Confirmed later (read in #27's transcript with `list_events`, ~09:35Z):** #27 read the brief and the 001 handoff, ruled **A with one change** (the owner picks on the Conductor desk page, not a Router desk card), asked CONDUCTOR 018 to file the three tasks **not queued**, and told this desk it owes nothing more. #27's own replies to this session and to the conductor were still queued at that read; the ruling itself is what I verified from its transcript.

## Took on trust (from 001, production reads, not re-run by 2/2)
Hold var already set on NovaHub; digest summaries empty for builds 10-04/05/06; watchdog `source_down:ingest:fieldy` claimed newest row 10-04 while rows landed 10-06 and 10-07; all segments unattributed; 50 items in the review queue. Re-running any of these is a production read and needs the owner in this desk's own chat.

## Next
Nothing owed by this desk. The three tasks wait on the Conductor desk page for the owner to queue; if he queues the diagnosis, ROUTER #27 opens a FIELD desk from handoff 001 and this session is not needed. This desk does not start any of them. If the owner asks in this chat to build the digest fix itself, that is FIELD's lane (`webhook:fieldy` and `sources.py` per SESSION_MAP); take a hub worktree first, the acceptance bar is in handoff 001, section "Owner direction".

## Gotchas (unchanged from 001)
- `railway ssh` mangles quoted args; pipe the script on stdin to `/opt/venv/bin/python -`.
- Railway SSH proxy throttles after a burst; back off 90 s.
- `SendMessage` by display name is held across permission modes; use the `local_` id.
