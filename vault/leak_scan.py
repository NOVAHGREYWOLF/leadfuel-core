"""VAULT S1: a read-only, local leak scanner with a canary that says `unknown` when it is blind.

Slice S1 of the SECRETS-NEVER-SEEN design (sections 7 and 9). It answers one question: has a
secret this process holds already reached a file under the roots it is given (transcripts, logs,
handoff notes, history files)?

What it does:
- It reads the VALUES of the named environment variables from its own process environment, and
  only those. By default the names are RAILWAY_API_TOKEN, HOSTINGER_API_TOKEN and BESTTIME_KEY.
- It searches every file under each root for each value in every form a value usually takes when
  it is written down: raw, base64 and base64url at all three alignments, hex (both cases),
  URL-encoded, and JSON-escaped (once and twice).
- For a secret nobody keeps (generated, placed and forgotten), it takes a declared shape and a
  keyed fingerprint instead of a value, cuts every run of that shape out of the text, and compares
  the run's fingerprint (`hk1:` + 12 hex of an HMAC-SHA256). It finds the secret without holding it.
- It reports secret NAMES, file paths and line numbers. Never the matching text, never any
  encoding of a value, never a value's length.

How it refuses to report a false clean:
- Positive control. Before each run it plants a fresh random canary, in every encoded form, plus
  one canary per declared shape, in `.leak-scan-canary.txt` at the top of every root. If the scan
  does not find every form of its own canary in that file, the root is `unknown`, never `clean`.
- A root whose real content was zero bytes, a file or folder that could not be read, and a named
  secret that is not in the environment are each `unknown`, never `clean`.
- Before anything is printed, the report itself is checked for every scanned value in every form.
  If one is there (a file named after a secret, say), the paths are withheld and only names and
  statuses are printed.
- Any error prints `unknown` and the error's TYPE only: an error's text can quote what it read.

What it does not do: it sets nothing, sends nothing and starts no process. It has no network code
(a test reads its imports). Its only writes are the canary file (removed at the end of the run)
and, if asked for with --state, a local file of per-file offsets and past findings (paths and line
numbers only) so a 15-minute run reads only what was appended. A finding stays reported on later
runs until the state is cleared, because a found secret has already left the machine and must be
rotated (owner card q441 A); the push and the rotation draft are later slices, not this one.

Exit codes: 0 clean, 1 found, 2 unknown. With --canary-only (no secret is read at all): 0 when
every root's canary was found and it held real content, else 2.

There is deliberately no default root: the first real run, over the real roots with the real
values, is the owner's step.
"""
from __future__ import annotations

import argparse
import base64
import fnmatch
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import quote, quote_plus

DEFAULT_NAMES = ("RAILWAY_API_TOKEN", "HOSTINGER_API_TOKEN", "BESTTIME_KEY")
CANARY_FILE = ".leak-scan-canary.txt"
CANARY = "__canary__"
CHUNK = 8 << 20
HEAD_BYTES = 4096
STATE_VERSION = 1
EXIT_CLEAN, EXIT_FOUND, EXIT_UNKNOWN = 0, 1, 2
URLSAFE = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
SENT = "nothing: this scanner has no network code and starts no process"
ERROR_DETAIL = ("the scan failed; the error text is not printed because it could quote a scanned "
                "value. Result is unknown, not clean.")


def fingerprint(key: bytes, candidate: bytes) -> str:
    """The keyed fingerprint the design keeps instead of a value: `hk1:` + 12 hex of HMAC-SHA256."""
    return "hk1:" + hmac.new(key, candidate, hashlib.sha256).hexdigest()[:12]


@dataclass(frozen=True)
class ShapeSpec:
    """A secret that is not held: its name, its shape and its keyed fingerprint."""

    name: str
    alphabet: str
    length: int
    fingerprint: str
    key: bytes = field(repr=False)


@dataclass(frozen=True)
class _Needle:
    secret: str
    form: str
    ident: str
    data: bytes = field(repr=False)


def _b64_fragments(value: bytes, altchars: bytes | None) -> list[bytes]:
    """The part of a value's base64 that does not depend on its neighbours, at all 3 alignments."""
    out = []
    for k in range(3):
        enc = base64.b64encode(b"\0" * k + value, altchars).rstrip(b"=")
        frag = enc[(0, 2, 3)[k]:((k + len(value)) * 8) // 6]
        if frag:
            out.append(frag)
    return out


def encoded_forms(value: str) -> list[tuple[str, bytes]]:
    """Every form this scanner looks for, de-duplicated, first label kept."""
    raw = value.encode("utf-8")
    forms: list[tuple[str, bytes]] = [("raw", raw)]
    forms += [("base64", f) for f in _b64_fragments(raw, None)]
    forms += [("base64url", f) for f in _b64_fragments(raw, b"-_")]
    forms += [("hex", raw.hex().encode()), ("hex", raw.hex().upper().encode())]
    forms += [("url", quote(value, safe="").encode()), ("url", quote_plus(value, safe="").encode())]
    once = json.dumps(value)[1:-1]
    forms += [("json", once.encode()), ("json", json.dumps(value, ensure_ascii=False)[1:-1].encode()),
              ("json", json.dumps(once)[1:-1].encode())]
    seen, out = set(), []
    for label, data in forms:
        if data and data not in seen:
            seen.add(data)
            out.append((label, data))
    return out


def _needles(secret: str, value: str) -> list[_Needle]:
    return [_Needle(secret, label, f"{label}#{i}", data)
            for i, (label, data) in enumerate(encoded_forms(value))]


def _shape_regex(spec: ShapeSpec) -> re.Pattern:
    cls = "".join(re.escape(c) for c in spec.alphabet).encode()
    return re.compile(b"(?<![" + cls + b"])[" + cls + b"]{" + str(spec.length).encode()
                      + b"}(?![" + cls + b"])")


class _Matcher:
    def __init__(self, needles: list[_Needle], shapes: list[ShapeSpec]):
        self.needles = needles
        self.shapes = [(s, _shape_regex(s)) for s in shapes]
        lengths = [len(n.data) for n in needles] + [s.length for s in shapes]
        # +2: one byte of look-behind context and one of look-ahead for the shape runs.
        self.overlap = (max(lengths) if lengths else 0) + 2

    def matches(self, buf: bytes):
        for n in self.needles:
            i = buf.find(n.data)
            while i != -1:
                yield i, i + len(n.data), n.secret, n.form, n.ident
                i = buf.find(n.data, i + 1)
        for spec, rx in self.shapes:
            for m in rx.finditer(buf):
                if hmac.compare_digest(fingerprint(spec.key, m.group()), spec.fingerprint):
                    yield m.start(), m.end(), spec.name, "shape", "shape:" + spec.name


def _open_for_read(path: str):
    """The scanner's one way to open a scanned file (read-only). Tests replace it."""
    return open(path, "rb")


def _head_hash(path: str, upto: int) -> str:
    with _open_for_read(path) as fh:
        return hashlib.sha256(fh.read(min(upto, HEAD_BYTES))).hexdigest()


def _scan_file(path: str, matcher: _Matcher, offset: int, lines_at_offset: int):
    """Scan from `offset` to the end. Returns hits, the new end, its line count, new bytes read.

    Re-reads `overlap` bytes before `offset`, so a value that straddles the old end is found; a
    match is reported only if it ENDS past the old end, so nothing found before is found twice.
    """
    hits = []
    overlap = matcher.overlap
    read_from = max(0, offset - overlap)
    with _open_for_read(path) as fh:
        fh.seek(read_from)
        # The first read always holds every re-read byte, so the line count at its start is right.
        pending = fh.read(offset - read_from + CHUNK)
        tail = b""
        bstart = read_from
        limit = offset
        lines_at_bstart = None
        while True:
            nxt = fh.read(CHUNK) if pending else b""
            eof = not nxt
            buf = tail + pending
            bend = bstart + len(buf)
            if lines_at_bstart is None:
                lines_at_bstart = lines_at_offset - buf[:offset - read_from].count(b"\n")
            # A match touching the buffer's end could continue in the next chunk: defer it.
            upper = bend if eof else bend - 1
            for s, e, secret, form, ident in matcher.matches(buf):
                if limit < bstart + e <= upper:
                    hits.append((secret, form, ident, lines_at_bstart + buf.count(b"\n", 0, s) + 1))
            limit = max(limit, upper)
            if eof:
                return hits, bend, lines_at_bstart + buf.count(b"\n"), max(0, bend - offset)
            keep = min(len(buf), overlap)
            tail = buf[len(buf) - keep:]
            lines_at_bstart += buf[:len(buf) - keep].count(b"\n")
            bstart = bend - keep
            pending = nxt


def _excluded(rel: str, excludes) -> bool:
    rel = rel.replace(os.sep, "/")
    return any(fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(rel.rsplit("/", 1)[-1], p) for p in excludes)


def _walk(root: str, excludes, unreadable: list):
    def onerror(err):
        unreadable.append(getattr(err, "filename", None) or root)

    for dirpath, dirnames, filenames in os.walk(root, onerror=onerror):
        rel_dir = os.path.relpath(dirpath, root)
        dirnames[:] = sorted(d for d in dirnames
                             if not _excluded(os.path.normpath(os.path.join(rel_dir, d)), excludes))
        for name in sorted(filenames):
            rel = os.path.normpath(os.path.join(rel_dir, name))
            if not _excluded(rel, excludes):
                yield os.path.join(dirpath, name), rel


def _plant(root: str, value: str, shape_canaries: list[tuple[ShapeSpec, str]]):
    """Write the canary file at the top of `root`. Returns its path, or None if it could not."""
    if not os.path.isdir(root):
        return None
    lines = ["leak_scan canary: random, not a secret; written at the start of a run, removed at its end"]
    lines += [f"{label} {data.decode('utf-8', 'replace')}" for label, data in encoded_forms(value)]
    lines += [f"shape {canary}" for _spec, canary in shape_canaries]
    path = os.path.join(root, CANARY_FILE)
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines) + "\n")
    except OSError:
        return None
    return path


def _remove(path):
    try:
        os.remove(path)
        return True
    except OSError:
        return False


def _fresh_canary() -> str:
    # Mixed in: characters that make the url and json forms differ from the raw one, so the
    # canary proves those paths too.
    return secrets.token_urlsafe(24) + '+/="\\ ' + secrets.token_urlsafe(8)


def _shape_canary(spec: ShapeSpec) -> tuple[ShapeSpec, str]:
    value = "".join(secrets.choice(spec.alphabet) for _ in range(spec.length))
    return ShapeSpec(CANARY + spec.name, spec.alphabet, spec.length,
                     fingerprint(spec.key, value.encode()), spec.key), value


def _scrub(report: dict, needles: list[_Needle]) -> dict:
    """Withhold the report's paths if it would print a scanned value in any form."""
    text = json.dumps(report, ensure_ascii=False)
    blob, blob_ascii = text.encode("utf-8"), json.dumps(report).encode()
    if not any(n.data in blob or n.data in blob_ascii for n in needles):
        return report
    minimal = {
        "tool": report["tool"],
        "result": report["result"],
        "sent": SENT,
        "withheld": "the report would have printed a scanned value (a path or file name holds one), "
                    "so every path is withheld; names and statuses only",
        "secrets": report["secrets"],
    }
    text = json.dumps(minimal)
    if any(n.data in text.encode() for n in needles):
        return {"tool": report["tool"], "result": "unknown", "sent": SENT, "withheld": "everything"}
    return minimal


def scan(roots, *, names=DEFAULT_NAMES, env=None, shapes=(), state=None, full=False,
         excludes=(), canary_only=False):
    """Scan `roots`. Returns (report, new_state). Reads values for `names` from `env` only."""
    env = os.environ if env is None else env
    names = [] if canary_only else list(names)
    shapes = [] if canary_only else list(shapes)
    values = {n: env.get(n) or None for n in names}  # the only place a value is read
    needles: list[_Needle] = []
    for n, v in values.items():
        if v:
            needles += _needles(n, v)
    secret_needles = list(needles)
    canary_value = _fresh_canary()
    shape_canaries = [_shape_canary(s) for s in shapes]
    canary_needles = _needles(CANARY, canary_value)
    expected = {n.ident for n in canary_needles} | {"shape:" + s.name for s, _ in shape_canaries}
    matcher = _Matcher(needles + canary_needles, shapes + [s for s, _ in shape_canaries])

    scanned_names = sorted(names + [s.name for s in shapes])
    prior = state if isinstance(state, dict) and state.get("version") == STATE_VERSION else {}
    use_offsets = (not full) and prior.get("names") == scanned_names
    old_files = prior.get("files", {}) if use_offsets else {}
    findings = [dict(f, new=False) for f in prior.get("findings", [])
                if isinstance(f, dict) and f.get("secret") in scanned_names]
    seen = {(f["secret"], f["path"], f["line"], f["form"]) for f in findings}
    new_files: dict = {}
    roots_out = []

    planted = {}
    try:
        for root in roots:
            planted[root] = _plant(root, canary_value, shape_canaries)
        for root in roots:
            canary_path = planted[root]
            unreadable: list = []
            files = scanned = covered = 0
            found_canary: set = set()
            for path, rel in _walk(root, excludes, unreadable):
                is_canary = canary_path is not None and rel == CANARY_FILE
                key = os.path.abspath(path)
                old = None if is_canary else old_files.get(key)
                try:
                    size = os.stat(path).st_size
                    offset, lines = 0, 0
                    if old and old.get("offset", 0) <= size \
                            and _head_hash(path, old["offset"]) == old.get("head"):
                        offset, lines = old["offset"], old["lines"]
                    hits, end, end_lines, read = _scan_file(path, matcher, offset, lines)
                except OSError:
                    unreadable.append(path)
                    continue
                files += 1
                if is_canary:
                    found_canary |= {ident for secret, _f, ident, _l in hits
                                     if secret == CANARY or secret.startswith(CANARY)}
                    continue
                scanned += read
                covered += end
                new_files[key] = {"offset": end, "lines": end_lines, "head": _head_hash(path, end)}
                for secret, form, _ident, line in hits:
                    if secret == CANARY or secret.startswith(CANARY):
                        continue
                    k = (secret, path, line, form)
                    if k not in seen:
                        seen.add(k)
                        findings.append({"secret": secret, "path": path, "line": line,
                                         "form": form, "new": True})
            if canary_path is None:
                canary = "not planted (root missing or not writable)"
            elif found_canary >= expected:
                canary = "found"
            else:
                canary = "missing"
            blind = []
            if canary != "found":
                blind.append("canary " + canary.split(" ")[0])
            if covered == 0:
                blind.append("zero bytes of real content")
            if unreadable:
                blind.append(f"{len(unreadable)} unreadable path(s)")
            roots_out.append({"root": root, "canary": canary, "files_scanned": files,
                              "bytes_scanned": scanned, "bytes_covered": covered,
                              "unreadable": unreadable, "blind": blind})
    finally:
        removed = all(_remove(p) for p in planted.values() if p)

    blind_roots = [r["root"] for r in roots_out if r["blind"]] or ([] if roots else ["(no root given)"])
    statuses = {}
    for n in scanned_names:
        if any(f["secret"] == n for f in findings):
            statuses[n] = {"status": "found", "why": "see findings; a found secret has left the "
                                                     "machine, so rotate it (q441 A)"}
        elif n in values and not values[n]:
            statuses[n] = {"status": "unknown", "why": "not in this process's environment, so not checked"}
        elif blind_roots:
            statuses[n] = {"status": "unknown", "why": "blind under: " + ", ".join(blind_roots)}
        else:
            statuses[n] = {"status": "clean", "why": "every root seen in full and its canary found"}

    if canary_only:
        result = "unknown" if blind_roots else "canary-ok"
    elif any(s["status"] == "found" for s in statuses.values()):
        result = "found"
    elif any(s["status"] == "unknown" for s in statuses.values()) or not statuses:
        result = "unknown"
    else:
        result = "clean"

    report = {
        "tool": "leak_scan (VAULT S1)",
        "result": result,
        "at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "canary-only" if canary_only else ("incremental" if use_offsets else "full"),
        "sent": SENT,
        "secrets": statuses,
        "findings": findings,
        "roots": roots_out,
        "canary_removed": removed,
    }
    new_state = {"version": STATE_VERSION, "names": scanned_names, "files": new_files,
                 "findings": [{k: f[k] for k in ("secret", "path", "line", "form")} for f in findings]}
    return _scrub(report, secret_needles), new_state


def exit_code(report: dict) -> int:
    return {"clean": EXIT_CLEAN, "canary-ok": EXIT_CLEAN, "found": EXIT_FOUND}.get(
        report.get("result"), EXIT_UNKNOWN)


def _load_state(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None  # no usable state: a full scan, never a skipped one


def _save_state(path, state):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=1)
    os.replace(tmp, path)


def _parse(argv):
    p = argparse.ArgumentParser(prog="leak_scan", description=__doc__.split("\n\n")[0])
    p.add_argument("--root", action="append", required=True,
                   help="a folder to scan (repeat for more). There is no default.")
    p.add_argument("--names", default=",".join(DEFAULT_NAMES),
                   help="comma-separated environment variable NAMES whose values to look for")
    p.add_argument("--canary-only", action="store_true",
                   help="read no secret at all; prove only that every root can be seen")
    p.add_argument("--state", help="offsets file for incremental runs (paths and line numbers only)")
    p.add_argument("--full", action="store_true", help="ignore the offsets and scan everything")
    p.add_argument("--exclude", action="append", default=[], help="glob on a relative path or name")
    return p.parse_args(argv)


def main(argv=None, env=None, out=None) -> int:
    out = out or sys.stdout
    args = _parse(argv)
    try:
        names = [n.strip() for n in args.names.split(",") if n.strip()]
        state = _load_state(args.state) if args.state and not args.full else None
        report, new_state = scan(args.root, names=names, env=env, state=state, full=args.full,
                                 excludes=args.exclude, canary_only=args.canary_only)
        if args.state:
            _save_state(args.state, new_state)
    except Exception as exc:  # noqa: BLE001 - the type only; the text could quote a value
        out.write(json.dumps({"tool": "leak_scan (VAULT S1)", "result": "unknown", "sent": SENT,
                              "error": type(exc).__name__, "detail": ERROR_DETAIL}, indent=2) + "\n")
        return EXIT_UNKNOWN
    out.write(json.dumps(report, indent=2) + "\n")
    return exit_code(report)


if __name__ == "__main__":
    sys.exit(main())
