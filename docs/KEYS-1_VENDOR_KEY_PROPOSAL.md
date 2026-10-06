# KEYS-1: classify leftover vendor-key variables (proposal, nothing changed)

Source: owner's yes on Router card Q51; G8 desk's names-only audit of Railway project
LeadfuelBusinessSuites, env production. **Read-only.** Variable names and service names only; no value
was printed or stored. Comparisons were done by SHA-256 inside one process that printed yes/no.
2026-10-02 (UTC).

## Method (what I verified myself)
- Pulled production variables per service with `railway variables --json` into a script that held them
  in memory and printed only: prefix class (`tok_`, `sk-ant-`, `sk-`), length bucket, and boolean
  equality against (a) the key set of hub's `LLM_GATEWAY_TOKENS` table, (b) hub's own
  `ANTHROPIC_API_KEY`, (c) the service's other variables.
- Read who reads each name with `rg` in the local checkouts (main/default branches; one worktree branch
  for lucid, so treat lucid code as verified-on-that-branch). Not verified: the deployed commit of each service.

## Findings

| Variable | Service(s) | Is it | Read by code? |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | icp (SMART ICP), odyssey, odyssey-cron, lucid, echo, NovaHound (signal), NovaHawk, NovaHerald, web (leadfuel-intake) | **Gateway token.** Each value is a key of hub's token table and maps to that service's own name (9/9 yes). None equals hub's vendor key. | **Yes, live.** The Anthropic SDK / litellm reads it as the api key (`signal/config.py`, `scope/agent.py`, `agents.py`, `extractor.py`, `lucid`, `echo`). |
| `ANTHROPIC_BASE_URL` | same 9 | Gateway URL (`leadfuel.cloud/llm`), not secret. | **Yes, live.** Without it the SDK's default is a direct call to the vendor, with a gateway token that would 401. |
| `ANTHROPIC_KEY_PREGATEWAY_BACKUP` | lucid, NovaHound | **A real vendor key.** Starts `sk-ant-`, and its hash **equals hub's `ANTHROPIC_API_KEY`** (yes on both). Not in the token table. | **No.** Zero hits in any repo, doc or worktree under F:\Leadfuel. Nothing reads it. |
| `OPENAI_API_KEY` | web (leadfuel-intake / scope) | **A real vendor key shape** (`sk-`). Very short (<20 chars), so possibly a placeholder; I cannot tell without testing it, which I did not do. | **Yes.** `scope/app.py` uses it to mint OpenAI Realtime tokens for voice intake and to show the mic button. It goes straight to api.openai.com, not through the gateway. |
| `ANTHROPIC_API_KEY` | hub (NovaHub) | **The real vendor key.** Not in the token table. | Yes: the gateway itself (`llm_gateway.py` refuses with 503 without it). **Keep.** |
| `ANTHROPIC_ADMIN_KEY` | hub | Real admin key. | Yes: `admin_costs.py`, `spend_reconcile.py`, cron heartbeat. **Keep.** |

Also set on the nine callers: `LLM_GATEWAY_TOKEN` and `LLM_GATEWAY_URL` (the newer names). The services
still carry **both** the old SDK names and the new ones. That is why the first two rows must not be removed yet.

## Proposal

**P1. Remove `ANTHROPIC_KEY_PREGATEWAY_BACKUP` from lucid and NovaHound.** (Recommended, do first.)
- Why safe: no code reads it. It duplicates the live hub vendor key, so it is two extra copies of a
  credential sitting on services that are supposed never to hold one (lucid's own `config.py` says so).
- Rollback: none needed for function. The value is identical to hub's `ANTHROPIC_API_KEY`, so nothing is
  lost. If anyone wanted it back, copy from hub.
- Order: unset one service, redeploy not required for a variable no code reads, but Railway redeploys on
  variable change; do lucid, check `/healthz`, then NovaHound.
- Needs the owner's yes (a production change). **Not** the same word as the `ANTHROPIC_API_KEY` rule below.
- Follow-up question for the owner: the vendor key was exposed to those two services' env and logs-reach
  for however long; rotating the hub key afterwards is worth considering. Not proposed here.

**P2. Leave `ANTHROPIC_API_KEY` and `ANTHROPIC_BASE_URL` on the nine callers alone for now.** They are gateway
tokens, so they are not a vendor-key leak, but they are what the code reads. Removing them breaks every model
caller. The only safe future removal is a rename: make each service read `LLM_GATEWAY_TOKEN` /
`LLM_GATEWAY_URL` (code change per desk, DOORS/ARMS lane), prove it in staging, then drop the old pair.
**ANTHROPIC_API_KEY must not be deleted by anyone without the owner's explicit word for that step.**
Rollback for any future removal: re-set the variable from hub's token table entry for that service.

**P3. `OPENAI_API_KEY` on web: owner decision, do not remove.** It is a live Law 9 egress path
(voice intake) that bypasses the gateway. Options: (A) keep as is; (B) unset it, which hides the mic
button and is reversible by re-setting the key; (C) route voice through a gate. Default A until the owner chooses.
Check first whether the value is a real key: the short length suggests it may already be a dead
placeholder, in which case (B) costs nothing.

**P4. hub's `ANTHROPIC_API_KEY` and `ANTHROPIC_ADMIN_KEY`:** expected for the gateway. No change.

## Not checked
- Whether `novahub-cron-*`, APOLLO and novahub-mcp hold any of these: they had none of the names.
- Whether the hub vendor key is still valid at Anthropic (no call made).
- Deployed commits of each service (read local checkouts only).
