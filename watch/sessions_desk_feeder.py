#!/usr/bin/env python3
"""sessions_desk_feeder - build the snapshot the Sessions desk page shows.

Session data is reachable only through the desktop app's session tools, so a Claude session (the
keeper) collects it and hands it here as files. This script does the rest, read-only:

  * `gh pr view` for the PR each session carries (state, draft, checks, merged time),
  * the slot locks under F:\\Claude Sessions\\.locks (who holds a slot, who waits for one),
  * `git` in each session's own worktree for unpushed work (local remote-tracking refs, no fetch).

It writes snapshot.json (one row per session) and to_read.json (the sessions whose state changed
since the previous snapshot, so the keeper reads only those transcripts). It runs no CI, writes no
lock, archives nothing, messages nobody and never talks to the page.

Honesty rules (the estate's own):
  * A value the inputs cannot establish is None and is shown as 'unknown'. Never a guess.
  * Percent toward done is computed only from evidence; one unknown milestone makes it unknown.
  * The keep / rotate / archive verdict applies the Conductor desk's EXISTING archive gate
    (collection 'archive', doc 'gate'). It is not a second gate. 'archive' means listed for
    archiving; nothing here archives.
  * Only ids, titles, stages, PR numbers and one status line per session are emitted.

Inputs (all JSON):
  --sessions FILE   list_sessions output: an array of session objects (required)
  --usage FILE      {sessionId: {"tokens": int|null, "model": str|null}} from get_usage/get_session
  --evidence FILE   {sessionId: {"status_line", "handoff", "read_at"}} from transcript reads
  --prev FILE       the previous snapshot (the page's snapshot/current doc, data or full doc)
  --gate FILE       the Conductor desk archive/gate doc (rules are copied onto the page)

Usage:
  python watch/sessions_desk_feeder.py --sessions s.json [--usage u.json] [--evidence e.json]
      [--prev prev.json] [--gate gate.json] [--locks DIR] [--out DIR] [--no-gh] [--no-git]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from merge_desk_feeder import classify  # noqa: E402  (one check-rollup reading for both pages)

LOCKS_DEFAULT = r"F:\Claude Sessions\.locks"
OUT_DEFAULT = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "sessions-desk")
REPOS_ROOT = r"F:\Leadfuel\repos"
STALE_AFTER_MIN = 45          # the page says 'stale' past this
IDLE_STALE_MIN = 120          # a stopped session with nothing pending is idle-stale after this
NEEDED_STOPPED_MIN = 60       # a stopped desk with open work is flagged after this
QUIET_RUNNING_MIN = 180       # reported running but silent this long: possibly hung
CAP_DEFAULT, CAP_HAIKU = 300_000, 120_000
STAGES = ("working", "waiting-owner", "waiting-ci", "pr-open", "done", "idle-stale")
STATUS_RE = re.compile(r"\bSTATUS:\s*(DONE|BLOCKED|NEEDS-NOVAH|CONTINUING)\b")
ASK_RE = re.compile(r"^\s*ASK:", re.M)
DESK_TITLE_RE = re.compile(r"^([A-Z][A-Z0-9_-]*)\s+·\s+(\S+)\s+(\d+)/(\d+)(?:\s+·|\s*$)")
ROUTER_RE = re.compile(r"^ROUTER\s*#\s*(\d+)", re.I)
CONDUCTOR_NUM_RE = re.compile(r"\b(\d{3})\b")
SESSION_RE = re.compile(r"local_([0-9a-f]{8})")
GH_REMOTE_RE = re.compile(r"github\.com[:/]([^/]+/[^/.\s]+?)(?:\.git)?\s*$")
MILESTONES = ("pr_open", "checks_green", "merged", "final_report", "nothing_unpushed")


# ---------------------------------------------------------------- small pure helpers

def parse_ts(s):
    """ISO time with or without millis -> aware datetime, or None."""
    if not s:
        return None
    s = str(s).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def iso(dt):
    return None if dt is None else dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def short(sid):
    m = SESSION_RE.search(sid or "")
    return m.group(1) if m else (sid or "")[:8]


def role_of(title):
    t = (title or "").strip()
    if t.upper().startswith("CONDUCTOR"):
        return "conductor"
    if t.upper().startswith("ROUTER"):
        return "router"
    if " · " in t:
        return "desk"
    return "unfiled"


def parse_title(title):
    """(lane, task_id, n, m) for a desk title `LANE · TASK n/m · topic`, else lane only."""
    t = (title or "").strip()
    m = DESK_TITLE_RE.match(t)
    if m:
        return m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
    lane = t.split(" · ", 1)[0].strip() if " · " in t else None
    return lane, None, None, None


def incarnation(title, role):
    if role == "router":
        m = ROUTER_RE.match(title or "")
        return int(m.group(1)) if m else None
    if role == "conductor":
        m = CONDUCTOR_NUM_RE.search(title or "")
        return int(m.group(1)) if m else None
    return None


def cap_for(model):
    return CAP_HAIKU if model and "haiku" in model.lower() else CAP_DEFAULT


def status_from_line(line):
    """'DONE' | 'BLOCKED' | 'NEEDS-NOVAH' | 'CONTINUING' | 'ASK' | None."""
    if not line:
        return None
    m = STATUS_RE.search(line)
    if m:
        return m.group(1)
    if ASK_RE.search(line):
        return "ASK"
    return None


def repo_root_for(cwd):
    """F:\\Leadfuel\\repos\\<name>\\... -> F:\\Leadfuel\\repos\\<name>; else cwd itself."""
    if not cwd:
        return None
    norm = cwd.replace("/", "\\")
    root = REPOS_ROOT.lower() + "\\"
    if norm.lower().startswith(root):
        name = norm[len(root):].split("\\", 1)[0]
        return REPOS_ROOT + "\\" + name
    return norm


# ---------------------------------------------------------------- slot locks

def read_tickets(root):
    """[(kind, lock, file_name, text)] for every slot ticket; None when the folder is unreadable.

    kind is 'holds' (a held lock or a running full-suite entry) or 'waits' (a .wait queue entry).
    """
    if not root or not os.path.isdir(root):
        return None
    out = []
    for name in sorted(os.listdir(root)):
        full = os.path.join(root, name)
        if not os.path.isdir(full):
            continue
        kind = "waits" if name.endswith(".wait") else ("holds" if "." not in name or name.endswith(".running") else None)
        if kind is None:
            continue
        lock = name.split(".", 1)[0]
        for f in sorted(os.listdir(full)):
            try:
                with open(os.path.join(full, f), encoding="utf-8", errors="replace") as fh:
                    text = fh.read(4000)
            except OSError:
                continue
            out.append((kind, lock, f, text))
    return out


def ticket_matches(row, ticket):
    """True when a ticket is this session's own.

    Tickets share no single format. A ticket is the session's when its file name or text carries
    the session's `LANE-TASK` / `LANE · TASK n/m`, or when the session's id sits on a line that is
    not about a router or an offer (tickets also name the router and whoever offered the slot).
    """
    _, _, fname, text = ticket
    if row.get("task") and row.get("lane"):
        tok = ("%s-%s" % (row["lane"], row["task"])).upper()
        if tok in fname.upper() or tok in text.upper():
            return True
        if ("%s · %s %s/%s" % (row["lane"], row["task"], row["n"], row["m"])) in text:
            return True
    sid = row.get("short")
    if sid:
        for line in text.splitlines():
            if ("local_" + sid) in line and not re.search(r"router|offer", line, re.I):
                return True
    return False


def slot_for(row, tickets):
    hit = None
    for tk in tickets or []:
        if ticket_matches(row, tk):
            if tk[0] == "holds":
                return {"kind": "holds", "lock": tk[1]}
            hit = hit or {"kind": "waits", "lock": tk[1]}
    return hit


# ---------------------------------------------------------------- gh and git (read-only)

def _run(args, cwd=None, timeout=30):
    try:
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout if p.returncode == 0 else None


def gh_repo_for(cwd, cache):
    root = repo_root_for(cwd)
    if root is None:
        return None
    if root not in cache:
        out = _run(["git", "-C", root, "remote", "get-url", "origin"]) if os.path.isdir(root) else None
        m = GH_REMOTE_RE.search(out or "")
        cache[root] = m.group(1) if m else None
    return cache[root]


def gh_pr(repo, number):
    out = _run(["gh", "pr", "view", str(number), "--repo", repo, "--json",
                "state,isDraft,mergedAt,statusCheckRollup,url"], timeout=60)
    if not out:
        return None
    try:
        return json.loads(out)
    except ValueError:
        return None


def unpushed(cwd):
    """(count_or_None, basis). Commits on HEAD that no remote-tracking ref has, plus a dirty tree.

    Uses local refs only (no fetch, no network). A missing worktree is unknown, not clean.
    """
    if not cwd or not os.path.isdir(cwd):
        return None, "worktree not on disk"
    remotes = _run(["git", "-C", cwd, "remote"])
    if remotes is None:
        return None, "not a git checkout"
    if not remotes.strip():
        return None, "repo has no remote, so pushed cannot be judged"
    n = _run(["git", "-C", cwd, "rev-list", "--count", "HEAD", "--not", "--remotes"])
    dirty = _run(["git", "-C", cwd, "status", "--porcelain", "--untracked-files=no"])
    if n is None or dirty is None:
        return None, "git could not read the worktree"
    count = int(n.strip() or 0)
    if dirty.strip():
        return count + 1, "%d commit(s) on no remote ref, and uncommitted changes (local refs, no fetch)" % count
    return count, "%d commit(s) on no remote ref (local refs, no fetch)" % count


# ---------------------------------------------------------------- per-session reasoning

def pr_facts(pr):
    """{'state','draft','checks','merged_at','url'} from a gh pr view result; None stays None."""
    if not pr:
        return None
    state = (pr.get("state") or "").upper() or None
    draft = bool(pr.get("isDraft"))
    checks = None
    if state == "OPEN":
        stage, _, _ = classify(pr.get("statusCheckRollup") or [], False)
        checks = {"green-waiting": "green", "ci-red": "red", "ci-running": "running"}.get(stage, "unknown")
    elif state == "MERGED":
        checks = "green"
    return {"state": state, "draft": draft, "checks": checks, "merged_at": pr.get("mergedAt"), "url": pr.get("url")}


def gate_cells(row):
    """The Conductor desk archive gate's five cells, same names and values: yes / no / unknown.

    merged: PR really merged per gh (the app badge alone is 'badge', not yes).
    report: last report line is STATUS: DONE (or a final report).
    handoff: a handoff was seen in the transcript.
    pushed: nothing unpushed in the session's worktree.
    decision: 'no' means no owner decision pending; 'yes' means one is.
    """
    pr = row.get("pr") or {}
    if pr.get("state") == "MERGED":
        merged = "yes"
    elif pr.get("state") in ("OPEN", "CLOSED"):
        merged = "no"
    elif row.get("pr_badge") == "merged":
        merged = "badge"
    elif row.get("pr_number") is None:
        merged = "none"
    else:
        merged = "unknown"
    st = row.get("last_status")
    report = "yes" if st == "DONE" else ("no" if st in ("CONTINUING", "BLOCKED", "NEEDS-NOVAH", "ASK") else "unknown")
    h = row.get("handoff")
    handoff = "yes" if h is True else ("no" if h is False else "unknown")
    u = row.get("unpushed")
    pushed = "unknown" if u is None else ("yes" if u == 0 else "no")
    decision = "yes" if st in ("NEEDS-NOVAH", "ASK") else ("no" if st in ("DONE", "CONTINUING") else "unknown")
    return {"merged": merged, "report": report, "handoff": handoff, "pushed": pushed, "decision": decision}


def stage_of(row, now):
    """One of STAGES, with the basis that decided it."""
    st = row.get("last_status")
    pr = row.get("pr") or {}
    if st == "DONE" and not row["running"]:
        return "done", "last report says STATUS: DONE"
    if row.get("slot") and row["slot"]["kind"] == "holds":
        return "working", "holds the %s slot" % row["slot"]["lock"]
    if row.get("slot") and row["slot"]["kind"] == "waits" and not row["running"] and st not in ("NEEDS-NOVAH", "ASK", "BLOCKED"):
        return "waiting-ci", "has a ticket in %s.wait" % row["slot"]["lock"]
    if pr.get("state") == "MERGED" and not row["running"] and st not in ("NEEDS-NOVAH", "ASK", "BLOCKED"):
        return "done", "its PR is merged (gh) and the session is stopped"
    if row["running"]:
        return "working", "the app reports it running"
    if st in ("NEEDS-NOVAH", "ASK", "BLOCKED"):
        return "waiting-owner", "last report says %s" % st
    if pr.get("state") == "OPEN" or (row.get("pr_badge") == "open" and not pr):
        return "pr-open", "its PR is open" + ("" if pr else " (app badge)")
    age = row.get("idle_min")
    return "idle-stale", "stopped%s, nothing pending it is waiting on" % ("" if age is None else " %d min ago" % age)


def milestones(row):
    pr = row.get("pr") or {}
    g = row["gate"]
    out = {}
    if row.get("pr_number") is None:
        out["pr_open"] = "no" if row["role"] == "desk" else "n/a"
    else:
        out["pr_open"] = "yes" if pr.get("state") else "unknown"
    out["checks_green"] = {"green": "yes", "red": "no", "running": "no"}.get(pr.get("checks"), "unknown") if pr else ("no" if out["pr_open"] == "no" else "unknown")
    out["merged"] = {"yes": "yes", "no": "no", "none": "no"}.get(g["merged"], "unknown")
    out["final_report"] = {"yes": "yes", "no": "no"}.get(g["report"], "unknown")
    out["nothing_unpushed"] = {"yes": "yes", "no": "no"}.get(g["pushed"], "unknown")
    return out


def percent_of(row):
    """Evidence-only progress toward the task's definition of done; None when not computable."""
    if row["role"] != "desk" or not row.get("task"):
        return None, "no task with a definition of done"
    ms = row["milestones"]
    if ms["merged"] == "yes" and ms["final_report"] == "yes":
        return 100, "PR merged (gh) and STATUS: DONE reported"
    unknown = [k for k in MILESTONES if ms.get(k) == "unknown"]
    if unknown:
        return None, "not computable: %s unknown" % ", ".join(unknown)
    done = sum(1 for k in MILESTONES if ms.get(k) == "yes")
    return round(100 * done / len(MILESTONES)), "%d of %d milestones met" % (done, len(MILESTONES))


def verdict_of(row, has_successor):
    """keep / rotate / archive, applying the Conductor desk archive gate rules."""
    g = row["gate"]
    size, cap = row.get("tokens"), row.get("cap")
    if size is not None and cap and size >= cap and not has_successor:
        return "rotate", "past the %dk handoff cap with no successor" % (cap // 1000)
    gate_ok = (g["merged"] in ("yes", "none") and g["report"] == "yes" and g["handoff"] in ("yes",)
               and g["pushed"] == "yes" and g["decision"] == "no")
    if row["role"] in ("router", "conductor"):
        if has_successor and g["handoff"] == "yes" and g["pushed"] == "yes" and not row["running"]:
            return "archive", "successor is live and the handoff is pushed (gate rule 2)"
        return "keep", "a %s archives only after its successor is live (gate rule 2)" % row["role"]
    if gate_ok and not row["running"]:
        return "archive", "all five gate cells pass; listed for archiving, not archived"
    missing = [k for k, v in g.items() if not ((k == "merged" and v in ("yes", "none")) or (k == "decision" and v == "no") or (k not in ("merged", "decision") and v == "yes"))]
    return "keep", "gate not met: " + ", ".join(missing)


# ---------------------------------------------------------------- build

def build(sessions, usage=None, evidence=None, prev=None, gate=None, tickets=None,
          pr_lookup=None, unpushed_lookup=None, now=None):
    """Pure core. pr_lookup(session) -> gh pr json or None; unpushed_lookup(session) -> (n, basis)."""
    now = now or datetime.now(timezone.utc)
    usage = usage or {}
    evidence = evidence or {}
    prev_rows = {r["id"]: r for r in ((prev or {}).get("rows") or [])}
    rows = []
    for s in sessions:
        if s.get("isArchived"):
            continue
        sid = s.get("sessionId")
        title = s.get("title") or ""
        role = role_of(title)
        lane, task, n, m = parse_title(title)
        group = (s.get("group") or {}).get("name") if s.get("group") else None
        last = parse_ts(s.get("lastActivityAt"))
        p = prev_rows.get(sid, {})
        u = usage.get(sid) or {}
        ev = evidence.get(sid) or {}
        tokens = u.get("tokens") if u.get("tokens") is not None else p.get("tokens")
        size_at = iso(now) if u.get("tokens") is not None else p.get("size_at")
        model = u.get("model") or p.get("model")
        line = ev.get("status_line") if "status_line" in ev else p.get("status_line")
        handoff = ev.get("handoff") if "handoff" in ev else p.get("handoff")
        read_at = ev.get("read_at") or p.get("read_at")
        row = {
            "id": sid, "short": short(sid), "title": title, "group": group or "(ungrouped)",
            "role": role, "lane": lane, "task": task, "n": n, "m": m,
            "running": bool(s.get("isRunning")), "last": iso(last),
            "idle_min": None if (last is None or s.get("isRunning")) else int((now - last).total_seconds() // 60),
            "pr_number": s.get("prNumber"), "pr_badge": (s.get("prState") or "").lower() or None,
            "tokens": tokens, "size_at": size_at, "model": model, "cap": cap_for(model),
            "status_line": (line or "")[:200] or None, "last_status": status_from_line(line),
            "handoff": handoff, "read_at": read_at,
            "branch": s.get("branch"),
        }
        pr = None
        if row["pr_number"] is not None:
            same_pr = p.get("pr_number") == row["pr_number"]
            if same_pr and (p.get("pr") or {}).get("state") == "MERGED":
                pr = p["pr"]  # merged is final: no need to ask gh again
            elif pr_lookup:
                pr = pr_facts(pr_lookup(s))
            if pr is None and same_pr:
                pr = p.get("pr")
        row["pr"] = pr
        row["slot"] = slot_for(row, tickets)
        if unpushed_lookup:
            row["unpushed"], row["unpushed_basis"] = unpushed_lookup(s)
        else:
            row["unpushed"], row["unpushed_basis"] = p.get("unpushed"), p.get("unpushed_basis") or "not read this tick"
        row["gate"] = gate_cells(row)
        row["stage"], row["stage_basis"] = stage_of(row, now)
        row["milestones"] = milestones(row)
        row["percent"], row["percent_basis"] = percent_of(row)
        row["changed"] = (not p) or any(p.get(k) != row.get(k) for k in ("running", "last", "pr_badge", "pr_number", "title"))
        rows.append(row)

    # successors and duplicates need the whole set
    by_task = {}
    for r in rows:
        if r["task"]:
            by_task.setdefault(r["task"], []).append(r)
    max_router = max([incarnation(r["title"], "router") or 0 for r in rows if r["role"] == "router"] or [0])
    max_cond = max([incarnation(r["title"], "conductor") or 0 for r in rows if r["role"] == "conductor"] or [0])
    for r in rows:
        if r["role"] == "router":
            k = incarnation(r["title"], "router")
            succ = k is not None and k < max_router
        elif r["role"] == "conductor":
            k = incarnation(r["title"], "conductor")
            succ = k is not None and k < max_cond
        elif r["task"]:
            succ = any((o["n"] or 0) > (r["n"] or 0) for o in by_task[r["task"]] if o is not r)
        else:
            succ = False
        r["has_successor"] = succ
        r["verdict"], r["verdict_basis"] = verdict_of(r, succ)
        r["flags"] = []

    for task, group_rows in by_task.items():
        live = [r for r in group_rows if r["stage"] != "done"]
        seen = {}
        for r in live:
            seen.setdefault(r["n"], []).append(r)
        for n, same in seen.items():
            if len(same) > 1:
                for r in same:
                    r["flags"].append("duplicate")
        if sum(1 for r in live if r["running"]) > 1:
            for r in live:
                if r["running"] and "duplicate" not in r["flags"]:
                    r["flags"].append("duplicate")

    for r in rows:
        if r["role"] == "desk" and not r["task"] and r["stage"] != "done":
            r["flags"].append("orphan")
        if (r["role"] == "desk" and r["task"] and not r["running"] and r["stage"] in ("idle-stale", "pr-open")
                and not r["has_successor"] and (r["idle_min"] or 0) >= NEEDED_STOPPED_MIN):
            r["flags"].append("needed-stopped")
        if r["running"] and r["last"] and (now - parse_ts(r["last"])).total_seconds() >= QUIET_RUNNING_MIN * 60:
            r["flags"].append("quiet-running")
        if r["verdict"] == "rotate":
            r["flags"].append("past-cap")
        if r["verdict"] == "archive":
            r["flags"].append("archivable")

    order = {s: i for i, s in enumerate(STAGES)}
    rows.sort(key=lambda r: (r["group"], order.get(r["stage"], 9), r["title"]))
    summary = {s: sum(1 for r in rows if r["stage"] == s) for s in STAGES}
    summary["sessions"] = len(rows)
    flags = {f: [r["short"] for r in rows if f in r["flags"]]
             for f in ("needed-stopped", "quiet-running", "past-cap", "archivable", "orphan", "duplicate")}
    snap = {
        "refreshed_at": iso(now), "stale_after_min": STALE_AFTER_MIN, "summary": summary, "flags": flags,
        "gate_source": "Conductor desk (MKAx49RAskZ3cV7f2EkDMF) collection archive, doc gate",
        "gate_rules": (gate or {}).get("rules") or [],
        "caps": {"default": CAP_DEFAULT, "haiku": CAP_HAIKU},
        "rows": [{k: v for k, v in r.items() if k not in ("changed",)} for r in rows],
    }
    to_read = [r["id"] for r in rows if r["changed"] or r["read_at"] is None]
    return snap, to_read


def digest(snap, prev_flags=None):
    """Short text for the conductor's feed: counts, then flags with what is new since last tick."""
    sm, fl = snap["summary"], snap["flags"]
    prev_flags = prev_flags or {}
    title = {r["short"]: r["title"][:70] for r in snap["rows"]}
    lines = ["%d sessions: %s." % (sm["sessions"], ", ".join("%d %s" % (sm[s], s) for s in STAGES if sm.get(s)))]
    new = {}
    for f, ids in fl.items():
        if not ids:
            continue
        fresh = [i for i in ids if i not in set(prev_flags.get(f) or [])]
        new[f] = fresh
        shown = "; ".join("%s %s" % (i, title.get(i, "")) for i in ids[:6])
        more = " (+%d more)" % (len(ids) - 6) if len(ids) > 6 else ""
        lines.append("%s %d%s: %s%s" % (f, len(ids), (", %d new" % len(fresh)) if fresh else "", shown, more))
    return "\n".join(lines), new


def _load(path):
    if not path:
        return None
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    # an ArtifactData get result keeps the document under "data"
    if isinstance(d, dict) and "data" in d and isinstance(d["data"], dict) and "rows" not in d:
        d = d["data"]
    return d


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sessions", required=True)
    ap.add_argument("--usage")
    ap.add_argument("--evidence")
    ap.add_argument("--prev")
    ap.add_argument("--gate")
    ap.add_argument("--locks", default=LOCKS_DEFAULT)
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--no-gh", action="store_true")
    ap.add_argument("--no-git", action="store_true")
    a = ap.parse_args(argv)

    sessions = _load(a.sessions)
    if isinstance(sessions, dict):
        sessions = sessions.get("sessions") or []
    prev = _load(a.prev)
    repo_cache = {}

    def lookup_pr(s):
        repo = gh_repo_for(s.get("cwd"), repo_cache)
        return gh_pr(repo, s["prNumber"]) if repo else None

    live = [s for s in sessions if not s.get("isArchived")]
    prs, unp = {}, {}
    prev_rows = {r["id"]: r for r in ((prev or {}).get("rows") or [])}
    with ThreadPoolExecutor(max_workers=8) as ex:
        if not a.no_gh:
            need = [s for s in live if s.get("prNumber") is not None and not (
                prev_rows.get(s["sessionId"], {}).get("pr_number") == s["prNumber"]
                and (prev_rows.get(s["sessionId"], {}).get("pr") or {}).get("state") == "MERGED")]
            for s, r in zip(need, ex.map(lookup_pr, need)):
                prs[s["sessionId"]] = r
        if not a.no_git:
            for s, r in zip(live, ex.map(lambda s: unpushed(s.get("cwd")), live)):
                unp[s["sessionId"]] = r

    snap, to_read = build(
        sessions, usage=_load(a.usage), evidence=_load(a.evidence), prev=prev, gate=_load(a.gate),
        tickets=read_tickets(a.locks),
        pr_lookup=None if a.no_gh else (lambda s: prs.get(s["sessionId"])),
        unpushed_lookup=None if a.no_git else (lambda s: unp.get(s["sessionId"], (None, "not read"))),
    )
    text, new = digest(snap, (prev or {}).get("flags"))
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "snapshot.json"), "w", encoding="utf-8") as fh:
        json.dump(snap, fh, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(a.out, "to_read.json"), "w", encoding="utf-8") as fh:
        json.dump(to_read, fh)
    with open(os.path.join(a.out, "digest.json"), "w", encoding="utf-8") as fh:
        json.dump({"at": snap["refreshed_at"], "text": text, "new_flags": new, "summary": snap["summary"]}, fh, ensure_ascii=False)
    print(text)
    print("to_read: %d  out: %s" % (len(to_read), a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
