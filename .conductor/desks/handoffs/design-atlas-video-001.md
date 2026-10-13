# DESIGN · Atlas video demo · handoff 001 (2026-10-02)

Session local_15e83b97-650c-4caa-8a40-169e7935a8ba (conversation f0122e34). Source: the owner's direct request in this session ("can you make a video demo of what the Atlas does?"). No router, no task id, no PR. Stopped at the 300k guard with the work delivered.

## Done
- A 3:06 captioned demo (1080p30, no audio) of LeadFuel Flow Atlas v3 (artifact UCCG9zfCDWeveQMuT1MFZ5, version 1790946334-1680). It was made by driving a local copy of the page in headless Chrome over CDP with virtual time, with a scripted cursor and real clicks. The artifact is unchanged; nothing was published or sent.
- Chapters: the shape, the answer, a record panel (Embedding gateway), drag and zoom, trace (Mailbox), the full tour "An email becomes a reply", layers (sensors off and on, clock), measure, key and breaks, search (QuickBooks balances), index, end card.
- Delivered: 1080p (78 MB) and 720p (25 MB), desktop app only; the 720p in three parts (11, 8, 7 MB) reached Remote Control.

## State
- Copied out of the temporary scratchpad to `F:\novah\media\flow-atlas-demo\` (local, not synced): the mp4s (1080p, 720p, three parts) and `kit\` (`render.mjs`, `cdp.mjs`, `vt.js`, `overlay.js`, `atlas-src.html`). The 1080p sha256 matches the original. The kit runs from that folder: `node kit\render.mjs` re-renders the frames into `kit\frames`. The frames were not copied (2.2 GB, re-renderable).
- Verified myself: no page errors, every scripted target found, frames sampled from the preview, the final and the 720p. Not watched end to end at speed.

## Next
The owner asked, in this session: add a voice track, and save the files in a OneDrive "marketing" folder. The owner also said to route it through the router and the conductor, so it was sent to ROUTER #13 (local_21748811) and CONDUCTOR · system build (local_e8701502) as msg 13e21fd8 and 4d3f3122. Both were queued; neither has been confirmed read. The conductor filed it as ATLAS-VIDEO-VOICE (rank 207); ROUTER #13 opens the desk. The voice must come from an offline Windows voice only (no cloud TTS, Law 9).

## Owed
- Owner: which OneDrive Marketing folder. There is no top-level one; the router is posting a card with a default (create one at the top of the business OneDrive).
- Offered, not asked for: an Atlas Live segment (it would record live connector data, so it needs the owner's yes); a fix for the QuickBooks balances panel clipping "asked every 15 min, written on change" (`.nums td` nowrap).
- Reported to the owner: eight concurrent pytest runs at about 18:30 PDT, six of them `pytest tests/`.

## Gotchas
- OrbitControls autoRotate and damping advance per update, not per second: keep 60 steps a second.
- Under CPU contention the piped render fell to 3.5 s a frame; `render.mjs` now writes resumable frames.
- Remote Control uploads: 30 MB cap and a 30 s timeout on the ~5 Mbps link; parts of about 10 MB get through.
