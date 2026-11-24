"""NODE redline-1: delete the two HIGH branches of leadfuel-core. Refuses unless told, twice.

Deleting a branch is irreversible and does NOT purge GitHub's pull refs (refs/pull/3 and /4 keep
the commits fetchable; that needs a GitHub Support request or the repo being private). So this
script is for the owner, after the repo is private, and it is never run by a desk.

Default is a dry run: it lists what it would delete and exits 2. It deletes only when ALL hold:
  * --confirm-delete is given, and
  * the repo is reported private by GitHub (override with --even-if-public, said out loud), and
  * the branch is one of the two names in HIGH_BRANCHES (nothing else can be named), and
  * its tip is the SHA recorded in the exposure report (a moved tip means someone pushed since;
    the script stops and says so).
Any probe that fails is a refusal, never a pass.

Usage: python node/delete_high_branches.py [--repo OWNER/NAME] [--confirm-delete] [--even-if-public]
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import private_preflight as pf  # noqa: E402


def gh_delete(path):
    p = subprocess.run(["gh", "api", "-X", "DELETE", path], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise pf.GhError((p.stderr or p.stdout).strip()[:200])


def plan(repo, api):
    """Return (refusals, targets). Targets are branches that exist at the expected tip."""
    refusals, targets = [], []
    vis = pf.visibility_section(repo, api)
    if vis["state"] != "ok":
        refusals.append(f"cannot establish visibility: {vis['why']}")
    elif not vis["private"]:
        refusals.append("repo is still PUBLIC")
    for name, meta in pf.HIGH_BRANCHES.items():
        try:
            tip = api(f"repos/{repo}/branches/{name}")["commit"]["sha"]
        except (pf.GhError, KeyError) as e:
            refusals.append(f"{name}: cannot read it ({e}); not treated as already gone")
            continue
        if tip != meta["tip"]:
            refusals.append(f"{name}: tip moved ({tip[:10]} is not {meta['tip'][:10]}); someone pushed, look first")
            continue
        targets.append(name)
    return refusals, targets


def main(argv=None, api=pf.gh_api, delete=gh_delete):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=pf.DEFAULT_REPO)
    ap.add_argument("--confirm-delete", action="store_true")
    ap.add_argument("--even-if-public", action="store_true")
    a = ap.parse_args(argv)
    refusals, targets = plan(a.repo, api)
    if a.even_if_public:
        refusals = [r for r in refusals if r != "repo is still PUBLIC"]
    for t in targets:
        print(f"would delete: {a.repo} {t}")
    for r in refusals:
        print(f"REFUSED: {r}")
    if not a.confirm_delete:
        print("dry run: nothing deleted. Pass --confirm-delete to delete.")
        return 2
    if refusals or not targets:
        print("nothing deleted.")
        return 1
    for t in targets:
        delete(f"repos/{a.repo}/git/refs/heads/{t}")
        print(f"deleted: {t}")
    print("pull refs refs/pull/3 and refs/pull/4 are NOT removed; ask GitHub Support for the purge.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
