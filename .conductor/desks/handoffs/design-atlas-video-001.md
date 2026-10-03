# DESIGN · Atlas video demo · handoff 001 (2026-10-02)

Session local_15e83b97-650c-4caa-8a40-169e7935a8ba (conversation f0122e34). Source: the owner's direct request in this session ("can you make a video demo of what the Atlas does?"). No router, no task id, no PR. Stopped at the 300k guard with the work delivered.

## Done
- A 3:06 captioned demo (1080p30, no audio) of LeadFuel Flow Atlas v3 (artifact UCCG9zfCDWeveQMuT1MFZ5, version 1790946334-1680). It was made by driving a local copy of the page in headless Chrome over CDP with virtual time, with a scripted cursor and real clicks. The artifact is unchanged; nothing was published or sent.
- Chapters: the shape, the answer, a record panel (Embedding gateway), drag and zoom, trace (Mailbox), the full tour "An email becomes a reply", layers (sensors off and on, clock), measure, key and breaks, search (QuickBooks balances), index, end card.
- Delivered: 1080p (78 MB) and 720p (25 MB), desktop app only; the 720p in three parts (11, 8, 7 MB) reached Remote Control.

## State
- Files exist only in this conversation's scratchpad, folder `atlas-video`: the render kit (`cdp.mjs`, `vt.js`, `overlay.js`, `render.mjs`), `frames/`, and the mp4s. The scratchpad is temporary.
- Verified myself: no page errors, every scripted target found, frames sampled from the preview, the final and the 720p. Not watched end to end at speed.

## Next
Nothing queued. Wait for the owner.

## Owed
- Owner: where to keep the video and the kit (not this public repo).
- Offered, not asked for: an offline voice track; an Atlas Live segment (it would record live connector data, so it needs the owner's yes); a fix for the QuickBooks balances panel clipping "asked every 15 min, written on change" (`.nums td` nowrap).
- Reported to the owner: eight concurrent pytest runs at about 18:30 PDT, six of them `pytest tests/`.

## Gotchas
- OrbitControls autoRotate and damping advance per update, not per second: keep 60 steps a second.
- Under CPU contention the piped render fell to 3.5 s a frame; `render.mjs` now writes resumable frames.
- Remote Control uploads: 30 MB cap and a 30 s timeout on the ~5 Mbps link; parts of about 10 MB get through.
