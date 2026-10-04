# Access inventory (verified 2026-10-01 by router #2; no secrets, names only)

Checked from a cloud session in env_01Vkn9CZfpoTrsp5mrW69qFx (the only environment).

| Program | Reachable from a cloud session? | How | Notes |
|---|---|---|---|
| GitHub (leadfuel-core) | YES | github MCP + git | other repos need add_repo (hub = literal repo `novahub`, signal, scope, reach, lucid, orbit, novahos work) |
| Claude Code Remote (sessions, routines) | YES | claude-code-remote MCP | child -> router send_message is blocked by a permission prompt; use pull |
| Artifact board (A4uS9xn1emqupohdE4DUfV) | YES | ArtifactData | |
| hub brain | YES | connector | no Railway actions in its catalog (61 actions: odyssey, reach, signal, scope, orbit, echo, lucid, self, prospect, qbo) |
| Gmail, Microsoft 365 | YES | connectors | |
| Apollo.io | NO | connector needs authorization | |
| Railway | NO | no connector, no token | CLI installs fine but `railway whoami` = Unauthorized. Needs RAILWAY_API_TOKEN in the environment settings. Project LeadfuelBusinessSuites, production |
| Routine-fired sessions | NO connectors | claude.ai routines UI | connectors must be added to each routine by the owner |

## To get Railway (owner, one time)
1. Create a Railway API token (project token for LeadfuelBusinessSuites / production is safest).
2. Add it in the environment settings (cloud environment menu, Edit) as RAILWAY_API_TOKEN. Never paste it in chat.
3. Start a new session. It can `npm i -g @railway/cli` and run `railway variable set ... --service <name>`.

Earlier sessions (G4, G5, G6) never touched Railway; the owner ran it from their own PC (railway 5.43.1, `railway link`).
