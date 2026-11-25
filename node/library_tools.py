"""NODE document-library tools (library-6, W12, library-7). Read-only, local, names and counts only.

  scan-withheld  <withheld.jsonl>   per withheld file: sha256, pattern TYPES and line numbers, verdict.
                                    CLEAN = readable and no pattern hit (an allow entry may be added).
                                    HITS  = at least one hit: redact into a copy, never allow as is.
                                    UNKNOWN = missing, unreadable, UTF-16, binary or not UTF-8:
                                    never reads as clean.
                                    A placeholder word only excuses a match when it is inside the
                                    matched span itself, never elsewhere on the line.
                                    No matched text is ever printed or stored.
  dups           <MANIFEST.jsonl>   duplicate groups by sha256 with a chosen canonical copy.
  compare        <MANIFEST.jsonl> <hashlist>
                                    hashlist = `sha256sum` output from another tree (made by whoever runs it on that
                                    machine); counts how many files are already in the library and lists the rest.
Nothing here writes into the library, calls a network, or deletes.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys

PATTERNS = {
    "private-key-block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "anthropic-or-openai-key": re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_\-]{20,}"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    "slack-token": re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}"),
    "assigned-secret": re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|token)\b\s*[:=]\s*[\"']?[A-Za-z0-9/+_\-]{12,}"),
    "bearer-token": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{20,}"),
    "long-hex-secret": re.compile(r"(?i)(key|secret|token)[^\n]{0,20}\b[0-9a-f]{40,}\b"),
}
PLACEHOLDER = re.compile(r"(?i)example|placeholder|<[a-z _-]+>|xxxx|your[_-]|\.\.\.")


def scan_file(path: str) -> dict:
    """CLEAN only when the whole file was readable as UTF-8 text and no non-placeholder match exists.
    The placeholder test looks at the matched span only, never at the rest of the line."""
    try:
        raw = open(path, "rb").read()
    except OSError as e:
        return {"path": path, "verdict": "UNKNOWN", "why": type(e).__name__}
    base = {"path": path, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff") or b"\x00" in raw:
        return {**base, "verdict": "UNKNOWN", "why": "utf16-or-binary: this scanner reads UTF-8 text only"}
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return {**base, "verdict": "UNKNOWN", "why": "not-utf8"}
    hits: dict[str, list[int]] = collections.defaultdict(list)
    for n, line in enumerate(text.splitlines(), 1):
        for name, rx in PATTERNS.items():
            if any(not PLACEHOLDER.search(m.group(0)) for m in rx.finditer(line)):
                hits[name].append(n)
    return {**base, "verdict": "HITS" if hits else "CLEAN", "hits": {k: v[:20] for k, v in hits.items()}}


def scan_withheld(jsonl: str) -> list[dict]:
    seen, out = set(), []
    for line in open(jsonl, encoding="utf-8"):
        if line.strip():
            p = json.loads(line)["source_path"]
            if p not in seen:
                seen.add(p)
                out.append(scan_file(p))
    return out


def _rows(manifest: str):
    return [json.loads(ln) for ln in open(manifest, encoding="utf-8") if ln.strip()]


def canonical(group: list[dict]) -> dict:
    """Prefer a filed project over 'unfiled', then a repo/book document over a nightly mirror, then the shortest path."""
    def key(r):
        return (r.get("project") == "unfiled", r.get("kind") in ("sessions-notes", "other"),
                "nightly" in str(r.get("version", "")), len(r["path"]), r["path"])
    return sorted(group, key=key)[0]


def dup_groups(manifest: str) -> list[dict]:
    by = collections.defaultdict(list)
    for r in _rows(manifest):
        by[r["sha256"]].append(r)
    out = []
    for h, g in by.items():
        if len(g) > 1:
            c = canonical(g)
            out.append({"sha256": h, "bytes": c.get("bytes", 0), "canonical": c["path"], "copies": len(g),
                        "others": sorted(r["path"] for r in g if r is not c)})
    return sorted(out, key=lambda d: -d["bytes"] * (d["copies"] - 1))


def compare(manifest: str, hashlist: str) -> dict:
    known = {r["sha256"] for r in _rows(manifest)}
    have, missing, bad = 0, [], 0
    for line in open(hashlist, encoding="utf-8", errors="replace"):
        parts = line.rstrip("\n").split(None, 1)
        if len(parts) != 2 or not re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
            bad += 1
            continue
        h, p = parts[0].lower(), parts[1].lstrip("*")
        if h in known:
            have += 1
        else:
            missing.append(p)
    top = collections.Counter("/".join(p.replace("\\", "/").split("/")[:3]) for p in missing)
    return {"in_library": have, "not_in_library": len(missing), "unparseable_lines": bad,
            "unknown_if_zero_lines": have + len(missing) == 0, "missing_by_folder": top.most_common(25)}


def main(argv=None, out=sys.stdout) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scan-withheld").add_argument("jsonl")
    sub.add_parser("dups").add_argument("manifest")
    c = sub.add_parser("compare")
    c.add_argument("manifest")
    c.add_argument("hashlist")
    a = ap.parse_args(argv)
    if a.cmd == "scan-withheld":
        res = scan_withheld(a.jsonl)
    elif a.cmd == "dups":
        res = dup_groups(a.manifest)
    else:
        res = compare(a.manifest, a.hashlist)
    json.dump(res, out, indent=1)
    out.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
