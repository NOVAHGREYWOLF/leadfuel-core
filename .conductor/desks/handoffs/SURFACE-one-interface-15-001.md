# Handoff 001: SURFACE · one-interface part · 15

Session `local_1146d1f7-08f6-4eb2-b990-3844c4347b15` (Opus), group one-interface. Opened directly by the owner, so there is no router brief. Build material is kept privately in `F:\Claude Sessions\handoff\surface-one-interface-15\material.md`.

## Done
- I showed the owner the built /command in production (character card, teller, globe).
- I read production's world state; it is in the material file.
- **Owner's word in this session:** build the real-earth globe from self-hosted NASA imagery and turn it on ("build and turn on", then "yes").
- **Hub worktree** `.claude/worktrees/surface-globe-imagery`, branch `surface/command-globe-imagery`, based on 94e64d48. Commit `bcd1a2e1` adds `static/command/earth/`: two NASA Blue Marble textures, public domain, plus `SOURCE.txt`.

## State
- **Not pushed, no PR, no CI.**
- **A build sub-agent was still running at handoff.** It adds the renderer to `universe.js` plus `tests/test_command_globe_imagery.py`, and commits to the same branch.
- **Verified:** bcd1a2e1 is in the local branch.
- **Not verified:** anything the sub-agent did.

## Next
Wait for the predecessor's `BUILD-REPORT` message. If it says the report is lost, read the branch log yourself. Then:
1. Run the local preview (recipe in the material file) and look at the globe in the browser pane.
2. Run `SKIP_TESTS=1 sh scripts/gates.sh` and the targeted tests.
3. Push, then open a draft PR.
4. Take `ci-novahub`, get CI green on that head, then merge. The owner's go is given.

After that, publish the one-app NovahOS plan page from the material file's skeleton.

## Owed (owner decides)
- Group 1 world feeds on in production (quakes, NWS weather alerts, GDACS): asked, not yet answered. The `NWS_USER_AGENT` wording needs his approval with it.
- The FIRMS key.
- EONET and CelesTrak terms.
- The "you are here" pin. It is not this PR: `world_routes` belongs to INTELLIGENCE.

## Gotchas
- eoimages.gsfc.nasa.gov refused connections, so the image came from the Wikimedia Commons mirror.
- Chrome's screenshot hangs on `/command/oracle`; use page text there.
- The :8080 door is a bare-admin session, so it shows no character sheet and no teller.
