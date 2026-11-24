"""Cluster files part 8: the gated apply step for the dedupe page's clicks. Stdlib only, all local.

DRY-RUN BY DEFAULT. Nothing moves unless `--apply` is passed, and nothing is ever deleted by `apply`:
the non-canonical copies of a group are MOVED (a same-volume rename) into a quarantine folder with a
manifest, and `restore` puts them back. Deleting a quarantined copy is a separate command, `purge`,
which also needs `--apply` and refuses any batch younger than 30 days.

What `apply` acts on: ONLY groups whose recorded decision (the `decisions` table that
`file_index.py decisions` fills from the page export) is `keep_canonical` and names its canonical
path. A group with no decision, `keep_both` or `decide_later` is refused. There is no "apply the
proposal" mode: the proposal in the report is not a decision.

A group is refused as a whole (nothing in it moves) when any of these holds:
  * the recorded canonical path is not one of the group's indexed copies;
  * a copy is not on this machine (a remote copy cannot be verified or moved from here);
  * a path is in the privacy tier, in the book (F:\\repos\\resonance, a separate estate), or a copy
    to be moved is inside a repository (`in_git` in the index, a `.git` above it, or a `/repos/`
    segment), or inside the quarantine itself;
  * the canonical copy is missing or no longer hashes to the group's SHA-256 (checked immediately
    before the moves);
  * a copy is missing, unreadable or no longer hashes to the group's SHA-256 (the index is stale:
    re-index first);
  * a copy is the same file as the canonical (a hard link, or the same path in another case);
  * the quarantine folder is on a different volume from the copy (a move would be a copy + delete).
After the moves the canonical copy is hashed again; if it is missing or changed, every copy moved for
that group is put back at once and the group is reported `rolled-back`.

Quarantine layout, one root per volume (default `<drive>:\\.cluster-files-quarantine`; the scanner
skips that folder name):
    <root>/<batch>/manifest.json
    <root>/<batch>/files/<group hash[:16]>/<n>-<original file name>
The manifest records, per copy: original path, quarantined path, group hash, size, mtime, moved_at,
canonical path, state (quarantined | restored | purged | kept), and the restore command.

The index is opened read-only. This tool writes only inside quarantine roots (and moves files back
out of them on `restore`); it never touches the decisions table or any other row.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import socket
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import file_index as fi  # noqa: E402

QUARANTINE_DIRNAME = fi.QUARANTINE_DIRNAME
RESTORE_DAYS = 30
DAY = 86400

# Group verdicts
PLANNED, MOVED, REFUSED, ROLLED_BACK = "planned", "moved", "refused", "rolled-back"


def _now() -> float:
    return time.time()


def _iso(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="seconds")


def _same_path(a: str, b: str) -> bool:
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def default_quarantine_root(path: str) -> str | None:
    """`<drive>:/.cluster-files-quarantine` on Windows. Elsewhere there is no safe default."""
    drive = os.path.splitdrive(os.path.abspath(path))[0]
    if not drive:
        return None
    return fi.norm(drive + "/" + QUARANTINE_DIRNAME)


def _git_above(path: str) -> bool:
    d = os.path.dirname(os.path.abspath(path))
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return True
        up = os.path.dirname(d)
        if up == d:
            return False
        d = up


def protected(path: str, in_git: int = 0, moving: bool = True) -> str | None:
    """Why a path may not take part in an apply, or None. The canonical copy (`moving=False`) may
    sit in a repo (that is often why it was chosen); it may not be private or in the book."""
    n = fi.norm(path).lower()
    priv = fi.privacy_of(path)
    if priv:
        return f"privacy tier ({priv})"
    if fi.BOOK_PART + "/" in n + "/":
        return "in the book (a separate estate)"
    if "/" + QUARANTINE_DIRNAME.lower() + "/" in n:
        return "inside the quarantine"
    if moving:
        if in_git:
            return "inside a git repo (index)"
        if "/repos/" in n + "/" or "/.claude/worktrees/" in n:
            return "on a repo path"
        if _git_above(path):
            return "inside a git repo (.git above it)"
    return None


def _hash(path: str, mbps: float) -> str | None:
    try:
        return fi.full_hash(path, fi.Throttle(mbps))
    except OSError:
        return None


def _check_hash(path: str, want: str, mbps: float) -> str | None:
    """None when `path` exists and hashes to `want`; otherwise the reason."""
    if not os.path.isfile(path):
        return "missing"
    got = _hash(path, mbps)
    if got is None:
        return "unreadable"
    if got != want:
        return "changed since it was indexed"
    return None


# --------------------------------------------------------------------------- planning

def load_group(con, h: str) -> dict:
    """The recorded decision and the indexed copies for one group hash. Read-only."""
    dec = con.execute("SELECT decision, canonical, at, source FROM decisions WHERE hash=?", (h,)).fetchone()
    copies = [dict(r) for r in con.execute(
        "SELECT machine, path, size, mtime, in_git FROM files WHERE hash=? AND hash_state='full'", (h,))]
    return {"hash": h, "decision": dict(dec) if dec else None, "copies": copies}


def plan_group(con, h: str, machine: str, quarantine: str | None = None, mbps: float = 0.0) -> dict:
    """Every check `apply` makes before a move, with nothing moved. Returns a plan whose `verdict`
    is `planned` or `refused` (with `why`)."""
    out = {"hash": h, "verdict": REFUSED, "why": None, "canonical": None, "moves": []}
    if not re.fullmatch(r"[0-9a-f]{64}", h or ""):
        out["why"] = "not a SHA-256 group hash"
        return out
    g = load_group(con, h)
    dec = g["decision"]
    if dec is None:
        out["why"] = "not decided (no recorded click for this group)"
        return out
    if dec["decision"] != "keep_canonical":
        out["why"] = f"decision is {dec['decision']}, only keep_canonical is applied"
        return out
    if not dec["canonical"]:
        out["why"] = "the decision does not name a canonical path"
        return out
    if len(g["copies"]) < 2:
        out["why"] = "the index has fewer than two copies for this hash (re-index, then re-decide)"
        return out
    canon = next((c for c in g["copies"] if c["path"] == dec["canonical"]), None)
    if canon is None:
        out["why"] = "the recorded canonical path is not one of this group's indexed copies"
        return out
    remote = sorted({c["machine"] for c in g["copies"] if c["machine"] != machine})
    if remote:
        out["why"] = f"copies on other machines ({', '.join(remote)}): only local groups are applied"
        return out
    out["canonical"] = canon["path"]
    why = protected(canon["path"], canon["in_git"], moving=False)
    if why:
        out["why"] = f"canonical {why}"
        return out
    others = [c for c in g["copies"] if c is not canon]
    for c in others:
        why = protected(c["path"], c["in_git"], moving=True)
        if why:
            out["why"] = f"copy {c['path']}: {why}"
            return out
    bad = _check_hash(canon["path"], h, mbps)
    if bad:
        out["why"] = f"canonical {bad}"
        return out
    for c in others:
        bad = _check_hash(c["path"], h, mbps)
        if bad:
            out["why"] = f"copy {c['path']}: {bad} (re-index first)"
            return out
        try:
            if os.path.samefile(c["path"], canon["path"]):
                out["why"] = f"copy {c['path']} is the same file as the canonical"
                return out
        except OSError as e:
            out["why"] = f"copy {c['path']}: cannot compare with the canonical ({type(e).__name__})"
            return out
        root = quarantine or default_quarantine_root(c["path"])
        if not root:
            out["why"] = "no quarantine root (pass --quarantine on this platform)"
            return out
        vol = _volume_of(root)
        try:
            if os.stat(c["path"]).st_dev != os.stat(vol).st_dev:
                out["why"] = f"copy {c['path']}: the quarantine {root} is on another volume"
                return out
        except OSError as e:
            out["why"] = f"quarantine {root}: cannot stat ({type(e).__name__})"
            return out
        out["moves"].append({"original": c["path"], "root": fi.norm(root), "size": c["size"],
                             "mtime": c["mtime"]})
    out["verdict"] = PLANNED
    return out


def _volume_of(root: str) -> str:
    """The nearest existing folder at or above `root` (the root may not exist yet)."""
    d = os.path.abspath(root)
    while not os.path.exists(d):
        up = os.path.dirname(d)
        if up == d:
            break
        d = up
    return d


# --------------------------------------------------------------------------- manifests

def _write_manifest(path: str, man: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=1)
    os.replace(tmp, path)


def _read_manifest(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class Batch:
    """One batch folder per quarantine root, created on the first move into that root."""

    def __init__(self, machine: str, db: str, clock=_now):
        self.machine, self.db, self.clock = machine, db, clock
        t = clock()
        self.id = datetime.fromtimestamp(t, timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3)
        self.created = t
        self.manifests: dict[str, tuple[str, dict]] = {}

    def manifest_for(self, root: str) -> tuple[str, dict]:
        if root not in self.manifests:
            bdir = os.path.join(root, self.id)
            os.makedirs(os.path.join(bdir, "files"), exist_ok=False)
            mpath = os.path.join(bdir, "manifest.json")
            man = {"batch": self.id, "created": _iso(self.created), "created_ts": self.created,
                   "restore_until": _iso(self.created + RESTORE_DAYS * DAY), "machine": self.machine,
                   "db": self.db, "tool": "node/dedupe_apply.py",
                   "restore_command": f'python node/dedupe_apply.py restore --manifest "{fi.norm(mpath)}" --apply',
                   "purge_command": f'python node/dedupe_apply.py purge --root "{fi.norm(root)}" --apply',
                   "note": ("Copies moved here by a recorded Keep-canonical click. Restore with the restore "
                            "command (dry-run without --apply). Purge deletes them only after "
                            f"{RESTORE_DAYS} days and only with --apply."),
                   "entries": []}
            _write_manifest(mpath, man)
            self.manifests[root] = (mpath, man)
        return self.manifests[root]


def _dest(bdir: str, h: str, n: int, original: str) -> str:
    name = re.sub(r'[<>:"|?*\x00-\x1f]', "_", os.path.basename(original)) or "file"
    return os.path.join(bdir, "files", h[:16], f"{n}-{name}")


def apply_group(plan: dict, batch: Batch, mbps: float = 0.0, log=print) -> dict:
    """Move a PLANNED group's copies into quarantine. Re-checks the canonical immediately before and
    after; on an after-check failure every copy moved for this group is put back."""
    res = {**plan, "moved": []}
    if plan["verdict"] != PLANNED:
        return res
    h, canon = plan["hash"], plan["canonical"]
    bad = _check_hash(canon, h, mbps)
    if bad:
        res.update(verdict=REFUSED, why=f"canonical {bad} (checked immediately before the move)")
        return res
    done = []
    for mv in plan["moves"]:
        src = mv["original"]
        bad = _check_hash(src, h, mbps)
        if bad:
            _undo(done)
            res.update(verdict=ROLLED_BACK if done else REFUSED, why=f"copy {src}: {bad} at move time")
            return res
        mpath, man = batch.manifest_for(mv["root"])
        dst = _dest(os.path.dirname(mpath), h, len(man["entries"]), src)
        if os.path.exists(dst):
            _undo(done)
            res.update(verdict=ROLLED_BACK if done else REFUSED, why=f"quarantine slot {dst} already exists")
            return res
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        os.rename(src, dst)
        entry = {"group_hash": h, "original": src, "quarantined": fi.norm(dst), "size": mv["size"],
                 "mtime": mv["mtime"], "moved_at": _iso(batch.clock()), "canonical": canon,
                 "state": "quarantined"}
        man["entries"].append(entry)
        _write_manifest(mpath, man)       # written after every move: a crash leaves a true record
        done.append((src, dst, mpath, man, entry))
        res["moved"].append(entry)
    bad = _check_hash(canon, h, mbps)
    if bad:
        _undo(done)
        res.update(verdict=ROLLED_BACK, why=f"canonical {bad} after the move: every copy was put back",
                   moved=[])
        return res
    res["verdict"] = MOVED
    log(f"moved {len(done)} cop{'y' if len(done) == 1 else 'ies'} of {h[:12]} to quarantine; "
        f"kept {canon}")
    return res


def _undo(done: list) -> None:
    for src, dst, mpath, man, entry in reversed(done):
        if not os.path.exists(src) and os.path.exists(dst):
            os.makedirs(os.path.dirname(src) or ".", exist_ok=True)
            os.rename(dst, src)
            entry["state"] = "restored"
            entry["restored_at"] = _iso(_now())
            entry["note"] = "rolled back in the same run"
            _write_manifest(mpath, man)


def run_apply(db: str, hashes: list[str], machine: str, apply: bool, quarantine: str | None = None,
              mbps: float = 0.0, log=print, clock=_now) -> list[dict]:
    con = fi.connect_ro(db)
    try:
        plans = [plan_group(con, h, machine, quarantine, mbps) for h in hashes]
    finally:
        con.close()
    if not apply:
        return plans
    batch = Batch(machine, db, clock)
    return [apply_group(p, batch, mbps, log) for p in plans]


def keep_canonical_hashes(db: str) -> list[str]:
    con = fi.connect_ro(db)
    try:
        return [r[0] for r in con.execute(
            "SELECT hash FROM decisions WHERE decision='keep_canonical' ORDER BY hash")]
    finally:
        con.close()


# --------------------------------------------------------------------------- restore and purge

def restore(manifest: str, apply: bool, mbps: float = 0.0, clock=_now) -> list[dict]:
    """Put quarantined copies back where they were. Dry-run unless `apply`. Never overwrites a file
    that now sits at the original path; a copy whose content changed in quarantine is not restored."""
    man = _read_manifest(manifest)
    out = []
    for e in man["entries"]:
        if e["state"] != "quarantined":
            continue
        r = {"original": e["original"], "quarantined": e["quarantined"], "verdict": "restore"}
        if os.path.exists(e["original"]):
            r.update(verdict="refused", why="a file already exists at the original path")
        else:
            bad = _check_hash(e["quarantined"], e["group_hash"], mbps)
            if bad:
                r.update(verdict="refused", why=f"quarantined copy {bad}")
        if r["verdict"] == "restore" and apply:
            os.makedirs(os.path.dirname(e["original"]) or ".", exist_ok=True)
            os.rename(e["quarantined"], e["original"])
            e["state"], e["restored_at"] = "restored", _iso(clock())
            _write_manifest(manifest, man)
            r["verdict"] = "restored"
        out.append(r)
    return out


def manifests_under(root: str) -> list[str]:
    if not os.path.isdir(root):
        return []
    found = []
    for b in sorted(os.listdir(root)):
        m = os.path.join(root, b, "manifest.json")
        if os.path.isfile(m):
            found.append(m)
    return found


def purge(root: str, apply: bool, days: int = RESTORE_DAYS, mbps: float = 0.0, clock=_now) -> list[dict]:
    """Delete quarantined copies from batches at least `days` (never under 30) old. Dry-run unless
    `apply`. Before each delete the canonical copy must still exist and hash the same; if it does
    not, the quarantined copy is the one left and it is KEPT."""
    days = max(days, RESTORE_DAYS)
    out = []
    for mpath in manifests_under(root):
        man = _read_manifest(mpath)
        age = clock() - float(man.get("created_ts", clock()))
        if age < days * DAY:
            left = days - int(age // DAY)
            out.append({"batch": man["batch"], "verdict": "too-young",
                        "why": f"{left} day(s) left of the {days}-day restore window"})
            continue
        for e in man["entries"]:
            if e["state"] != "quarantined":
                continue
            r = {"batch": man["batch"], "quarantined": e["quarantined"], "original": e["original"],
                 "verdict": "purge"}
            bad = _check_hash(e["canonical"], e["group_hash"], mbps)
            if bad:
                r.update(verdict="kept", why=f"canonical {bad}: this copy may be the last one")
                if apply:
                    e["state"], e["note"] = "kept", r["why"]
                    _write_manifest(mpath, man)
            elif apply:
                os.remove(e["quarantined"])
                e["state"], e["purged_at"] = "purged", _iso(clock())
                _write_manifest(mpath, man)
                r["verdict"] = "purged"
            out.append(r)
    return out


# --------------------------------------------------------------------------- CLI

def _print_plans(res: list[dict], apply: bool) -> None:
    for r in res:
        v = r["verdict"]
        if v == REFUSED:
            print(f"REFUSED  {r['hash'][:12]}  {r['why']}")
        elif v == ROLLED_BACK:
            print(f"ROLLED-BACK  {r['hash'][:12]}  {r['why']}")
        else:
            verb = "moved" if v == MOVED else "would move"
            print(f"{'MOVED' if v == MOVED else 'PLAN'}  {r['hash'][:12]}  keep {r['canonical']}")
            for m in (r.get("moved") or r["moves"]):
                print(f"    {verb} {m['original']}")
    n = {k: sum(1 for r in res if r["verdict"] == k) for k in (PLANNED, MOVED, REFUSED, ROLLED_BACK)}
    print(f"{len(res)} group(s): {n[PLANNED]} planned, {n[MOVED]} moved, {n[REFUSED]} refused, "
          f"{n[ROLLED_BACK]} rolled back" + ("" if apply else "  (DRY RUN: nothing moved; pass --apply)"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="dedupe_apply", description=__doc__.split("\n")[0])
    ap.add_argument("--db", default=fi.default_db())
    ap.add_argument("--mbps", type=float, default=60.0, help="hash read cap, MB/s (0 = none)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("apply", help="move non-canonical copies of Keep-canonical groups to quarantine")
    a.add_argument("--group", action="append", default=[], help="a group hash (repeatable)")
    a.add_argument("--all-keep-canonical", action="store_true",
                   help="every group whose recorded decision is keep_canonical")
    a.add_argument("--machine", default=socket.gethostname().lower())
    a.add_argument("--quarantine", help="quarantine root (default <drive>:/.cluster-files-quarantine)")
    a.add_argument("--apply", action="store_true", help="really move (default is a dry run)")
    a.add_argument("--json", action="store_true")

    r = sub.add_parser("restore", help="put a batch's quarantined copies back")
    r.add_argument("--manifest", required=True)
    r.add_argument("--apply", action="store_true")

    p = sub.add_parser("purge", help=f"delete quarantined copies older than {RESTORE_DAYS} days")
    p.add_argument("--root", required=True, help="a quarantine root")
    p.add_argument("--days", type=int, default=RESTORE_DAYS, help=f"at least {RESTORE_DAYS}")
    p.add_argument("--apply", action="store_true")

    ls = sub.add_parser("list", help="batches under a quarantine root")
    ls.add_argument("--root", required=True)

    o = ap.parse_args(argv)
    if o.cmd == "apply":
        hashes = list(o.group)
        if o.all_keep_canonical:
            hashes += [h for h in keep_canonical_hashes(o.db) if h not in hashes]
        if not hashes:
            print("nothing to do: pass --group HASH or --all-keep-canonical")
            return 1
        res = run_apply(o.db, hashes, o.machine, o.apply, o.quarantine, o.mbps)
        if o.json:
            print(json.dumps(res, indent=1))
        else:
            _print_plans(res, o.apply)
        return 0 if all(x["verdict"] in (PLANNED, MOVED) for x in res) else 2
    if o.cmd == "restore":
        res = restore(o.manifest, o.apply, o.mbps)
        for x in res:
            print(f"{x['verdict'].upper():9} {x['original']}" + (f"  ({x['why']})" if x.get("why") else ""))
        print(f"{len(res)} entr{'y' if len(res) == 1 else 'ies'}" + ("" if o.apply else "  (DRY RUN; pass --apply)"))
        return 0 if all(x["verdict"] in ("restore", "restored") for x in res) else 2
    if o.cmd == "purge":
        res = purge(o.root, o.apply, o.days, o.mbps)
        for x in res:
            print(f"{x['verdict'].upper():9} {x.get('quarantined') or x['batch']}"
                  + (f"  ({x['why']})" if x.get("why") else ""))
        print(f"{len(res)} item(s)" + ("" if o.apply else "  (DRY RUN: nothing deleted; pass --apply)"))
        return 0
    if o.cmd == "list":
        for m in manifests_under(o.root):
            man = _read_manifest(m)
            states = {}
            for e in man["entries"]:
                states[e["state"]] = states.get(e["state"], 0) + 1
            print(f"{man['batch']}  created {man['created']}  restore until {man['restore_until']}  {states}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
