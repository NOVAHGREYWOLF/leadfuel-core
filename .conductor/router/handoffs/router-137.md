# ROUTER #137 · novah estate: HANDOFF at the 300k point (2026-11-23, about 17:5x PT; 304k tokens by get_usage, verified)
Session local_845fc055-c6e1-47ec-9d00-18656510b738, branch claude/router-137 (cut from claude/router-136 eb67ee4). Predecessors: #136 local_22102ccc-2608-40f3-adf6-3f4bf45a7353 (ARCHIVED by me through the gate), #135 local_e039c5ab-d12b-49a5-a566-2b876238eb64 (archive refused: Remote Control attached; handoff afcf680 pushed, worktree clean; owner can archive it from the sidebar). Conductor 060 local_21c3e030-71d7-4ae9-aefe-5a4886ccf22a (confirmed: hold lifted, cap 25, keep refilling at 20 per process, no second router for the extra 5, do not touch CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS, STATUS to 060 only on a change or a block). All state lines are claims unless marked verified: re-read live state first.

## Owner word (typed, relayed by 060)
"I just want you to code. why cant you push every desk to its max and just go." Policy cap 25; the app refuses a 21st subagent in one process (error "You can run 20 subagents at once").

## What #137 left running (agents live in MY process and DIE if I am archived or rotate: I stay open and only drain them)
20 agents, ids and tasks in F:\Claude Sessions\handoff\ROUTER-137\ROSTER.md (parts 58-79; fold-s-prime first). Their reports arrive as task notifications to me (#137). Count live ones with ListAgents. Reports so far: NODE 61 mail2-38 (finished, report pending), ARMS 77 desks-3-4 DONE no PR (fix already on hub main as PR 1134, verified with gh), NODE 65 merge train interim only.

## For the successor (#138): you open all NEW work; do not touch my agents
- Cap rule: 25 total counting mine. While mine run, open at most 5; fill up to 20 in your own process as mine report (CPU on GREYWOLF was 100% at 24-28 claude.exe; if a test job stalls, drop back and tell 060).
- Brief pattern: F:\Claude Sessions\handoff\ROUTER-137\BRIEF-COMMON.md + RULES.md (ROUTER-135). Roster pattern: ROSTER.md.
- Waiting briefs (not started): W06 Fieldy local embedding + insight layer (INTELLIGENCE, code only, bulk pass not run); LAB Character Design rename (F:\video\ai); INTELLIGENCE residual from ARMS 77 (live send in app.py drops a failing attachment without naming it; agent claim); then C10 signal 13, K14/K13 scoping, mail-2 scoping, p16-4 count guard (heavy lock), fold-a-phone Browser look, G36 backend (owner mockup approval first). After hub 1121 lands (author merges, head 9833542a verified re-review APPROVE): lucid-health hub half, hub 1123 rebase (CONFLICTING, verified), Steward 1124.
- Owner steps stay attached to the work they block (in ROSTER.md, router-136.md, router-135.md). Post no cards for anything that does not block code. P02 decision (remote phase0-dump pg session) and C11 drafts 62-64 close-or-port are parked with 060, not cards.
- When my agents have all reported (ListAgents shows none running), archive #137 through the gate (this note pushed, nothing unpushed).
