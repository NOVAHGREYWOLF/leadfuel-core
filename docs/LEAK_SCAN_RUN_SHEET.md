# Run sheet: the owner's first real leak scan (VAULT S1, `vault/leak_scan.py`)

This is the owner's step, not a desk's. It has two runs: a canary-only run that reads no secret,
then one full scan with no `--state` and no `--exclude`. This page holds names and commands only,
never a value. The scanner reads only the values of `RAILWAY_API_TOKEN`, `HOSTINGER_API_TOKEN` and
`BESTTIME_KEY` from its own process environment, prints names, paths and line numbers (never text,
never an encoding of a value, never a length), sends nothing and starts no process.

## 1. Precondition (check before either run)

1. **No `.leak-scan-canary.txt` at the top of any root.** The tool plants that file at the top of
   every root and removes it at the end. A file with that name already there is never touched, the
   root becomes `unknown`, and the run cannot be `clean`. A killed earlier run can leave one: delete
   it by hand.
2. **Each folder once, and no root inside another.** The tool now drops a folder given twice (by
   resolved path), but a root nested inside another is read twice, so give `%USERPROFILE%\.claude`
   and not also `...\.claude\projects`, and `F:\Leadfuel` and not also `F:\Leadfuel\repos`.
3. **No `--exclude`, no `--state`.** An exclude hides files the same way a blind scan would. A
   state file is for later scheduled runs, not for this one.
4. **Run it in a shell that holds the three variables**, from a `leadfuel-core` checkout that has
   this fix merged. Do not print the variables to check them: a name that is not in the process
   environment shows up in the report as `unknown`.

## 2. Candidate roots (confirm or cut each one)

Checked on 2026-10-13 by looking for the item and listing folder names only. No file content was
opened. `<him>` is the owner's Windows profile folder, `%USERPROFILE%`.

| Root (folder) | Why it is a candidate | Exists |
|---|---|---|
| `%USERPROFILE%\.claude` | Claude Code transcript store (`projects`), `history.jsonl`, `file-history`, `shell-snapshots`, `session-env`, `backups`, `telemetry` | yes |
| `F:\Claude Sessions` | session notes and handoff files (`handoff`) | yes |
| `F:\Leadfuel` | the estate: every checkout and worktree under `repos`, plus `docs`, `home-node`, `health` | yes |
| `%APPDATA%\Microsoft\Windows\PowerShell\PSReadLine` | holds `ConsoleHost_history.txt`, the PowerShell command history | yes (folder and file) |
| `F:\novah` | CI notes and reference copies | yes |
| `%USERPROFILE%` itself | would take in everything above and all other personal files; do not use it | n/a |
| `.bash_history`, `.zsh_history`, `.python_history`, `.node_repl_history` under `%USERPROFILE%` | other shell and REPL history files | **no** (none of the four exist; skip) |

A root has to be a folder, because the canary goes at its top. History *files* are covered by the
folder that holds them. `%USERPROFILE%\.claude.json` is a single file in the profile folder and is
not a root; its content is not covered unless you decide to add `%USERPROFILE%` (not advised).

Things to decide before you run:

- **`F:\Leadfuel` will contain the places the real values legitimately live** (an `.env` in a
  checkout, say). The tool cannot tell a secret's own home from a leak, so those paths will be
  findings. See 5 below for how to read that.
- **Size.** `F:\Leadfuel` holds many worktrees. Expect a long first run.
- **Git objects are compressed, so a clean over a checkout says nothing about what was committed.**
  The report says so under `not_looked_for`.
- The tool writes the canary file into each root for the length of the run (a temporary file in
  the PSReadLine folder too) and removes it at the end.

## 3. Run 1: canary only (reads no secret)

```powershell
python vault/leak_scan.py --canary-only `
  --root "$env:USERPROFILE\.claude" `
  --root "F:\Claude Sessions" `
  --root "F:\Leadfuel" `
  --root "$env:APPDATA\Microsoft\Windows\PowerShell\PSReadLine"
```

Exit 0 means every root was seen: the canary was found in every encoded form and each root held
real content. Exit 2 means at least one root is blind. Do not go on to run 2 until this is 0.

## 4. Run 2: the full scan (no `--state`, no `--exclude`)

Same roots, same order, without `--canary-only`:

```powershell
python vault/leak_scan.py `
  --root "$env:USERPROFILE\.claude" `
  --root "F:\Claude Sessions" `
  --root "F:\Leadfuel" `
  --root "$env:APPDATA\Microsoft\Windows\PowerShell\PSReadLine"
```

The default names are the three above. To scan other names, add `--names A,B` (names only).

## 5. Reading the result

| Exit | `result` | Meaning |
|---|---|---|
| 0 | `clean` | every root was seen in full and its canary found, for the forms listed in the report (`forms`), and not for the gaps in `not_looked_for`. It is not "written down nowhere". |
| 1 | `found` | at least one value is on disk under a root. See `findings`: secret name, path (or `<withheld>` when the path itself holds the value), line, form. |
| 2 | `unknown` | the tool could not tell. **Unknown is not clean.** |

**On exit 1.** A secret found in a transcript, a history file or a session note has already left
the machine (it was sent as part of a conversation), whatever happens to the file now. Rotate it:
owner card q441 A. Deleting or redacting the file does not undo that, and the finding stays
reported on later runs that use a state file until it is cleared on purpose. A finding inside the
secret's own deliberate home (an `.env`, a secret store) is a different thing from a leak: the
tool reports it because it cannot tell them apart, and whether such a path counts is the owner's
call. Do not paste the report into a chat or a public place: it holds paths, which may be private.

**On exit 2.** Read `secrets.<name>.why` and each `roots[].blind`:

- `not in this process's environment`: that name's variable was not set in this shell. Set it and
  run again.
- `canary missing` or `not planted`: the root could not be seen (a pre-existing
  `.leak-scan-canary.txt`, a folder that cannot be written, or a path that does not exist).
  Delete the stale file or fix the path.
- `unreadable path(s)`: a file or folder could not be opened (locked by a running program, or
  permissions). Close the program and run again. Do not add `--exclude` to get a green: an exclude
  is printed in the report and makes the clean smaller.
- `zero bytes of real content`: the root held nothing readable.
- an `error` field with a type name: the run failed; the message is withheld on purpose.

Whatever the exit code, no root should keep a `.leak-scan-canary.txt` afterwards; the report's
`canary_removed` says whether the tool removed its own.

## 6. After the first scan (not part of this step)

Later scheduled runs would use `--state <file>`. Put the state file and its `<state>.key` outside
every root and outside any synced or backed-up folder (for example under `%LOCALAPPDATA%`). On
Windows the tool restricts the key file to the current user and, if it cannot, does not use it
(every run is then a full scan). A scheduled run that is incremental is only as good as its state:
add `--full` when in doubt.
