# LeadFuel completion (Reports + conductor fixes + gateway) - report

## Goal

Finish the Reports program, land the conductor fixes, and move the remaining apps onto the LLM gateway. Cloud sessions do the code; Railway and PC steps stay with Novah.

## Tasks

10 task(s): todo 2, doing 1, pr 0, review 4, done 2, blocked 1.

| id | title | status | model | PR |
|---|---|---|---|---|
| P5-F4 | Reports P5-F4: auto-archive line in the briefing (novahub#692) | done | sonnet | #692 |
| P6 | Reports 6: Scope and Core report builders | review | - | #694 |
| P7 | Reports 7: Estate weekly report (domains, DNS, liveness) | done | - | #696 |
| P8 | Reports 8: DMARC digest (Deliverability report) | blocked | - | - |
| P9 | Reports 9: attach every report as a PDF to the briefing | todo | - | - |
| P10 | Reports 10: end-to-end check that the briefing lands with every attachment | todo | - | - |
| CND-1 | Conductor fixes: session JSON paths, per-task briefs, per-session budget and handoff-due, adopted tasks do not use slots | review | - | - |
| G4-followup-models | Reach: align default model IDs with novahos model_tiers (after gateway cutover) | review | - | - |
| G5 | Scope: check gateway PR scope#11 (+#12,#13) is mergeable against main, update if small, add to runbook | review | - | - |
| G6 | Signal: route the direct vendor client through the hub gateway (G1 model map, G2 template) | doing | - | - |

## Cost

By task:

| task | model | cost | context tokens |
|---|---|---|---|
| P5-F4 | sonnet | $0.87 | 96,615 |
| P6 | - | $1.90 | 166,954 |
| P7 | - | $1.22 | 148,558 |
| P8 | - | $1.06 | 137,388 |
| P9 | - | $0.00 | 0 |
| P10 | - | $0.00 | 0 |
| CND-1 | - | $0.68 | 109,482 |
| G4-followup-models | - | $0.75 | 103,534 |
| G5 | - | $0.63 | 97,415 |
| G6 | - | $0.54 | 109,044 |

By model:

| model | tasks | cost | context tokens |
|---|---|---|---|
| sonnet | 1 | $0.87 | 96,615 |
| unassigned | 9 | $6.78 | 872,375 |

## Budget

- Total spend: $7.65
- Total context tokens: 968,990
- Soft budget: 5,000,000 tokens (ok)
- Hard budget: 8,000,000 tokens (ok)
- Status: **within budget**

## Archive candidates

auto_archive is on: these sessions are eligible for archiving.

- P5-F4: session session_01E4SGoX7VSuJHKATRrcVsde
- P7: session session_013Z7qK6SXAW9BqJZXFfWdn9

## Decisions

None.

## Lessons

None.

## Open items

- P8 is blocked: Reports 8: DMARC digest (Deliverability report)
