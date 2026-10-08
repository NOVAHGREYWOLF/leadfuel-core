# Handoff: DESIGN · etg.ai billboard video · 1

Session: local_dfa3737d-640b-469e-8b71-a6b2ada1bdaf (branch claude/zealous-heisenberg-tlqil3, no PR; nothing in this repo changed by the task).

**Done:** pipeline to track and composite the etg.ai tile onto every LED screen of the owner's phone clip IMG_5211.mov (Downloads):
feature tracker, 4 annotator agents (about 110 annotated screens), merge/dedupe, curation, renderer, ffmpeg export with audio.
Second half of the clip is tight; the early half is plausible but busy. A v1 render exists from the previous tracks.

**State (not re-verified by the successor yet):** all build files and the full build notes are in the session scratchpad
(`...\claude\F--Leadfuel-repos-leadfuel-core\6569ff04-99f3-4eb4-af8c-8bfc7231ebe2\scratchpad`, file `NOTES.md`). They are kept
out of the repo on purpose.

**Next:** follow "Next" in the scratchpad `NOTES.md`: rebuild `tracks.json` (annotators finished after the last build),
review labelled sheets, add the two missing screens, render the final mp4, copy it to Downloads, send it to the owner.

**Owed:** the owner has not yet seen any video. Deliver v1 or the final file with SendUserFile.

**Gotchas:** Bash halves backslashes (use Write/Edit for code); flow-based occlusion does not work here.
