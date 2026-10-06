# ATLAS-ARM-SENDS 1/1 handoff (ARMS desk)

Status: BLOCKED on ownership. No code changed.

Verified myself (2026-10-03, read-only):
- Atlas v3 rows for reach, signal, odyssey, lucid are marked "bypass" (own transports, no intent row before the socket).
- reach main b0645bc: sender.py still calls Resend (:40) and Twilio (:43) directly; SEND_VIA_NOVAHUB proxy is flag-gated (:99).
- signal main 4633b82: linkedin.py posts itself; hub proxy only when SEND_VIA_NOVAHUB is set (:336).
- SESSION_MAP: reach scheduler.py/sender.py and signal scheduler.py at the publish call are DOORS. Rows 36-37 overlap ATLAS-G2/ATLAS-DOORS.
- odyssey #35/#36 and lucid #115 (gateway) are merged; #37-39, #116, #117 open (titles only; not read).

Took on trust: the Atlas claims themselves (snapshot 10-02), not re-measured beyond the lines above. Not checked: odyssey and lucid send code, scope knowledge-gate row, KNOWLEDGE_GATE_ENFORCE state.

Next: DOORS (ATLAS-DOORS, local_3f2e7535) takes the send-path edits. ARMS can take the non-send parts (scope write path, per-spoke tokens) once ROUTER confirms the split. The enforce flag is an owner card.

## Update 2026-10-05: scope write path (read-only, hub 5c2218f, scope 65ee909)
- scope writes knowledge via leadfuel_core.knowledge.add_knowledge (app.py:~1010, source="smarticp"), then POST /api/knowledge/distill.
- hub add_knowledge (app.py:2300) observes every direct write; with KNOWLEDGE_GATE_ENFORCE on it returns 403 for any caller not in KNOWLEDGE_GATE_ALLOWED (default hub,legacy,mcp,novaprime,novahprime). scope is not in that list.
- scope swallows the failure (log.info "knowledge emit skipped"), so flipping the flag would silently stop the flywheel, not error.
- The 403 text points at /api/report/submit, but that route takes a daily spoke report (source+day), not a knowledge doc: not a drop-in.
- Unverified: the caller name scope's token resolves to; whether the flag is set in production; who owns leadfuel_core/knowledge.py.
