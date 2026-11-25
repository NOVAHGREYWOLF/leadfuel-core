"""VAULT P11: name-only scan and post-rotation checklist for the two exposed Anthropic keys.

Two jobs, both local and read-only:

1. `scan ROOT...` lists every file (path and line number) that NAMES one of the credential
   variables below. It prints names, paths and line numbers only. It never prints the text of a
   line, a value, a hash of a value or a length. For each hit it says whether the line looks like
   it assigns a literal (true/false), so the owner knows which files to open first.
2. `checklist` prints the steps that prove a new key works after the owner rotates it. `check-env`
   reports, for the current process only, whether each variable is set and which kind of string
   it is (the public key-type prefix, nothing else).

What it does not do: it makes no network call, starts no process, writes nothing, and reads no
production variable. The proof that a NEW key works is a call the owner makes (see OWNER-STEP in
the checklist); this module has no transport and no flag that adds one (Law 9). A root that cannot
be read, or that held zero scannable files, is `unknown`, never `clean`.
"""
from __future__ import annotations

import json
import os
import re
import sys

NAMES = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_ADMIN_KEY",
    "ANTHROPIC_KEY_PREGATEWAY_BACKUP",
    "ADMIN_PASSWORD",
)
EXIT_CLEAN, EXIT_FOUND, EXIT_UNKNOWN = 0, 1, 2
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache"}
MAX_BYTES = 5_000_000
# NAME [:=] then something that is not empty, a reference, or an obvious placeholder.
_ASSIGN = r"""["']?\s*[:=]\s*["']?(?P<rhs>[^\s"']*)"""
_PLACEHOLDER = re.compile(r"^(|\$.*|%.*%|<.*>|\{.*\}|\.\.\.|x{3,}|changeme|your[-_].*|sk-ant-\.\.\.)$", re.I)
KEY_KINDS = (("sk-ant-admin", "admin key"), ("sk-ant-api", "api key"), ("sk-ant-", "other anthropic key"))
SENT = "nothing: no network code, no process start, no write"

CHECKLIST = (
    ("owner", "Anthropic console: create the new hub key, copy it straight into Railway `web` "
              "(production) variable ANTHROPIC_API_KEY. Do not paste it into any chat or file."),
    ("owner", "Rotate ADMIN_PASSWORD on the same Railway service (it was printed in the same transcript)."),
    ("owner", "Redeploy `web`; confirm the deploy is healthy."),
    ("owner", "Prove the new key works: trigger one hub call that uses call_claude (for example one "
              "approved draft); it must return 200 and show in the console's usage for the NEW key."),
    ("owner", "Console key list: the OLD key's last-used time must stop moving; then revoke it."),
    ("owner", "Revoke the second exposed key in the console after reading its last-used time."),
    ("desk", "Run `scan` over the local roots and the repos again: every NAME hit with literal=true "
             "is a file to open; update the local .env copies by hand."),
    ("desk", "Run vault/leak_scan.py with the OLD value in its environment, outside this module, "
             "to see which transcripts still hold it."),
    ("owner", "Redact the brain record (evidence 11540) that carries the second key's text."),
)


def _line_hits(text: str, names=NAMES):
    for no, line in enumerate(text.splitlines(), 1):
        for n in names:
            if not re.search(r"\b" + re.escape(n) + r"\b", line):
                continue
            a = re.search(re.escape(n) + _ASSIGN, line)
            literal = bool(a) and not _PLACEHOLDER.match(a.group("rhs"))
            yield {"name": n, "line": no, "literal_on_line": literal}


def scan(roots, names=NAMES):
    """Return {status, files, hits, ...}. Never any line text."""
    hits, unreadable, scanned = [], [], 0
    for root in roots:
        if not os.path.isdir(root):
            unreadable.append("root")
            continue
        for dp, dns, fns in os.walk(root, onerror=lambda e: unreadable.append(type(e).__name__)):
            dns[:] = [d for d in dns if d not in SKIP_DIRS]
            for fn in fns:
                p = os.path.join(dp, fn)
                try:
                    if os.path.getsize(p) > MAX_BYTES:
                        continue
                    with open(p, "rb") as fh:
                        raw = fh.read()
                    if b"\0" in raw[:4096]:
                        continue
                    text = raw.decode("utf-8", "replace")
                except OSError as e:
                    unreadable.append(type(e).__name__)
                    continue
                scanned += 1
                for h in _line_hits(text, names):
                    hits.append({"path": p, **h})
    status = "unknown" if (unreadable or scanned == 0) else ("found" if hits else "clean")
    return {"status": status, "files_scanned": scanned, "unreadable_count": len(unreadable),
            "hits": hits, "files": sorted({h["path"] for h in hits}),
            "names": list(names), "sent": SENT,
            "scope": "text files up to 5 MB under the roots, UTF-8; names only, never values"}


def check_env(env=None, names=NAMES):
    env = os.environ if env is None else env
    out = {}
    for n in names:
        v = env.get(n)
        if not v:
            out[n] = {"set": False}
            continue
        kind = next((k for pre, k in KEY_KINDS if v.startswith(pre)), "not an anthropic key shape")
        out[n] = {"set": True, "kind": kind if n.startswith("ANTHROPIC") else "n/a"}
    return {"env": out, "sent": SENT}


def exit_code(report):
    return {"clean": EXIT_CLEAN, "found": EXIT_FOUND}.get(report.get("status"), EXIT_UNKNOWN)


def main(argv=None, out=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    out = out or sys.stdout
    cmd = argv.pop(0) if argv else "checklist"
    if cmd == "scan" and argv:
        rep = scan(argv)
        print(json.dumps(rep, indent=1), file=out)
        return exit_code(rep)
    if cmd == "check-env":
        print(json.dumps(check_env(), indent=1), file=out)
        return EXIT_CLEAN
    if cmd == "checklist":
        for who, step in CHECKLIST:
            print(f"[{who}] {step}", file=out)
        print("OWNER-STEP: rotate in the Anthropic console and Railway yourself; this tool never holds a key.", file=out)
        return EXIT_CLEAN
    print("usage: key_names_scan.py scan ROOT... | check-env | checklist", file=out)
    return EXIT_UNKNOWN


if __name__ == "__main__":
    sys.exit(main())
