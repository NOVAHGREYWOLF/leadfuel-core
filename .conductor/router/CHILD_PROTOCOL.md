# Child protocol (paste at the end of every task brief)

```
REPORTING. You do not talk to the owner. You report to the ROUTER, session_01PjWdddCUgWifTFgyqnt7Pe.
If that session is archived or send_message fails, read doc router/current on the LeadFuel Build Board
(ArtifactData get, collection router, doc_id current) and use its session_id.

TOOL: use `mcp__claude-code-remote__send_message` with `session_id` (load it with ToolSearch `select:mcp__claude-code-remote__send_message`).
Do NOT use the generic `SendMessage` / `ListAgents` tools: they address by name and fail with "No agent named ... is reachable".
NOTE: the first send_message from a spawned child can stop on a permission prompt. The router does not depend on it: it reads your harness status summary directly. So always end with a clear one-line final message (what is done, what you need) and your handoff; that is what gets read.

When you finish, are blocked, or need a decision, send ONE message to the router:

STATUS: DONE|BLOCKED|NEEDS-NOVAH|CONTINUING | <task id> | <PR url or "no PR"> | <one line, 120 chars max>
(then at most 5 lines of detail)

If you need a decision, instead send:
ASK: <task id> | <the question, 200 chars max>
OPTIONS: A) ... B) ...
DEFAULT: A (why)

After you send it, write your handoff, commit and push, and STOP. Do not wait for an answer, do not poll, do not
schedule a wake-up. The router will either wake you with the answer or start a fresh session with it.
Do not merge your own PR (the tick merges it once its checks are green), deploy, force-push, archive anything, or message anyone but the router.
```

Notes for the router:
- Keep the router id in this block current when it rotates (the pointer doc is the source of truth; this id is only the first guess).
- The public repo rule applies: no private details in anything committed.
