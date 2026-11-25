# NODE lab plans and library tools

Everything here is plan-only or read-only. The tools render scripts and reports; they open no
connection, run nothing on any machine, send nothing and delete nothing.

**No real host data lives in this repository.** Addresses, ssh logins, aliases, VM and container
ids, storage names and user paths are read from a local, git-ignored file. The values in the code
and the tests are placeholders (`10.0.0.x`, `100.64.x`, VM `90x`, `/dev/sdz`, `C:\Users\<user>`).

## The local host file

Default path `node/lab_hosts.local.json` (listed in `.gitignore`), or pass `--hosts PATH`. Without
a file the CLI refuses; `--placeholders` renders with the placeholders and says so in the script
header (`# HOSTS: PLACEHOLDER values ... NOT runnable as is`).

Every key is optional; a missing key keeps its placeholder. Unknown sections or keys are refused,
and every host must pass the LAN check (loopback, RFC 1918 or tailnet, or a name listed in
`aliases`).

```json
{
  "hosts":   {"proxmox": "root@<addr or alias>", "backup": "root@<addr>", "library": "root@<addr>",
              "ci_vm": "<alias or user@addr>"},
  "aliases": ["<ssh alias from ~/.ssh/config>", "..."],
  "ids":     {"ci_vm": 0, "restore_vm": 0, "gpu_ct": 0},
  "paths":   {"backup_root": "/...", "pve_storage": "<proxmox storage id>", "pve_mount": "/mnt/pve/<id>",
              "library_root": "/...", "opt_root": "/opt", "opt_folders": ["<folder>", "..."],
              "busy_pattern": "<pgrep -f pattern of the ingest job>", "salvage_disk": "/dev/sdX",
              "surface_home": "C:\\Users\\<user>"}
}
```

## Tools (tests in `tests/test_node_lab_and_library.py`)
| Id | Tool | What it does | Gate it leaves |
|---|---|---|---|
| machines-6 | `python node/lab_plans.py machines-6 --date YYYY-MM-DD` | renders the script: idle check, space check, refuse-to-overwrite, tar the CI VM's data folders to the backup host (`set -C` on the far side), sha256 both ends, listing; vzdump job drafted | the vzdump line is GATED (Proxmox standing config); run inside the heavy slot |
| P08 | `... P08` | usage, cold-file list, dry run, additive copy (GATED), hash both ends, whole-line sorted `comm`, writes the CANDIDATES list to `<list>.candidates` and prints its count | the copy line, and any removal, are a person's |
| P14 | `... P14` | read-only salvage of the worn disk with ddrescue to a seekable file on the backup storage: `setro` proven with `getro`, mount and space checked, sha256 | the two ddrescue lines are GATED; the disk is only ever the input |
| desks-1-9 | `... desks-1-9` | last three vzdump task logs, storage online, backups present, scratch id free (`pvesh get /cluster/nextid --vmid`), restore to scratch 91xx, every NIC link-down and proven down, boot, stop | `qmrestore`, `qm set` and `qm start` are UNGATED on purpose (scratch VM only, network down); the one `qm destroy 91xx --purge` is GATED and is the only destroy any shape allows |
| W09 | `... W09` | refuses unless MemAvailable covers cap + 2 GB (unreadable is UNKNOWN), caps memory, `onboot 0`, vulkaninfo | `pct set` and `pct start` are UNGATED on purpose (reversible container settings); the runtime install is a download, an owner step |
| machines-8 | `... machines-8` | send-only Syncthing folder definitions; device id and hosts flagged when placeholders | vault device id; receiver sets `ignoreDelete`; OneDrive folders held back |
| library-6 | `python node/library_tools.py scan-withheld <withheld.jsonl>` | per file: sha256, pattern types, line numbers, verdict CLEAN/HITS/UNKNOWN; never prints matched text | allow entries belong to the nightly's owner |
| W12 | `... dups <MANIFEST.jsonl>` | duplicate groups with a chosen canonical copy | trimming waits for the owner's yes |
| library-7 | `... compare <MANIFEST.jsonl> <sha256sum-output>` | counts files already in the library vs not, by folder; empty input says UNKNOWN | the hash list is made on the other machine (read-only `sha256sum`) |

## The command guard is an allowlist

`assert_safe` accepts a command only if it is **exactly** one of the shapes in `SHAPES`, with every
slot value matching a narrow type (paths are `/[A-Za-z0-9._/-]` without `..` or `/dev/`, ids are
digits, hosts are an address or a listed alias, and no slot can hold a space, quote, `$`, `;`,
`|`, `&`, `<` or `>`). Quoting tricks, re-spacing, tabs, variable-built verbs and anything not
shaped like a step of these plans match nothing and are refused. Every IPv4 literal anywhere in a
command must also pass the LAN check. Shapes for standing config, long copies and the scratch-VM
destroy are GATED-only: they are refused unless the step is GATED, and GATED steps render
commented out. `--date` accepts `YYYY-MM-DD`, `YYYYMMDD` or the placeholder `DATE`, nothing else.

## Guards that really stop

`set -e` does not stop on `! cmd`, on the failure of anything but the last stage of a pipeline,
or on a failing `&&` list. So no guard is written that way: each one captures the exit code or the
value and tests it explicitly (`rc=0; cmd || rc=$?; [ "$rc" -eq 1 ] || { echo UNKNOWN; exit 1; }`,
or `A=$(...)` then a numeric `case`). The tests run every guard line under `sh -c 'set -eu; ...'`
with stub commands, once with a state that must stop the script and once with a state that must
let it continue, so a guard that silently passes everything fails its control.

## The scanner does not say CLEAN when it cannot tell

A placeholder word (`example`, `...`, `your-`, `xxxx`, `<...>`) only excuses a match when it is
inside the matched span itself, never elsewhere on the line. UTF-16 (BOM), binary (NUL bytes) and
non-UTF-8 files are UNKNOWN, not CLEAN.

Run results, the machine name table and anything naming a real host or file are kept in the
owner's private handoff, not here.
