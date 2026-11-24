# SURFACE firstwalk: handoff 001 (fold-a-firstwalk and chats-2)

Written by the SURFACE background desk for ROUTER #135 at its size cap, 2026-11-23. Branch
`surface/firstwalk-checklist-smoke`. Ids and paths only. Re-read live state before acting; do not trust
the state lines below.

## What the task is
Build everything except the owner's walk: one checklist per room (steps, expected result, proof field), an
automated read-only smoke pass run against what answers locally, and a results file with honest unknowns.
Per-room results go as JSON to `F:\Claude Sessions\handoff\ROUTER-135\firstwalk\results.json` so the p16-1
scoreboard desk can read them. Draft PR only. Owner steps: the walk itself.

## Done on the branch (committed, not yet run end to end)
- `firstwalk/walk.json`: the data. 15 lines (L01 to L15, from PRIORITY-AND-DUPLICATES.md Part 3), 9 rooms
  (R01 to R09, line 3 split), 12 named things with built / partial / not built (N01 to N12, chats-2), 3 mockups
  (M1 original Atlas candidate, M2 in-depth command mock, M3 "mockup 3"). Each step has do, expect, proof.
- `firstwalk/smoke.py`: read-only, loopback-only smoke runner. Compiles; `python firstwalk/smoke.py controls`
  prints "controls ok". NOT yet run for real and NOT yet unit-tested.

## Still to do (in this order)
1. `firstwalk/render.py`: render `walk.json` to `docs/firstwalk/CHECKLIST.md` (per cell a table: Step, Do,
   Expected result, Result [ ] pass [ ] fail [ ] closed by design, Proof) and to a self-contained
   `docs/firstwalk/checklist.html` (radio per step, proof input, localStorage in try/catch, export button that
   writes `firstwalk.marks/1` JSON: `{"schema","exported_at","marks":{stepId:{state,proof,at}},"cells":{}}`).
   Also a named-things table (N01 to N12) and a mockups table. `--write` and `--check` (exit 1 on drift).
2. `tests/test_firstwalk_smoke.py` (load by path with importlib like `tests/test_vault_sync_status.py`):
   loopback guard refuses a non-loopback host before a socket; redirects are not followed; `run_controls`
   ok; an all-absent and an all-raising env give no `pass`; every check id in walk.json resolves (no "no such
   check"); `rollup()` rules; `load_marks` rejects a wrong schema; `visible_text` drops comments and keeps
   title attributes; `region_status`; render drift guard; walk.json shape (15 lines, 9 rooms, unique ids, every
   step has do/expect/proof, every cell's queue ids are strings).
3. Fix the two known loose ends in `smoke.py`: none known beyond running it. Run it for real:
   - `python -X utf8 -m lfdesk.install.acceptance --json` from `F:\Leadfuel\home-node\app` (NODE's read-only
     tool; use `python -B`) saved to a scratch file, pass as `--acceptance-json`.
   - `python watch/vault_sync_status.py` (WATCH's reader) saved, pass as `--vault-sync-json`.
   - Hub source: `MSYS_NO_PATHCONV=1 git -C F:/Leadfuel/repos/novahub archive origin/main
     templates/command_screen.html templates/_command_base.html static/command | tar -x -C <scratch>/hubsnap`,
     then `--hub-root <scratch>/hubsnap --hub-rev d8e63f74a122ab3a237b1bdb42fee1d3b10e98d4` (that is the local
     `origin/main` as last fetched, 2026-11-23T12:37-08:00; the checkout's own `main` is 36 behind).
   - `--artifacts-root "F:\Claude Sessions\Document Library\artifacts"`, `--library-root "F:\Claude Sessions\Document Library"`,
     `--doc04 "F:\novahos-handoff\novahos-handoff\docs\04-command-center-and-document-map.md"`, `--model-call`
     (one tiny loopback chat; unloads the model), `--out "F:\Claude Sessions\handoff\ROUTER-135\firstwalk\results.json"`.
4. Fix N01 and N04 evidence text in `walk.json` to match what the page's own Start menu says (32 entries:
   12 built, 15 partly, 5 not built: needs, leads, log, crew, contracts; oracle says built). Then re-render.
5. chats-2 outputs to `F:\Claude Sessions\handoff\ROUTER-135\chats-2\`: `NOT-BUILT-ROWS.json` listing each
   named thing not built or partial with a proposed queue stub (id, title, lane, done_when) for the router.
   The agent cannot open desks.
6. `SKIP_TESTS=1 sh scripts/gates.sh` does not exist in this repo (no scripts/gates.sh; checked). CI is
   `.github/workflows/test.yml`, bare `pytest`. Run only `tests/test_firstwalk_smoke.py` locally with
   `python -m pytest tests/test_firstwalk_smoke.py -q`. No full pytest.
7. Update the draft PR body: what was verified by this desk, what was taken on trust, and the OWNER-STEP.

## Findings so far (this desk read them itself on 2026-11-23; ids and counts only)
- Local hub on 127.0.0.1:8080 answers `/healthz` (ok). Its `/command` answers 302 to the production sign-in
  page (`leadfuel.cloud/login`), not followed; its own `/login` answers 503 "login not enabled". Signed-out
  `/api/command/{feed,character,atlas}` answer 401. So `/command` cannot be opened on the node itself today.
- Local MCP on 8787 `/health` ok. Ollama on 11434 up with 12 models, chat-capable ones included.
  ComfyUI on 8188 up. Postgres has live connections (docker `novahub-pg` up). The window's route on 8766
  answers JSON 404 for an unknown path.
- Character Design on 8760: nothing listening (acceptance row `chardesign.api` also fails: "start it from the
  pane"). Prime dashboard on 8765: listening, no answer in 20 s (unknown, not down).
- Phone chat host: listening on the machine's tailnet address, port 8106 (netstat). A paired phone reaching it
  is not read.
- NODE acceptance run (31 rows): 20 pass, 7 fail, 4 unknown. Fails: `shell.one_ai_entry` (other AI icons:
  Character Design, Decompress, Hermes, LM Studio, Ollama, Open WebUI), `openwebui.chats_imported`,
  `openwebui.web_search_carried`, `hermes.memories_imported`, `prime.services_off_prime`,
  `prime.voice_interpreter`, `chardesign.api`.
- WATCH vault-sync reader: state `failed`, exit 3 ("an excluded path or a big blob survived the filter;
  nothing pushed"), last end 2026-11-23T11:52:18Z. That is walk line 13's off-machine copy.
- Hub `templates/command_screen.html` at origin/main: six of doc 04's eight regions have template ids
  (Character, Action Feed, Mission Board, Crews as party and regions, Resources, Radar); Contracts and Log
  are declared "not built" by the page's own Start menu. The five "stage N" or "not wired yet" matches in
  the template are all inside comments; visible text has none.
- Mockups: M3 "mockup 3" = artifact `6ye3qLYh8LDhDT4CX3WVGL` (named by an assistant in session 1e44a1 on
  2026-10-27, owner approved after); M2 = `TL21cZ8Bh5GnKixuQFjwaM` (best match named 2026-10-15; owner did not
  confirm it in the lines read); M1 candidates `UCCG9zfCDWeveQMuT1MFZ5` (Flow Atlas) and
  `6LEvF7K9u9qnSxh68VWsfA` (Atlas Live). All have saved pages in the Document Library artifacts folder.

## Owner steps this work needs (name them in the final report; no questions)
- OWNER-STEP: walk lines L01 to L15 and rooms R01 to R09 in `docs/firstwalk/checklist.html` and export the
  marks file | blocks: every walk_state leaving "not tested" on the p16-1 scoreboard.
- OWNER-STEP: confirm which Atlas is "the original" (step R02.4) and that M2 is the in-depth mock | blocks:
  chats-2's "links to the mockup it came from".

## Rules that held
No production read, no vendor call, no egress: every probe is loopback; redirects not followed. The only
non-loopback fact (the redirect target host) was read from a header, never followed. Nothing was written
outside the worktree except this desk's own results under ROUTER-135 (not yet written).
