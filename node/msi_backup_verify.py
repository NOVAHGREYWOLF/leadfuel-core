"""NODE P17: MSI backup verifier. Offline comparison, plan-only, never wipes.

Question it answers: is every folder copied from the MSI onto the backup host complete,
by file count and byte size? It never connects to anything. A person runs two read-only
listings (one on the MSI, one on the backup host) and this module compares the two files.

  plan-source  prints a PowerShell listing for the MSI (read-only: Get-ChildItem, no copy, no delete).
  plan-target  --root PATH  prints a POSIX sh listing for the backup host (read-only: find and awk).
  verify       --source FILE --target FILE [--out FILE]
                 reads both listings and writes a result.

Listing format, one line per copied folder, tab separated: name  files  bytes
and a last line `# END <n>` where n is the number of folder lines. A listing without
its END line, or with a different n, is truncated and reads as UNKNOWN.

Verdicts per folder:  MATCH, SHORT (target has less), EXTRA (target has more),
MISSING (in source, not in target), UNKNOWN (cannot be established: zero files in
the source, or a malformed line). Overall: COMPLETE only if every source folder is MATCH.
Anything else is INCOMPLETE or UNKNOWN. UNKNOWN is never rounded up to COMPLETE.

The result always carries wipe_allowed = false. A complete verdict is evidence for the owner;
it is not permission. Powering the MSI on and saying when it may be wiped are the owner's.
Only folder names appear in output, never file names or contents.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

NAME_RX = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
PATH_RX = re.compile(r"/[A-Za-z0-9._/-]{1,200}")
WIPE_NOTE = "Evidence only. The wipe is the owner's call; this tool never wipes, copies or deletes."


class Refused(ValueError):
    pass


def parse_listing(text: str) -> tuple[dict, list[str]]:
    """Return ({"folders": {name: (files, bytes)}, "bad": [names]}, problems)."""
    folders: dict[str, tuple[int, int]] = {}
    problems: list[str] = []
    bad: set[str] = set()
    end = None
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip("\r\n")
        if not line.strip():
            continue
        if line.startswith("# END"):
            parts = line.split()
            if len(parts) == 3 and parts[2].isdigit():
                end = int(parts[2])
            else:
                problems.append(f"line {n}: malformed END line")
            continue
        if line.startswith("#"):
            continue
        cols = line.split("\t")
        if len(cols) != 3 or not NAME_RX.fullmatch(cols[0]) or not cols[1].isdigit() or not cols[2].isdigit():
            problems.append(f"line {n}: not name<TAB>files<TAB>bytes")
            if cols and NAME_RX.fullmatch(cols[0]):
                bad.add(cols[0])
            continue
        if cols[0] in folders:
            problems.append(f"line {n}: folder {cols[0]} listed twice")
            bad.add(cols[0])
            continue
        folders[cols[0]] = (int(cols[1]), int(cols[2]))
    if end is None:
        problems.append("no '# END n' line: listing may be truncated")
    elif end != len(folders) + len(bad):
        problems.append(f"END says {end} folders, parsed {len(folders) + len(bad)}")
    for b in bad:
        folders.pop(b, None)
    return {"folders": folders, "bad": sorted(bad)}, problems


def compare(source_text: str, target_text: str, tolerance_files: int = 0) -> dict:
    src, sp = parse_listing(source_text)
    tgt, tp = parse_listing(target_text)
    structural = [p for p in sp + tp if p.startswith(("no '# END", "END says"))]
    rows = []
    for name in sorted(set(src["folders"]) | set(src["bad"])):
        if name in src["bad"] or name in tgt["bad"]:
            rows.append({"folder": name, "verdict": "UNKNOWN", "why": "listing line unreadable"})
            continue
        sf, sb = src["folders"][name]
        if sf == 0:
            rows.append({"folder": name, "verdict": "UNKNOWN",
                         "why": "source folder lists zero files; cannot establish a copy"})
            continue
        if name not in tgt["folders"]:
            rows.append({"folder": name, "verdict": "MISSING", "source": {"files": sf, "bytes": sb}})
            continue
        tf, tb = tgt["folders"][name]
        if sb == tb and abs(sf - tf) <= tolerance_files:
            v = "MATCH"
        elif tf < sf or tb < sb:
            v = "SHORT"
        else:
            v = "EXTRA"
        rows.append({"folder": name, "verdict": v, "source": {"files": sf, "bytes": sb},
                     "target": {"files": tf, "bytes": tb}, "delta": {"files": tf - sf, "bytes": tb - sb}})
    target_only = sorted(set(tgt["folders"]) - set(src["folders"]) - set(src["bad"]))
    verdicts = {r["verdict"] for r in rows}
    if structural or not rows or "UNKNOWN" in verdicts:
        overall = "UNKNOWN"
    elif verdicts == {"MATCH"}:
        overall = "COMPLETE"
    else:
        overall = "INCOMPLETE"
    return {"tool": "msi_backup_verify", "overall": overall, "folders": rows,
            "target_only_folders": target_only, "problems": sp + tp,
            "tolerance_files": tolerance_files, "wipe_allowed": False, "note": WIPE_NOTE}


def plan_source() -> str:
    return (
        "# P17 source listing: run by a person on the MSI. Read-only. Nothing is copied or deleted.\n"
        "# Fill $roots with the folders that were copied; each leaf name must equal its copy name on the backup host.\n"
        "$roots = @()\n"
        "if ($roots.Count -eq 0) { Write-Output 'UNKNOWN: fill $roots first'; exit 1 }\n"
        "foreach ($r in $roots) {\n"
        "  $files = @(Get-ChildItem -LiteralPath $r -Recurse -File -Force -ErrorAction SilentlyContinue)\n"
        "  $bytes = ($files | Measure-Object -Property Length -Sum).Sum\n"
        "  if ($null -eq $bytes) { $bytes = 0 }\n"
        "  '{0}`t{1}`t{2}' -f (Split-Path -Leaf $r), $files.Count, $bytes\n"
        "}\n"
        "'# END {0}' -f $roots.Count\n"
        "# Save the output to a file and give it to `verify --source`.\n"
    )


def plan_target(root: str) -> str:
    if not PATH_RX.fullmatch(root) or ".." in root or "//" in root:
        raise Refused("--root must be an absolute path of letters, digits, . _ / -")
    return (
        "# P17 target listing: run by a person on the backup host. Read-only (find, awk). No du over the tree.\n"
        f"ROOT={root}\n"
        '[ -d "$ROOT" ] || { echo "UNKNOWN: $ROOT is not a directory"; exit 1; }\n'
        "n=0\n"
        'for d in "$ROOT"/*/; do\n'
        '  [ -d "$d" ] || continue\n'
        '  name=$(basename "$d")\n'
        '  find "$d" -type f -printf "%s\\n" | awk -v n="$name" \'{c++; b+=$1} END {printf "%s\\t%d\\t%d\\n", n, c, b}\'\n'
        "  n=$((n+1))\n"
        "done\n"
        'echo "# END $n"\n'
        "# Save the output to a file and give it to `verify --target`.\n"
    )


def _read(path: str) -> str | None:
    try:
        with open(path, "rb") as f:
            raw = f.read()
        if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):   # PowerShell redirects write UTF-16
            return raw.decode("utf-16")
        return raw.decode("utf-8-sig")
    except (OSError, UnicodeError) as e:
        sys.stderr.write(f"UNKNOWN: cannot read {path}: {type(e).__name__}\n")
        return None


def main(argv=None, out=sys.stdout) -> int:
    ap = argparse.ArgumentParser(description="MSI backup verifier (P17), offline and plan-only")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan-source")
    pt = sub.add_parser("plan-target")
    pt.add_argument("--root", required=True)
    v = sub.add_parser("verify")
    v.add_argument("--source", required=True)
    v.add_argument("--target", required=True)
    v.add_argument("--out")
    v.add_argument("--tolerance-files", type=int, default=0)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "plan-source":
            out.write(plan_source())
            return 0
        if a.cmd == "plan-target":
            out.write(plan_target(a.root))
            return 0
        s, t = _read(a.source), _read(a.target)
        res = compare(s or "", t or "", max(0, a.tolerance_files))
        if s is None or t is None:
            res["overall"] = "UNKNOWN"
            res["problems"].append("a listing file could not be read")
        body = json.dumps(res, indent=1) + "\n"
        if a.out:
            if os.path.exists(a.out):
                sys.stderr.write("refused: result file exists, will not overwrite\n")
                return 2
            with open(a.out, "x", encoding="utf-8") as f:
                f.write(body)
        out.write(body)
        return {"COMPLETE": 0, "INCOMPLETE": 1, "UNKNOWN": 3}[res["overall"]]
    except Refused as e:
        sys.stderr.write(f"refused: {e}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
