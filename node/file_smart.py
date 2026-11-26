"""Cluster files part 4 (smart indexing): near-duplicates and tags, all local.

Reads the part 2 index (node/file_index.py) READ-ONLY and writes its own results to a separate local
SQLite file beside it (%LOCALAPPDATA%\\cluster_files\\smart.sqlite). Nothing in the index is changed
and no indexed file is written, moved, renamed or deleted.

(a) Near-duplicates
- Images ("same photo, different size"): a 64-bit difference hash (dHash) of a 9x8 greyscale
  thumbnail, decoded locally with Pillow, compared by Hamming distance with an aspect-ratio check.
  Formats Pillow cannot decode here (heic, svg, raw) are `unknown`, never "unique".
- Documents ("same document, different format"): word 4-gram shingles of the text the index already
  holds (md, txt, html, docx, xlsx, pptx, ...) plus, in a bounded sample, pdf text extracted locally
  with pypdf; one-permutation MinHash (64 bins, densified), banded LSH for candidates, and the
  estimated Jaccard similarity to confirm.

(b) Tags: facets media, kind (code/docs/data/media/backup/model/...), scope (estate/personal), project,
client and privacy. Rules first (path, name, extension, git flag). Then a LOCAL model (Ollama on
loopback, the same server Hermes uses) for a bounded sample the rules left open. If no local model is
reachable the model tags are written as `unknown` with no confidence, never invented. Every tag row
stores its source (rule|model) and a confidence.

Privacy: a path in the privacy tier (health, financial, credential; decided by the index and checked
again here) is tagged by name only. Its content is never read: no image decode, no text, no pdf, and
the model sees only its path.

Heavy work (decoding images, pdf text, the model) runs under scripts/heavy_lock.py, at background
priority, throttled, inside time and byte budgets, and refuses busy hours while the machine is in use.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import random
import re
import socket
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import zlib
from array import array
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import file_index as fi  # noqa: E402  (sibling module, node/ is not a package)

SMART_SCHEMA_VERSION = 1

# --------------------------------------------------------------------------- local store

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY, kind TEXT, started REAL, finished REAL, state TEXT, params TEXT,
  counts TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS imgsig (
  machine TEXT, path TEXT, mtime_ns INTEGER, size INTEGER, state TEXT, dhash TEXT, w INTEGER,
  h INTEGER, run INTEGER, PRIMARY KEY (machine, path));
CREATE TABLE IF NOT EXISTS docsig (
  machine TEXT, path TEXT, mtime_ns INTEGER, size INTEGER, ext TEXT, state TEXT, words INTEGER,
  sig BLOB, src TEXT, run INTEGER, PRIMARY KEY (machine, path));
CREATE TABLE IF NOT EXISTS near_groups (
  id INTEGER PRIMARY KEY, run INTEGER, kind TEXT, members INTEGER, reclaimable INTEGER,
  min_sim REAL, max_sim REAL, formats TEXT, canonical TEXT, reason TEXT);
CREATE TABLE IF NOT EXISTS near_members (
  group_id INTEGER, machine TEXT, path TEXT, size INTEGER, ext TEXT, role TEXT, sim REAL, note TEXT);
CREATE INDEX IF NOT EXISTS near_members_g ON near_members (group_id);
CREATE TABLE IF NOT EXISTS tags (
  machine TEXT, path TEXT, facet TEXT, value TEXT,
  source TEXT NOT NULL CHECK (source IN ('rule','model')),
  confidence REAL, detail TEXT, run INTEGER, at TEXT,
  PRIMARY KEY (machine, path, facet, source));
CREATE INDEX IF NOT EXISTS tags_fv ON tags (facet, value);
"""


def default_smart_db(index_db: str | None = None) -> str:
    env = os.environ.get("CLUSTER_FILES_SMART_DB")
    if env:
        return env
    return os.path.join(os.path.dirname(os.path.abspath(index_db or fi.default_db())), "smart.sqlite")


def connect_smart(db: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(os.path.abspath(db)), exist_ok=True)
    con = sqlite3.connect(db, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    con.execute("INSERT OR IGNORE INTO meta VALUES ('schema', ?)", (str(SMART_SCHEMA_VERSION),))
    return con


def connect_index_ro(db: str) -> sqlite3.Connection:
    """The index is only ever opened read-only here. A missing index is an error, not an empty one."""
    if not os.path.exists(db):
        raise SystemExit(f"index not found: {db} (run node/file_index.py index first); nothing is known")
    con = sqlite3.connect(f"file:{os.path.abspath(db)}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    return con


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def start_run(sc, kind: str, params: dict) -> int:
    cur = sc.execute("INSERT INTO runs (kind, started, state, params) VALUES (?,?,?,?)",
                     (kind, time.time(), "running", json.dumps(params)))
    sc.commit()
    return cur.lastrowid


def finish_run(sc, run: int, state: str, counts: dict, note: str | None = None) -> None:
    sc.execute("UPDATE runs SET finished=?, state=?, counts=?, note=? WHERE id=?",
               (time.time(), state, json.dumps(counts), note, run))
    sc.commit()


def _private(row) -> bool:
    """Privacy tier: the index's verdict, checked again against the current rule."""
    return bool(row["private"]) or fi.privacy_of(row["path"]) is not None


# --------------------------------------------------------------------------- when heavy work may run

BUSY_HOURS = (8, 22)          # local time; inside it, heavy work needs an idle machine
IDLE_MINUTES = 15


def idle_seconds() -> float | None:
    """Seconds since the last keyboard or mouse input on this machine; None when unknown."""
    if os.name != "nt":
        return None
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
        li = LASTINPUTINFO()
        li.cbSize = ctypes.sizeof(li)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li)):
            return None
        return ((ctypes.windll.kernel32.GetTickCount() - li.dwTime) & 0xFFFFFFFF) / 1000.0
    except Exception:
        return None


def may_run_now(now: datetime | None = None, idle: float | None = -1.0,
                busy: tuple[int, int] = BUSY_HOURS, idle_minutes: float = IDLE_MINUTES) -> tuple[bool, str]:
    """(allowed, why). Outside busy hours: allowed. Inside: only when the machine has been idle for
    `idle_minutes`; when idleness cannot be read inside busy hours the answer is no (unknown is not
    idle)."""
    now = now or datetime.now()
    if idle == -1.0:
        idle = idle_seconds()
    if not (busy[0] <= now.hour < busy[1]):
        return True, f"outside busy hours ({busy[0]:02d}:00-{busy[1]:02d}:00 local)"
    if idle is None:
        return False, "busy hours and idle time unknown: not running"
    if idle >= idle_minutes * 60:
        return True, f"busy hours but idle {idle / 60:.0f} min"
    return False, f"busy hours and the machine is in use (input {idle:.0f}s ago)"


# --------------------------------------------------------------------------- (a) images: dHash

PIL_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".ico"}
NO_DECODER_EXT = {".heic", ".heif", ".svg", ".raw", ".cr2", ".nef", ".dng", ".psd"}
MAX_PIXELS = 120_000_000
IMG_MAX_DIST = 5              # Hamming distance on 64 bits
ASPECT_TOL = 0.03
LOW_DETAIL_BITS = 3           # dHash with <=3 or >=61 set bits: flat image, not compared


def _pil():
    try:
        from PIL import Image, ImageOps
        Image.MAX_IMAGE_PIXELS = MAX_PIXELS
        return Image, ImageOps
    except Exception:
        return None, None


def dhash_image(path: str) -> tuple[str, int, int]:
    """(16-hex dHash, width, height). Opens the file for reading only."""
    Image, ImageOps = _pil()
    if Image is None:
        raise RuntimeError("no-decoder")
    with open(path, "rb") as fh:
        with Image.open(fh) as im:
            w, h = im.size
            if im.format == "JPEG":
                im.draft("L", (128, 128))
            try:
                im = ImageOps.exif_transpose(im)
            except Exception:
                pass
            g = im.convert("L").resize((9, 8), Image.Resampling.BOX)
            px = list(g.tobytes())
    bits = 0
    for r in range(8):
        row = px[r * 9:(r + 1) * 9]
        for c in range(8):
            bits = (bits << 1) | (1 if row[c] > row[c + 1] else 0)
    return f"{bits:016x}", w, h


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


_STEM_NOISE = re.compile(r"(?:[-_ .](?:\d{2,5}x\d{2,5}|thumb(?:nail)?|small|medium|large|scaled|resized|"
                         r"copy|edited|final|web|hi-?res|lo-?res|\d{1,2})|@\dx|\s*\(\d+\))+$")


def norm_stem(name: str) -> str:
    """'IMG_0042-1024x768 (1).jpg' -> 'img_0042'. Used only to choose a bounded sample."""
    stem = os.path.splitext(name)[0].lower()
    return _STEM_NOISE.sub("", stem) or stem


def pick_sample(rows: list, limit: int, seed: int = 7) -> list:
    """Files whose normalised stem is shared by another file come first (a resized or re-exported
    copy usually keeps its name), then a seeded random fill. Deterministic for a given seed."""
    by_stem: dict[str, list] = {}
    for r in rows:
        by_stem.setdefault(norm_stem(r["name"]), []).append(r)
    first = [r for g in by_stem.values() if len(g) > 1 for r in g]
    first.sort(key=lambda r: (norm_stem(r["name"]), r["path"]))
    chosen = first[:limit]
    if len(chosen) < limit:
        seen = {r["path"] for r in chosen}
        rest = [r for r in rows if r["path"] not in seen]
        random.Random(seed).shuffle(rest)
        chosen += rest[:limit - len(chosen)]
    return chosen


def sign_images(ic, sc, run: int, machine: str, limit: int, throttle, budget, byte_budget: int | None,
                log=print) -> dict:
    st = {"candidates": 0, "sampled": 0, "done": 0, "cached": 0, "private": 0, "cloud": 0,
          "no_decoder": 0, "errors": 0, "bytes": 0, "stopped": None}
    rows = ic.execute("SELECT path, name, ext, size, mtime_ns, private, cloud FROM files "
                      "WHERE machine=? AND ftype='image'", (machine,)).fetchall()
    st["candidates"] = len(rows)
    for r in rows:
        if _private(r):
            st["private"] += 1
        elif r["cloud"]:
            st["cloud"] += 1
        elif r["ext"] not in PIL_EXT:
            st["no_decoder"] += 1
    known = {(x["path"], x["mtime_ns"]) for x in sc.execute(
        "SELECT path, mtime_ns FROM imgsig WHERE machine=? AND state='done'", (machine,))}
    ok = [r for r in rows if not _private(r) and not r["cloud"] and r["ext"] in PIL_EXT and r["size"] > 0]
    sample = pick_sample(ok, limit)
    st["sampled"] = len(sample)
    for r in sample:
        if (r["path"], r["mtime_ns"]) in known:
            st["cached"] += 1
            continue
        if budget.out():
            st["stopped"] = "time budget"
            break
        if byte_budget is not None and st["bytes"] + r["size"] > byte_budget:
            st["stopped"] = "byte budget"
            break
        try:
            hx, w, h = dhash_image(r["path"])
            state = "done"
            st["done"] += 1
        except RuntimeError:
            hx, w, h, state = None, None, None, "no-decoder"
            st["no_decoder"] += 1
        except Exception:
            hx, w, h, state = None, None, None, "error"
            st["errors"] += 1
        st["bytes"] += r["size"]
        throttle.took(r["size"])
        sc.execute("INSERT OR REPLACE INTO imgsig VALUES (?,?,?,?,?,?,?,?,?)",
                   (machine, r["path"], r["mtime_ns"], r["size"], state, hx, w, h, run))
        if (st["done"] + st["errors"]) % 500 == 0:
            sc.commit()
    sc.commit()
    log(f"images: {st['done']} hashed, {st['cached']} cached of {st['sampled']} sampled "
        f"({st['candidates']} images indexed; {st['no_decoder']} no local decoder, {st['private']} private, "
        f"{st['cloud']} cloud), {st['bytes'] / 1e9:.2f} GB read" + (f", stopped: {st['stopped']}" if st["stopped"] else ""))
    return st


def image_pairs(sigs: list[dict], max_dist: int = IMG_MAX_DIST, aspect_tol: float = ASPECT_TOL) -> tuple[list, int]:
    """Pairs (i, j, distance) of near-identical images. Multi-index hashing: two 64-bit hashes within
    distance <= 7 share at least one of their eight bytes exactly, so only same-byte buckets are
    compared. Flat images (few or almost all bits set) are skipped and counted."""
    flat = 0
    buckets: dict[tuple[int, int], list[int]] = {}
    vals = []
    for i, s in enumerate(sigs):
        v = int(s["dhash"], 16)
        vals.append(v)
        ones = bin(v).count("1")
        if ones <= LOW_DETAIL_BITS or ones >= 64 - LOW_DETAIL_BITS:
            flat += 1
            continue
        for k in range(8):
            buckets.setdefault((k, (v >> (8 * k)) & 0xFF), []).append(i)
    seen, pairs = set(), []
    for members in buckets.values():
        for x in range(len(members)):
            for y in range(x + 1, len(members)):
                i, j = members[x], members[y]
                if (i, j) in seen:
                    continue
                seen.add((i, j))
                d = bin(vals[i] ^ vals[j]).count("1")
                if d > max_dist:
                    continue
                a, b = sigs[i], sigs[j]
                ra, rb = a["w"] / max(a["h"], 1), b["w"] / max(b["h"], 1)
                if abs(ra - rb) / max(ra, rb) > aspect_tol:
                    continue
                pairs.append((i, j, d))
    return pairs, flat


# --------------------------------------------------------------------------- (a) documents: MinHash

BINS = 64
SHINGLE = 4
MIN_WORDS = 50
DOC_SIM = 0.8
BANDS, ROWS = 16, 4
DOC_EXT_PREF = {".md": 0, ".docx": 0, ".odt": 0, ".txt": 1, ".tex": 1, ".rst": 1, ".markdown": 1,
                ".pptx": 1, ".xlsx": 1, ".html": 2, ".htm": 2, ".pdf": 3}
PDF_MAX_PAGES = 20
_SCRIPT = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")


def doc_words(text: str, ext: str) -> list[str]:
    if ext in (".html", ".htm", ".xml"):
        text = unescape(_TAG.sub(" ", _SCRIPT.sub(" ", text)))
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


def minhash(words: list[str]) -> array:
    """One-permutation MinHash with rotation densification: 64 bins of uint32. Same text, same
    signature, whatever the format it came from."""
    mask = (1 << 26) - 1
    bins = [None] * BINS
    for i in range(len(words) - SHINGLE + 1):
        h = (zlib.crc32(" ".join(words[i:i + SHINGLE]).encode("utf-8")) * 0x9E3779B1) & 0xFFFFFFFF
        b, v = h >> 26, h & mask
        if bins[b] is None or v < bins[b]:
            bins[b] = v
    out = array("I", [0] * BINS)
    if all(x is None for x in bins):
        return out
    for i in range(BINS):
        d = 0
        while bins[(i + d) % BINS] is None:
            d += 1
        out[i] = (d << 26) | bins[(i + d) % BINS]
    return out


def similarity(a: array, b: array) -> float:
    return sum(1 for x, y in zip(a, b) if x == y) / BINS


def pdf_text(path: str) -> str | None:
    """Local pdf text with pypdf, first pages only. None when no local extractor is installed."""
    try:
        from pypdf import PdfReader
    except Exception:
        return None
    with open(path, "rb") as fh:
        rd = PdfReader(fh)
        if rd.is_encrypted:
            raise ValueError("encrypted")
        out = []
        for page in rd.pages[:PDF_MAX_PAGES]:
            out.append(page.extract_text() or "")
            if sum(len(x) for x in out) > fi.EXTRACT_MAX_BODY:
                break
    return " ".join(out)[:fi.EXTRACT_MAX_BODY]


def sign_docs(ic, sc, run: int, machine: str, doc_limit: int | None, pdf_limit: int, throttle, budget,
              byte_budget: int | None, log=print) -> dict:
    """Signatures for documents. Text the index holds is read from the index (no file is opened);
    pdfs, which the index does not extract, are read locally in a bounded sample."""
    st = {"indexed_docs": 0, "signed": 0, "cached": 0, "too_short": 0, "private": 0,
          "pdf_candidates": 0, "pdf_sampled": 0, "pdf_signed": 0, "pdf_no_extractor": 0, "pdf_errors": 0,
          "not_extracted": 0, "bytes": 0, "stopped": None}
    known = {(x["path"], x["mtime_ns"]) for x in sc.execute(
        "SELECT path, mtime_ns FROM docsig WHERE machine=? AND state IN ('done','too-short')", (machine,))}
    rows = ic.execute("SELECT f.id, f.path, f.name, f.ext, f.size, f.mtime_ns, f.private, f.cloud, f.extract_state "
                      "FROM files f WHERE f.machine=? AND f.ftype='doc'", (machine,)).fetchall()
    st["indexed_docs"] = len(rows)
    done_rows = []
    pdfs = []
    for r in rows:
        if _private(r):
            st["private"] += 1
        elif r["extract_state"] == "done":
            done_rows.append(r)
        elif r["ext"] == ".pdf" and not r["cloud"] and r["size"] > 0:
            pdfs.append(r)
        else:
            st["not_extracted"] += 1
    if doc_limit is not None and len(done_rows) > doc_limit:
        done_rows = pick_sample(done_rows, doc_limit)
    n = 0
    for r in done_rows:
        if (r["path"], r["mtime_ns"]) in known:
            st["cached"] += 1
            continue
        if budget.out():
            st["stopped"] = "time budget"
            break
        body = ic.execute("SELECT body FROM fts WHERE rowid=?", (r["id"],)).fetchone()
        words = doc_words(body["body"] if body else "", r["ext"])
        _store_doc(sc, machine, r, words, "index", run, st)
        n += 1
        if n % 2000 == 0:
            sc.commit()
    sc.commit()
    st["pdf_candidates"] = len(pdfs)
    doc_stems = {norm_stem(r["name"]) for r in rows if r["ext"] != ".pdf"}
    pdfs.sort(key=lambda r: (norm_stem(r["name"]) not in doc_stems, r["path"]))   # a pdf twin of a doc first
    for r in pdfs[:pdf_limit]:
        if st["stopped"]:
            break
        if (r["path"], r["mtime_ns"]) in known:
            st["cached"] += 1
            st["pdf_sampled"] += 1
            continue
        if budget.out():
            st["stopped"] = "time budget"
            break
        if byte_budget is not None and st["bytes"] + r["size"] > byte_budget:
            st["stopped"] = "byte budget"
            break
        st["pdf_sampled"] += 1
        try:
            text = pdf_text(r["path"])
        except Exception:
            st["pdf_errors"] += 1
            sc.execute("INSERT OR REPLACE INTO docsig VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (machine, r["path"], r["mtime_ns"], r["size"], r["ext"], "error", None, None, "pypdf", run))
            continue
        st["bytes"] += r["size"]
        throttle.took(r["size"])
        if text is None:
            st["pdf_no_extractor"] += 1
            sc.execute("INSERT OR REPLACE INTO docsig VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (machine, r["path"], r["mtime_ns"], r["size"], r["ext"], "no-extractor", None, None,
                        "none", run))
            continue
        _store_doc(sc, machine, r, doc_words(text, ".pdf"), "pypdf", run, st)
        st["pdf_signed"] += 1
    sc.commit()
    log(f"docs: {st['signed']} signed ({st['pdf_signed']} pdf), {st['cached']} cached, {st['too_short']} too short; "
        f"{st['private']} private (never read), {st['not_extracted']} not extracted by the index"
        + (f", stopped: {st['stopped']}" if st["stopped"] else ""))
    return st


def _store_doc(sc, machine, r, words, src, run, st):
    if len(words) < MIN_WORDS:
        st["too_short"] += 1
        sc.execute("INSERT OR REPLACE INTO docsig VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (machine, r["path"], r["mtime_ns"], r["size"], r["ext"], "too-short", len(words), None, src, run))
        return
    sig = minhash(words)
    sc.execute("INSERT OR REPLACE INTO docsig VALUES (?,?,?,?,?,?,?,?,?,?)",
               (machine, r["path"], r["mtime_ns"], r["size"], r["ext"], "done", len(words), sig.tobytes(), src, run))
    st["signed"] += 1


CROWDED = 400


def doc_pairs(sigs: list[array], threshold: float = DOC_SIM) -> tuple[list, int]:
    """Pairs (i, j, similarity) at or above `threshold`. Banded LSH proposes candidates; a crowded
    bucket (boilerplate shared by hundreds of files) is compared against its first member only and
    counted, so the cost stays linear there."""
    buckets: dict[tuple, list[int]] = {}
    for i, s in enumerate(sigs):
        for band in range(BANDS):
            buckets.setdefault((band, tuple(s[band * ROWS:(band + 1) * ROWS])), []).append(i)
    crowded, seen, pairs = 0, set(), []
    for members in buckets.values():
        if len(members) < 2:
            continue
        if len(members) > CROWDED:
            crowded += 1
            cands = [(members[0], m) for m in members[1:]]
        else:
            cands = [(members[x], members[y]) for x in range(len(members)) for y in range(x + 1, len(members))]
        for i, j in cands:
            if (i, j) in seen:
                continue
            seen.add((i, j))
            s = similarity(sigs[i], sigs[j])
            if s >= threshold:
                pairs.append((i, j, s))
    return pairs, crowded


# --------------------------------------------------------------------------- grouping (report only)

def _groups(n: int, pairs: list) -> list[list[int]]:
    """Seed-anchored groups: a group is one seed plus the files that matched the seed itself, never
    files reached only through another member. The first version took connected components of the
    pair graph (single linkage), so A~B and B~C and C~D made one group of A..D although A and D were
    nothing alike, and one soft file could fuse hundreds of unrelated groups into one. Here every
    member is within the threshold of the seed, so any two members are within twice the threshold of
    each other (Hamming distance and Jaccard distance are metrics). Seeds are taken in order of how
    many files matched them (most first, then lowest index), so a boilerplate hub seeds one group and
    a file that matched only through it is not dragged along. A file belongs to at most one group."""
    adj: dict[int, set[int]] = {}
    for i, j, _ in pairs:
        adj.setdefault(i, set()).add(j)
        adj.setdefault(j, set()).add(i)
    assigned: set[int] = set()
    out: list[list[int]] = []
    for seed in sorted(adj, key=lambda x: (-len(adj[x]), x)):
        if seed in assigned:
            continue
        mates = adj[seed] - assigned
        if not mates:
            continue
        group = sorted(mates | {seed})
        assigned.update(group)
        out.append(group)
    return out


def _pair_sim(kind: str, sigs: list, arrs: list | None, i: int, j: int) -> float:
    """Similarity of two signed files, computed directly (not read off the pair list, which only
    holds the pairs that cleared the threshold)."""
    if kind == "image":
        return 1 - hamming(sigs[i]["dhash"], sigs[j]["dhash"]) / 64
    return similarity(arrs[i], arrs[j])


def propose_near_canonical(kind: str, members: list[dict]) -> tuple[dict, str]:
    """Most durable location first (git repo, synced trees; downloads/tmp last, the part 5 rule),
    then for images the largest picture and for documents the editable source format, then the
    oldest modified date, then the shortest path."""
    def key(m):
        d, _ = fi.durability(m["path"], m.get("in_git", 0))
        second = -(m.get("w") or 0) * (m.get("h") or 0) if kind == "image" else DOC_EXT_PREF.get(m["ext"], 2)
        return (-d, second, m.get("mtime") or 0, len(m["path"]), m["path"])
    ranked = sorted(members, key=key)
    best = ranked[0]
    why = fi.durability(best["path"], best.get("in_git", 0))[1]
    if len(ranked) > 1 and key(ranked[1])[0] == key(best)[0]:
        why += ("; largest picture among equally durable copies" if kind == "image"
                else "; editable source format among equally durable copies")
    return best, why


def build_near_groups(ic, sc, run: int, machine: str, kind: str, img_dist: int = IMG_MAX_DIST,
                      doc_sim: float = DOC_SIM, log=print) -> dict:
    """Replace this machine's `kind` groups with a fresh set. Writes only the smart store."""
    if kind == "image":
        sigs = [dict(r) for r in sc.execute(
            "SELECT path, size, dhash, w, h FROM imgsig WHERE machine=? AND state='done'", (machine,))]
        pairs, skipped = image_pairs(sigs, img_dist)
        arrs = None
        floor = 1 - img_dist / 64
    else:
        rows = [dict(r) for r in sc.execute(
            "SELECT path, size, ext, sig FROM docsig WHERE machine=? AND state='done'", (machine,))]
        sigs = rows
        arrs = []
        for r in rows:
            a = array("I")
            a.frombytes(r["sig"])
            arrs.append(a)
        pairs, skipped = doc_pairs(arrs, doc_sim)
        floor = doc_sim
    meta = {}
    for r in ic.execute("SELECT path, size, ext, mtime, in_git, hash FROM files WHERE machine=? AND ftype=?",
                        (machine, "image" if kind == "image" else "doc")):
        meta[r["path"]] = dict(r)
    old = [r["id"] for r in sc.execute(
        "SELECT g.id FROM near_groups g WHERE g.kind=? AND g.id IN "
        "(SELECT group_id FROM near_members WHERE machine=?)", (kind, machine))]
    for gid in old:
        sc.execute("DELETE FROM near_members WHERE group_id=?", (gid,))
        sc.execute("DELETE FROM near_groups WHERE id=?", (gid,))
    st = {"signatures": len(sigs), "pairs": len(pairs), "groups": 0, "members": 0, "exact_only_skipped": 0,
          "cross_format_groups": 0, "reclaimable": 0, "skipped": skipped}
    for g in _groups(len(sigs), pairs):
        members = []
        for i in g:
            m = {**sigs[i], **meta.get(sigs[i]["path"], {"ext": os.path.splitext(sigs[i]["path"])[1].lower()})}
            members.append(m)
        hashes = {m.get("hash") for m in members}
        if len(hashes) == 1 and None not in hashes:
            st["exact_only_skipped"] += 1          # all byte-identical: already in the exact report
            continue
        canon, why = propose_near_canonical(kind, members)
        ci = g[members.index(canon)]
        # similarity of every member to the keep copy, computed directly: the pair list only holds
        # pairs that matched, and a member that matched the seed may not match the keep copy
        sim_to = {i: (1.0 if i == ci else _pair_sim(kind, sigs, arrs, i, ci)) for i in g}
        sims = [s for i, s in sim_to.items() if i != ci]
        formats = sorted({m["ext"] for m in members})
        recl = sum(m["size"] for m in members if m is not canon)
        cur = sc.execute("INSERT INTO near_groups (run, kind, members, reclaimable, min_sim, max_sim, formats, "
                         "canonical, reason) VALUES (?,?,?,?,?,?,?,?,?)",
                         (run, kind, len(members), recl, min(sims), max(sims), ",".join(formats), canon["path"], why))
        gid = cur.lastrowid
        for i, m in zip(g, members):
            s = sim_to[i]
            note = []
            if i != ci and s < floor:
                note.append(f"matched the group's seed, not the keep copy (similarity {s:.2f}, "
                            f"below {floor:.2f}): review before treating as a copy")
            if m is not canon and m.get("hash") and m.get("hash") == canon.get("hash"):
                note.append("byte-identical to the keep copy")
            if kind == "image" and m is not canon and (m.get("w"), m.get("h")) != (canon.get("w"), canon.get("h")):
                note.append(f"{m.get('w')}x{m.get('h')} vs {canon.get('w')}x{canon.get('h')}")
            if m["ext"] != canon["ext"]:
                note.append(f"format {m['ext']} vs {canon['ext']}")
            sc.execute("INSERT INTO near_members VALUES (?,?,?,?,?,?,?,?)",
                       (gid, machine, m["path"], m["size"], m["ext"], "keep" if m is canon else "near-copy",
                        s, "; ".join(note) or None))
        st["groups"] += 1
        st["members"] += len(members)
        st["reclaimable"] += recl
        if len(formats) > 1:
            st["cross_format_groups"] += 1
    sc.commit()
    log(f"near {kind}: {st['groups']} groups ({st['cross_format_groups']} across formats), {st['members']} files, "
        f"{fi.human(st['reclaimable'])} if the near-copies went; {st['exact_only_skipped']} byte-identical sets left "
        f"to the exact report; skipped {st['skipped']} ({'flat images' if kind == 'image' else 'crowded buckets'})")
    return st


# --------------------------------------------------------------------------- (b) tags: rules

KINDS = ("code", "docs", "data", "media", "backup", "model", "archive", "binary", "other")
SCOPES = ("estate", "personal")
BACKUP_TOKENS = {"backup", "backups", "bak", "offload", "snapshot", "snapshots", "archive", "archived",
                 "old", "stick"}
BACKUP_EXT = {".bak", ".old", ".orig", ".bkp"}
MODEL_EXT = {".gguf", ".safetensors", ".onnx", ".pt", ".ckpt"}
ESTATE_TOKENS = {"leadfuel", "novahos", "colibri", "fieldy", "lucid", "toolkit", "estate", "homenode"}
ESTATE_SEGMENTS = {"claude sessions", "home-node", "novah-estate", "novahos-handoff", "fieldy-local"}
ESTATE_TOP = {"novah"}         # F:\novah is estate; C:\Users\novah (a home folder) is not
PERSONAL_TOKENS = {"pictures", "photos", "photo", "dcim", "documents", "music", "family", "personal",
                   "iphone", "whatsapp", "screenshots", "wallpapers", "vacation", "wedding"}
# Ratified arm names. Old folders still carry the retired spellings, so they are recognised and mapped
# to the ratified name; the retired words are assembled from fragments so no retired name is typed.
ARMS = ("hub", "signal", "scope", "reach", "orbit", "odyssey")
_N = "nova" + "h"
RETIRED_TO_ARM = {_N + "hub": "hub", _N + "hound": "signal", _N + "hawk": "orbit", _N + "herald": "reach",
                  _N + "hunt": "odyssey", "smart" + "icp": "scope"}
PROJECT_TOKENS = {"leadfuel": ("leadfuel", 0.7), "novahos": ("novahos", 0.85), "colibri": ("colibri", 0.85),
                  "fieldy": ("fieldy", 0.85), "lucid": ("lucid", 0.8), "homenode": ("home-node", 0.85)}
PREFIX_PROJECTS = (("/video/ai", "character-design", 0.75), ("/home-node", "home-node", 0.85))


def _segs(path: str) -> list[str]:
    return [s for s in fi.norm(path).split("/") if s]


def _toks(seg: str) -> set[str]:
    t = set(re.split(r"[^a-z0-9]+", seg.lower())) - {""}
    t.add(re.sub(r"[^a-z0-9]", "", seg.lower()))       # 'home-node' -> 'homenode'
    return t


def rule_tags(path: str, ext: str, ftype: str, private: str | None, in_git: int) -> list[tuple]:
    """[(facet, value, confidence, detail)] from the path alone. A facet no rule can decide is left
    out (the model or `unknown` fills it later); a rule never guesses."""
    out = []
    segs = _segs(path)
    dirs = segs[:-1]
    low = "/" + "/".join(s.lower() for s in segs)
    ext = (ext or "").lower()
    out.append(("media", ftype or "other", 0.95, f"extension {ext or '(none)'}"))
    if private:
        out.append(("privacy", private.split(":", 1)[0], 1.0, f"privacy-tier path rule ({private})"))
    # kind
    bk = next((s for s in reversed(dirs) if _toks(s) & BACKUP_TOKENS), None)
    if bk is not None:
        out.append(("kind", "backup", 0.85, f"folder '{bk}' reads as a backup"))
    elif ext in BACKUP_EXT:
        out.append(("kind", "backup", 0.8, f"extension {ext}"))
    elif ext in MODEL_EXT or any(s.lower() == "models" for s in dirs):
        out.append(("kind", "model", 0.85, "model weights folder or extension"))
    elif ftype == "code":
        out.append(("kind", "code", 0.95 if in_git else 0.9, "code extension" + (" inside a git repo" if in_git else "")))
    elif ftype == "doc":
        out.append(("kind", "docs", 0.9, "document extension"))
    elif ftype in ("image", "video", "audio"):
        out.append(("kind", "media", 0.9, f"{ftype} extension"))
    elif ftype in ("data", "archive", "binary"):
        out.append(("kind", ftype, 0.75, f"{ftype} extension"))
    # scope: the deepest folder that says estate or personal wins
    scope = None
    for depth, s in enumerate(dirs):
        t, sl = _toks(s), s.lower()
        if (depth == 1 and sl in ESTATE_TOP) or sl in ESTATE_SEGMENTS or t & ESTATE_TOKENS or t & set(RETIRED_TO_ARM) or sl in ARMS:
            scope = ("estate", 0.8 if sl in ESTATE_SEGMENTS or t & ESTATE_TOKENS else 0.6, f"folder '{s}'", depth)
        elif t & PERSONAL_TOKENS:
            scope = ("personal", 0.75, f"folder '{s}'", depth)
    if scope is None and private and private.split(":", 1)[0] in ("health", "financial"):
        scope = ("personal", 0.6, "health or financial path", -1)
    if scope:
        out.append(("scope", scope[0], scope[1], scope[2]))
    # project: the most distinctive match, deeper on ties
    best = None
    for depth, s in enumerate(dirs):
        t, sl = _toks(s), s.lower()
        cands = []
        for old, arm in RETIRED_TO_ARM.items():
            if old in t or sl.startswith(old):
                cands.append((arm, 0.8, f"folder '{s}' (older name of {arm})"))
        for arm in ARMS:
            if sl == arm or sl.startswith(arm + "-") or sl.startswith(arm + "_"):
                cands.append((arm, 0.55, f"folder '{s}'"))
        for tok, (proj, conf) in PROJECT_TOKENS.items():
            if tok in t:
                cands.append((proj, conf, f"folder '{s}'"))
        for c in cands:
            if best is None or (c[1], depth) >= (best[1], best[3]):
                best = (*c, depth)
    for pre, proj, conf in PREFIX_PROJECTS:
        if pre in low and (best is None or conf > best[1]):
            best = (proj, conf, f"path under {pre}", 99)
    if best:
        out.append(("project", best[0], best[1], best[2]))
    # client: the folder right under a 'clients' folder
    for i, s in enumerate(dirs[:-1] if dirs else []):
        if s.lower() in ("clients", "client"):
            out.append(("client", dirs[i + 1].lower(), 0.85, f"folder under '{s}'"))
            break
    return out


def tag_rules(ic, sc, run: int, machine: str, log=print) -> dict:
    """Rule tags for every indexed row of `machine`: the index's metadata only, no file is opened."""
    at = _now_iso()
    st = {"files": 0, "rows": 0, "by_facet": {}}
    sc.execute("DELETE FROM tags WHERE machine=? AND source='rule'", (machine,))
    batch = []
    for r in ic.execute("SELECT path, ext, ftype, private, in_git FROM files WHERE machine=?", (machine,)):
        st["files"] += 1
        priv = r["private"] or fi.privacy_of(r["path"])
        for facet, value, conf, detail in rule_tags(r["path"], r["ext"], r["ftype"], priv, r["in_git"]):
            batch.append((machine, r["path"], facet, value, "rule", conf, detail, run, at))
            st["by_facet"][facet] = st["by_facet"].get(facet, 0) + 1
        if len(batch) >= 20000:
            sc.executemany("INSERT OR REPLACE INTO tags VALUES (?,?,?,?,?,?,?,?,?)", batch)
            st["rows"] += len(batch)
            batch = []
    sc.executemany("INSERT OR REPLACE INTO tags VALUES (?,?,?,?,?,?,?,?,?)", batch)
    st["rows"] += len(batch)
    sc.commit()
    log(f"rule tags: {st['rows']} tags on {st['files']} files {st['by_facet']}")
    return st


# --------------------------------------------------------------------------- (b) tags: local model

OLLAMA_URL = os.environ.get("CLUSTER_FILES_OLLAMA", "http://127.0.0.1:11434")
DEFAULT_MODEL = "qwen3:4b-instruct-2507-q8_0"
MODEL_BATCH = 20
SNIPPET = 240


def assert_loopback(url: str) -> str:
    host = urlparse(url).hostname or ""
    if host not in fi.LOOPBACK:
        raise SystemExit(f"refused: the model must be on this machine (loopback), not {host or url}")
    return url.rstrip("/")


def model_available(url: str, model: str, timeout: float = 5.0) -> tuple[bool, str]:
    url = assert_loopback(url)
    try:
        with urllib.request.urlopen(url + "/api/tags", timeout=timeout) as resp:
            names = [m.get("name") for m in json.load(resp).get("models", [])]
    except Exception as e:
        return False, f"no local model server at {url} ({type(e).__name__})"
    if model not in names:
        return False, f"model {model} is not installed in the local server"
    return True, f"{model} at {url}"


def _prompt(items: list[dict]) -> list[dict]:
    sys_msg = ("You tag files for a private index on the owner's own machine. For each item decide: "
               f"kind (one of {', '.join(KINDS)}), scope (estate = his software business and its projects; "
               "personal = his own life, photos, documents; or unknown), project (a short lowercase slug, "
               "or unknown), and confidence (0 to 1). Say unknown rather than guess. "
               'Answer JSON only: {"items":[{"id":1,"kind":"...","scope":"...","project":"...","confidence":0.5}]}')
    lines = []
    for it in items:
        line = {"id": it["id"], "path": it["path"], "type": it["ftype"]}
        if it.get("snippet"):
            line["start_of_text"] = it["snippet"]
        lines.append(json.dumps(line, ensure_ascii=False))
    return [{"role": "system", "content": sys_msg}, {"role": "user", "content": "\n".join(lines)}]


def ask_model(url: str, model: str, items: list[dict], timeout: float = 600.0) -> list[dict]:
    body = json.dumps({"model": model, "messages": _prompt(items), "stream": False, "format": "json",
                       "options": {"temperature": 0, "num_predict": 120 * len(items)},
                       "keep_alive": "5m"}).encode("utf-8")
    req = urllib.request.Request(assert_loopback(url) + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        msg = json.load(resp).get("message", {}).get("content", "")
    data = json.loads(msg)
    return data.get("items", []) if isinstance(data, dict) else []


_SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")


def clean_model_answer(a: dict) -> dict:
    """Keep only values from the allowed sets; anything else becomes `unknown`."""
    def pick(v, allowed):
        v = str(v or "").strip().lower()
        return v if v in allowed else "unknown"
    proj = str(a.get("project") or "").strip().lower()
    proj = RETIRED_TO_ARM.get(proj, proj)
    try:
        conf = max(0.0, min(1.0, float(a.get("confidence"))))
    except (TypeError, ValueError):
        conf = None
    return {"kind": pick(a.get("kind"), KINDS), "scope": pick(a.get("scope"), SCOPES),
            "project": proj if _SLUG.fullmatch(proj) and proj != "unknown" else "unknown", "confidence": conf}


def tag_model(ic, sc, run: int, machine: str, sample: int, url: str, model: str, budget, ask=ask_model,
              log=print) -> dict:
    """Model tags for a bounded sample of files the rules left without a scope or project. Private
    rows go to the model by path only. With no local model the sample is tagged `unknown`."""
    at = _now_iso()
    st = {"sample": 0, "tagged": 0, "unknown_no_model": 0, "unknown_answers": 0, "batches": 0,
          "errors": 0, "seconds": 0.0, "stopped": None, "model": None}
    have = {}
    for r in sc.execute("SELECT path, facet FROM tags WHERE machine=? AND source='rule' AND facet IN ('scope','project')",
                        (machine,)):
        have.setdefault(r["path"], set()).add(r["facet"])
    rows = [r for r in ic.execute("SELECT id, path, ftype, private, extract_state FROM files WHERE machine=?",
                                  (machine,)) if have.get(r["path"], set()) != {"scope", "project"}]
    random.Random(11).shuffle(rows)
    rows = rows[:sample]
    st["sample"] = len(rows)
    ok, why = model_available(url, model)
    st["model"] = why
    if not ok:
        for r in rows:
            for facet in ("kind", "scope", "project"):
                sc.execute("INSERT OR REPLACE INTO tags VALUES (?,?,?,?,?,?,?,?,?)",
                           (machine, r["path"], facet, "unknown", "model", None, why, run, at))
        st["unknown_no_model"] = len(rows)
        sc.commit()
        log(f"model tags: {why}; {len(rows)} sampled files tagged unknown (nothing invented)")
        return st
    t0 = time.monotonic()
    for k in range(0, len(rows), MODEL_BATCH):
        if budget.out():
            st["stopped"] = "time budget"
            break
        part = rows[k:k + MODEL_BATCH]
        items = []
        for n, r in enumerate(part, 1):
            it = {"id": n, "path": r["path"], "ftype": r["ftype"]}
            if not _private(r) and r["extract_state"] == "done" and r["ftype"] == "doc":
                b = ic.execute("SELECT body FROM fts WHERE rowid=?", (r["id"],)).fetchone()
                if b and b["body"]:
                    it["snippet"] = " ".join(b["body"][:SNIPPET * 2].split())[:SNIPPET]
            items.append(it)
        try:
            answers = {int(a.get("id", -1)): a for a in ask(url, model, items) if isinstance(a, dict)}
        except Exception as e:
            st["errors"] += 1
            answers = {}
            err = f"model call failed ({type(e).__name__})"
        else:
            err = None
        st["batches"] += 1
        for n, r in enumerate(part, 1):
            a = answers.get(n)
            c = clean_model_answer(a) if a else {"kind": "unknown", "scope": "unknown", "project": "unknown",
                                                  "confidence": None}
            detail = err or (f"{model}, self-reported confidence" + (", path only (private)" if _private(r) else ""))
            if a is None:
                st["unknown_answers"] += 1
            for facet in ("kind", "scope", "project"):
                conf = c["confidence"] if c[facet] != "unknown" else None
                sc.execute("INSERT OR REPLACE INTO tags VALUES (?,?,?,?,?,?,?,?,?)",
                           (machine, r["path"], facet, c[facet], "model", conf, detail, run, at))
            st["tagged"] += 1
        sc.commit()
    st["seconds"] = round(time.monotonic() - t0, 1)
    log(f"model tags: {st['tagged']} files in {st['batches']} batches, {st['seconds']}s, {st['errors']} failed calls, "
        f"{st['unknown_answers']} with no answer (stored as unknown)" + (f", stopped: {st['stopped']}" if st["stopped"] else ""))
    return st


# --------------------------------------------------------------------------- report

def report(sc, top: int = 25) -> dict:
    groups = {}
    for kind in ("image", "doc"):
        gs = [dict(g) for g in sc.execute("SELECT * FROM near_groups WHERE kind=? ORDER BY reclaimable DESC", (kind,))]
        for g in gs[:top]:
            g["members_list"] = [dict(m) for m in sc.execute(
                "SELECT machine, path, size, ext, role, sim, note FROM near_members WHERE group_id=? "
                "ORDER BY role='keep' DESC, path", (g["id"],))]
        groups[kind] = {"groups": len(gs), "members": sum(g["members"] for g in gs),
                        "cross_format": sum(1 for g in gs if "," in (g["formats"] or "")),
                        "reclaimable": sum(g["reclaimable"] for g in gs), "top": gs[:top]}
    sig = {k: {r[0]: r[1] for r in sc.execute(f"SELECT state, COUNT(*) FROM {t} GROUP BY 1")}
           for k, t in (("image", "imgsig"), ("doc", "docsig"))}
    tags = {}
    for r in sc.execute("SELECT facet, source, value, COUNT(*) n, ROUND(AVG(confidence),2) c FROM tags "
                        "GROUP BY 1,2,3 ORDER BY 1,2,4 DESC"):
        tags.setdefault(r["facet"], {}).setdefault(r["source"], []).append(
            {"value": r["value"], "files": r["n"], "avg_confidence": r["c"]})
    runs = [dict(r) for r in sc.execute("SELECT id, kind, state, started, finished, counts, note FROM runs "
                                        "ORDER BY id DESC LIMIT 10")]
    return {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "near": groups,
            "signatures": sig, "tags": tags, "runs": runs,
            "note": ("Report only. Nothing was moved or deleted. Near-duplicate groups cover only the files "
                     "signed so far (a bounded sample for images and pdfs); every other file's near-duplicate "
                     "status is unknown, not unique. Byte-identical sets are in the part 5 exact report.")}


def report_markdown(rep: dict) -> str:
    out = [f"# Near-duplicates and tags (report only, generated {rep['generated']})", "", rep["note"], ""]
    for kind, g in rep["near"].items():
        out += [f"## {kind}: {g['groups']} groups, {g['members']} files, {g['cross_format']} across formats, "
                f"{fi.human(g['reclaimable'])} if the near-copies went", "",
                f"Signatures: {json.dumps(rep['signatures'][kind])}", "",
                "| # | files | similarity | formats | proposed keep | why |", "|---|---|---|---|---|---|"]
        for i, x in enumerate(g["top"], 1):
            out.append(f"| {i} | {x['members']} | {x['min_sim']:.2f}-{x['max_sim']:.2f} | {x['formats']} | "
                       f"`{x['canonical']}` | {x['reason']} |")
        out.append("")
    out += ["## Tags", ""]
    for facet, by_src in rep["tags"].items():
        for src, vals in by_src.items():
            out.append(f"- **{facet}** ({src}): " + ", ".join(
                f"{v['value']} {v['files']}" + (f" (avg {v['avg_confidence']})" if v["avg_confidence"] is not None else "")
                for v in vals[:12]))
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="file_smart", description=__doc__.split("\n")[0])
    ap.add_argument("--db", default=fi.default_db(), help="the part 2 index (opened read-only)")
    ap.add_argument("--smart-db", default=None, help="where results go (default: smart.sqlite beside the index)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="near-duplicates and tags on the existing index plus a bounded sample")
    r.add_argument("--machine", default=socket.gethostname().lower())
    r.add_argument("--images", type=int, default=3000, help="image sample size (decoded locally)")
    r.add_argument("--docs", type=int, default=None, help="cap on documents signed from the index's text")
    r.add_argument("--pdfs", type=int, default=300, help="pdf sample size (text extracted locally)")
    r.add_argument("--model-sample", type=int, default=100, help="files sent to the local model")
    r.add_argument("--model", default=DEFAULT_MODEL)
    r.add_argument("--ollama", default=OLLAMA_URL)
    r.add_argument("--minutes", type=float, default=60.0, help="time budget for the run")
    r.add_argument("--gb", type=float, default=5.0, help="byte budget for files read (images, pdfs)")
    r.add_argument("--mbps", type=float, default=40.0, help="read cap, MB/s")
    r.add_argument("--skip", action="append", default=[], choices=("images", "docs", "rules", "model"))
    r.add_argument("--heavy-lock", default=os.environ.get("HEAVY_LOCK_PY"))
    r.add_argument("--wait-lock", type=float, default=0, help="minutes to queue for the heavy lock")
    r.add_argument("--no-lock", action="store_true", help="tests and tiny indexes only")
    p = sub.add_parser("report", help="write near.json and near.md (report only)")
    p.add_argument("--out", help="folder (keep it off the vault: it lists real paths)")
    p.add_argument("--top", type=int, default=25)
    sub.add_parser("stats", help="signature, group and tag counts")
    a = ap.parse_args(argv)
    smart_db = a.smart_db or default_smart_db(a.db)

    if a.cmd in ("report", "stats"):
        sc = connect_smart(smart_db)
        rep = report(sc, getattr(a, "top", 10))
        if a.cmd == "stats":
            print(json.dumps({k: rep[k] for k in ("signatures", "tags")} |
                             {"near": {k: {x: v[x] for x in ("groups", "members", "cross_format", "reclaimable")}
                                       for k, v in rep["near"].items()}}, indent=1, default=str))
            sc.close()
            return 0
        if a.out:
            os.makedirs(a.out, exist_ok=True)
            with open(os.path.join(a.out, "near.json"), "w", encoding="utf-8") as fh:
                json.dump(rep, fh, indent=1, default=str)
            with open(os.path.join(a.out, "near.md"), "w", encoding="utf-8") as fh:
                fh.write(report_markdown(rep))
        sc.close()
        print(report_markdown(rep))
        return 0

    allowed, why = may_run_now()
    if not allowed:
        print(f"WAIT: {why}")
        return 4
    ic = connect_index_ro(a.db)
    token = None
    if not a.no_lock:
        give_up = time.monotonic() + a.wait_lock * 60
        while True:
            state, token = fi.heavy_lock_acquire(f"file-smart {a.machine}", a.heavy_lock)
            if state in ("granted", "unknown") or time.monotonic() >= give_up:
                break
            time.sleep(60)
        if state != "granted":
            print(f"WAIT: heavy lock {state}; " + (
                "another heavy job or hub CI holds it, try again later (--wait-lock queues)" if state == "refused"
                else "set HEAVY_LOCK_PY or --heavy-lock to scripts/heavy_lock.py"))
            return 3
    sc = connect_smart(smart_db)
    params = {k: v for k, v in vars(a).items() if k not in ("cmd",)}
    run = start_run(sc, "run", params)
    counts, state = {"priority": fi.lower_priority(), "when": why}, "complete"
    try:
        budget = fi.Budget(a.minutes * 60)
        th = fi.Throttle(a.mbps)
        byte_budget = int(a.gb * 1e9)
        if "rules" not in a.skip:
            counts["rules"] = tag_rules(ic, sc, run, a.machine)
        if "images" not in a.skip:
            counts["images"] = sign_images(ic, sc, run, a.machine, a.images, th, budget, byte_budget)
            counts["near_image"] = build_near_groups(ic, sc, run, a.machine, "image")
        if "docs" not in a.skip:
            left = byte_budget - counts.get("images", {}).get("bytes", 0)
            counts["docs"] = sign_docs(ic, sc, run, a.machine, a.docs, a.pdfs, th, budget, max(left, 0))
            counts["near_doc"] = build_near_groups(ic, sc, run, a.machine, "doc")
        if "model" not in a.skip:
            counts["model"] = tag_model(ic, sc, run, a.machine, a.model_sample, a.ollama, a.model, budget)
        if any(isinstance(v, dict) and v.get("stopped") for v in counts.values()):
            state = "partial"
    except KeyboardInterrupt:
        state = "partial"
    finally:
        finish_run(sc, run, state, counts, None if state == "complete" else "stopped early; unsigned files are unknown")
        sc.close()
        ic.close()
        if token:
            fi.heavy_lock_release(token, a.heavy_lock)
    print(f"run {run}: {state}")
    return 0 if state == "complete" else 2


if __name__ == "__main__":
    sys.exit(main())
