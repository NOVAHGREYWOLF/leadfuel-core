# NODE merge train, ROUTER #135 wave 3: handoff at 300k tokens (2026-11-24T00:02Z)

Ids only. Full note, scripts and surveys: `F:\Claude Sessions\handoff\ROUTER-135\merge-train\` (HANDOFF.md, land_pr.py).

Owner word via ROUTER #135: land green ones through the merge train, one PR per ci-<repo> hold, one at a time, squash with --match-head-commit.

## Merged (each verified MERGED, tested head == merged head)
- novahub 778, 1143, 1142, 1120, 1138, 1147, 1152, 1144
- lucid 129, orbit 39, reach 44
- leadfuel-core 80, 81, 82

## Update 2026-11-24T00:55Z
- novahub chain finished: also merged 1145, 1146, 1150, 1097, 1110. ci-novahub released.
- leadfuel-core also merged 86, 88, 53, 83, 85.

## Resume (re-check state with gh first)
- leadfuel-core: 87 (in flight when written, ci-leadfuel-core held by my stamp), then 76
- Tool: `python -X utf8 land_pr.py <repo> <pr> [--hub]` (stops, never merges, when it cannot establish green).

## Held
- Router's list: orbit 41, lucid 131, odyssey 62, novahub 1028 (counts-only arm reads, no owner go); lucid 132 (hosted CI cap); novahub-mcp 54 (ROUTER #135 order: ARMS tools/apps.py and Law 9 gate, lucid.today needs a DOORS yes).
- Same genre as held reads: lucid 130, odyssey 61, signal 39, scope 31, lucid 134, novahub-mcp 53.
- Owner decides in own description: lucid 133, orbit 43, reach 50, scope 36, orbit 42, odyssey 63, odyssey 64, signal 37, novahub 1121, 1126.

## Owner steps (deploy, env, migration; not merged)
novahub 1102, 1151, 1119, 1105, 1044, 1053, 1075, 1107, 992; odyssey 58, 60; orbit 40; signal 41, 28; scope 35.
