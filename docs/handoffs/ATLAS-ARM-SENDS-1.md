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
