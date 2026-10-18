# Handoff: SURFACE · leadfuel.cloud website part · 1

Session local_c164e7c8-d30f-417d-82d1-7d30d5dd6834, branch claude/zealous-heisenberg-tlqil3, 2026-10-18. No router exists for this project; the owner worked with this desk directly. No PR.

## Done
- Titled and filed (group "leadfuel.cloud website").
- Owner locked NovahOS as the whole-product name, pending a trademark check. LeadFuel stays the business side and the domain for now.
- Hostinger read-only check done. Details are in the private notes.
- Built and published a private mockup of the rebuilt site (artifact id LhCZgmdPQwhJ8VUL644c2p, claude.ai/artifact/LhCZgmdPQwhJ8VUL644c2p). Skin: LeadFuel base, Novah as the Life half and dark theme.

## State
- Verified by me: mockup renders at 1280 and 400 wide, no overflow, no console errors, sample card buttons work.
- Taken on trust: every product-state claim in the mockup, from the Important Documents (private folder on F:). The successor re-reads state.
- All private detail (domain findings, two live-site claims needing a decision, sources) is in F:\Claude Sessions\handoff\leadfuel-website-rebuild\NOTES-private.md. Mockup source is in the same folder.

## Next
Ask the owner for mockup feedback, then: (1) take a hub worktree and build the home page in content.py, marketing.py and templates with the name as one setting; (2) capture real app screens from a local sample-data run; (3) get the DESIGN desk to review template changes.

## Owed
- Owner or COUNSEL: trademark clearance on NovahOS.
- Owner: whether novahos.com fronts NovahOS.
- Owner or router: decide two claims on the live site (see private notes).
- No handoff message was sent to any session; none was owed.

## Update, same day: mockup 2 supersedes mockup 1
- Owner rejected mockup 1 as too light ("the website needs to be as amazing as the app") and switched this session to Fable 5.1 for a second pass.
- Mockup 2 is the site as the app: Command's own dark frame, the founder's character, one request run end to end by the staff, honest live/built/planned labels. Artifact id 8kKEcqhuGqJTwQST7oErAu (claude.ai/artifact/8kKEcqhuGqJTwQST7oErAu). Source and notes in the private folder named above.
- The LeadFuel light skin is no longer the base. Build from mockup 2.
- Verified by me: desktop and phone render, no overflow, no console errors, the run and the feed buttons work. Not checked: light theme, tablet.

## Gotchas
- The Browser pane cannot drive file:// pages; serve the file over localhost from a launch.json entry.
- Local previews need a charset and a viewport meta; the publish skeleton adds both.
- The Bash tool's cd changes the session working directory; use absolute paths.
