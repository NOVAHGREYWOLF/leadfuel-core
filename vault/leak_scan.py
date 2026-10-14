"""VAULT S1: a read-only, local leak scanner with a canary that says `unknown` when it is blind.

Slice S1 of the SECRETS-NEVER-SEEN design (sections 7 and 9). It answers one question: has a
secret this process holds already reached a file under the roots it is given (transcripts, logs,
handoff notes, history files)?

What it does:
- It reads the VALUES of the named environment variables from its own process environment, and
  only those. By default the names are RAILWAY_API_TOKEN, HOSTINGER_API_TOKEN and BESTTIME_KEY.
- It searches every file under each root for each value in every form a value usually takes when
  it is written down: raw, base64 and base64url at all three alignments (also when the base64 is
  wrapped across lines, as MIME, PEM and certutil do), hex (both cases), URL-encoded, JSON-escaped
  (once and twice, with and without the `\\/` slash escape), and the raw value as UTF-16 (LE and
  BE, which is what Windows PowerShell redirection writes). A value with stray whitespace is
  also searched stripped. It also matches every file and folder NAME under a root.
- Every report lists the forms it looked for, the `--exclude` patterns in force, and a
  `not_looked_for` list (compressed content such as git objects, truncated values, and the
  rest), so `clean` states its own scope and never reads as "not written down anywhere".
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
(a test reads its imports). Its only writes are the canary file (created exclusively, so it never
touches a file that already has that name, and removing only the one it created; removed at the
end of the run) and, if asked for with --state, three small local files: the state, its `.tmp`,
and `<state>.key`, a random 32-byte key made once.

The state holds, per file, an HMAC of the file's path (never the path), the offset and line count,
and an HMAC (under that key) of the WHOLE prefix before the offset, plus past findings (paths and
line numbers only). It never holds a value, an unkeyed hash of content, or a path that holds a
scanned value (such a path is stored as `<withheld>`). A resumed file has its whole prefix
re-read and re-hashed, so an edit anywhere before the old offset makes it rescan from the start;
what a resumed run saves is the matching, not the reading. Keep the key file out of any place the
state is copied to. Without a usable key, every run is a full scan.

A finding stays reported on every later run until it is cleared on purpose (`--clear-findings`):
`--full` resets only the offsets, a shorter `--names` list keeps the other names' findings, and an
unusable state file makes the run `unknown` without overwriting it. A found secret has already
left the machine and must be rotated (owner card q441 A); the push and the rotation draft are
later slices, not this one.

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
STATE_VERSION = 2
WITHHELD = "<withheld>"
WRAPPABLE = ("base64", "base64url")
_EOL = re.compile(rb"[\r\n]")
FORMS = ("raw", "base64", "base64url", "base64 (line-wrapped)", "hex", "url", "json (once and twice, "
         "with and without the \\/ slash escape)", "utf-16le", "utf-16be", "file and folder names")
NOT_LOOKED_FOR = (
    "compressed content (zlib, gzip, zip), which includes every git object and packfile: a clean "
    "over a repository root says nothing about what was committed",
    "the other encodings of a value as UTF-16 (only its raw form is searched there), and any "
    "encoding not named in `forms`",
    "a truncated or partly redacted value, and a value split across lines in a way other than "
    "base64 wrapped at line ends",
    "the names of empty folders (a file or a folder that holds a file is matched by name)",
    "any file an --exclude pattern hides (see `excludes`)",
    "a value that was never in this process's environment under the names given",
)
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
    once_u = json.dumps(value, ensure_ascii=False)[1:-1]
    # `\/` is the slash escape some serialisers (PHP, a few JSON libraries) write.
    once_s, once_us = once.replace("/", "\\/"), once_u.replace("/", "\\/")
    forms += [("json", once.encode()), ("json", once_u.encode()), ("json", once_s.encode()),
              ("json", once_us.encode()), ("json", json.dumps(once)[1:-1].encode()),
              ("json", json.dumps(once_s)[1:-1].encode())]
    forms += [("utf-16le", value.encode("utf-16-le")), ("utf-16be", value.encode("utf-16-be"))]
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
        self.wrappable = [n for n in needles if n.form in WRAPPABLE]
        lengths = [len(n.data) for n in needles] + [s.length for s in shapes]
        # Doubled so a base64 needle with line breaks inside it (a CRLF every few columns) still
        # fits; +2: one byte of look-behind context and one of look-ahead for the shape runs.
        self.overlap = 2 * (max(lengths) if lengths else 0) + 2

    def matches(self, buf: bytes):
        for n in self.needles:
            i = buf.find(n.data)
            while i != -1:
                yield i, i + len(n.data), n.secret, n.form, n.ident
                i = buf.find(n.data, i + 1)
        if self.wrappable and b"\n" in buf:
            yield from self._wrapped(buf)
        for spec, rx in self.shapes:
            for m in rx.finditer(buf):
                if hmac.compare_digest(fingerprint(spec.key, m.group()), spec.fingerprint):
                    yield m.start(), m.end(), spec.name, "shape", "shape:" + spec.name

    def _wrapped(self, buf: bytes):
        """base64 with line breaks inside it: search the buffer with CR and LF taken out.

        Only a match that really spans a removed byte is yielded (an unwrapped one was found by
        the plain search), with the `~wrap` ident so the canary can prove this path separately.
        """
        flat = buf.translate(None, b"\r\n")
        removed: list[int] = []

        def original(i: int) -> int:
            if not removed:
                removed.extend(m.start() for m in _EOL.finditer(buf))
            o = i
            for p in removed:
                if p <= o:
                    o += 1
                else:
                    break
            return o

        for n in self.wrappable:
            j = flat.find(n.data)
            while j != -1:
                start, end = original(j), original(j + len(n.data) - 1) + 1
                if end - start > len(n.data):
                    yield start, end, n.secret, n.form, n.ident + "~wrap"
                j = flat.find(n.data, j + 1)


def _open_for_read(path: str):
    """The scanner's one way to open a scanned file (read-only). Tests replace it."""
    return open(path, "rb")


def _subkey(key: bytes, purpose: bytes) -> bytes:
    return hmac.new(key, purpose, hashlib.sha256).digest()


def _prefix_mac(path: str, upto: int, key: bytes):
    """A keyed MAC over the first `upto` bytes (all of them: an edit anywhere in the prefix must
    show). Returns (the live MAC object, the bytes actually read)."""
    mac = hmac.new(_subkey(key, b"leak_scan content"), digestmod=hashlib.sha256)
    done = 0
    with _open_for_read(path) as fh:
        while done < upto:
            block = fh.read(min(CHUNK, upto - done))
            if not block:
                break
            mac.update(block)
            done += len(block)
    return mac, done


def _path_key(key: bytes, abspath: str) -> str:
    """What the state holds in place of a path."""
    return hmac.new(_subkey(key, b"leak_scan path"), abspath.encode("utf-8", "surrogatepass"),
                    hashlib.sha256).hexdigest()[:40]


def _scan_file(path: str, matcher: _Matcher, offset: int, lines_at_offset: int, mac=None):
    """Scan from `offset` to the end. Returns hits, the new end, its line count, new bytes read.

    Re-reads `overlap` bytes before `offset`, so a value that straddles the old end is found; a
    match is reported only if it ENDS past the old end, so nothing found before is found twice.
    If `mac` is given it has already seen the bytes before `offset`; this feeds it the rest, so
    afterwards it covers exactly the bytes up to the returned end.
    """
    hits = []
    overlap = matcher.overlap
    read_from = max(0, offset - overlap)
    with _open_for_read(path) as fh:
        fh.seek(read_from)
        # The first read always holds every re-read byte, so the line count at its start is right.
        pending = fh.read(offset - read_from + CHUNK)
        if mac is not None:
            mac.update(pending[offset - read_from:])
        tail = b""
        bstart = read_from
        limit = offset
        lines_at_bstart = None
        while True:
            nxt = fh.read(CHUNK) if pending else b""
            if mac is not None:
                mac.update(nxt)
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
    """Create the canary file at the top of `root`. Returns its path, or None if it could not.

    Created exclusively ("x"): a file that already has this name is never overwritten, and since
    the caller removes only a path this returns, never deleted either.
    """
    if not os.path.isdir(root):
        return None
    lines = [b"leak_scan canary: random, not a secret; written at the start of a run, removed at its end"]
    forms = encoded_forms(value)
    lines += [label.encode() + b" " + data for label, data in forms]
    # One line per base64 form with a line break inside it, so the wrapped path is proven too.
    lines += [b"wrapped-" + label.encode() + b" " + data[:len(data) // 2] + b"\n" + data[len(data) // 2:]
              for label, data in forms if label in WRAPPABLE and len(data) > 1]
    lines += [b"shape " + canary.encode() for _spec, canary in shape_canaries]
    path = os.path.join(root, CANARY_FILE)
    try:
        fh = open(path, "xb")
    except OSError:  # includes FileExistsError: not ours, so not touched
        return None
    try:
        with fh:
            fh.write(b"\n".join(lines) + b"\n")
    except OSError:
        _remove(path)  # we created it just now, so removing it is ours to do
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


def _holds_value(text: str, needles: list[_Needle]) -> bool:
    """True if `text` holds any scanned value in any form, raw or as it would sit inside JSON."""
    blobs = (text.encode("utf-8", "replace"), json.dumps(text).encode(),
             json.dumps(text, ensure_ascii=False).encode("utf-8", "replace"))
    return any(n.data in b for n in needles for b in blobs)


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
        "excludes": report["excludes"],
    }
    text = json.dumps(minimal)
    if any(n.data in text.encode() for n in needles):
        return {"tool": report["tool"], "result": "unknown", "sent": SENT, "withheld": "everything"}
    return minimal


def _state_path(path: str, needles: list[_Needle]) -> str:
    """The path as the state may hold it: a path that embeds a scanned value is not stored."""
    return WITHHELD if _holds_value(path, needles) else path


def _state_for_disk(state: dict, needles: list[_Needle]) -> dict:
    """Last line of defence before the state is written: no scanned value in any form, ever."""
    def dump(s):
        return json.dumps(s, ensure_ascii=False), json.dumps(s)

    if not any(_holds_value(t, needles) for t in dump(state)):
        return state
    blanked = dict(state, findings=[dict(f, path=WITHHELD) for f in state["findings"]])
    if any(_holds_value(t, needles) for t in dump(blanked)):
        raise ValueError("the state would hold a scanned value")  # the type is printed, not the text
    return blanked


def _usable_findings(state: dict) -> list[dict]:
    out = []
    for f in state.get("findings", []):
        if isinstance(f, dict) and isinstance(f.get("secret"), str) and isinstance(f.get("path"), str) \
                and isinstance(f.get("line"), int) and isinstance(f.get("form"), str):
            out.append({k: f[k] for k in ("secret", "path", "line", "form")})
    return out


def scan(roots, *, names=DEFAULT_NAMES, env=None, shapes=(), state=None, full=False,
         excludes=(), canary_only=False, key=None, clear_findings=False):
    """Scan `roots`. Returns (report, new_state). Reads values for `names` from `env` only.

    `key` is the state key (see the module docstring). Without it no file offsets are kept, so
    every run is a full scan. `full` ignores the offsets; it never drops earlier findings, which
    go only with `clear_findings`.
    """
    env = os.environ if env is None else env
    names = [] if canary_only else list(names)
    shapes = [] if canary_only else list(shapes)
    excludes = list(excludes)
    # The only place a value is read. A blank (whitespace-only) value is "not set": it would match
    # everything, and a scan for it would say nothing.
    values = {n: (env.get(n) or None) for n in names}
    values = {n: (v if v and v.strip() else None) for n, v in values.items()}
    needles: list[_Needle] = []
    for n, v in values.items():
        if v:
            needles += _needles(n, v)
            if v.strip() and v.strip() != v:  # stray whitespace around a value in the environment
                needles += [x for x in _needles(n, v.strip()) if x.data not in {y.data for y in needles}]
    secret_needles = list(needles)
    canary_value = _fresh_canary()
    shape_canaries = [_shape_canary(s) for s in shapes]
    canary_needles = _needles(CANARY, canary_value)
    expected = {n.ident for n in canary_needles} | {"shape:" + s.name for s, _ in shape_canaries}
    expected |= {n.ident + "~wrap" for n in canary_needles if n.form in WRAPPABLE}
    matcher = _Matcher(needles + canary_needles, shapes + [s for s, _ in shape_canaries])

    scanned_names = sorted(names + [s.name for s in shapes])
    prior = state if isinstance(state, dict) and state.get("version") == STATE_VERSION else {}
    use_offsets = (not full) and key is not None and prior.get("names") == scanned_names
    old_files = prior.get("files", {}) if use_offsets else {}
    # Earlier findings stay (q441 A: a found secret has left the machine, whatever happens to the
    # file), for every name, scanned this run or not. Only clear_findings drops them.
    findings = [] if (clear_findings or canary_only) else \
        [dict(f, new=False) for f in _usable_findings(prior)]
    seen = {(f["secret"], _state_path(f["path"], secret_needles), f["line"], f["form"])
            for f in findings}

    def add_finding(secret, path, line, form):
        k = (secret, _state_path(path, secret_needles), line, form)
        if k not in seen:
            seen.add(k)
            findings.append({"secret": secret, "path": path, "line": line, "form": form, "new": True})

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
                if not is_canary and secret_needles:  # a value in a file or folder NAME
                    rel_bytes = rel.replace(os.sep, "/").encode("utf-8", "replace")
                    for sn in secret_needles:
                        if sn.data in rel_bytes:
                            add_finding(sn.secret, path, 0, "path")
                abspath = os.path.abspath(path)
                old = None if (is_canary or key is None) else old_files.get(_path_key(key, abspath))
                old = old if isinstance(old, dict) else None
                try:
                    size = os.stat(path).st_size
                    offset, lines = 0, 0
                    mac = hmac.new(_subkey(key, b"leak_scan content"), digestmod=hashlib.sha256) \
                        if key is not None and not is_canary else None
                    if old and isinstance(old.get("offset"), int) and 0 < old["offset"] <= size:
                        prefix, got = _prefix_mac(path, old["offset"], key)
                        if got == old["offset"] and hmac.compare_digest(prefix.hexdigest(),
                                                                         str(old.get("mac"))):
                            offset, lines, mac = old["offset"], int(old.get("lines", 0)), prefix
                    hits, end, end_lines, read = _scan_file(path, matcher, offset, lines, mac)
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
                if key is not None:
                    new_files[_path_key(key, abspath)] = {"offset": end, "lines": end_lines,
                                                          "mac": mac.hexdigest()}
                for secret, form, _ident, line in hits:
                    if secret == CANARY or secret.startswith(CANARY):
                        continue
                    add_finding(secret, path, line, form)
            if canary_path is None:
                if os.path.lexists(os.path.join(root, CANARY_FILE)):
                    canary = ("not planted (a file named " + CANARY_FILE + " already exists here and "
                              "was left alone; if a killed run left it, delete it by hand)")
                else:
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
                              "unreadable": unreadable, "excludes": excludes, "blind": blind})
    finally:
        removed = all(_remove(p) for p in planted.values() if p)

    blind_roots = [r["root"] for r in roots_out if r["blind"]] or ([] if roots else ["(no root given)"])
    scope = ("except files matching --exclude " + ", ".join(excludes)) if excludes else "no --exclude"
    statuses = {}
    for n in sorted(set(scanned_names) | {f["secret"] for f in findings}):
        if any(f["secret"] == n for f in findings):
            statuses[n] = {"status": "found", "why": "see findings; a found secret has left the "
                                                     "machine, so rotate it (q441 A)"}
        elif n in values and not values[n]:
            statuses[n] = {"status": "unknown", "why": "not in this process's environment, so not checked"}
        elif blind_roots:
            statuses[n] = {"status": "unknown", "why": "blind under: " + ", ".join(blind_roots)}
        else:
            statuses[n] = {"status": "clean",
                           "why": "every root seen in full and its canary found (" + scope + "); "
                                  "clean for the listed forms only, see not_looked_for"}

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
        "forms": list(FORMS),
        "excludes": excludes,
        "not_looked_for": list(NOT_LOOKED_FOR),
        "roots": roots_out,
        "canary_removed": removed,
    }
    new_state = {"version": STATE_VERSION, "names": scanned_names, "files": new_files,
                 "findings": [{"secret": f["secret"], "path": _state_path(f["path"], secret_needles),
                               "line": f["line"], "form": f["form"]} for f in findings]}
    return _scrub(report, secret_needles), _state_for_disk(new_state, secret_needles)


def exit_code(report: dict) -> int:
    return {"clean": EXIT_CLEAN, "canary-ok": EXIT_CLEAN, "found": EXIT_FOUND}.get(
        report.get("result"), EXIT_UNKNOWN)


def _load_state(path):
    """Returns (state, usable). A missing file is a first run; one that exists and cannot be used
    is NOT: it may hold earlier findings, so the caller must not overwrite it."""
    try:
        with open(path, encoding="utf-8") as fh:
            state = json.load(fh)
    except FileNotFoundError:
        return None, True
    except (OSError, ValueError):
        return None, False
    if not isinstance(state, dict) or state.get("version") != STATE_VERSION:
        return None, False
    return state, True


def _load_key(state_path):
    """The state key, from `<state>.key`; made on first use. None if it cannot be had (then every
    run is a full scan: slower, never wrong)."""
    path = state_path + ".key"
    for _ in range(2):
        try:
            with open(path, "rb") as fh:
                data = fh.read()
            return data if len(data) == 32 else None
        except FileNotFoundError:
            pass
        except OSError:
            return None
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
            with os.fdopen(fd, "wb") as fh:
                fh.write(secrets.token_bytes(32))
        except FileExistsError:
            continue
        except OSError:
            return None
    return None


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
    p.add_argument("--state", help="offsets and findings file for incremental runs (no values, no "
                                   "paths that hold one, no unkeyed hashes); its key is <state>.key")
    p.add_argument("--full", action="store_true",
                   help="ignore the offsets and scan everything (earlier findings are kept)")
    p.add_argument("--clear-findings", action="store_true",
                   help="drop the earlier findings held in --state (the only way they go)")
    p.add_argument("--exclude", action="append", default=[],
                   help="glob on a relative path or name; the report lists every one")
    return p.parse_args(argv)


def main(argv=None, env=None, out=None) -> int:
    out = out or sys.stdout
    args = _parse(argv)
    try:
        names = [n.strip() for n in args.names.split(",") if n.strip()]
        keep_state = bool(args.state) and not args.canary_only
        state, usable = _load_state(args.state) if keep_state else (None, True)
        if not usable:
            out.write(json.dumps({"tool": "leak_scan (VAULT S1)", "result": "unknown", "sent": SENT,
                                  "error": "StateUnusable",
                                  "detail": "the --state file exists but cannot be used, and it may "
                                            "hold earlier findings, so it was not scanned over or "
                                            "overwritten. Move it aside on purpose to start again."},
                                 indent=2) + "\n")
            return EXIT_UNKNOWN
        key = _load_key(args.state) if keep_state else None
        report, new_state = scan(args.root, names=names, env=env, state=state, full=args.full,
                                 excludes=args.exclude, canary_only=args.canary_only, key=key,
                                 clear_findings=args.clear_findings)
        if keep_state:
            _save_state(args.state, new_state)
    except Exception as exc:  # noqa: BLE001 - the type only; the text could quote a value
        out.write(json.dumps({"tool": "leak_scan (VAULT S1)", "result": "unknown", "sent": SENT,
                              "error": type(exc).__name__, "detail": ERROR_DETAIL}, indent=2) + "\n")
        return EXIT_UNKNOWN
    out.write(json.dumps(report, indent=2) + "\n")
    return exit_code(report)


if __name__ == "__main__":
    sys.exit(main())
