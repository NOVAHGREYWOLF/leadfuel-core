# DESIGN · ATLAS-3D · handoff 002 (2026-10-03)

Session `DESIGN · ATLAS-3D 2/2 · Atlas Live in 3D` (Opus). Follows atlas-3d-001.md. Built option B as decided.

## Done
- Atlas Live (6LEvF7K9u9qnSxh68VWsfA) republished as **version 5** (version id 1790998250-e0ba). Title kept, stored mcp declaration carried forward (no capabilities or icon passed).
- It opens in 2D. A 2D/3D switch sits in both headers; `#3d` or a part id in the link opens the crystal.
- 3D is the Flow Atlas crystal and data, lifted unchanged from UCCG9zfCDWeveQMuT1MFZ5 (not republished, not changed). The ten live layers are drawn on it, plus a Live tab in the rail (status, layer chips, waiting pools, newest 8 arrivals).
- One adapter seam (`start(emit)`), connector adapter only. No hub adapter.
- Fixed: an unavailable spend meter now reads unknown, not "none held". Borders and claims in 2D now come from the Flow Atlas data.
- Predecessor local_0f7bb7a2 archived (its branch was clean and pushed).

## Verified here
- Page script parses. Local check with made-up stub data through the seam, at desktop and phone width, 2D and 3D: renders, no console errors.
- The tool arguments the page sends match this session's schemas for the five connector tools.

## Not verified
- The page's real connector calls have never run. Result shapes rest on atlas-3d-001's reading of the code, not on a live call.

## Next
- None owed by this desk. The owner opening the page is the first live run of the connector path.
