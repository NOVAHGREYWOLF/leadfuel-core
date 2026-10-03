# ATLAS-DATA-REFRESH handoff 001 (DESIGN desk, 1/1 predecessor session local_605ac0c5-66c8-4e07-b9a1-71feb5c2a716)

## Done
Batch 1 (NODE ATLAS-INFRA-MEASURE, session local_305f9cf3-a429-44b0-8d9f-7816dacf22ac, measured 2026-10-03 16:22-16:28 UTC) written into:
- Flow Atlas v3, artifact UCCG9zfCDWeveQMuT1MFZ5, now version 4
- Atlas Live v5, artifact 6LEvF7K9u9qnSxh68VWsfA, now version 6
Rows: i-railway (row 29) unknown -> live, 34 services/4 projects, 32 deployed, 2 sleeping; i-ci (row 42) 13 runners, hub 5 queued/2 running, others 0 (point in time). Atlas Live CI-queue pool stays "?" with last-reading text; footer updated.

## State (verified by me)
DATA block was byte-identical in both artifacts before and after (diff of const DATA). Both pages' scripts parse (node). Not verified: pages rendering in a browser; Atlas Live's novahub-brain connector (publish warned it is unobserved; I changed strings only).
Reported to ROUTER #15 (local_8e21f892-8f9f-4a18-9624-bef6418d1cd4): message QUEUED, not confirmed read.

## Next
Wait for further ATLAS-* DONE reports from ROUTER #15. For each: read its transcript with list_events, apply only what it measured to BOTH artifacts' DATA (never paint green; cite desk, session id, UTC time), diff DATA equal, republish with Artifact action read first, report STATUS to ROUTER #15.

## Gotchas
- Bash tool halves backslashes: a \' in JS strings broke the script once. Avoid apostrophes in edited strings, or use Edit/Write.
- Do not set checked:true on nodes not re-read in code: the panel then claims "Re-read in code on 2 Oct".
- Publish needs the whole saved file read first (v3 1863 lines, v5 2555 lines); edit copies in the scratchpad, publish with url + file_path.
- Row text on the Conductor desk doc: design.json tasks.ATLAS-DATA-REFRESH (artifact MKAx49RAskZ3cV7f2EkDMF).
