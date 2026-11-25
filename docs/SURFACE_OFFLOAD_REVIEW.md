# The Surface offload folder: one line per document (p16-6)

Desk NODE, part 203, 2026-11-23 Pacific. Folder read: the Surface offload folder (55 files, all stamped 2026-11-19 by the copy; the real dates are the ones the documents carry). Read-only. **Nothing was copied, moved, quoted from the private files, or deleted.**

How strong each verdict is: **built** means a file of the matching name exists in `F:\Leadfuel\repos\novahub` main (I checked the name, not the behaviour, and did not read the hub file). **Open** means the document holds an ask I could not find queued (searched `QUEUE-v2.json`, `LIBRARY.md`, `CONNECTIONS.md`, `ONEDRIVE-F-SWEEP.md`). I read the first lines of each estate document, not the whole of any.

## Estate documents (25)

| Document | Written | Verdict |
|---|---|---|
| TODAY_GOALS_IDOR_HANDOFF.md | 2026-06-30 | Overtaken: the queue row for this sweep says its fix is on hub main (commit e5322676, merge 9ea08a0f, 2026-07-01). Taken on trust from that row; I did not check the commit. |
| DATA_FLOW_REAUDIT_2026-07-01.md | 2026-07-01 | **Open, check it.** Two acute risks; the IDOR one is the handoff above. The second, `/api/self` honouring a client-sent `include_sensitive=1` with no wall, I did not verify as fixed. Proposed queue line: re-read `/api/self` on hub main against this finding. |
| TEAMS_BOT_SETUP.md | date not read | Overtaken: byte-identical copy is already in the hub at `docs/TEAMS_BOT_SETUP.md`, and `teams_bot.py` exists. Its Azure registration step is the owner's and is already indexed in `LIBRARY.md`. |
| CONNECTORS_MCP_TEAMS_PLAN.md | 2026-07-17 | Built: `mcp_client.py` and `teams_bot.py` exist in the hub. |
| CONNECTOR_OAUTH_STATUS.md | 2026-07-01 | Already in the queue (`QUEUE-v2.json`, `LIBRARY.md`); `oauth_as.py` exists. States OAuth is merged but dormant. |
| UNIVERSAL_CONNECTOR_PLAN.md | 2026-06-30 | Partly built (`oauth_as.py`, the MCP). The public listing, billing and multi-tenant parts: **open, no queue line.** Proposed: one scope item for "list the connector in the AI directories". Needs his word because listing is public. |
| MCP_PARITY_PLAN.md | 2026-06-30 | Probably overtaken by the MCP work since; I did not check tool by tool. Unverified. |
| MAIL_OAUTH_VERIFICATION_RUNBOOK.md | 2026-06-26 | **Open ask nobody queued**: what Google's restricted-scope review and Microsoft's verification take to read and send mail. No queue row mentions it. Owner-only (a provider application). |
| MS365_CONNECT_RUNBOOK.md | 2026-06-26 | Indexed in `LIBRARY.md`; its Azure steps are the owner's. Same family as the row above. |
| LINKEDIN_DM_CHANNEL_PLAN.md | 2026-06-26 | Overtaken: Batch 3's own text says the LinkedIn-via-Unipile path already existed, and `unipile_client.py` is in the hub. |
| CONDUCTOR_BATCH3_EDIT_PLAN.md | date not read | Built: `unipile_client.py`. |
| CONDUCTOR_BATCH4_EDIT_PLAN.md | date not read | Built: `prospector.py` (the "Scout"). |
| NOVAHPRIME_CONDUCTOR_ARCHITECTURE.md | 2026-07-01 | Built in part: `goal_plan.py`, `book_conductor.py`, `conductor_caps.py` exist. |
| NOVAHPRIME_CONDUCTOR_BUILD_PLAN.md | date not read | Same as above; the plan's Batch 0 "safety spine" status I did not check. |
| NOVAHPRIME_ACTIVATION_RUNBOOK.md | date not read | **Open owner steps**: it is the list of env flags that turn the dormant conductor on. Nobody queued it, and setting production variables is his. |
| BRAIN_TAG_TAXONOMY_PLAN.md | 2026-07-07 | Probably overtaken (the hub's brain code uses facets, 213 matches), but its section 10 decisions were not checked. Unverified. |
| DOSSIER_GENIUS_REDESIGN.md | date not read | `command_dossier.py` exists; whether the redesign landed is unknown. No queue row. |
| DOSSIER_REDESIGN_APPENDIX.md | date not read | Raw lens notes behind the row above. Reference only. |
| LIFE_ECHO_STEP4_BUILD_SPEC.md | 2026-06-26 | `self_infer.py` exists; the sign-up to $19.99 unlock flow is unchecked. Pricing text is his to confirm. |
| echo-launch-calendar.md | date not read | Superseded by the FINAL below. |
| echo-launch-calendar-FINAL.md | date not read | Already in the queue (`QUEUE-v2.json`). 90 posts; posting any of them is his (Law 9). |
| USB-README.md | date not read | **Not indexed anywhere.** The hand-out of the NovahOS USB trial; ties to queue item `mail2-14` (parked, see `NODE_PART203_DECISION_RECORDS.md`). |
| fleet-setup-log.txt | 2026-11-01 | A PowerShell transcript of the Surface setup. No ask. |
| greywolf-setup-log.txt | 2026-11-01 | Same. No ask. |
| clone-all.txt | n/a | Empty file. |

## Private or secret-bearing: counted by category, not read (30)

30 files: client and business files (14), meeting and personal files (4), a creative project outside the estate queue (9), and secret-bearing or identity material (5, of which 3 are public keys). None was opened, quoted or copied. The per-file list is kept in the private estate repo, not here. **Advice, not done:** secret-bearing material should not sit in a Documents folder; it belongs in the password manager.

## Result against the done-when
One line per document: yes (above). **Overtaken or built:** 12. **Open with a proposed queue line:** DATA_FLOW_REAUDIT (re-check `/api/self`), UNIVERSAL_CONNECTOR_PLAN (listing), MAIL_OAUTH_VERIFICATION_RUNBOOK (provider review), NOVAHPRIME_ACTIVATION_RUNBOOK (env flags), USB-README (trial hand-out). **Unverified:** MCP_PARITY_PLAN, BRAIN_TAG_TAXONOMY_PLAN, DOSSIER_GENIUS_REDESIGN, LIFE_ECHO_STEP4 and the two conductor plans' completeness. The desk's own earlier count was 39; this folder has 55 files.
