# DESIGN · Atlas video demo 2/2 · handoff 002 (2026-10-03)

Session local_66e28df6-5bb3-4809-b5dd-8227649ed94f. Source: the owner, relayed by ROUTER #13 then #14. Predecessor local_15e83b97 (handoff 001) archived.

## Done
- Voice track added to the Atlas demo with offline Windows speech only (System.Speech, David). No cloud TTS, nothing transmitted for the voice.
- Owner answered card q197 "new" (03:41:47Z): files are in `OneDrive - Emerging Technology Group LLC\Marketing\Flow Atlas demo`. OneDrive syncs to Microsoft's cloud; the owner chose it by name.
- Five mp4s there, byte-identical to the durable copy: 1080p voiced (84,015,695 B), 720p voiced (28,685,450 B), 720p parts 1-3 (11,025,251 / 11,989,623 / 5,911,784 B). 185.77 s.

## State
- Durable kit and videos: `F:\novah\reference\atlas-video\` (silent originals) and `...\voice\` (narration.json, speak.ps1, timeline.mjs, place.mjs, clips). Rebuild: node timeline.mjs, speak.ps1, node place.mjs, ffmpeg mux.
- Not listened to end to end; timings and levels checked only.

## Next
Nothing queued.
