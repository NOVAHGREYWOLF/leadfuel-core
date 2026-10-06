# Handoff: NODE · python3 hook error (desk), 2026-10-06 ~21:35Z

Session local_3c42ae12. DONE. Ids and titles only.

## Done (verified by me via tools)
- Cause: `.claude/settings.json` ran `python3 .claude/hooks/context_guard.py` on PostToolUse and UserPromptSubmit. On the home node `python3` is only the Windows Store stub (exit 49), so the guard never ran. The leadfuel-way plugin's guard is live and replaces it.
- q301 = A (Router desk, 21:21:53Z, relayed by ROUTER #24): PR #31 removed the two hook entries. Env caps kept (the plugin's way_hook.py reads them). Bare pytest 483 passed locally; CI 482 passed + 1 skipped; merged on unmoved main as 921fcc8 at 21:34:08Z.
- q312 = A (21:20:03Z): user-settings snippet sent to ROUTER #24 (queued, not confirmed read). Snippet only; the user settings file was not opened or edited.

## Open
- The main leadfuel-core checkout is on `claude/zealous-heisenberg-tlqil3` (PR #8), whose settings file still has the hook. Sessions there keep the errors until main is merged into it. Not done here; reported to ROUTER #24.
- `.claude/hooks/context_guard.py` and older skills that mention it are still on main (dead references).
