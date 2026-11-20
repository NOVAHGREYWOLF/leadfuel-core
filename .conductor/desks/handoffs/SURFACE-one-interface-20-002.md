# Handoff 002: SURFACE · one-interface part · 20 (adds to 001)

Both sub-agents finished. Their work is pushed, and part 20 is idle.

## Done (verified by this desk: commits, status clean, ls-remote)
- **#1131 review fixes:** `a802c4e6` on `surface/command-chat-steers`, pushed.
  - Esc and mode change bump `C.seq`; `parse` never raises; every ignored item is listed in `dropped`; reasons quote the received value; the steer 401/403 carry no-store and Vary.
  - The sub-agent reported 581 passed in seven files, gates 14 of 16 green, and both revert checks failing as expected.
  - Main was `f2a58543` at push, so the branch is on current main.
- **Step 6 task B, the frame:** `7d75d5aa` on `surface/plain-skin-frame` (from `c983aefd`), pushed.
  - `command_shell.py` holds `SKINS` and `skin_for()`; `plain_pages()` reads `command_steer.places()`.
  - The template has the header `nav.seg.skin` and `section#plain` with every id in `step6-plan.md`.
  - `plain.css` uses the prefix `body[data-skin="plain"].cmdx`.
  - The sub-agent reported 590 passed (seven files) and 2,809 passed (49 files that render /command), with no pin changed.

## Gotchas found by task B
- The owner's mine/platform scope form (`command_scope` route), the brand link and the World menu link drop `skin=`, so they go back to Game.
- `screen.js` keys still act on the hidden game in Plain. Task C should stop the game keys when `data-skin` is plain.
- The header is crowded at 1440px: the census pill shrinks to 71px.

## Next
Unchanged from 001. Merge #1131 first, on the CI run for `a802c4e6`. Then branch task A from the merged main, and merge `surface/plain-skin-frame` with main in.
