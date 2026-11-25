# NODE part 203: decision records for the B-class rows, and the next piece under each umbrella goal

Desk NODE, part 203, 2026-11-23 Pacific. True source: CONDUCTOR 061 relayed the owner's typed words of 2026-11-23 Pacific, "code everything you can ... dont stop full bypass mode", with defaults from `CONDUCTOR-061-owner-classification.csv`. A record here is a **default taken on his standing words**, not a new answer from him; he can overturn any line.

## Decision records

### mail2-14, first outside install (default: park until the installer is done)
**Status: parked, dated 2026-11-23.** An earlier plan said a first trial user would run the full install from a stick and then answer five questions. Whether the trial happened is not recorded anywhere I could find; a hand-out for it exists in the Surface offload (see `docs/SURFACE_OFFLOAD_REVIEW.md`), which shows the stick existed. **Not dropped.** When the installer work closes, one queue row follows: run the install on a machine that is not his and write down the five answers. The five questions as the plan gives them: the story, which half first, price, install friction, who else.
OWNER-STEP: say whether the trial happened | blocks: a dated line saying what became of it (the note above says "unknown").

### mail2-16, the two server handover packs (default: shelve both, no send)
**Status: shelved, nothing sent, 2026-11-23.** Two server handover packs were review copies and say nothing was sent. Both stay shelved. Not done and why: one pack still shows three decisions as open that are already made; correcting it means editing drafts this desk does not touch. The open hardware list, copied from the queue row, so it is not lost: firewall, per-person logins, RAID battery and cache policy, the memory-stick move, backups (now the PBS plan in `docs/OSS_PILOT_PLANS_COOLIFY_PBS.md`), and the update path. Handing any of it to a receiving team is a send and waits for him.

### webchat-19, hardware buys priced in web chats (default: buy nothing now)
**Decision: buy nothing now.** A hardware purchase (a lot of GPU cards and several rack servers) was priced in web chats and a sheet was made. This estate's GPU plan (W09) runs on the 8 GB card that overlord already has and on GREYWOLF's RTX 3070; the one model service (`node/model_service.json`) is the first thing that would show whether more GPU is the bottleneck. Revisit when W09's measurement (GREYWOLF load lower, one model answering through the router) exists. **I did not open the sheet** and filed no copy of it.

### fold-c-G03, name the one local model service (default: the overlord GPU service)
Built: [`node/model_service.json`](../node/model_service.json) and [`node/model_service.py`](../node/model_service.py), tests in `tests/test_model_service.py` (34 pass). The one address is `http://overlord:8080/v1` **as a proposal**: the port is llama-swap's default and the container (W09, CT 105) does not exist, so the service is listed `enabled: false`. Until then the file's interim entry is Ollama on GREYWOLF, allowed for the shell, refused for anything scheduled. No fallback to a vendor: with nothing usable the resolver exits 2 and says why. **Not duplicated:** PR 109 (NODE 174, cluster job rules) is job placement; this is model-address resolution. They share no file.
OWNER-STEP: after W09's container exists, run `python node/model_service.py probe overlord-gpu` on GREYWOLF, and if it lists a model, flip `enabled` to `true` | blocks: "the shell, the local hub and one other machine each get an answer from it".

### fold-c-jobrouter-build (default: approve design steps 2 and 3 as written)
Already built and open as draft PR [#96](https://github.com/NOVAHGREYWOLF/leadfuel-core/pull/96): `node/jobrouter/route.py` places one real job class (the standby refresh catch-up); a host with no fresh reading is never picked. Nothing for this desk to duplicate. Its own "not done": nothing runs on overlord yet and no job ran on a second machine (needs an ssh key from overlord).

### desks-2-1, local-only desk commits (default: bundle locally; the push route is a separate yes)
Git bundles of the estate repository's local-only history exist and were checked with `git bundle verify` (okay): one for the session-notes repo, one for all local branches not merged into the estate main (64 branches). The branch tips in the earlier bundle equal the current tips. Bundles hold git history only, not uncommitted files; I did not check any desk's dirty tree. The location is in the private estate notes, not here. The VAULT sync route (`push` is disabled by design) stays a separate yes.

## The next buildable piece under each umbrella (nothing umbrella-sized is built here)

| Umbrella | Next buildable piece | Why it is next | What stops it |
|---|---|---|---|
| **GOAL-CLUSTER** | A second job class, `model-call`, in `node/jobrouter/classes.json` that gets its host from `model_service.resolve(scheduled=True)` instead of its own list. | #96 places jobs, this PR names the model address; the goal's done-when needs "a job and a model call" through one router. | #96 must merge first (the merge train does that). Real run needs W09 and the owner's `enabled` flip. |
| **GOAL-ONEAPP** | The shell's Jobs tab: read `route.py status --json` and `log` and show "ran on <machine>". | It is the "usable inside NovahOS" line of the job router; the data exists once #96 merges. | #96 merging; shell files are `home-node/app` (NODE-owned). |
| **GOAL-NOVAHOS** | FD-1, device sessions on the hub (see `docs/FRONT_DOOR_DESIGN.md` section 4). | First-walk steps 2 and 9 cannot pass without a sign-in on two devices. | His approval of the front-door design from the mockup; the hub is shared, so a worktree and its own desk. |
