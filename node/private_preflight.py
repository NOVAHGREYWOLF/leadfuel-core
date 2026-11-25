"""NODE redline-1: read-only preflight for making leadfuel-core private (owner card q482 B).

What it does: asks GitHub (GET requests only, through `gh api`) and reads this checkout's
workflow files, then prints ONE report: what going private breaks, the two HIGH branches, whether
the Lava Cap files already exist in the private clients repo, and which self-hosted runners are
registered on a repo that is still public.

What it never does: change visibility, delete a branch, unregister a runner, push, send, or print
a file's content. Visibility is the owner's click in GitHub settings; branch deletion is
irreversible and lives in node/delete_high_branches.py behind a flag.

Rules (a check that cannot establish a state must not report one):
  * Every probe returns ok, or unknown with the reason. A failed or empty `gh` call is `unknown`,
    never "none found" and never a pass.
  * Positive control: the workflow parser is first run on a built-in sample whose answer is
    known; if it comes out wrong the workflow section is `unknown`.
  * Names and counts only. Nothing here reads blob content.

Usage:  python node/private_preflight.py [--repo OWNER/NAME] [--clients OWNER/NAME]
                                         [--workflows DIR] [--json] [--write PATH]
Flags default to the values for leadfuel-core. Nothing is written unless --write is given.
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys

SCHEMA = "node.private_preflight/1"
DEFAULT_REPO = "NOVAHGREYWOLF/leadfuel-core"
DEFAULT_CLIENTS = "NOVAHGREYWOLF/clients"
# The two HIGH branches from NODE-public-repo-exposure-report.md (H1, H2), with the tip each had
# when the report was written. A tip that moved is reported, not hidden.
HIGH_BRANCHES = {
    "claude/funny-ritchie-n9rjpd": {"finding": "H1", "tip": "cdd750c3af4a800b459bf1969a76227d1b0a99b6"},
    "claude/modest-knuth-0i92qa": {"finding": "H2", "tip": "13e0f8b418d215d9a036973771eed556e7dc0ba1"},
}
LAVA_PREFIXES = ("lava-cap-audit/", "lava-cap-site/")
HOSTED_MINUTES_FREE = 2000  # private repos, shared by all of them (F:\novah\ci\NOTES.md, Hybrid CI)

RUNS_ON_RX = re.compile(r"^\s*runs-on:\s*(.+?)\s*$")
JOB_RX = re.compile(r"^  ([A-Za-z0-9_\-]+):\s*$")


class GhError(Exception):
    pass


def gh_api(path):
    """GET only. Returns parsed JSON, raises GhError on any failure or non-JSON output."""
    try:
        p = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise GhError(f"gh could not run: {e}")
    if p.returncode != 0:
        raise GhError((p.stderr or p.stdout).strip().splitlines()[-1][:200] if (p.stderr or p.stdout).strip() else "gh failed")
    try:
        return json.loads(p.stdout)
    except ValueError:
        raise GhError("gh returned non-JSON")


def unknown(why):
    return {"state": "unknown", "why": why}


def parse_workflow(text):
    """Return [(job, runs_on_string)] for a workflow file. Plain line scan, no YAML library."""
    jobs, current, in_jobs = [], None, False
    for line in text.splitlines():
        if re.match(r"^jobs:\s*$", line):
            in_jobs = True
            continue
        if in_jobs:
            m = JOB_RX.match(line)
            if m:
                current = m.group(1)
                continue
            m = RUNS_ON_RX.match(line)
            if m and current:
                jobs.append((current, m.group(1).strip("'\"")))
                current = None
    return jobs


_SAMPLE = "name: t\njobs:\n  a:\n    runs-on: ubuntu-latest\n  b:\n    runs-on: [self-hosted, novah]\n"


def workflow_section(workflow_dir):
    if parse_workflow(_SAMPLE) != [("a", "ubuntu-latest"), ("b", "[self-hosted, novah]")]:
        return unknown("workflow parser failed its own positive control")
    if not workflow_dir or not os.path.isdir(workflow_dir):
        return unknown(f"workflow directory not found: {workflow_dir}")
    files = sorted(f for f in os.listdir(workflow_dir) if f.endswith((".yml", ".yaml")))
    if not files:
        return unknown("no workflow files found; cannot say what runs where")
    rows, hosted, self_hosted = [], 0, 0
    for f in files:
        with open(os.path.join(workflow_dir, f), encoding="utf8") as fh:
            for job, ro in parse_workflow(fh.read()):
                kind = "self-hosted" if "self-hosted" in ro else ("hosted" if "ubuntu" in ro or "windows" in ro or "macos" in ro else "other")
                hosted += kind == "hosted"
                self_hosted += kind == "self-hosted"
                rows.append({"file": f, "job": job, "runs_on": ro, "kind": kind})
    return {"state": "ok", "jobs": rows, "hosted_jobs": hosted, "self_hosted_jobs": self_hosted}


def visibility_section(repo, api):
    try:
        r = api(f"repos/{repo}")
    except GhError as e:
        return unknown(str(e))
    if "private" not in r:
        return unknown("repo response had no `private` field")
    return {"state": "ok", "private": bool(r["private"]), "visibility": r.get("visibility", "?")}


def branches_section(repo, api):
    try:
        names = {}
        for page in range(1, 6):
            batch = api(f"repos/{repo}/branches?per_page=100&page={page}")
            if not isinstance(batch, list):
                return unknown("branch list was not a list")
            for b in batch:
                names[b["name"]] = b["commit"]["sha"]
            if len(batch) < 100:
                break
    except (GhError, KeyError) as e:
        return unknown(f"could not list branches: {e}")
    if not names:
        return unknown("branch list came back empty; a repo always has main, so this is not a finding")
    out = {}
    for name, meta in HIGH_BRANCHES.items():
        if name in names:
            out[name] = {"present": True, "finding": meta["finding"], "tip": names[name][:10],
                         "tip_matches_report": names[name] == meta["tip"]}
        else:
            out[name] = {"present": False, "finding": meta["finding"]}
    return {"state": "ok", "branch_count": len(names), "high": out}


def runners_section(repo, api):
    try:
        r = api(f"repos/{repo}/actions/runners")
    except GhError as e:
        return unknown(str(e))
    if "runners" not in r:
        return unknown("response had no `runners` field")
    return {"state": "ok", "runners": [{"name": x.get("name"), "status": x.get("status")} for x in r["runners"]]}


def runs_section(repo, api, now):
    since = (now - dt.timedelta(days=30)).strftime("%Y-%m-%d")
    try:
        r = api(f"repos/{repo}/actions/runs?per_page=1&created=%3E%3D{since}")
    except GhError as e:
        return unknown(str(e))
    if "total_count" not in r:
        return unknown("response had no `total_count`")
    return {"state": "ok", "runs_last_30_days": r["total_count"],
            "minutes_last_30_days": "unknown: run counts only; minutes need the billing API, which this probe does not call"}


def _paths(repo, sha, api):
    t = api(f"repos/{repo}/git/trees/{sha}?recursive=1")
    if t.get("truncated"):
        raise GhError("tree truncated; file list incomplete")
    return {e["path"] for e in t.get("tree", []) if e.get("type") == "blob"}


def clients_section(repo, clients, api, branches):
    """Which lava-cap-* files on the H2 branch have no same-suffix path in the clients repo."""
    h2 = [n for n, m in HIGH_BRANCHES.items() if m["finding"] == "H2"][0]
    if not branches.get("state") == "ok" or not branches["high"][h2]["present"]:
        return unknown("H2 branch not present or branches unknown; nothing to compare")
    try:
        sha = api(f"repos/{repo}/branches/{h2}")["commit"]["sha"]
        src = {p for p in _paths(repo, sha, api) if p.startswith(LAVA_PREFIXES)}
        csha = api(f"repos/{clients}")["default_branch"]
        dst = _paths(clients, csha, api)
    except (GhError, KeyError) as e:
        return unknown(f"could not compare with the clients repo: {e}")
    if not src:
        return unknown("no lava-cap-* paths found on the H2 branch; the comparison saw nothing to check")
    def present(p):
        tail = p.split("/", 1)[1]
        return any(d == tail or d.endswith("/" + tail) for d in dst)

    missing = sorted(p for p in src if not present(p))
    return {"state": "ok", "files_on_branch": len(src), "found_in_clients": len(src) - len(missing),
            "missing_in_clients": missing}


def build(repo=DEFAULT_REPO, clients=DEFAULT_CLIENTS, workflow_dir=None, api=gh_api, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    rep = {"schema": SCHEMA, "repo": repo, "generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
           "visibility": visibility_section(repo, api)}
    rep["branches"] = branches_section(repo, api)
    rep["runners"] = runners_section(repo, api)
    rep["runs"] = runs_section(repo, api, now)
    rep["workflows"] = workflow_section(workflow_dir)
    rep["clients_copy"] = clients_section(repo, clients, api, rep["branches"])
    rep["breaks_on_private"] = breaks(rep)
    rep["owner_step"] = ("OWNER-STEP: in GitHub, Settings > General > Danger Zone > Change visibility of "
                         f"{repo} to private (his hands only). Then run node/private_preflight.py again, and "
                         "node/delete_high_branches.py only with its confirm flag.")
    return rep


def breaks(rep):
    out = []
    wf, vis = rep["workflows"], rep["visibility"]
    if wf["state"] != "ok":
        out.append("UNKNOWN: workflow files unreadable, so what hosted CI loses cannot be said")
    elif wf["hosted_jobs"]:
        out.append(f"{wf['hosted_jobs']} job(s) run on a GitHub-hosted runner. Public repos get these free; a private repo "
                   f"draws on {HOSTED_MINUTES_FREE} shared free minutes a month and the $0 cap stays, so a capped job logs "
                   "as a failure with steps=0. Plan: copy the hub's try-hosted-then-[self-hosted, novah] fallback and the "
                   "CI_HOSTED=off variable BEFORE the flip (F:\\novah\\ci\\NOTES.md, Hybrid CI).")
    rn = rep["runners"]
    if rn["state"] == "ok" and rn["runners"] and vis["state"] == "ok" and not vis["private"]:
        out.append(f"{len(rn['runners'])} self-hosted runner(s) registered on a repo that is still PUBLIC (report M1): "
                   + ", ".join(f"{r['name']} ({r['status']})" for r in rn["runners"]))
    if rn["state"] == "ok" and rn["runners"] and vis["state"] == "ok" and vis["private"]:
        out.append("runners are registered on a private repo: that is fine, and `[self-hosted, novah]` fallback now works")
    out.append("plugin marketplace source and any `git clone` of this repo from a machine without a GitHub login will "
               "stop working once private. This probe cannot see those machines: UNKNOWN, check by hand.")
    return out


def render(rep):
    L = [f"# redline-1 preflight: {rep['repo']} ({rep['generated_utc']})", ""]
    v = rep["visibility"]
    L.append("visibility: " + (f"{v['visibility']} (private={v['private']})" if v["state"] == "ok" else f"UNKNOWN ({v['why']})"))
    b = rep["branches"]
    if b["state"] == "ok":
        L.append(f"branches: {b['branch_count']}")
        for n, m in b["high"].items():
            if m["present"]:
                L.append(f"  {m['finding']} {n} PRESENT tip {m['tip']} (matches report: {m['tip_matches_report']})")
            else:
                L.append(f"  {m['finding']} {n} not on the server")
    else:
        L.append(f"branches: UNKNOWN ({b['why']})")
    r = rep["runners"]
    if r["state"] == "ok":
        L.append("runners: " + (", ".join(f"{x['name']} ({x['status']})" for x in r["runners"]) or "none registered"))
    else:
        L.append(f"runners: UNKNOWN ({r['why']})")
    u = rep["runs"]
    L.append(f"runs last 30 days: {u['runs_last_30_days']} (minutes: {u['minutes_last_30_days']})" if u["state"] == "ok" else f"runs: UNKNOWN ({u['why']})")
    w = rep["workflows"]
    if w["state"] == "ok":
        L.append(f"workflows: {w['hosted_jobs']} hosted job(s), {w['self_hosted_jobs']} self-hosted")
        L += [f"  {j['file']}:{j['job']} -> {j['runs_on']}" for j in w["jobs"]]
    else:
        L.append(f"workflows: UNKNOWN ({w['why']})")
    c = rep["clients_copy"]
    if c["state"] == "ok":
        L.append(f"lava-cap files on H2 branch: {c['files_on_branch']}, found in clients repo: {c['found_in_clients']}, "
                 f"missing: {len(c['missing_in_clients'])}")
        L += [f"  missing: {p}" for p in c["missing_in_clients"]]
    else:
        L.append(f"clients copy: UNKNOWN ({c['why']})")
    L += ["", "What breaks on private:"] + [f"- {x}" for x in rep["breaks_on_private"]] + ["", rep["owner_step"]]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=DEFAULT_REPO)
    ap.add_argument("--clients", default=DEFAULT_CLIENTS)
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--workflows", default=os.path.join(here, os.pardir, ".github", "workflows"))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", metavar="PATH")
    a = ap.parse_args(argv)
    rep = build(a.repo, a.clients, a.workflows)
    text = json.dumps(rep, indent=2) + "\n" if a.json else render(rep)
    if a.write:
        with open(a.write, "w", encoding="utf8") as fh:
            fh.write(text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
