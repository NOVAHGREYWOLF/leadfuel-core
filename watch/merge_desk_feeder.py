#!/usr/bin/env python3
"""merge_desk_feeder - build the snapshot the Merge desk page shows.

Reads (read-only): `gh` for open and recently merged PRs and CI run durations, and the slot
locks under F:\\Claude Sessions\\.locks for who holds a slot and who waits. Optionally reads the
Conductor desk's exported queue (a directory of JSON files) so queued tasks with no PR yet get
a row. It runs no CI, writes no lock, merges nothing, messages nobody.

It writes ONE local file, snapshot.json. Putting that file into the page's database is the
refresh runner's job (docs/MERGE_DESK_INTENTS.md, "Refresh"). This script never talks to the page.

Honesty rules (the estate's own):
  * A value the inputs cannot establish is None and is shown as 'unknown'. Never a guess.
  * ETA = live queue position x measured CI time. Fewer than MIN_SAMPLES measured runs for a
    repo means that repo's ETA is unknown.
  * A stage that cannot be read from the checks is 'unknown', not 'green'.
  * Only ids, titles, stages and PR numbers are emitted: no PR bodies, no comments.

Usage:
  python watch/merge_desk_feeder.py [--out DIR] [--locks DIR] [--queue-dir DIR] [--owner NAME]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

OWNER_DEFAULT = "NOVAHGREYWOLF"
LOCKS_DEFAULT = r"F:\Claude Sessions\.locks"
TRAIN_STATE_DEFAULT = r"F:\Claude Sessions\merge-train\state.json"
OUT_DEFAULT = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "merge-desk")
MIN_SAMPLES = 3
STALE_AFTER_MIN = 15
STAGES = ("no-pr", "draft", "ci-red", "ci-running", "green-waiting", "in-train", "merged", "unknown")
RED = {"FAILURE", "ERROR", "TIMED_OUT", "STARTUP_FAILURE", "ACTION_REQUIRED"}
RUNNING = {"IN_PROGRESS", "QUEUED", "PENDING", "WAITING", "REQUESTED"}
SESSION_RE = re.compile(r"local_[0-9a-f]{8}(?:-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})?")
ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
COMPACT_RE = re.compile(r"^(\d{8}T\d{6}Z)-(.*)$")
PR_NUM_RE = re.compile(r"(?:\bpr\s?#?|#|\bpr)(\d{1,6})\b", re.I)


# ---------------------------------------------------------------- small pure helpers

def parse_iso(s):
    if not s or s.startswith("0001-01-01"):
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def iso(dt):
    return None if dt is None else dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def median_or_none(values, minimum=1):
    vals = [v for v in values if v is not None]
    return statistics.median(vals) if len(vals) >= minimum else None


def classify(pr_checks, is_draft):
    """Stage from a PR's check rollup. Returns (stage, since_dt, basis).

    Draft wins. No checks at all is 'unknown' (a PR with nothing to read is not green).
    'Skipped' and 'neutral' count as passing; a mix of red and running is red (a verdict exists).
    """
    if is_draft:
        return "draft", None, "PR is a draft"
    if not pr_checks:
        return "unknown", None, "no checks reported on the PR head"
    states = []
    starts, ends = [], []
    for c in pr_checks:
        status = (c.get("status") or c.get("state") or "").upper()
        concl = (c.get("conclusion") or "").upper()
        started = parse_iso(c.get("startedAt"))
        ended = parse_iso(c.get("completedAt"))
        if started:
            starts.append(started)
        if ended:
            ends.append(ended)
        if status in RUNNING or (status == "" and concl == ""):
            states.append("running")
        elif concl in RED or status in RED:
            states.append("red")
        elif concl in ("SUCCESS", "SKIPPED", "NEUTRAL") or status == "SUCCESS":
            states.append("ok")
        elif concl == "CANCELLED":
            states.append("red")
        else:
            states.append("unknown")
    if "red" in states:
        return "ci-red", max(ends) if ends else None, "latest failed check finished"
    if "running" in states:
        return "ci-running", min(starts) if starts else None, "earliest running check started"
    if "unknown" in states:
        return "unknown", None, "a check has a state this feeder does not recognise"
    return "green-waiting", max(ends) if ends else None, "latest check finished"


def ci_minutes_from_runs(runs):
    """Durations (minutes) of completed successful PR/push runs; startedAt to updatedAt."""
    out = []
    for r in runs:
        if (r.get("conclusion") or "").lower() != "success":
            continue
        a, b = parse_iso(r.get("startedAt")), parse_iso(r.get("updatedAt"))
        if a and b and b > a:
            out.append((b - a).total_seconds() / 60.0)
    return out


def eta_for(stage, ci_med, ci_n, elapsed_ci_min, queue_ahead, holder_age_min):
    """Return (minutes_or_None, basis). Never guesses: any missing input gives (None, why)."""
    if stage in ("merged",):
        return 0, "already merged"
    if stage == "draft":
        return None, "unknown: draft, not asking to land yet"
    if stage == "ci-red":
        return None, "unknown: CI is red, needs a fix before it can land"
    if stage == "no-pr":
        return None, "unknown: no PR yet"
    if stage in ("unknown", "in-train"):
        return None, "unknown: stage not readable from the inputs" if stage == "unknown" else "unknown: waiting on the merge train, which reports no times yet"
    if ci_med is None:
        return None, "unknown: fewer than %d measured CI runs for this repo" % MIN_SAMPLES
    basis_ci = "median CI %.0fm over %d runs" % (ci_med, ci_n)
    hold = ci_med  # one slot hold = merge main in, CI on that tree, squash ~ one CI duration
    if stage == "ci-running":
        if elapsed_ci_min is None:
            return None, "unknown: CI start time not reported"
        to_green = max(0.0, ci_med - elapsed_ci_min)
        extra = ""
        if elapsed_ci_min > ci_med:
            extra = " (running longer than the median; this part is a floor)"
        return round(to_green + hold), "CI left %.0fm + one slot hold %.0fm; %s%s" % (to_green, hold, basis_ci, extra)
    if stage == "green-waiting":
        if queue_ahead is None:
            return None, "unknown: this PR has no ticket in the slot queue, so its place is not known"
        holder_left = 0.0
        if holder_age_min is not None:
            holder_left = max(0.0, ci_med - holder_age_min)
        elif holder_age_min is None and queue_ahead is not None and queue_ahead[1]:
            return None, "unknown: slot is held but the hold start time is unreadable"
        n_ahead = queue_ahead[0]
        total = holder_left + (n_ahead + 1) * hold
        return round(total), "%d ahead x %.0fm + own hold %.0fm + holder left %.0fm; %s" % (n_ahead, hold, hold, holder_left, basis_ci)
    return None, "unknown"


def match_pr_number(text):
    nums = {int(m) for m in PR_NUM_RE.findall(text or "")}
    return nums


def desk_from_name(name):
    """Desk token from <ts>-[<ref>-]<DESK>[--<job>] (the ticket format). None when it does not parse."""
    m = COMPACT_RE.match(name)
    if not m:
        return None
    rest = re.sub(r"^[0-9a-f]{6}-", "", m.group(2))
    tok = re.split(r"--|-", rest, maxsplit=1)[0]
    return tok or None


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def read_locks(root):
    """{lock_name: {"holder": {...}|None, "waiters": [ticket,...]}} or None when unreadable.

    Ticket order is oldest first by the compact timestamp in the file name. A KIND:
    merge-on-green ticket is NOT moved ahead here (the releaser may offer it first; that
    shows up as a shorter wait, never a longer one, so the ETA is an upper bound on position).
    """
    if not os.path.isdir(root):
        return None
    locks = {}
    for name in sorted(os.listdir(root)):
        full = os.path.join(root, name)
        if not name.startswith("ci-") or not os.path.isdir(full):
            continue
        if name.endswith(".wait"):
            base = name[:-5]
            entry = locks.setdefault(base, {"holder": None, "waiters": []})
            tickets = []
            for t in sorted(os.listdir(full)):
                text = read_text(os.path.join(full, t)) or ""
                m = COMPACT_RE.match(t)
                tickets.append({
                    "name": t,
                    "ts": iso(datetime.strptime(m.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)) if m else None,
                    "text": text,
                    "sessions": SESSION_RE.findall(text) or [("session " + x) for x in re.findall(r"session(?: ref)?\s+([0-9a-f]{6})", text)],
                    "prs": sorted(match_pr_number(t) | match_pr_number(text)),
                    "kind": (re.search(r"^\s*KIND:\s*(\S+)", text, re.M | re.I) or [None, None])[1],
                    "desk": (re.search(r"^\s*(?:DESK|desk):\s*(.+)$", text, re.M) or [None, None])[1] or desk_from_name(t),
                })
            tickets.sort(key=lambda x: (x["ts"] or "9999", x["name"]))
            entry["waiters"] = tickets
        else:
            entry = locks.setdefault(name, {"holder": None, "waiters": []})
            stamps = [f for f in os.listdir(full) if os.path.isfile(os.path.join(full, f))]
            if stamps:
                text = read_text(os.path.join(full, stamps[0])) or ""
                tsm = ISO_RE.search(text)
                entry["holder"] = {
                    "stamp": stamps[0],
                    "since": tsm.group(0) if tsm else None,
                    "sessions": SESSION_RE.findall(text),
                    "prs": sorted(match_pr_number(text)),
                    "desk": stamps[0].replace("held-by-", "", 1),
                }
            else:
                entry["holder"] = {"stamp": None, "since": None, "sessions": [], "prs": [], "desk": None}
    return locks


# ---------------------------------------------------------------- gh

def gh_json(args):
    try:
        out = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return None


def pacific_midnight_utc(now):
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("America/Los_Angeles")
        local = now.astimezone(tz)
        start = local.replace(hour=0, minute=0, second=0, microsecond=0)
        return start.astimezone(timezone.utc), "America/Los_Angeles"
    except Exception:
        local = now - timedelta(hours=7)  # PDT; the zone database was not available
        start = local.replace(hour=0, minute=0, second=0, microsecond=0)
        return start + timedelta(hours=7), "fixed UTC-7 (zone database unavailable)"


def load_queue(qdir):
    """Conductor desk export: <qdir>/picks/*.json (choice == now) and <qdir>/desks/*.json."""
    if not qdir or not os.path.isdir(qdir):
        return None
    def docs(sub):
        d = os.path.join(qdir, sub)
        out = []
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.endswith(".json"):
                    try:
                        with open(os.path.join(d, f), encoding="utf-8") as fh:
                            out.append(json.load(fh))
                    except (OSError, json.JSONDecodeError):
                        pass
        return out
    picks, desks = docs("picks"), docs("desks")
    tasks = {}
    for dk in desks:
        data = dk.get("data", dk)
        for k, t in (data.get("tasks") or {}).items():
            tasks[(data.get("name"), k)] = t
    queued = []
    for p in picks:
        data = p.get("data", p)
        if data.get("choice") == "now" and not data.get("done"):
            t = tasks.get((data.get("desk"), data.get("tkey")), {})
            queued.append({
                "key": data.get("tkey"), "lane": data.get("desk") or "unknown",
                "title": data.get("title") or t.get("title") or "(title not in export)",
                "id": t.get("id"), "repo": t.get("repo") or "", "rank": data.get("rank"),
                "queued_at": data.get("decided_at"),
            })
    queued.sort(key=lambda x: (x["rank"] if x["rank"] is not None else 1e9))
    return queued


def load_train(path):
    """Optional merge-train state: {"batches":[{"n":1,"prs":["repo#12"],"started":"...Z"}]}. None when absent."""
    text = read_text(path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------- build

def build(owner, locks_root, queue_dir, train_path, prev_state, now):
    errors = []
    open_prs = gh_json(["search", "prs", "--owner", owner, "--state", "open", "--limit", "300",
                        "--json", "repository,number,title,isDraft,createdAt,updatedAt,url"])
    if open_prs is None:
        errors.append("gh search for open PRs failed; rows are not refreshed")
        open_prs = []
    midnight, tzname = pacific_midnight_utc(now)
    merged = gh_json(["search", "prs", "--owner", owner, "--merged", "--merged-at",
                      ">=" + (now - timedelta(days=7)).strftime("%Y-%m-%d"), "--limit", "300",
                      "--json", "repository,number,title,createdAt,closedAt,url"])
    if merged is None:
        errors.append("gh search for merged PRs failed; landed-today and time-to-land are unknown")
    locks = read_locks(locks_root)
    if locks is None:
        errors.append("slot locks unreadable; slot positions are unknown")
    train = load_train(train_path)
    queue = load_queue(queue_dir)
    if queue is None:
        errors.append("no Conductor desk queue export; rows for tasks without a PR are not included")

    repos = sorted({p["repository"]["name"] for p in open_prs})
    ci = {}
    for repo in repos:
        runs = gh_json(["run", "list", "-R", "%s/%s" % (owner, repo), "--limit", "40", "--status", "success",
                        "--json", "conclusion,startedAt,updatedAt,event"]) or []
        runs = [r for r in runs if r.get("event") in ("pull_request", "push")]
        mins = ci_minutes_from_runs(runs)
        ci[repo] = {"median_min": median_or_none(mins, MIN_SAMPLES), "n": len(mins)}

    prev_rows = (prev_state or {}).get("rows", {})
    train_index = {}  # "repo#n" -> batch id, only for PRs the train reports as in-train
    if train:
        default_batch = (train.get("batch") or {}).get("id")
        for ref, st in (train.get("prs") or {}).items():
            if st.get("stage") == "in-train":
                train_index[ref] = st.get("batch", default_batch)

    def fetch(p):
        return gh_json(["pr", "view", str(p["number"]), "-R", "%s/%s" % (owner, p["repository"]["name"]),
                        "--json", "headRefName,isDraft,statusCheckRollup,mergeStateStatus"])
    with ThreadPoolExecutor(max_workers=8) as pool:
        details = list(pool.map(fetch, open_prs))

    rows = []
    for p, detail in zip(open_prs, details):
        repo, num = p["repository"]["name"], p["number"]
        rid = "%s~pr%d" % (repo, num)
        if detail is None:
            stage, since, sbasis = "unknown", None, "gh pr view failed"
            head, checks = "", []
        else:
            head, checks = detail.get("headRefName", ""), detail.get("statusCheckRollup") or []
            stage, since, sbasis = classify(checks, detail.get("isDraft", p.get("isDraft")))
        ref = "%s#%d" % (repo, num)
        batch = train_index.get(ref)
        if batch is not None and stage not in ("merged",):
            stage, sbasis = "in-train", "listed in merge-train state"
        if stage == "draft":
            since, sbasis = parse_iso(p.get("createdAt")), "PR opened (draft may have been created later)"
        # holder / lane / queue position from the slot locks
        holder, hbasis, lane = "unknown", "no slot ticket or lock stamp names this PR", "unassigned"
        queue_ahead, holder_age = None, None
        lock = (locks or {}).get("ci-" + repo)
        if lock:
            for i, t in enumerate(lock["waiters"]):
                if num in t["prs"]:
                    holder = t["sessions"][0] if t["sessions"] else "unknown"
                    hbasis = "slot ticket %s" % t["name"] if t["sessions"] else "slot ticket %s names no session id" % t["name"]
                    lane = (t["desk"] or "").split(" ")[0] or lane
                    queue_ahead = (i, lock["holder"] is not None)
                    break
            h = lock["holder"]
            if h and num in h["prs"]:
                holder = h["sessions"][0] if h["sessions"] else "unknown"
                hbasis = "holds slot ci-%s" % repo
                queue_ahead = (-1, False)
            if queue_ahead is not None and lock["holder"] is not None:
                hs = parse_iso(lock["holder"]["since"])
                holder_age = (now - hs).total_seconds() / 60.0 if hs else None
        elapsed_ci = (now - since).total_seconds() / 60.0 if (since and stage == "ci-running") else None
        if queue_ahead == (-1, False):
            eta_min, eta_basis = None, "unknown: this PR is holding the slot now; time to squash is not measured"
        else:
            eta_min, eta_basis = eta_for(stage, ci.get(repo, {}).get("median_min"), ci.get(repo, {}).get("n", 0),
                                         elapsed_ci, queue_ahead, holder_age)
        # time in stage: gh when it can say, else carry the previous first-seen time
        prev = prev_rows.get(rid)
        if since is None:
            if prev and prev.get("stage") == stage and prev.get("since"):
                since, sbasis = parse_iso(prev["since"]), "first seen in this stage by the feeder"
            else:
                since, sbasis = now, "first seen in this stage by the feeder (true start unknown)"
        rows.append({
            "id": rid, "kind": "pr", "repo": repo, "number": num, "title": p.get("title", ""), "url": p.get("url"),
            "lane": lane, "stage": stage, "since": iso(since), "since_basis": sbasis,
            "holder": holder, "holder_basis": hbasis,
            "slot": ({"lock": "ci-" + repo, "ahead": queue_ahead[0] if queue_ahead and queue_ahead[0] >= 0 else None,
                      "held_by": (lock["holder"] or {}).get("desk")} if lock and queue_ahead is not None else None),
            "batch": batch, "eta_min": eta_min, "eta_basis": eta_basis,
            "branch": head,
        })

    # queued desk tasks with no PR yet
    pr_text = [(r["repo"], (r["title"] + " " + r.get("branch", "")).lower()) for r in rows]
    for q in queue or []:
        key = (q["key"] or "").lower()
        if key and any(key in t for _, t in pr_text):
            continue
        rid = "task~%s" % re.sub(r"[^A-Za-z0-9_.-]", "-", (q["key"] or q["title"])[:150])
        prev = prev_rows.get(rid)
        since = parse_iso(q.get("queued_at"))
        sbasis = "queued on the Conductor desk"
        if since is None:
            since = parse_iso(prev["since"]) if prev and prev.get("since") else now
            sbasis = "first seen queued by the feeder"
        rows.append({
            "id": rid, "kind": "task", "repo": q["repo"] if re.fullmatch(r"[A-Za-z0-9_.-]{1,60}", q["repo"] or "") else "(repo not named)", "number": None, "title": q["title"],
            "url": None, "lane": q["lane"], "stage": "no-pr", "since": iso(since), "since_basis": sbasis,
            "holder": "unknown", "holder_basis": "Conductor export names the lane, not a session",
            "slot": None, "batch": None, "eta_min": None, "eta_basis": "unknown: no PR yet", "branch": "",
        })

    landed_today, ttl = [], []
    for m in merged or []:
        c, d = parse_iso(m.get("createdAt")), parse_iso(m.get("closedAt"))
        if not (c and d):
            continue
        ttl.append((d - c).total_seconds() / 60.0)
        if d >= midnight:
            landed_today.append({
                "id": "%s~pr%d" % (m["repository"]["name"], m["number"]), "kind": "merged",
                "repo": m["repository"]["name"], "number": m["number"], "title": m.get("title", ""),
                "url": m.get("url"), "lane": "landed", "stage": "merged", "since": iso(d),
                "since_basis": "merged", "holder": "n/a", "holder_basis": "", "slot": None, "batch": None,
                "eta_min": 0, "eta_basis": "already merged", "branch": "",
            })
    rows.extend(landed_today)

    return {
        "schema": 1,
        "refreshed_at": iso(now),
        "stale_after_min": STALE_AFTER_MIN,
        "errors": errors,
        "ci": ci,
        "locks_readable": locks is not None,
        "train_present": train is not None,
        "summary": {
            "open_prs": sum(1 for r in rows if r["kind"] == "pr"),
            "green_waiting": sum(1 for r in rows if r["stage"] == "green-waiting"),
            "in_train": sum(1 for r in rows if r["stage"] == "in-train"),
            "landed_today": len(landed_today) if merged is not None else None,
            "median_minutes_to_land_7d": round(statistics.median(ttl), 1) if len(ttl) >= MIN_SAMPLES else None,
            "landed_7d": len(ttl) if merged is not None else None,
            "day_boundary": tzname,
        },
        "rows": rows,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--locks", default=LOCKS_DEFAULT)
    ap.add_argument("--queue-dir", default=None)
    ap.add_argument("--train", default=TRAIN_STATE_DEFAULT)
    ap.add_argument("--owner", default=OWNER_DEFAULT)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    state_path = os.path.join(a.out, "state.json")
    prev = None
    txt = read_text(state_path)
    if txt:
        try:
            prev = json.loads(txt)
        except json.JSONDecodeError:
            prev = None
    now = datetime.now(timezone.utc).replace(microsecond=0)
    snap = build(a.owner, a.locks, a.queue_dir, a.train, prev, now)
    with open(os.path.join(a.out, "snapshot.json"), "w", encoding="utf-8") as fh:
        json.dump(snap, fh, indent=1)
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump({"rows": {r["id"]: {"stage": r["stage"], "since": r["since"]} for r in snap["rows"]}}, fh)
    print("merge-desk snapshot: %d rows, %d errors, written %s" % (len(snap["rows"]), len(snap["errors"]), snap["refreshed_at"]))
    for e in snap["errors"]:
        print("  note:", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
