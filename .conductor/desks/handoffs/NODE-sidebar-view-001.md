# NODE · sidebar view — desk handoff 001 (2026-10-19 UTC)

Desk: `NODE · sidebar view` (local_768eb023-e60e-4c3e-8b08-af3d9673e545), branch `claude/zealous-heisenberg-tlqil3`. Owner asked why the sidebar Routines section and per-session token readout disappeared after a desktop update.

## Done
- Cause: app bug since desktop build 2.37337.1 (auto-update 2026-10-14), still present in 2.42304.0 (owner's build; winget `Anthropic.Claude`, developer-signed MSIX). `list_sections` reports `routines` as `shown:false`; no tool flips it; config edits are reverted on launch; the section menu's "Show" list holds only "Metadata". Public reports, all open with no staff reply seen: anthropics/claude-code #102150, #102555, #102247, #102703, #102489, #103215.
- Live conductor and routers run as slot runs, so they never show as sidebar rows (routine runs cannot be pinned or grouped): way-slot-01 conductor local_259a7d41-316f-422b-93d3-9306c2b5f09b, way-slot-04 ROUTER #72 local_47411781-90af-470d-93c6-b310a287fd12, way-slot-06 ROUTER #71 local_64df054f-bf33-4516-9280-61c5abac4141.
- Changelog for v2.42304.0 (claude.com/docs/cowork/changelog.md): the usage ring under the message box now shows plan usage; per-session context moved to a Context card on the session rail; the first top-right toolbar icon is "Show session rail" (tooltip verified by hover); the sidebar "Group and sort" button appears when hovering a section heading and is documented as able to "show routines or empty groups"; custom groups are now called sections.
- Memory notes written: reference_desktop_app_sidebar_and_usage_gone, reference_scheduled_run_as_session_launcher (private, not in repo).

## State
Nothing in the repo changed except this note. Verified myself: slot and session ids, app version and install source, the hover tooltip, the "Show" menu contents, issue states and absence of staff replies. Took on trust: the changelog wording (read through a summarising fetch) and the claim that an old build would or would not fix anything.

## Next
With the owner at the screen, one step at a time: (1) click "Show session rail" and confirm a Context card with per-session tokens; (2) the built-in "Recents" section sits at the bottom of the sidebar: hover its heading, open "Group and sort", read the "Show" submenu for a Routines entry (not yet checked; the ROUTER section's menu had none); (3) if none, the owner chooses: wait for a fix, comment on #102150, or roll back.

## Owed
- Rollback is the owner's call and is not recommended: winget's newest version (2.19675.1) is older than the build before the bad update (2.31226.1 per one reporter), it would stop every live session, and the app data is 11.7 GB in `%APPDATA%\Claude`.
- A public GitHub comment or +1 needs the owner's yes.
- Background search for old installers (task b87q810pn) may still be running; its result was not read.
- No messages to other sessions were sent.

## Gotchas
Bottom-left sunburst icon opens "Send feedback" (never click Send). x=411 in the sidebar is its scrollbar. The usage ring popover's icons open Settings → Usage, which shows plan usage by product, not by session. Screen look/click works through PowerShell `CopyFromScreen` and `mouse_event`; the owner may be clicking at the same time, so one click per screenshot.
