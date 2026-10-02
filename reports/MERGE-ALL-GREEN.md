# MERGE-ALL-GREEN report (WATCH desk, 2026-10-02)

Task: picks/u-merge-all-green (owner, via CONDUCTOR · system build, ~20:30 UTC). Router: ROUTER #11.
All times are UTC. **Verified by me** means read from `gh` or `git ls-remote` at the time stated. Anything else is marked as taken on trust.

Census at 21:10Z: **133 open PRs across 21 repos** (the conductor's ~100 was low). Listed with `gh pr list` over every non-archived repo.

## Merged

Each merge followed the same sequence: CI green on a head with current main merged in, then `ls-remote main` unmoved, then a squash pinned with `--match-head-commit`, all inside the `ci-<repo>` hold.

| PR | squash sha | notes |
|---|---|---|
| odyssey#50 | 8e9d136 | GDPR purge fix. Head b9dfbce already contained main 9352b58 (behind 0), CI green. I took over ci-odyssey as successor to DOORS · Odyssey purge, which had stood down holding the lock for one. Lock released. |
| novahub-mcp#35 | 1e18f2d | Auth refusal message. Main c9187a8 merged in, head 6768e3e, CI green (smoke, pip-audit). |

| orbit#26 | b40e800 | Re-rendered marketing PDFs. Main 0eae05f merged in, head f820cb5, CI green (pytest, ruff, pip-audit, check_writing). |

<!-- MERGED-MORE -->

## Owner runs these: Railway deploy configuration (Q142, card q148). I did not merge them.

The commands come from the PR bodies. **I have not run `railway config plan` myself.**

Most shared checkouts are not on main (echo, signal, scope, lucid are on `n1-f2-names-gate`; reach is on `claude/n1-f1-display-names`; orbit is on `marketing-refresh-pngs`). So each apply runs from a throwaway worktree of `origin/main`. If `railway` says the directory is not linked, run `railway link` there and pick project LeadfuelBusinessSuites, environment production, and the service named in the PR title.

### Set A: remove railway.toml (cutover due 2026-12-01). Merging deploys; there is no apply step.

Each PR deletes `railway.toml`, so the service runs on the settings already stored on it. The `.railway/railway.ts` migration was applied on 2026-10-01, per the PR bodies (taken on trust). odyssey#49 also edits `tests/test_migration_safety.py`. All nine are ready (not draft) and green on their current heads as of 21:35Z, but none has had current main merged in by me. Proof after each merge: the deployment status reaches `success`, and in `railway status --json` the new deployment's `meta.configFile` no longer names a toml. Revert the PR if either check fails.

```powershell
gh pr merge 699 -R NOVAHGREYWOLF/novahub --squash
```
```powershell
gh pr merge 49 -R NOVAHGREYWOLF/odyssey --squash
```
```powershell
gh pr merge 37 -R NOVAHGREYWOLF/novahub-mcp --squash
```
```powershell
gh pr merge 55 -R NOVAHGREYWOLF/echo --squash
```
```powershell
gh pr merge 29 -R NOVAHGREYWOLF/signal --squash
```
```powershell
gh pr merge 23 -R NOVAHGREYWOLF/scope --squash
```
```powershell
gh pr merge 34 -R NOVAHGREYWOLF/reach --squash
```
```powershell
gh pr merge 30 -R NOVAHGREYWOLF/orbit --squash
```
```powershell
gh pr merge 126 -R NOVAHGREYWOLF/lucid --squash
```

### Set B: wait for CI before deploying (`checkSuites: true` in `.railway/railway.ts`). Merge, then plan and apply.

Each PR changes one file, `.railway/railway.ts`, and sets `source.checkSuites` from null to true. Merging alone changes nothing. The switch takes effect at `railway config apply`. **The plan must read `0 to destroy`; an apply deletes any variable the .ts does not name.** All are drafts, so each starts with `gh pr ready`.

**Do not apply hub #737 yet.** ROUTER #11 says the hub's two CI runners must first be rebuilt without their resource cap, and no desk is queued for that. #737 is also UNSTABLE (one check has no conclusion).

One block per PR; change the repo and number:

```powershell
$repo='novahub-mcp'; $n=38
gh pr ready $n -R NOVAHGREYWOLF/$repo
gh pr merge $n -R NOVAHGREYWOLF/$repo --squash
git -C "F:\Leadfuel\repos\$repo" fetch origin main
git -C "F:\Leadfuel\repos\$repo" worktree add --detach "$env:TEMP\rw-$repo" origin/main
Push-Location "$env:TEMP\rw-$repo"
railway config plan --verbose      # read it: must say 0 to destroy, and only source.checkSuites (null -> true) plus the restartPolicyType default line
railway config apply
Pop-Location
git -C "F:\Leadfuel\repos\$repo" worktree remove "$env:TEMP\rw-$repo"
```

Run the same block with these values:
- `$repo='odyssey'; $n=51` (odyssey and Odyssey Cron)
- `$repo='echo'; $n=56`
- `$repo='signal'; $n=31` (NovaHound)
- `$repo='scope'; $n=26` (SMART ICP)
- `$repo='orbit'; $n=32` (NovaHawk)
- `$repo='reach'; $n=37` (NovaHerald)
- **Later, after the runner rebuild:** `$repo='novahub'; $n=737`

### Hub #714: WeasyPrint system libraries in the Railway build (nixpacks.toml), deploy configuration

The PR adds `nixpacks.toml` with apt packages for every service built from the hub repo root, plus a fail-closed PDF engine check at boot. Its body says not to merge before the owner's yes. NODE · CAND-weasyprint-libs says Q133 was that yes, relayed by ROUTER #10 (taken on trust). NODE's own auto mode refused the merge as a production deploy. Per NODE (taken on trust), CI was green on head 80c2d89 with main merged in, but main has moved since, so a merge now needs a fresh CI run on current main (Q144).

```powershell
gh pr ready 714 -R NOVAHGREYWOLF/novahub
gh pr update-branch 714 -R NOVAHGREYWOLF/novahub
gh pr checks 714 -R NOVAHGREYWOLF/novahub --watch
gh pr merge 714 -R NOVAHGREYWOLF/novahub --squash
```

## Green, but held for a reason. The owner can run these once the reason clears.

| PR | why not merged |
|---|---|
| signal#13, signal#28, scope#11, scope#25 | LLM gateway cutovers. Merging before the gateway tokens are set takes the LLM down (card q146; DOORS · one door out runbook). |
| reach#33 | Changes default model IDs to claude-sonnet-5-5. Its own body asks for a live smoke call through the gateway before deploy, and the hub's `costs.py` has no 5-5 pricing row. Draft from a finished cloud session. |
| hub #723 | GDELT world sensor. Draft; its desk (INTELLIGENCE · world intelligence lane) was active at 20:58Z. |
| Session budget kit: hub #693, odyssey#48, novahub-mcp#36, echo#54, signal#27, scope#22, reach#32, orbit#29, lucid#125 (leadfuel-core#5 has no CI) | Drafts from finished cloud sessions that add a context-guard hook to every repo. The leadfuel-way plugin now installs the same guard, so merging would likely run two guards. NODE should decide; not merged blind. |
| novahos #26, #28, #29, #30, #31, #32, #38 (green); #27, #34 (green but conflicting) | Conductor build stack. Each targets another `claude/conductor-*` branch, not main, and no PR takes the root of the stack to main. Stacked on unmerged bases. |
| hub queue holders: #702, #709, #719, #724 (green) | Their desks hold ci-novahub tickets and merge their own PRs. I did not jump them. |

PowerShell for any of these, once cleared:
```powershell
gh pr ready <n> -R NOVAHGREYWOLF/<repo>
gh pr merge <n> -R NOVAHGREYWOLF/<repo> --squash
```

## Skipped: not green

- **HOLD:** hub #704 (marked HOLD, do not merge; also red).
- **Stacked:** hub #736 (based on atlas-in-command-center / #730; red).
- **Red on current head:** hub #592, #657, #705, #708, #710, #711, #712, #713, #716, #718, #720, #722, #727, #728 (also conflicting); hub #706 pending; odyssey#47; leadfuel-core#6.
- **Stale August PRs, red and/or conflicting, other desks' work, not rebased blind:** odyssey#37, #38, #39; echo#42, #43, #44, #45, #46; signal#14, #15, #16; scope#12, #13, #14; reach#11, #21; orbit#12, #13, #14, #15; lucid#113, #116, #117; NovahPrime#11, #12, #13.
- **No CI ran, so there is no green to merge on:** leadfuel-core#3, #7 to #16 (the repo has no CI; #10 and #16 are also stacked); leadfuel-ios#1, #2; novahos#11; hub #730 (draft, its stacked child is #736); scope#7; orbit#5 (stacked); Jarvis#2; apollo-enricher#1; leadfuel-intake#1 to #4; wolfos#5, #6; JobHunter#1 to #6; email-app#1; n8n-leadfuel#1.
- **howlclip#1:** reads green but is not. Its title says ".gitignore", yet it changes 30 files, including railway.toml, app.py and security code. The only check that ran is Dependabot's config check; the repo's own CI never ran on it.

<!-- QUEUE-STATE -->
