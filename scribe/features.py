#!/usr/bin/env python3
"""SCRIBE K09 first slice: the FEATURES table, with shipped, dormant and planned never blurred.

    python scribe/features.py --hub <hub checkout> [--prs merged_prs.json] [--flags flag_state.json] \
        [--registry scribe/features.json] [--out FEATURES.md]

WHY: "built and off" is the case that blurs. A feature behind a flag that is off is not shipped, and a page that
calls it shipped is a claim nobody verified. This generator reads two things and refuses to guess:

  * the REGISTRY (`features.json`), one row per feature a person has named, with an evidence pointer; and
  * the flags the hub's code reads (`os.environ.get("X_ENABLED", ...)`), found by scanning a checkout.

THE RULES (each has a test that can fail):
  * `shipped` needs a VERIFIED evidence pointer: a test file that exists in the checkout, or a PR number that is
    in the merged-PR list you passed in. No pointer, or a pointer that cannot be checked, is `unverified`.
  * A feature whose flag is off never says `shipped`. Without a deployment snapshot (`--flags`), a flag whose
    code default is off reads `dormant`, and the table says the state came from the code default and that the
    deployment was not read. This tool never reads production.
  * A flag that is present in code but has no registry row appears as its own row (`dormant` or `unverified`),
    never as `shipped`, so a built-and-off feature cannot go missing from the table.
  * A flag the registry names that the scan cannot find is `unverified`, not `shipped`.
  * `planned` is only what the registry says is planned; it never needs evidence and never reads as shipped.
  * An empty registry and an empty scan give "nothing to show", not a table of invented rows.

READ-ONLY and LOCAL: it reads files under the paths you give it and writes one output file. No network, no `gh`
call (you pass the PR list in, from `gh pr list --state merged --json number,title`), no model, nothing sent.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SHIPPED, DORMANT, PLANNED, UNVERIFIED = "shipped", "dormant", "planned", "unverified"
STATUSES = (SHIPPED, DORMANT, PLANNED, UNVERIFIED)

_FLAG_RE = re.compile(
    r"""(?:os\.environ\.get|os\.getenv)\(\s*["']([A-Z][A-Z0-9_]*(?:_ENABLED|_ON))["']\s*(?:,\s*([^)\n]*))?\)""")
_TRUTHY = {"1", "true", "yes", "on"}
_SKIP_DIRS = {".git", ".claude", "node_modules", "__pycache__", ".venv", "venv", "static", "tests"}


def _default_state(raw: str | None) -> str:
    """'on', 'off' or 'unknown' from the text of a default argument."""
    if raw is None:
        return "off"                       # no default: the call returns None, which is off
    raw = raw.strip()
    m = re.fullmatch(r"""["']([^"']*)["']""", raw)
    if m:
        return "on" if m.group(1).strip().lower() in _TRUTHY else "off"
    if raw in ("None", ""):
        return "off"
    return "unknown"                       # an expression: not guessed


def scan_flags(hub_root: Path) -> dict[str, dict]:
    """flag -> {default: on|off|unknown, sites: ['file:line', ...]}. Tests and vendored code are skipped."""
    found: dict[str, dict] = {}
    root = Path(hub_root)
    for p in sorted(root.rglob("*.py")):
        rel = p.relative_to(root)
        if any(part in _SKIP_DIRS for part in rel.parts[:-1]) or rel.name.startswith("test_"):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for m in _FLAG_RE.finditer(line):
                name, dflt = m.group(1), _default_state(m.group(2))
                e = found.setdefault(name, {"default": dflt, "sites": []})
                if e["default"] != dflt:
                    e["default"] = "unknown"       # two call sites disagree: say so, do not pick
                if len(e["sites"]) < 3:
                    e["sites"].append(f"{rel.as_posix()}:{i}")
    return found


def _check_evidence(ev: dict, hub_root: Path, merged: dict[int, str] | None) -> tuple[bool, str]:
    """(verified, pointer text). A pointer that cannot be checked is not verified."""
    if not ev:
        return False, "none"
    if "test" in ev:
        ok = (Path(hub_root) / ev["test"]).is_file()
        return ok, f"test `{ev['test']}`" + ("" if ok else " (file not found)")
    if "pr" in ev:
        n = int(ev["pr"])
        if merged is None:
            return False, f"PR #{n} (no merged-PR list given)"
        if n in merged:
            return True, f"PR #{n}"
        return False, f"PR #{n} (not in the merged list)"
    return False, "none"


def classify(entry: dict, flags: dict[str, dict], flag_state: dict[str, str] | None,
             hub_root: Path, merged: dict[int, str] | None) -> dict:
    row = {"feature": entry["feature"], "flag": entry.get("flag") or "", "status": UNVERIFIED,
           "evidence": "none", "state_source": "", "note": entry.get("note", "")}
    if entry.get("planned"):
        row.update(status=PLANNED, evidence=entry.get("evidence_text", "planned, not built"))
        return row
    ok, pointer = _check_evidence(entry.get("evidence") or {}, hub_root, merged)
    row["evidence"] = pointer
    flag = entry.get("flag")
    if flag:
        seen = flags.get(flag)
        if flag_state is not None and flag in flag_state:
            state, row["state_source"] = flag_state[flag], "deployment snapshot"
        elif seen is not None and seen["default"] in ("on", "off"):
            state, row["state_source"] = seen["default"], "code default; deployment not read"
        else:
            row["note"] = (row["note"] + " " if row["note"] else "") + "flag not found in the scan or default not literal"
            return row                      # unverified
        if state == "off":
            row["status"] = DORMANT
            return row
        if state != "on":
            return row
    if ok:
        row["status"] = SHIPPED
    return row


def build_rows(registry: list[dict], hub_root: Path, merged: dict[int, str] | None = None,
               flag_state: dict[str, str] | None = None) -> list[dict]:
    flags = scan_flags(hub_root)
    rows = [classify(e, flags, flag_state, hub_root, merged) for e in registry]
    registered = {e.get("flag") for e in registry if e.get("flag")}
    for name, info in sorted(flags.items()):
        if name in registered:
            continue
        status = DORMANT if info["default"] == "off" else UNVERIFIED
        src = "code default; deployment not read"
        if flag_state is not None and name in flag_state:
            status, src = (DORMANT if flag_state[name] == "off" else UNVERIFIED), "deployment snapshot"
        rows.append({"feature": f"(unregistered) {name}", "flag": name, "status": status,
                     "evidence": "`" + info["sites"][0] + "`", "state_source": src,
                     "note": "flag in code, no registry row; never shipped until a person adds one"})
    return rows


def render(rows: list[dict], as_of: str) -> str:
    out = ["# FEATURES", "", f"As of {as_of}. Generated by `scribe/features.py`; do not edit by hand.", "",
           "`shipped` needs a checked evidence pointer and a flag that is on. A flag that is off is `dormant`. "
           "`unverified` means the evidence or the flag state could not be checked, which is not a yes. "
           "Where the state came from the code default, the deployment was not read.", ""]
    if not rows:
        return "\n".join(out + ["Nothing to show: the registry is empty and the scan found no flags.", ""])
    out += ["| Feature | Status | Flag | Evidence | State source | Note |", "| --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        flag = f"`{r['flag']}`" if r["flag"] else ""
        out.append(f"| {r['feature']} | {r['status']} | {flag} | {r['evidence']} | {r['state_source']} | {r['note']} |")
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in STATUSES}
    out += ["", "Counts: " + ", ".join(f"{s} {n}" for s, n in counts.items()) + ".", ""]
    return "\n".join(out)


def _load_merged(path: str | None) -> dict[int, str] | None:
    if not path:
        return None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {int(p["number"]): p.get("title", "") for p in data}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--hub", required=True)
    ap.add_argument("--registry", default=str(Path(__file__).with_name("features.json")))
    ap.add_argument("--prs")
    ap.add_argument("--flags")
    ap.add_argument("--as-of", required=True, help="the date to print, e.g. 2026-11-23")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    hub = Path(a.hub)
    if not hub.is_dir():
        print(f"UNKNOWN: hub checkout not found: {hub}", file=sys.stderr)
        return 2
    registry = json.loads(Path(a.registry).read_text(encoding="utf-8"))
    flag_state = json.loads(Path(a.flags).read_text(encoding="utf-8")) if a.flags else None
    text = render(build_rows(registry, hub, _load_merged(a.prs), flag_state), a.as_of)
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
