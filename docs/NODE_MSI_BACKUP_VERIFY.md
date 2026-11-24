# NODE P17: MSI backup verifier

Offline and plan-only. `node/msi_backup_verify.py` opens no connection, copies nothing, deletes nothing.
Stacked on PR 110 (lab plans), which it does not edit.

1. `python node/msi_backup_verify.py plan-source` prints a read-only PowerShell listing. A person fills `$roots`, runs it on the MSI and saves the output.
2. `python node/msi_backup_verify.py plan-target --root /path/to/msi/DATE` prints a read-only sh listing (find, awk; no `du`). A person runs it on the backup host and saves the output.
3. `python node/msi_backup_verify.py verify --source S --target T --out result.json` compares folder by folder (files and bytes). Exit 0 COMPLETE, 1 INCOMPLETE, 3 UNKNOWN, 2 refused. It will not overwrite a result file.

UNKNOWN covers a truncated listing (no `# END n`, or the wrong n), a source folder with zero files, an unreadable line, an unreadable file. It is never reported as COMPLETE.
The result always says `wipe_allowed: false`. Powering the MSI on and saying when it may be wiped are the owner's.
Caveat: Windows and Linux can count the same folder differently (junctions, reparse points, permission-denied files); a SHORT verdict is a reason to look, and `--tolerance-files N` only forgives a file-count gap when the bytes are equal.
