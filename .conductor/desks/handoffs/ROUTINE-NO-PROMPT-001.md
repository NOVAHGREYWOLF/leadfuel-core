# Handoff: WATCH · ROUTINE-NO-PROMPT 1/1 (desk), 2026-10-06 ~22:31Z

Session: this desk (WATCH group). Router: ROUTER #24. Source: Router desk q314 = C (21:19:47Z). NEEDS-NOVAH. Ids and titles only.

## Done (verified by me via tools)
- Cause: scheduled task `merge-desk-refresh` runs in permission mode `default` (read from each run's own transcript). Every ArtifactData call there waits for a person, reads included: all four default-mode runs stalled on step 1's two reads. Run local_2a41fc63 finished only after it was switched by hand to bypass + Haiku.
- App code (v2.19675.0.0): a task's permission mode is a per-task field (`default`, `acceptEdits`, `plan`, `bypassPermissions`, `dontAsk`, `auto`) that the scheduled-task tools cannot set. Stored "always allow" rules never answer an ArtifactData ask in a scheduled run.
- Task prompt: on any refused tool call, stop and report `FAILED at step N`; never retry a refusal.
- Model: `model: claude-haiku-4-5-20251001` in the task's SKILL.md frontmatter. Test run local_e0f03b48 started on Haiku, then stalled on step 1 as predicted.
- Stopped runs local_73bb1e3c (the hung one) and local_e0f03b48 (my test). Neither is archived.
- Task is **paused** (enabled=false) so that no new run hangs.

## Next
After Novah sets the permission mode (card from ASK ROUTINE-NO-PROMPT): enable the task, run it once, and confirm the run ends with `merge-desk refresh: N rows ...` without a prompt.

## Owed
- Novah: the task's permission mode, set in the app (Scheduled → Merge desk refresh → Edit). Default: Bypass permissions.

## Gotchas
- A stopped run shows status "succeeded" in list_task_runs.
- list_events hides tool calls. The run transcripts under the project's `.claude/projects` folder show them.
