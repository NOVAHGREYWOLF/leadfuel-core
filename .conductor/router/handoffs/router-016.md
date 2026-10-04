# Router handoff #016 -> #017 (2026-10-04 ~02:00 UTC, ROTATING)

ROUTER #16 is local_dd131408-d1fa-434b-a5ef-dfecbc0f6708 (Opus), ~305k tokens. Ids only. Re-read live state before acting.
Router desk LzmP6QcxmYh9TdvMMjS883, Conductor desk MKAx49RAskZ3cV7f2EkDMF, board router/current (A4uS9xn1emqupohdE4DUfV). Conductor 010 local_5340d134 (009 is archived).
Owner, ~21:45Z: "keep going all night with things you can do. fully auto." There is no start_session, so new desks are chips that wait for the owner's click.

## State (verified 01:58Z unless marked)
- CI is back: Docker was relaunched ~20:29Z, and the restarts are ephemeral (NODE verified). A network ENOTFOUND blip around 01:20-01:58Z killed several desk turns. Woken at 01:58Z: AI-STORE, CI-OVERFLOW, CI-STARVATION, BRAIN-MEASURE, SIGNAL-WORLD.
- ci-novahub is held by ATLAS-B1 local_70fae0d7 (#740: pytest and gates green, pip-audit QUEUED). Offer order after it: #760 CI-OVERFLOW local_02e3cc60, then #755 CI-STARVATION local_5bc2f56b, then old tickets (#726 QBO local_6343c1fa, #728, #749, #750, #751, #757, #759, #761 ...). Offer the slot by messaging the desk by name.
- full-suite.running has 14 markers, most stale. CI-STARVATION is told to audit them; do not delete what can't be proven dead.
- Hub #752 (ATLAS-DOORS local_3f2e7535) is HELD on q227 = B: NODE ATLAS-FLAGS-APPLY local_27c655ce measures email volume (system mail shares one account) and resizes EGRESS_EMAIL_DAILY_MAX (now 100). Needs the owner's yes in that desk's chat. #754/#758/odyssey #52/lucid #127/reach #38 (ARM-SENDS-DOORS 2/2 local_c572e6ef) follow #752.
- q228 = desk: LUCID-DAY-SUBMIT local_36d20e10 flips n8n lucid-hub-report (owner's yes in its chat).
- CI-OVERFLOW: the owner decided "run the hub tests on github too"; the desk's classifier needs the owner's approval in its chat. #760 merges as is first.

## Desks opened by #16
PART-SCHEMA 2/2 local_1275553f (#759), INVENTORY-ARMS local_197a5c5c, MCP-MAP local_bf111dae, LUCID-DAY-HUB-ACCEPT local_aaafc9b9 (#761), AI-STORE-GOAL-TEST local_0a6c7ff4 (Opus, plan only; its gap table goes to conductor 010 for AI-STORE-GAP-FIXES), CI-OVERFLOW, ARM-SENDS-DOORS 2/2. All are #16's side sessions; detach is refused for chips.

## Next
Claim, then the queue: open ATLAS-ESTATE-LAYER, ATLAS-AGENTS-LAYER (NODE), INVENTORY-HUB (after #730), ACT-USERMODE (after #713) and OPS-BRIDGE (NODE, design only, q220 = A). Route /goal/atlas wiring to SURFACE once #736 lands. LUCID-DAY-RECURRING (SENSORS) only after #761 merges and rows land.

## Owner items
q208 (server purchase, optional). Yes typed in desk chats: FLAGS (q227), LUCID (q228), CI-OVERFLOW (test.yml), plus older ones: COMMS q211, VAULT-RAW q210, SENSOR-REG q218. Next free card q231.

## Gotchas
- Start hub desks with cwd F:\Leadfuel\repos\novahub, not F:\Leadfuel: an edit hook blocks cross-worktree edits.
- Chips land in the ROUTER group: move each one and set its model.
- The LUCID-DAY-SUBMIT worktree has unpushed "DO NOT PUSH" estate commits. Do not archive it.
- Archive owed: ROUTER #14 local_34998bfa (after its ATLAS chip desks finish). Keep #11, #12, #13 and conductor 005.
