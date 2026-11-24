"""Cluster files parts 2+3 (+ the report-only half of 5): a local file index, search, and an
exact-duplicate report. Stdlib only. All local: nothing in this file opens a network socket except
`serve`, which binds loopback and refuses any other address.

Read-only by construction: the scanner opens files for reading only, never writes, moves, renames or
deletes anything it indexes. The dedupe report PROPOSES a canonical copy per group; the page records
clicks (Keep canonical / Keep both / Decide later) and nothing else. Applying a click is a separate,
gated step that this file does not contain.

Honesty rules this file keeps:
- A directory that cannot be listed is recorded as `unreadable` and its old rows are kept, never
  reported as empty or removed.
- A scan that stopped early (time budget, Ctrl-C, error) is `partial`; only a `complete` scan may
  drop rows for files that disappeared.
- A machine with no complete scan reads `unknown (not indexed yet)` in search, never "0 results".
- Content that was not extracted (private tier, pdf, cloud placeholder, too big, pending) is counted
  and reported, so a content search with no hit says how much it could not see.

Privacy tier: paths that look like health, financial or credential material are indexed by name,
size and date only. Their content is never read: no extract, no hash.

Index location: %LOCALAPPDATA%\\cluster_files\\index.sqlite (outside git); see node/FILE_INDEX.md.
"""
from __future__ import annotations

import argparse
import ctypes
import fnmatch
import hashlib
import html
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

SCHEMA_VERSION = 1
KNOWN_MACHINES = ("overlord", "r710", "r620", "greywolf", "surface", "msi")

# Directory names never descended into, anywhere.
SKIP_DIR_NAMES = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache",
                  ".pytest_cache", ".ruff_cache", "$recycle.bin", "system volume information",
                  ".tox", ".gradle"}
# Path fragments never descended into (lower case, os.sep normalised to "/").
SKIP_PATH_PARTS = ("/.claude/worktrees",)
# The book is a separate estate: never indexed as part of anything else.
BOOK_PART = "/repos/resonance"

# Pilot exclusions for GREYWOLF F:\ (owner brief: "excluding repos").
PILOT_EXCLUDES = ("F:/repos", "F:/Leadfuel/repos")

PRIVATE_TOKENS = {
    "health": {"health", "healthkit", "medical", "medicine", "therapy", "doctor", "prescription",
               "prescriptions", "hipaa", "diagnosis", "labs"},
    "financial": {"finance", "finances", "financial", "bank", "banking", "tax", "taxes", "irs",
                  "quickbooks", "payroll", "brokerage", "invoice", "invoices", "w2", "1099",
                  "statements"},
    "credential": {"secret", "secrets", "credential", "credentials", "password", "passwords",
                   "keys", "ssh", "gnupg", "gpg", "keepass", "keychain", "tokens", "vaultwarden",
                   "bitwarden", "1password"},
}
PRIVATE_FILE_GLOBS = (".env", ".env.*", "*.env", "*.pem", "*.key", "*.pfx", "*.p12", "*.kdbx",
                      "*.ppk", "id_rsa*", "id_ed25519*", "id_ecdsa*", "id_dsa*", "credentials*",
                      "*secret*", "*password*", "*token*.json", "known_hosts", "authorized_keys",
                      "*.keychain*", "login data", "cookies*.sqlite", "*.ovpn", "*.jks")

TEXT_EXT = {".txt", ".md", ".markdown", ".rst", ".csv", ".tsv", ".json", ".jsonl", ".yaml",
            ".yml", ".toml", ".ini", ".cfg", ".conf", ".log", ".py", ".ps1", ".psm1", ".js",
            ".mjs", ".ts", ".tsx", ".jsx", ".html", ".htm", ".css", ".sql", ".sh", ".bat",
            ".cmd", ".xml", ".tex", ".srt", ".vtt", ".org", ".rs", ".go", ".java", ".c", ".h",
            ".cpp", ".cs", ".rb", ".php", ".swift", ".kt", ".lua", ".r", ".ipynb"}
ZIP_DOC_EXT = {".docx": ("word/document.xml",), ".pptx": ("ppt/slides/",),
               ".xlsx": ("xl/sharedStrings.xml",), ".odt": ("content.xml",),
               ".ods": ("content.xml",), ".odp": ("content.xml",)}
NO_EXTRACTOR_EXT = {".pdf", ".doc", ".xls", ".ppt", ".rtf", ".epub", ".pages", ".key"}
# Machine output: large and noisy. Name and path are indexed; content is not (reported as unknown).
NOISY_EXT = {".log", ".jsonl"}

TYPE_OF_EXT = {}
for _t, _exts in {
    "doc": TEXT_EXT - {".py", ".ps1", ".psm1", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".css",
                       ".sql", ".sh", ".bat", ".cmd", ".rs", ".go", ".java", ".c", ".h", ".cpp",
                       ".cs", ".rb", ".php", ".swift", ".kt", ".lua", ".r", ".ipynb", ".json",
                       ".jsonl", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".csv", ".tsv",
                       ".log", ".xml"} | set(ZIP_DOC_EXT) | NO_EXTRACTOR_EXT,
    "code": {".py", ".ps1", ".psm1", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".css", ".sql", ".sh",
             ".bat", ".cmd", ".rs", ".go", ".java", ".c", ".h", ".cpp", ".cs", ".rb", ".php",
             ".swift", ".kt", ".lua", ".r", ".ipynb"},
    "data": {".json", ".jsonl", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".csv", ".tsv",
             ".log", ".xml", ".sqlite", ".db", ".parquet", ".duckdb"},
    "image": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif", ".bmp", ".tif", ".tiff",
              ".svg", ".raw", ".cr2", ".nef", ".dng", ".psd", ".ico"},
    "video": {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".wmv", ".mts"},
    "audio": {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg", ".opus", ".wma"},
    "archive": {".zip", ".7z", ".rar", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".zst", ".iso",
                ".img", ".vhd", ".vhdx", ".vmdk", ".qcow2", ".vma", ".dmg"},
    "binary": {".exe", ".dll", ".msi", ".so", ".bin", ".gguf", ".safetensors", ".pt", ".onnx",
               ".pyd", ".lib", ".obj"},
}.items():
    for _e in _exts:
        TYPE_OF_EXT[_e] = _t
FILE_TYPES = ("doc", "code", "data", "image", "video", "audio", "archive", "binary", "other")

EXTRACT_MAX_FILE = 5 * 1024 * 1024     # files above this are not content-extracted
EXTRACT_MAX_BODY = 16 * 1024           # characters stored per file (64 K measured too big in the pilot)
ZIP_MEMBER_MAX = 8 * 1024 * 1024       # decompressed bytes read from one zip member
QUICK_BYTES = 64 * 1024                # head and tail bytes for the quick hash
CHUNK = 1024 * 1024

# Windows attributes that mean "reading this would recall it from the cloud".
CLOUD_ATTRS = 0x00400000 | 0x00040000 | 0x00001000   # RECALL_ON_DATA_ACCESS | RECALL_ON_OPEN | OFFLINE
REPARSE_ATTR = 0x00000400


# --------------------------------------------------------------------------- paths and rules

def norm(p: str) -> str:
    return p.replace("\\", "/").rstrip("/") if len(p) > 3 else p.replace("\\", "/")


def default_db() -> str:
    env = os.environ.get("CLUSTER_FILES_DB")
    if env:
        return env
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "cluster_files", "index.sqlite")


def _tokens(s: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", s.lower()) if t}


def privacy_of(path: str) -> str | None:
    """Return a reason string when `path` is in the privacy tier (never content-indexed)."""
    parts = [p for p in norm(path).split("/") if p]
    if not parts:
        return None
    name = parts[-1].lower()
    for g in PRIVATE_FILE_GLOBS:
        if fnmatch.fnmatchcase(name, g):
            return f"credential:file {g}"
    for seg in parts:
        toks = _tokens(seg)
        for tier, words in PRIVATE_TOKENS.items():
            hit = toks & words
            if hit:
                return f"{tier}:{sorted(hit)[0]}"
    return None


def is_excluded_dir(path: str, excludes: tuple[str, ...], root: str) -> bool:
    n = norm(path).lower()
    base = n.rsplit("/", 1)[-1]
    if base in SKIP_DIR_NAMES:
        return True
    if any(part in n + "/" for part in (s + "/" for s in SKIP_PATH_PARTS)):
        return True
    if BOOK_PART in n + "/" and BOOK_PART not in norm(root).lower() + "/":
        return True
    for e in excludes:
        e = norm(e).lower()
        if n == e or n.startswith(e + "/"):
            return True
    return False


def file_type(ext: str) -> str:
    return TYPE_OF_EXT.get(ext.lower(), "other")


# --------------------------------------------------------------------------- database

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS sources (
  machine TEXT, root TEXT, excludes TEXT, last_scan INTEGER, state TEXT,
  PRIMARY KEY (machine, root));
CREATE TABLE IF NOT EXISTS scans (
  id INTEGER PRIMARY KEY, machine TEXT, root TEXT, started REAL, finished REAL, state TEXT,
  dirs INTEGER DEFAULT 0, files INTEGER DEFAULT 0, new INTEGER DEFAULT 0, changed INTEGER DEFAULT 0,
  removed INTEGER DEFAULT 0, unreadable INTEGER DEFAULT 0, note TEXT);
CREATE TABLE IF NOT EXISTS files (
  id INTEGER PRIMARY KEY, machine TEXT NOT NULL, path TEXT NOT NULL, dir TEXT NOT NULL,
  name TEXT NOT NULL, ext TEXT, ftype TEXT, size INTEGER, mtime REAL, mtime_ns INTEGER,
  private TEXT, in_git INTEGER DEFAULT 0, cloud INTEGER DEFAULT 0, seen_scan INTEGER,
  quick TEXT, hash TEXT, hash_state TEXT, extract_state TEXT,
  UNIQUE (machine, path));
CREATE INDEX IF NOT EXISTS files_dir ON files (machine, dir);
CREATE INDEX IF NOT EXISTS files_size ON files (size);
CREATE INDEX IF NOT EXISTS files_hash ON files (hash);
CREATE INDEX IF NOT EXISTS files_quick ON files (quick);
CREATE TABLE IF NOT EXISTS unreadable (
  machine TEXT, path TEXT, error TEXT, scan INTEGER, PRIMARY KEY (machine, path));
CREATE TABLE IF NOT EXISTS decisions (
  hash TEXT PRIMARY KEY, decision TEXT NOT NULL, canonical TEXT, at TEXT, source TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(name, path, body, tokenize='unicode61 remove_diacritics 2');
"""
DECISIONS = ("keep_canonical", "keep_both", "decide_later")


def connect(db: str) -> sqlite3.Connection:
    d = os.path.dirname(os.path.abspath(db))
    os.makedirs(d, exist_ok=True)
    con = sqlite3.connect(db, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.executescript(SCHEMA)
    con.execute("INSERT OR IGNORE INTO meta VALUES ('schema', ?)", (str(SCHEMA_VERSION),))
    return con


# --------------------------------------------------------------------------- low priority, throttle

def lower_priority() -> str:
    """Background CPU and I/O priority for this process. Returns what it managed."""
    if os.name == "nt":
        try:
            k = ctypes.windll.kernel32
            h = k.GetCurrentProcess()
            ok_io = k.SetPriorityClass(h, 0x00100000)        # PROCESS_MODE_BACKGROUND_BEGIN
            if not ok_io:
                k.SetPriorityClass(h, 0x00004000)           # BELOW_NORMAL_PRIORITY_CLASS
            return "background" if ok_io else "below-normal"
        except Exception:
            return "unchanged"
    try:
        os.nice(10)
        return "nice 10"
    except Exception:
        return "unchanged"


class Throttle:
    """Caps read throughput at `mbps` megabytes per second (0 = no cap)."""

    def __init__(self, mbps: float, sleep=time.sleep, clock=time.monotonic):
        self.rate = mbps * 1024 * 1024
        self.sleep, self.clock = sleep, clock
        self.t0 = clock()
        self.done = 0

    def took(self, n: int) -> None:
        self.done += n
        if self.rate <= 0:
            return
        ahead = self.done / self.rate - (self.clock() - self.t0)
        if ahead > 0:
            self.sleep(ahead)


# --------------------------------------------------------------------------- extraction

def _decode(raw: bytes) -> str | None:
    if raw[:3] == b"\xef\xbb\xbf":
        return raw[3:].decode("utf-8", "replace")
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", "replace")
    if b"\x00" in raw[:8192]:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", "replace")


_TAG = re.compile(r"<[^>]+>")


def _xml_text(raw: bytes) -> str:
    t = raw.decode("utf-8", "replace")
    t = re.sub(r"</(w:p|a:p|text:p|si)>", "\n", t)
    return html.unescape(_TAG.sub(" ", t))


def extract_text(path: str, ext: str, size: int) -> tuple[str, str | None]:
    """(state, text). States: done, none (not a text type), no-extractor, too-big, binary, error."""
    ext = ext.lower()
    if ext in NO_EXTRACTOR_EXT:
        return "no-extractor", None
    if ext in NOISY_EXT:
        return "skipped-noisy", None
    if ext not in TEXT_EXT and ext not in ZIP_DOC_EXT:
        return "none", None
    if size > EXTRACT_MAX_FILE:
        return "too-big", None
    try:
        if ext in ZIP_DOC_EXT:
            out = []
            with zipfile.ZipFile(path) as z:
                for info in z.infolist():
                    if not any(info.filename.startswith(m) for m in ZIP_DOC_EXT[ext]):
                        continue
                    if info.file_size > ZIP_MEMBER_MAX:
                        continue
                    with z.open(info) as fh:
                        out.append(_xml_text(fh.read(ZIP_MEMBER_MAX)))
            text = " ".join(" ".join(out).split())
        else:
            with open(path, "rb") as fh:
                raw = fh.read(EXTRACT_MAX_BODY * 4)
            text = _decode(raw)
            if text is None:
                return "binary", None
    except Exception:
        return "error", None
    return "done", text[:EXTRACT_MAX_BODY]


# --------------------------------------------------------------------------- hashing

def quick_hash(path: str, size: int, throttle: Throttle) -> str:
    h = hashlib.sha256(str(size).encode())
    with open(path, "rb") as fh:
        head = fh.read(QUICK_BYTES)
        h.update(head)
        n = len(head)
        if size > 2 * QUICK_BYTES:
            fh.seek(size - QUICK_BYTES)
            tail = fh.read(QUICK_BYTES)
            h.update(tail)
            n += len(tail)
    throttle.took(n)
    return h.hexdigest()


def full_hash(path: str, throttle: Throttle) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(CHUNK)
            if not b:
                break
            h.update(b)
            throttle.took(len(b))
    return h.hexdigest()


# --------------------------------------------------------------------------- scan

class Budget:
    def __init__(self, seconds: float | None, clock=time.monotonic):
        self.end = clock() + seconds if seconds else None
        self.clock = clock

    def out(self) -> bool:
        return self.end is not None and self.clock() >= self.end


def _git_root_marker(dirpath: str) -> bool:
    return os.path.isdir(os.path.join(dirpath, ".git")) or os.path.isfile(os.path.join(dirpath, ".git"))


def scan(con: sqlite3.Connection, machine: str, root: str, excludes: tuple[str, ...] = (),
         budget: Budget | None = None, extract: bool = True, log=print) -> dict:
    """Walk `root` read-only, upsert changed rows, extract text for new/changed files.
    Returns the scan row as a dict."""
    budget = budget or Budget(None)
    root = os.path.abspath(root)
    now = time.time()
    cur = con.execute("INSERT INTO scans (machine, root, started, state) VALUES (?,?,?,?)",
                      (machine, norm(root), now, "running"))
    scan_id = cur.lastrowid
    con.execute("INSERT OR REPLACE INTO sources VALUES (?,?,?,?,?)",
                (machine, norm(root), json.dumps(list(excludes)), scan_id, "running"))
    con.commit()
    st = {"dirs": 0, "files": 0, "new": 0, "changed": 0, "removed": 0, "unreadable": 0}
    unreadable: list[str] = []
    state = "complete"
    # stack of (dirpath, in_git)
    stack = [(root, _git_root_marker(root))]
    pending = 0
    try:
        while stack:
            if budget.out():
                state = "partial"
                break
            d, in_git = stack.pop()
            try:
                entries = list(os.scandir(d))
            except OSError as e:
                unreadable.append(norm(d))
                con.execute("INSERT OR REPLACE INTO unreadable VALUES (?,?,?,?)",
                            (machine, norm(d), type(e).__name__, scan_id))
                st["unreadable"] += 1
                continue
            st["dirs"] += 1
            nd = norm(d)
            known = {r["name"]: r for r in con.execute(
                "SELECT id, name, size, mtime_ns FROM files WHERE machine=? AND dir=?", (machine, nd))}
            for e in entries:
                try:
                    if e.is_dir(follow_symlinks=False):
                        attrs = getattr(e.stat(follow_symlinks=False), "st_file_attributes", 0)
                        if attrs & REPARSE_ATTR:
                            continue  # junctions and links: never followed (loops, other drives)
                        if not is_excluded_dir(e.path, excludes, root):
                            stack.append((e.path, in_git or _git_root_marker(e.path)))
                        continue
                    if not e.is_file(follow_symlinks=False):
                        continue
                    s = e.stat(follow_symlinks=False)
                except OSError as err:
                    con.execute("INSERT OR REPLACE INTO unreadable VALUES (?,?,?,?)",
                                (machine, norm(e.path), type(err).__name__, scan_id))
                    st["unreadable"] += 1
                    continue
                st["files"] += 1
                attrs = getattr(s, "st_file_attributes", 0)
                row = known.get(e.name)
                if row is not None and row["size"] == s.st_size and row["mtime_ns"] == s.st_mtime_ns:
                    con.execute("UPDATE files SET seen_scan=? WHERE id=?", (scan_id, row["id"]))
                else:
                    _upsert(con, machine, e.path, nd, e.name, s, attrs, in_git, scan_id, row, extract)
                    st["changed" if row is not None else "new"] += 1
                pending += 1
            if pending >= 5000:
                con.commit()
                pending = 0
    except KeyboardInterrupt:
        state = "partial"
    con.commit()
    if state == "complete":
        st["removed"] = _drop_missing(con, machine, norm(root), scan_id, unreadable)
    note = None if state == "complete" else "stopped early: rows for files not reached are kept, removals skipped"
    con.execute("UPDATE scans SET finished=?, state=?, dirs=?, files=?, new=?, changed=?, removed=?, "
                "unreadable=?, note=? WHERE id=?",
                (time.time(), state, st["dirs"], st["files"], st["new"], st["changed"], st["removed"],
                 st["unreadable"], note, scan_id))
    con.execute("UPDATE sources SET state=? WHERE machine=? AND root=?", (state, machine, norm(root)))
    con.commit()
    out = dict(con.execute("SELECT * FROM scans WHERE id=?", (scan_id,)).fetchone())
    log(f"scan {scan_id} {machine} {norm(root)}: {state}, {st['files']} files in {st['dirs']} dirs "
        f"({st['new']} new, {st['changed']} changed, {st['removed']} removed, {st['unreadable']} unreadable) "
        f"in {out['finished'] - out['started']:.1f}s")
    return out


def _upsert(con, machine, path, nd, name, s, attrs, in_git, scan_id, row, extract):
    ext = os.path.splitext(name)[1].lower()
    priv = privacy_of(path)
    cloud = 1 if attrs & CLOUD_ATTRS else 0
    if priv:
        hstate, xstate = "private", "private"
    elif cloud:
        hstate, xstate = "cloud", "cloud"
    else:
        hstate, xstate = "pending", "pending"
    body = None
    if xstate == "pending" and extract:
        xstate, body = extract_text(path, ext, s.st_size)
    vals = (machine, norm(path), nd, name, ext, file_type(ext), s.st_size, s.st_mtime, s.st_mtime_ns,
            priv, 1 if in_git else 0, cloud, scan_id, None, None, hstate, xstate)
    if row is None:
        cur = con.execute("INSERT INTO files (machine, path, dir, name, ext, ftype, size, mtime, mtime_ns, "
                          "private, in_git, cloud, seen_scan, quick, hash, hash_state, extract_state) "
                          "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", vals)
        fid = cur.lastrowid
    else:
        fid = row["id"]
        con.execute("UPDATE files SET machine=?, path=?, dir=?, name=?, ext=?, ftype=?, size=?, mtime=?, "
                    "mtime_ns=?, private=?, in_git=?, cloud=?, seen_scan=?, quick=?, hash=?, hash_state=?, "
                    "extract_state=? WHERE id=?", vals + (fid,))
        con.execute("DELETE FROM fts WHERE rowid=?", (fid,))
    con.execute("INSERT INTO fts (rowid, name, path, body) VALUES (?,?,?,?)",
                (fid, name, norm(path), body or ""))


def _drop_missing(con, machine, root, scan_id, unreadable) -> int:
    like = root.rstrip("/") + "/%"
    rows = con.execute("SELECT id, path FROM files WHERE machine=? AND (path LIKE ? ) AND seen_scan<>?",
                       (machine, like, scan_id)).fetchall()
    gone = [r["id"] for r in rows
            if not any(r["path"] == u or r["path"].startswith(u + "/") for u in unreadable)]
    for i in range(0, len(gone), 500):
        part = gone[i:i + 500]
        q = ",".join("?" * len(part))
        con.execute(f"DELETE FROM files WHERE id IN ({q})", part)
        con.execute(f"DELETE FROM fts WHERE rowid IN ({q})", part)
    con.commit()
    return len(gone)


def extract_pending(con, budget: Budget | None = None, log=print) -> int:
    """Extract text for rows a scan left `pending` (scan ran with extract off)."""
    budget = budget or Budget(None)
    n = 0
    for r in con.execute("SELECT id, path, ext, size, name FROM files WHERE extract_state='pending'").fetchall():
        if budget.out():
            break
        state, body = extract_text(r["path"], r["ext"], r["size"])
        con.execute("UPDATE files SET extract_state=? WHERE id=?", (state, r["id"]))
        if body:
            con.execute("DELETE FROM fts WHERE rowid=?", (r["id"],))
            con.execute("INSERT INTO fts (rowid, name, path, body) VALUES (?,?,?,?)",
                        (r["id"], r["name"], r["path"], body))
        n += 1
        if n % 2000 == 0:
            con.commit()
    con.commit()
    log(f"extract: {n} files")
    return n


def hash_candidates(con, mbps: float = 60.0, byte_budget: int | None = None,
                    budget: Budget | None = None, min_size: int = 1, throttle: Throttle | None = None,
                    log=print) -> dict:
    """Two-stage exact-duplicate hashing, throttled.
    1. quick hash (size + first and last 64 KiB) of every file whose size is shared by another file;
    2. full SHA-256 of files whose quick hash is shared, largest potential reclaim first.
    Files with a unique size cannot have an exact duplicate: they stay `pending` (no hash yet)."""
    budget = budget or Budget(None)
    th = throttle or Throttle(mbps)
    st = {"quick": 0, "full": 0, "bytes": 0, "errors": 0, "stopped": None}
    where = ("hash_state IN ('pending','quick') AND size>=? AND size IN "
             "(SELECT size FROM files WHERE hash_state NOT IN ('private','cloud') AND size>=? "
             "GROUP BY size HAVING COUNT(*)>1)")
    rows = con.execute(f"SELECT id, path, size FROM files WHERE quick IS NULL AND {where} ORDER BY size DESC",
                       (min_size, min_size)).fetchall()
    for r in rows:
        if budget.out():
            st["stopped"] = "time budget"
            break
        try:
            q = quick_hash(r["path"], r["size"], th)
            con.execute("UPDATE files SET quick=?, hash_state='quick' WHERE id=?", (q, r["id"]))
            st["quick"] += 1
        except OSError:
            con.execute("UPDATE files SET hash_state='error' WHERE id=?", (r["id"],))
            st["errors"] += 1
        if st["quick"] % 2000 == 0:
            con.commit()
    con.commit()
    if st["stopped"]:
        log(f"hash: stopped in the quick pass ({st['stopped']}); {st['quick']} quick hashes")
        return st
    groups = con.execute(
        "SELECT quick, size, COUNT(*) n FROM files WHERE quick IS NOT NULL AND hash_state IN ('quick','full') "
        "GROUP BY quick HAVING n>1 ORDER BY size*(n-1) DESC").fetchall()
    for g in groups:
        for r in con.execute("SELECT id, path, size FROM files WHERE quick=? AND hash_state='quick'",
                             (g["quick"],)).fetchall():
            if budget.out():
                st["stopped"] = "time budget"
                break
            if byte_budget is not None and st["bytes"] + r["size"] > byte_budget:
                st["stopped"] = "byte budget"
                break
            try:
                h = full_hash(r["path"], th)
                con.execute("UPDATE files SET hash=?, hash_state='full' WHERE id=?", (h, r["id"]))
                st["full"] += 1
                st["bytes"] += r["size"]
            except OSError:
                con.execute("UPDATE files SET hash_state='error' WHERE id=?", (r["id"],))
                st["errors"] += 1
        con.commit()
        if st["stopped"]:
            break
    log(f"hash: {st['quick']} quick, {st['full']} full ({st['bytes'] / 1e9:.2f} GB read), "
        f"{st['errors']} errors" + (f", stopped: {st['stopped']}" if st["stopped"] else ", complete"))
    return st


# --------------------------------------------------------------------------- coverage and search

def coverage(con) -> dict:
    """Per machine: indexed (complete), partial, or unknown (not indexed yet)."""
    out = {m: {"state": "unknown", "detail": "not indexed yet", "roots": []} for m in KNOWN_MACHINES}
    for s in con.execute("SELECT s.machine, s.root, s.state, s.excludes, c.finished, c.files "
                         "FROM sources s LEFT JOIN scans c ON c.id=s.last_scan"):
        m = out.setdefault(s["machine"], {"state": "unknown", "detail": "not indexed yet", "roots": []})
        when = (datetime.fromtimestamp(s["finished"], timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                if s["finished"] else None)
        m["roots"].append({"root": s["root"], "state": s["state"], "files": s["files"], "at": when,
                           "excludes": json.loads(s["excludes"] or "[]")})
    for m in out.values():
        states = {r["state"] for r in m["roots"]}
        if not states:
            continue
        m["state"] = "indexed" if states == {"complete"} else "partial"
        m["detail"] = ("only the roots listed are indexed; everything else on this machine is unknown"
                       if m["state"] == "indexed" else "a scan did not finish; missing rows are unknown")
    return out


def _fts_query(q: str) -> str:
    toks = re.findall(r"\w+", q, flags=re.UNICODE)
    return " ".join(f'"{t}"*' for t in toks)


def _day(s: str | None) -> float | None:
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()


def search(con, q: str = "", field: str = "any", machine: str | None = None, ftype: str | None = None,
           ext: str | None = None, after: str | None = None, before: str | None = None,
           min_size: int | None = None, limit: int = 50) -> dict:
    """Free search. `field` is any|name|path|content. Returns results plus an honest scope note."""
    cov = coverage(con)
    where, args = [], []
    if machine:
        where.append("f.machine=?")
        args.append(machine)
    if ftype:
        where.append("f.ftype=?")
        args.append(ftype)
    if ext:
        where.append("f.ext=?")
        args.append(ext if ext.startswith(".") else "." + ext)
    if after:
        where.append("f.mtime>=?")
        args.append(_day(after))
    if before:
        where.append("f.mtime<?")
        args.append(_day(before))
    if min_size:
        where.append("f.size>=?")
        args.append(min_size)
    fq = _fts_query(q)
    cols = {"any": "{name path body}", "name": "name", "path": "path", "content": "body"}[field]
    if fq:
        sql = ("SELECT f.*, snippet(fts, -1, '[', ']', ' ... ', 12) AS snip, bm25(fts) AS rank "
               "FROM fts JOIN files f ON f.id=fts.rowid WHERE fts MATCH ?")
        args = [f"{cols} : ({fq})"] + args
        order = " ORDER BY rank"
    else:
        sql = "SELECT f.*, NULL AS snip FROM files f WHERE 1=1"
        order = " ORDER BY f.mtime DESC"
    if where:
        sql += " AND " + " AND ".join(where)
    rows = [dict(r) for r in con.execute(sql + order + " LIMIT ?", args + [limit])]
    results = [{"machine": r["machine"], "path": r["path"], "size": r["size"],
                "modified": datetime.fromtimestamp(r["mtime"], timezone.utc).strftime("%Y-%m-%d"),
                "type": r["ftype"], "private": bool(r["private"]),
                "content": r["extract_state"], "snippet": r.get("snip")} for r in rows]
    notes = []
    scope_machines = [machine] if machine else list(cov)
    for m in scope_machines:
        c = cov.get(m, {"state": "unknown", "detail": "not indexed yet"})
        if c["state"] != "indexed":
            notes.append(f"{m}: {c['state']} ({c['detail']}); no result here means unknown, not absent")
    if fq and field in ("any", "content"):
        unseen = con.execute(
            "SELECT extract_state s, COUNT(*) n FROM files f WHERE extract_state NOT IN ('done','none','binary')"
            + ("".join(" AND " + w for w in where)) + " GROUP BY extract_state", args[1:]).fetchall()
        blind = {r["s"]: r["n"] for r in unseen}
        if blind:
            notes.append("content not searchable for " + ", ".join(f"{n} {s}" for s, n in sorted(blind.items()))
                         + " file(s) in scope: a content match there is unknown")
    return {"query": q, "field": field, "results": results, "count": len(results),
            "truncated": len(results) == limit, "notes": notes}


# --------------------------------------------------------------------------- dedupe (report only)

DURABLE_HINTS = (("claude sessions", 2, "in the vault-synced Claude Sessions tree"),
                 ("/leadfuel/", 2, "in the estate tree"),
                 ("/novah/reference", 2, "in novah/reference"))
TRANSIENT_SEGMENTS = {"downloads", "downloads-untrusted", "tmp", "temp", "scratch", "cache",
                      "_stick-archive", "incoming"}


def durability(path: str, in_git: int) -> tuple[int, str]:
    p = norm(path).lower()
    if in_git:
        return 3, "inside a git repo"
    for hint, score, why in DURABLE_HINTS:
        if hint in p:
            return score, why
    if set(p.split("/")[:-1]) & TRANSIENT_SEGMENTS:
        return 0, "in a transient folder (downloads, tmp, scratch, cache)"
    return 1, "ordinary folder"


def propose_canonical(copies: list[dict]) -> tuple[dict, str]:
    """Rule from the brief: most durable location first (git repo, then synced trees), then the
    oldest mtime, then the shortest path. Returns (copy, reason)."""
    scored = []
    for c in copies:
        d, why = durability(c["path"], c.get("in_git", 0))
        scored.append((-d, c["mtime"], len(c["path"]), c["path"], c, why))
    scored.sort(key=lambda t: t[:4])
    best = scored[0]
    reason = best[5]
    if len(scored) > 1 and scored[1][0] == best[0]:
        reason += ("; oldest modified date among equally durable copies"
                   if scored[1][1] != best[1] else "; shortest path among equal copies")
    return best[4], reason


def dedupe_groups(con, limit: int | None = None) -> dict:
    groups = []
    for g in con.execute("SELECT hash, size, COUNT(*) n FROM files WHERE hash_state='full' AND size>0 "
                         "GROUP BY hash HAVING n>1 ORDER BY size*(n-1) DESC").fetchall():
        copies = [dict(r) for r in con.execute(
            "SELECT machine, path, size, mtime, in_git FROM files WHERE hash=? AND hash_state='full'",
            (g["hash"],))]
        canon, why = propose_canonical(copies)
        dec = con.execute("SELECT decision FROM decisions WHERE hash=?", (g["hash"],)).fetchone()
        groups.append({
            "hash": g["hash"], "size": g["size"], "copies": len(copies),
            "reclaimable": g["size"] * (len(copies) - 1),
            "canonical": {"machine": canon["machine"], "path": canon["path"]}, "reason": why,
            "others": [{"machine": c["machine"], "path": c["path"],
                        "modified": datetime.fromtimestamp(c["mtime"], timezone.utc).strftime("%Y-%m-%d")}
                       for c in copies if c is not canon],
            "decision": dec["decision"] if dec else None})
    st = dict(con.execute(
        "SELECT COUNT(*) AS \"files\", SUM(hash_state='full') AS \"full\", SUM(hash_state='quick') AS \"quick\", "
        "SUM(hash_state='pending') AS \"pending\", SUM(hash_state='private') AS \"private\", "
        "SUM(hash_state='cloud') AS \"cloud\", SUM(hash_state='error') AS \"errors\" FROM files").fetchone())
    total = sum(g["reclaimable"] for g in groups)
    shown = groups[:limit] if limit else groups
    return {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "groups_total": len(groups), "reclaimable_total": total, "groups": shown,
            "hash_coverage": st, "coverage": coverage(con),
            "note": ("Report only. Nothing was moved or deleted. Groups come from full SHA-256 matches only. "
                     "Files with a quick hash but no full hash, and files not hashed at all, are not in any "
                     "group: their duplicate status is unknown, not unique.")}


def record_decisions(con, decisions: dict, source: str = "page export") -> int:
    """Record clicks from the page. Writes only the decisions table; never touches a file."""
    n = 0
    for h, d in decisions.items():
        choice = d.get("decision") if isinstance(d, dict) else d
        if choice not in DECISIONS or not re.fullmatch(r"[0-9a-f]{64}", h or ""):
            continue
        canon = d.get("canonical") if isinstance(d, dict) else None
        con.execute("INSERT OR REPLACE INTO decisions VALUES (?,?,?,?,?)",
                    (h, choice, canon, datetime.now(timezone.utc).isoformat(timespec="seconds"), source))
        n += 1
    con.commit()
    return n


# --------------------------------------------------------------------------- pages

def human(n: int | None) -> str:
    if n is None:
        return "unknown"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return str(n)


_CSS = """
:root{--bg:#fbfaf7;--fg:#1d1c1a;--mute:#6b675f;--line:#e4e0d8;--card:#fff;--acc:#2f5d8a;--warn:#9a5b00;--ok:#2f6b3a}
@media (prefers-color-scheme:dark){:root{--bg:#161614;--fg:#ecebe6;--mute:#a29e95;--line:#33312d;--card:#1f1e1b;--acc:#8db8e6;--warn:#e0a548;--ok:#8fcf98}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,Segoe UI,sans-serif}
main{max-width:1000px;margin:0 auto;padding:16px}h1{font-size:20px;margin:8px 0}small,.mute{color:var(--mute)}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px;margin:10px 0}
form{display:flex;flex-wrap:wrap;gap:8px}input,select,button{font:inherit;padding:6px 8px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg)}
input[name=q]{flex:1 1 260px}button{cursor:pointer}button.on{background:var(--acc);color:var(--bg);border-color:var(--acc)}
code,.path{font-family:ui-monospace,Consolas,monospace;font-size:13px;word-break:break-all}
.note{color:var(--warn)}.tag{display:inline-block;font-size:12px;padding:0 6px;border:1px solid var(--line);border-radius:10px;margin-right:4px}
table{border-collapse:collapse;width:100%}td,th{padding:4px 6px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
"""


def dedupe_page(report: dict) -> str:
    """Self-contained click-through page. Clicks are kept in this browser and exported as a JSON
    file the CLI records with `decisions`. The page has no network code."""
    data = json.dumps(report).replace("</", "<\\/")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Duplicate files review</title>
<style>{_CSS}</style></head><body><main>
<h1>Duplicate files review</h1>
<p class="mute" id="sum"></p>
<p class="note">Report only. Nothing on any drive is moved or deleted by this page. Your clicks are kept in this browser;
"Export decisions" saves them as a file, and a later separate step applies them (quarantine first, reversible for 30 days).</p>
<p><button id="exp">Export decisions</button> <span class="mute" id="cnt"></span></p>
<div id="groups"></div>
<script>
const R={data};
const K='cluster-files-decisions';
let D={{}};try{{D=JSON.parse(localStorage.getItem(K)||'{{}}')}}catch(e){{D={{}}}}
for(const g of R.groups){{if(g.decision&&!D[g.hash])D[g.hash]={{decision:g.decision,canonical:g.canonical.path}}}}
const H=n=>{{const u=['B','KB','MB','GB','TB'];let i=0;while(n>=1024&&i<4){{n/=1024;i++}}return (i?n.toFixed(1):n)+' '+u[i]}};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));
function save(){{try{{localStorage.setItem(K,JSON.stringify(D))}}catch(e){{}};document.getElementById('cnt').textContent=Object.keys(D).length+' of '+R.groups.length+' decided'}}
const hc=R.hash_coverage;
document.getElementById('sum').textContent=R.groups_total+' exact-duplicate groups, '+H(R.reclaimable_total)+' reclaimable (generated '+R.generated+'). Hashed in full: '+(hc.full||0)+' files; not yet hashed: '+((hc.pending||0)+(hc.quick||0))+' (unknown); private, never hashed: '+(hc.private||0)+'.';
const box=document.getElementById('groups');
R.groups.forEach((g,i)=>{{
 const c=document.createElement('div');c.className='card';
 const b=(v,l)=>'<button data-v="'+v+'" class="'+((D[g.hash]||{{}}).decision===v?'on':'')+'">'+l+'</button>';
 c.innerHTML='<div><b>#'+(i+1)+'</b> '+g.copies+' copies of '+H(g.size)+', <b>'+H(g.reclaimable)+'</b> reclaimable</div>'+
 '<div><span class="tag">keep</span><span class="path">'+esc(g.canonical.machine)+': '+esc(g.canonical.path)+'</span><br><small>'+esc(g.reason)+'</small></div>'+
 '<div>'+g.others.map(o=>'<span class="tag">copy</span><span class="path">'+esc(o.machine)+': '+esc(o.path)+'</span> <small>'+o.modified+'</small>').join('<br>')+'</div>'+
 '<p>'+b('keep_canonical','Keep canonical')+' '+b('keep_both','Keep both')+' '+b('decide_later','Decide later')+'</p>';
 c.querySelectorAll('button').forEach(x=>x.onclick=()=>{{D[g.hash]={{decision:x.dataset.v,canonical:g.canonical.path}};c.querySelectorAll('button').forEach(y=>y.classList.toggle('on',y===x));save()}});
 box.appendChild(c)}});
document.getElementById('exp').onclick=()=>{{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(D,null,1)],{{type:'application/json'}}));a.download='dedupe-decisions.json';a.click()}};
save();
</script></main></body></html>"""


def search_page() -> str:
    types = "".join(f'<option value="{t}">{t}</option>' for t in FILE_TYPES)
    machines = "".join(f'<option value="{m}">{m}</option>' for m in KNOWN_MACHINES)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Cluster file search</title>
<style>{_CSS}</style></head><body><main>
<h1>Cluster file search</h1>
<form id="f"><input name="q" placeholder="words in a name, path or document" autofocus>
<select name="field"><option value="any">anywhere</option><option value="name">name</option><option value="path">path</option><option value="content">content</option></select>
<select name="machine"><option value="">all machines</option>{machines}</select>
<select name="type"><option value="">any type</option>{types}</select>
<input name="after" type="date" title="modified on or after"><input name="before" type="date" title="modified before">
<button>Search</button></form>
<div id="cov" class="card"></div><div id="notes"></div><div id="out"></div>
<script>
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));
const H=n=>{{const u=['B','KB','MB','GB','TB'];let i=0;while(n>=1024&&i<4){{n/=1024;i++}}return (i?n.toFixed(1):n)+' '+u[i]}};
fetch('/api/coverage').then(r=>r.json()).then(c=>{{document.getElementById('cov').innerHTML='<b>What is indexed</b><br>'+Object.entries(c).map(([m,v])=>'<span class="tag">'+esc(m)+'</span> '+esc(v.state)+(v.roots.length?' : '+v.roots.map(r=>esc(r.root)+' ('+esc(r.state)+', '+(r.files??'?')+' files, '+esc(r.at??'')+')').join(', '):' : '+esc(v.detail))).join('<br>')}});
document.getElementById('f').onsubmit=e=>{{e.preventDefault();const p=new URLSearchParams(new FormData(e.target));
 fetch('/api/search?'+p).then(r=>r.json()).then(d=>{{
  document.getElementById('notes').innerHTML=d.notes.map(n=>'<p class="note">'+esc(n)+'</p>').join('');
  document.getElementById('out').innerHTML='<p class="mute">'+d.count+(d.truncated?'+':'')+' result(s)</p><table><tr><th>Machine</th><th>Path</th><th>Size</th><th>Modified</th></tr>'+
  d.results.map(r=>'<tr><td>'+esc(r.machine)+'</td><td class="path">'+esc(r.path)+(r.private?' <span class="tag">private: name only</span>':'')+(r.snippet&&r.content==='done'?'<br><small>'+esc(r.snippet)+'</small>':'')+'</td><td>'+H(r.size)+'</td><td>'+r.modified+'</td></tr>').join('')+'</table>'}})}};
</script></main></body></html>"""


def make_handler(db: str):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):  # no request logs (paths are private)
            pass

        def _send(self, code, body, ctype):
            b = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(b)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'")
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            con = connect(db)
            try:
                if u.path == "/":
                    return self._send(200, search_page(), "text/html; charset=utf-8")
                if u.path == "/dedupe":
                    return self._send(200, dedupe_page(dedupe_groups(con, limit=500)), "text/html; charset=utf-8")
                if u.path == "/api/coverage":
                    return self._send(200, json.dumps(coverage(con)), "application/json")
                if u.path == "/api/search":
                    field = q.get("field", "any")
                    if field not in ("any", "name", "path", "content"):
                        field = "any"
                    ftype = q.get("type") or None
                    res = search(con, q.get("q", ""), field=field, machine=q.get("machine") or None,
                                 ftype=ftype if ftype in FILE_TYPES else None,
                                 after=_safe_day(q.get("after")), before=_safe_day(q.get("before")),
                                 limit=min(int(q["limit"]) if q.get("limit", "").isdigit() else 100, 500))
                    return self._send(200, json.dumps(res), "application/json")
                return self._send(404, "not found", "text/plain")
            finally:
                con.close()
    return H


def _safe_day(s):
    return s if s and re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) else None


LOOPBACK = ("127.0.0.1", "::1", "localhost")


def serve(db: str, host: str = "127.0.0.1", port: int = 8471) -> None:
    if host not in LOOPBACK:
        raise SystemExit(f"refused: serve binds loopback only, not {host}")
    srv = ThreadingHTTPServer((host, port), make_handler(db))
    print(f"cluster file search on http://{host}:{port}/  (dedupe review at /dedupe); Ctrl-C stops")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


# --------------------------------------------------------------------------- heavy lock

def heavy_lock_acquire(job: str, lock_py: str | None) -> tuple[str, str | None]:
    """('granted', token) | ('refused', None) | ('unknown', None). Unknown never runs."""
    if not lock_py or not os.path.isfile(lock_py):
        return "unknown", None
    tok = os.path.join(os.path.dirname(default_db()), "heavy.token")   # one file, overwritten
    os.makedirs(os.path.dirname(tok), exist_ok=True)
    try:
        p = subprocess.run([sys.executable, lock_py, "acquire", "--job", job, "--pid", str(os.getpid()),
                            "--token-file", tok], capture_output=True, text=True, timeout=120)
    except Exception:
        return "unknown", None
    token = open(tok, encoding="utf-8").read().strip() if os.path.exists(tok) else ""
    if p.returncode == 0 and token:
        return "granted", token
    return "refused", None


def heavy_lock_release(token: str, lock_py: str) -> None:
    subprocess.run([sys.executable, lock_py, "release", "--token", token], capture_output=True, timeout=60)


# --------------------------------------------------------------------------- stats and CLI

def stats(con, db: str) -> dict:
    size = sum(os.path.getsize(db + s) for s in ("", "-wal") if os.path.exists(db + s))
    row = dict(con.execute("SELECT COUNT(*) files, SUM(size) bytes, SUM(private IS NOT NULL) private, "
                           "SUM(cloud) cloud, SUM(extract_state='done') extracted FROM files").fetchone())
    by_x = {r[0]: r[1] for r in con.execute("SELECT extract_state, COUNT(*) FROM files GROUP BY 1")}
    by_h = {r[0]: r[1] for r in con.execute("SELECT hash_state, COUNT(*) FROM files GROUP BY 1")}
    by_t = {r[0]: r[1] for r in con.execute("SELECT ftype, COUNT(*) FROM files GROUP BY 1")}
    priv = {r[0]: r[1] for r in con.execute(
        "SELECT substr(private,1,instr(private,':')-1), COUNT(*) FROM files WHERE private IS NOT NULL GROUP BY 1")}
    scans = [dict(r) for r in con.execute("SELECT * FROM scans ORDER BY id DESC LIMIT 5")]
    return {"db": db, "db_bytes": size, **row, "extract": by_x, "hash": by_h, "types": by_t,
            "private_by_tier": priv, "recent_scans": scans}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="file_index", description=__doc__.split("\n")[0])
    ap.add_argument("--db", default=default_db())
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("index", help="scan a root (read-only), extract text, hash duplicate candidates")
    s.add_argument("root")
    s.add_argument("--machine", default=socket.gethostname().lower())
    s.add_argument("--exclude", action="append", default=[])
    s.add_argument("--pilot", action="store_true", help="add the pilot excludes (F:/repos, F:/Leadfuel/repos)")
    s.add_argument("--minutes", type=float, default=None, help="time budget for the whole run")
    s.add_argument("--no-hash", action="store_true")
    s.add_argument("--mbps", type=float, default=60.0, help="hash read cap, MB/s (0 = none)")
    s.add_argument("--hash-gb", type=float, default=None, help="byte budget for full hashes")
    s.add_argument("--heavy-lock", default=os.environ.get("HEAVY_LOCK_PY"),
                   help="path to heavy_lock.py (default: $HEAVY_LOCK_PY)")
    s.add_argument("--no-lock", action="store_true", help="small roots and tests only: skip the heavy lock")
    s.add_argument("--wait-lock", type=float, default=0, help="minutes to queue for the heavy lock")

    q = sub.add_parser("search", help="search names, paths and extracted content")
    q.add_argument("q", nargs="?", default="")
    q.add_argument("--field", choices=("any", "name", "path", "content"), default="any")
    q.add_argument("--machine")
    q.add_argument("--type", choices=FILE_TYPES)
    q.add_argument("--ext")
    q.add_argument("--after", help="YYYY-MM-DD")
    q.add_argument("--before", help="YYYY-MM-DD")
    q.add_argument("--min-size", type=int)
    q.add_argument("--limit", type=int, default=30)
    q.add_argument("--json", action="store_true")

    d = sub.add_parser("dedupe", help="exact-duplicate report (report only, nothing moved)")
    d.add_argument("--out", help="folder for dedupe.json, dedupe.md and dedupe.html")
    d.add_argument("--top", type=int, default=25)

    r = sub.add_parser("decisions", help="record clicks exported from the dedupe page (no file is touched)")
    r.add_argument("file")

    sub.add_parser("stats", help="counts, sizes, timings")
    sub.add_parser("coverage", help="which machines and roots are indexed; the rest is unknown")
    v = sub.add_parser("serve", help="search and dedupe pages on loopback")
    v.add_argument("--port", type=int, default=8471)
    v.add_argument("--host", default="127.0.0.1")

    a = ap.parse_args(argv)
    if a.cmd == "serve":
        serve(a.db, a.host, a.port)
        return 0
    con = connect(a.db)

    if a.cmd == "index":
        token = None
        if not a.no_lock:
            give_up = time.monotonic() + a.wait_lock * 60
            while True:
                state, token = heavy_lock_acquire(f"file-index {a.machine} {a.root}", a.heavy_lock)
                if state == "granted" or state == "unknown" or time.monotonic() >= give_up:
                    break
                time.sleep(60)   # queued behind another heavy job (or hub CI), as the estate rule says
            if state != "granted":
                print(f"WAIT: heavy lock {state}; a full-drive index is a heavy job (set HEAVY_LOCK_PY or "
                      f"--heavy-lock to scripts/heavy_lock.py; --no-lock only for small roots)")
                return 3
        try:
            print(f"priority: {lower_priority()}")
            budget = Budget(a.minutes * 60 if a.minutes else None)
            excl = tuple(a.exclude) + (PILOT_EXCLUDES if a.pilot else ())
            sc = scan(con, a.machine, a.root, excl, budget)
            if not a.no_hash and not budget.out():
                hash_candidates(con, a.mbps, int(a.hash_gb * 1e9) if a.hash_gb else None, budget)
        finally:
            if token:
                heavy_lock_release(token, a.heavy_lock)
        return 0 if sc["state"] == "complete" else 2

    if a.cmd == "search":
        res = search(con, a.q, a.field, a.machine, a.type, a.ext, a.after, a.before, a.min_size, a.limit)
        if a.json:
            print(json.dumps(res, indent=1))
            return 0
        for n in res["notes"]:
            print(f"note: {n}")
        for x in res["results"]:
            flag = " [private: name only]" if x["private"] else ""
            print(f"{x['machine']}:{x['path']}  {human(x['size'])}  {x['modified']}{flag}")
            if x["snippet"] and x["content"] == "done":
                print(f"    {' '.join(x['snippet'].split())[:160]}")
        print(f"{res['count']}{'+' if res['truncated'] else ''} result(s)")
        return 0

    if a.cmd == "dedupe":
        rep = dedupe_groups(con)
        if a.out:
            os.makedirs(a.out, exist_ok=True)
            with open(os.path.join(a.out, "dedupe.json"), "w", encoding="utf-8") as fh:
                json.dump(rep, fh, indent=1)
            with open(os.path.join(a.out, "dedupe.html"), "w", encoding="utf-8") as fh:
                fh.write(dedupe_page({**rep, "groups": rep["groups"][:1000]}))
            with open(os.path.join(a.out, "dedupe.md"), "w", encoding="utf-8") as fh:
                fh.write(dedupe_markdown(rep, a.top))
        print(f"{rep['groups_total']} groups, {human(rep['reclaimable_total'])} reclaimable; "
              f"hash coverage {rep['hash_coverage']}")
        for g in rep["groups"][:a.top]:
            print(f"{human(g['reclaimable']):>9}  x{g['copies']}  keep {g['canonical']['path']}  ({g['reason']})")
        return 0

    if a.cmd == "decisions":
        with open(a.file, encoding="utf-8") as fh:
            n = record_decisions(con, json.load(fh))
        print(f"recorded {n} decision(s); no file was touched")
        return 0

    if a.cmd == "stats":
        print(json.dumps(stats(con, a.db), indent=1, default=str))
        return 0

    if a.cmd == "coverage":
        print(json.dumps(coverage(con), indent=1))
        return 0
    return 1


def dedupe_markdown(rep: dict, top: int) -> str:
    lines = [f"# Exact duplicates (report only, generated {rep['generated']})", "",
             rep["note"], "",
             f"{rep['groups_total']} groups, {human(rep['reclaimable_total'])} reclaimable.", "",
             f"Hash coverage: {json.dumps(rep['hash_coverage'])}", "",
             "| # | reclaimable | copies | proposed keep | why |", "|---|---|---|---|---|"]
    for i, g in enumerate(rep["groups"][:top], 1):
        lines.append(f"| {i} | {human(g['reclaimable'])} | {g['copies']} | `{g['canonical']['path']}` | {g['reason']} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
