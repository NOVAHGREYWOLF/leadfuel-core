# LeadFuel completion (Reports + conductor fixes + gateway) - report

## Goal

Finish the Reports program, land the conductor fixes, and move the remaining apps onto the LLM gateway. Cloud sessions do the code; Railway and PC steps stay with Novah.

## Tasks

10 task(s): todo 2, doing 7, pr 1, review 0, done 0, blocked 0.

| id | title | status | model | PR |
|---|---|---|---|---|
| P5-F4 | Reports P5-F4: auto-archive line in the briefing (novahub#692) | pr | sonnet | #692 |
| P6 | Reports 6: Scope and Core report builders | doing | - | - |
| P7 | Reports 7: Estate weekly report (domains, DNS, liveness) | doing | - | - |
| P8 | Reports 8: DMARC digest (Deliverability report) | doing | - | - |
| P9 | Reports 9: attach every report as a PDF to the briefing | todo | - | - |
| P10 | Reports 10: end-to-end check that the briefing lands with every attachment | todo | - | - |
| CND-1 | Conductor fixes: session JSON paths, per-task briefs, per-session budget and handoff-due, adopted tasks do not use slots | doing | - | - |
| G4-followup-models | Reach: align default model IDs with novahos model_tiers (after gateway cutover) | doing | - | - |
| G5 | Scope: check gateway PR scope#11 (+#12,#13) is mergeable against main, update if small, add to runbook | doing | - | - |
| G6 | Signal: route the direct vendor client through the hub gateway (G1 model map, G2 template) | doing | - | - |

## Cost

By task:

| task | model | cost | context tokens |
|---|---|---|---|
| P5-F4 | sonnet | $0.87 | 96,615 |
| P6 | - | $0.00 | 0 |
| P7 | - | $0.00 | 0 |
| P8 | - | $0.00 | 0 |
| P9 | - | $0.00 | 0 |
| P10 | - | $0.00 | 0 |
| CND-1 | - | $0.00 | 0 |
| G4-followup-models | - | $0.00 | 0 |
| G5 | - | $0.00 | 0 |
| G6 | - | $0.00 | 0 |

By model:

| model | tasks | cost | context tokens |
|---|---|---|---|
| sonnet | 1 | $0.87 | 96,615 |
| unassigned | 9 | $0.00 | 0 |

## Budget

- Total spend: $0.87
- Total context tokens: 96,615
- Soft budget: 700,000 tokens (ok)
- Hard budget: 1,000,000 tokens (ok)
- Status: **within budget**

## Archive candidates

None.

## Decisions

None.

## Lessons

None.

## Open items

None.
