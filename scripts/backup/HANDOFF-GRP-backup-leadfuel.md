# HANDOFF · GRP-backup-leadfuel (NODE desk)

State as of 2026-10-02 12:50 UTC. Re-read before acting; do not trust these lines.

- Second drive: C: (physical disk 0) vs F: (disk 1). Script refuses same-disk.
- Script: `scripts/backup/Backup-Leadfuel.ps1` (branch `claude/gracious-blackwell-d05c99`, no PR yet).
  Deployed copy: `C:\LeadfuelBackup\Backup-Leadfuel.ps1`.
- Scheduled task `LeadfuelBackup`: weekly Sunday 03:30, registered by ROUTER #10 on the owner's word (Q138).
  First full copy = the Sunday 2026-10-04 03:30 run (owner/router decision B).
- Logs: `C:\LeadfuelBackup\_logs\backup-*.log` (counts only, no file names).
- VAULT-private-remotes (local_00ff8154) is separately putting F:\Leadfuel and F:\Claude Sessions into private remotes.

## To do after Sunday
1. Read the newest log: last line must be `DONE failures=0`. If not, report the robocopy exit.
2. `pwsh C:\LeadfuelBackup\Backup-Leadfuel.ps1 -RestoreTest` -> expect `RESTORE TEST OK`.
3. Report STATUS to the current ROUTER; open a PR for the script if wanted.
