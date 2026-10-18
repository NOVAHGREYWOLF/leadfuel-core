# Handoff: SURFACE · leadfuel.cloud website part · 2

Session local_a2eff090-9ff2-4a61-b67a-a5bc96b8ceae (slot run way-slot-06), 2026-10-18. Router: ROUTER #68 local_df21a1a1-5520-4025-9cda-c831f10cc12c. Predecessor: part 1 local_c164e7c8-d30f-417d-82d1-7d30d5dd6834.

## State (re-read before acting; do not trust these lines)
- Hub PR NOVAHGREYWOLF/novahub#885, draft, branch surface/home-novahos, head 91fc7681 at handoff. Worktree F:/Leadfuel/repos/novahub/.claude/worktrees/surface-home-novahos.
- Built from mockup 2 (artifact 8kKEcqhuGqJTwQST7oErAu). Renders only on novahos hosts and only with HOME_NOVAHOS (owner card q570: site goes on novahos.com). Neutral placeholders per q567 = B. Claims softened per q564 = B. DESIGN review: F:\Claude Sessions\handoff\leadfuel-website-rebuild\DESIGN-REVIEW-885.md (read head a979efb7).
- Gates at 91fc7681: SKIP_TESTS gates 14/16 green, 12 tests pass.

## Done last
Host routing for novahos.com, DESIGN must-haves (sample chip, dead keys removed, softened headlines, no city), docs/NOVAHOS_COM_GOLIVE.md (production steps, prepared not run).

## Next (not done)
- STATUS to ROUTER #68 for head 91fc7681 (sent by part 2 at handoff; confirm it landed).
- DESIGN review of the new head (host routing and must-haves) if the router wants one.
- Open items in the runbook's last section: server-render content for crawlers, og:image/JSON-LD/favicons, tap targets and aria, robots/sitemap scoping on the novahos host, retake real-screen images.
- Production steps need the owner's typed go; none was run. Trademark check still open.

## Gotchas
- Slot run: use PowerShell for git; report with mcp__ccd_session_mgmt__send_message. The app's local server for captures: scratchpad serve.py (fake account via auth.current_account), nothing committed.
- PowerShell here-strings break on triple quotes; write Python edit scripts to files.
