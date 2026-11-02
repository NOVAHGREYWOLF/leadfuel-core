# Handoff: NODE · home node part · 3 (session local_8238872c-331e-4b21-8dde-cc8823009de6)

Successor title: `NODE · home node part · 4`, group `home node`. Written 2026-10-31 (Pacific). Ids only.

## Done
- Diagnosed Ollama, Hermes and Open WebUI on the home PC. Findings are in the local memory note
  `reference_local_ai_stack_ollama_hermes_openwebui.md` (not in the repo).
- Hermes `model.default` is now `qwen3-64k:4b`: an Ollama variant of `qwen3:4b-instruct-2507-q8_0` with
  `PARAMETER num_ctx 65536`, plus `model.ollama_num_ctx: 65536`. `mistral-64k:7b` is also installed, untested
  beyond its native 32768. Originals of the Hermes config are kept in the old session's scratchpad.
- Measured 2026-10-31 12:09-12:17 PT, box idle: `ollama ps` CONTEXT 65536, 14 GB, 59%/41% CPU/GPU; Hermes sent the
  full 14,095-token prompt; 0 truncation warnings; cold one-shot 301.9 s wall.

## State (verified by me at 12:17 PT; the successor re-reads)
- Ollama 0.40.11 up, owned by the node supervisor; no `replay_local.py` jobs; no Ollama clients.
- Open WebUI on 8081: UP since 2026-10-31 12:51 PT (started on the owner's "yes", PID 33700 then): health 200,
  onboarding empty, sign-up off, listener 127.0.0.1 only, real data. Saved config (read from a DB copy): Ollama
  enabled at `http://localhost:11434`; OpenAI enabled but 0 keys set. UNSUPERVISED: it will not survive a reboot or
  logoff (the previous launch died in the 10/26 reboot). Cold start took 12 minutes under load.
- Hermes gateway: not running (the test stops what it spawns).
- Not verified: Open WebUI listing Ollama's models (needs a login).

## Next
Nothing is owed by the owner for this task. Optional only: tell NODE that Open WebUI is not in `services.json`.
If it is down after a reboot, relaunch it as below (this is how it was done, not a pending order). Launch the pip `open_webui` package through `python.exe` (the `open-webui.exe` shim is blocked by Application
Control): argv `serve --host 127.0.0.1 --port 8081`, cwd the user profile (holds `.webui_secret_key`),
`DATA_DIR` = the desktop app's data folder (NOT the pip default, which is an empty database), `OFFLINE_MODE=true`,
`HF_HUB_OFFLINE=1`, telemetry and update checks off. Cold start takes 2-5 minutes. Confirm `/api/config`
shows no onboarding. Then note to NODE: Open WebUI is not in `services.json`, so it dies on every reboot.

## Owed
- Nothing pending on the restart (done). Tray-app-versus-supervisor Ollama startup conflict (`Ollama.lnk`) is
  undecided. Not verified: Open WebUI actually listing Ollama's models (needs a login).
- No handoff messages were sent to other sessions.

## FINAL STATE 2026-11-02 (supersedes everything below; nothing is owed to this desk, no successor needed)
- Owner reversed Open WebUI the same evening ("We don't want it. Everything is going to be Navahos"). It is OUT:
  the `open-webui` entry is gone from the live manifest (backup kept by part 7), its launcher is stopped, port 8081
  refuses (I checked with Ollama on 11434 as the positive control), the HKCU Run value is gone, one supervisor
  runs. Its data folder (one account, three chats) was left untouched. Supervisor support code is merged in
  `main` of the estate checkout (`55c9aba`), local only: push is disabled there by design (VAULT sync).
- Ollama stays the model server (0.40.11, supervisor-owned). Hermes default is `qwen3-64k:4b` (verified: ctx 65536,
  no truncation). Hermes always-on gateway: part 7 recommends leaving it OFF (it would poll catalogs and the Gamma
  and Hugging Face MCP servers outward, a Law 9 question). Owner has not said whether Hermes itself stays.
- Child sessions: part 4 `local_2dc2a18a-14e7-4e5b-9a5f-e6c8e3684a61` (done), part 7
  `local_42bcb22f-be9a-4ad2-8540-b5a9144d8ab4` (done). Part 7 then started an installer chain not ordered by me:
  parts 9 `local_31634206-5531-4e98-b21d-895d0d411a1d`, 10 `local_d14ab79f-2a7a-48c2-beb4-345143be8d74`,
  11 `local_5273a556-88ed-423b-95dd-0e343b1d8ab9`. That work belongs to `ROUTER #113 · one-app`. Part 11's
  branch `claude/node-ship-installer-11-1bc1e7` is NOT in `main`; nothing of mine merges it.
- Remaining NovahOS work (chat front end on Ollama in the Home Node window) is a new task for the one-app router.

## Update 2026-10-31 15:40 PT (older; superseded by the final state above)
- Owner decision, in chat to this session: "all of these things should be running from my NovahOS app. we dont
  need any of the other apps. they will run in background." Direction: headless services owned by the NovahOS
  supervisor; no tray or standalone-app windows. Embed-vs-replace for Hermes/Open WebUI panes is still undecided.
- This session started desk `local_2dc2a18a-14e7-4e5b-9a5f-e6c8e3684a61` (NODE · home node part · 4) for it. It
  has handed off at its cap; its note is `.conductor/desks/handoffs/home-node-4-001.md` on branch
  `claude/node-services-persist-345b07` (local only: push is disabled in that repo by design, VAULT sync).
  Built and tested on a spare port, NOT live: the live manifest is unedited, no reboot test yet.
- Owner decisions still owed to desk 4's successor: disable the Open WebUI desktop app's HKCU Run value (export
  to `.reg` first); any always-on Hermes gateway; a reboot test. No successor desk is running.

## Gotchas
- `Ollama\server.log` goes stale when the supervisor starts the server; the live log is the supervisor's
  `ollama.log`. A check on the stale file returned 0 and looked like a pass.
- Another desk's `replay_local.py --no-lock` jobs take Ollama's only slot; test only when none is alive.
- Never kill the Ollama server (auto mode refuses; it is not this desk's process).
- `hermes -z` can miss its gateway-start deadline (85-114 s); retry once.
