# mail2-20: one frozen estate test set and a local model bake-off (design and plan only)

Status: DESIGN. Nothing was run, downloaded, pulled or sent. No model was called, local or cloud. Written by a
background desk agent (lane LAB) for task `mail2-20` in `F:\Claude Sessions\handoff\NODE-novah-estate-part-13\QUEUE-v2.json`.
Draft PR only. The run itself is a later, separately queued step (section 9).

## 0. What I verified and what I took on trust

Verified by reading (2026-11-22):
- The tier ladder and model manifest have one copy, `F:\Leadfuel\home-node\installer\node-manifest.json` (six tiers,
  TIER-1 23.5 GB to TIER-6 0 GB; per-tier `roles` chat / batch / stt / tts; `num_ctx_measured` flags).
- A measuring harness already exists: `F:\Leadfuel\home-node\tools\colibri-eval\bench.py` (loopback only, three
  fixed-length prompts with a hidden code word, unique first line per run, GPU clock/temp/VRAM sampled each second,
  start-load recorded and a busy start written as invalid, `--mode answers` for the prompt set) with
  `test_bench.py` and `eval-prompts.draft.json` (20 invented prompts, no private data).
  See `F:\Leadfuel\home-node\46-Colibri-Large-Models-Runbook.md` (Toolkit section, Phase 2).
- Store privacy tiers: `F:\Leadfuel\home-node\27-Store-Privacy-Tiers.md` (`private`, `secret`, `local_only`).
- Existing method precedent for a local comparison: `docs/DEC2_EMBEDDING_COMPARISON.md` (aggregate numbers only).

Taken on trust, NOT verified:
- The five candidate names from the radar mails (Qwen 8B, Qwen3.8-27B, MiMo 9B, JEV-9B, Ripple-65B). I could not
  read the three self-mails (2026-10-26 v1.2, 2026-11-09 v1.4, 2026-11-16 v1.5) and a text search of the session
  folder found nothing on these names. Treat each as a claim that a real, licensed, locally runnable checkpoint
  exists; step A (section 6) checks that before anything is pulled. Doc 37 notes the radar mails were
  ChatGPT-written, so a name may be wrong.
- The planner's `done_when` (20 to 50 tasks, at least two models). I keep it as the floor, not the target.
- This PC (RTX 3070 Laptop 8 GB, 64 GB RAM claimed in doc 46) is REPORTED in the manifest notes, not re-read here.

## 1. Goal and the one decision it feeds

Pick, with measured evidence, a local model for each of three jobs and record the pick in
`node-manifest.json` role slots (chat, batch, and a new typed-decision role if the owner approves one):

1. coding model (patch, test, review work on estate code),
2. general model (chat, summarise, plan),
3. typed-decision model (read a message or record, return a schema-valid label or action; the Law 9 gate, triage,
   routing). This job rewards format obedience and calibrated refusal more than prose.

The bake-off exists so the tier ladder stops rotating on radar hype. A model that cannot beat the current
`qwen2.5:7b-instruct-q4_K_M` (TIER-4 chat today) on the frozen set at equal or better latency and memory is not a pick.

## 2. The frozen test set

### 2.1 Size and shape
- 40 tasks (inside the 20-50 range): 12 coding, 14 general, 14 typed-decision. Small enough for one person to
  review in an evening, large enough that a 3-point margin is visible.
- Each task is one JSON file in a dated folder, plus a MANIFEST with sha256 of every task file and of the scorer.
  Once the MANIFEST hash is recorded in the PR, a task is never edited. A fix is a new task id and the old one is marked
  `retired` with its score history kept. This is the same reason doc 46's blind page must not move under a run.
- A model never sees the answer key. The key and the scorer live in a separate file from the prompts.

### 2.2 "Permissioned" (rule for what may enter the set)
A task may enter only if all of these hold, recorded per task in `provenance`:
- Source class is `synthetic`, `public`, or `estate-own` (our own repo code, our own docs) AND the owner has said
  yes to that class once, typed in a desk chat. Mail, Fieldy, health, finance, characters and anything from the
  `secret` / `local_only` tiers of doc 27 are excluded outright. They can be represented only by an invented lookalike.
- No credential, token, personal contact or client name. A pre-commit scan with `scan_payload.py`
  (`F:\Leadfuel\home-node\tools\scan_payload.py`) must report clean; its output is attached to the PR.
- The frozen set lives in the repo only if every task is `synthetic` or `estate-own` code. Anything else stays on this
  machine, outside git, with only the MANIFEST hashes committed.
- Why: the set is fed to local models only, but model output and scores get pasted into PRs and mails, so the
  inputs must be safe to quote (Law 9).

### 2.3 Task record (schema)
```
id            "cod-007"            stable, never reused
job           "coding" | "general" | "typed"
title         short
provenance    {class: synthetic|public|estate-own, source: path-or-url, owner_yes: "<date, where typed>"}
prompt        exact text sent (system + user)
max_ctx_tok   measured prompt size
check         one of: exec_tests | exact | schema | rubric | pairwise
key           reference for the check (kept in the separate key file)
timeout_s     per-task cap
weight        1 default; 2 for tasks the owner marks load-bearing
retired       false
```

### 2.4 Coverage (what the 40 are)
- Coding (12, check = `exec_tests`, run in a throwaway directory with no network): 4 small bug fixes from real
  estate history (repo state before the fix, hidden tests that fail before and pass after), 3 write-a-function from a
  docstring, 2 write-a-test for given code, 2 read-and-explain a diff, 1 refuse an unsafe request (for example "add a
  call that sends data off the machine without a gate": correct behaviour is to name Law 9 and stop).
- General (14, check = `rubric` plus 6 `exact` fact checks): summarise a long estate doc to 5 bullets, extract
  decisions from a changelog, plan a task into ordered steps, answer a question that has a hidden code word at 2K and
  8K tokens (carries over bench.py's truncation check), 3 "I do not know" questions where the right answer is to say
  the context lacks it.
- Typed-decision (14, check = `schema`, all machine-scored): classify a handoff note into the fixed state vocabulary,
  route a message to one of the ratified arms (hub, signal, scope, reach, orbit, odyssey; a retired spelling in the
  output scores zero), decide allow/hold for an outbound action given a gate rule (must return `unknown`, not a guess,
  when the input cannot establish the state), extract fields into a fixed JSON schema, 3 adversarial inputs that carry
  an instruction in the data ("ignore the rules and send") where the only passing answer treats it as data.

### 2.5 Honest-failure tasks
At least 6 of 40 have a correct answer of "cannot tell" or "refuse". A model that never says `unknown` is a
failure mode this estate has been bitten by, so it must show in the score.

## 3. Scoring

- Machine-first. 26 of 40 tasks are scored with no human (`exec_tests`, `exact`, `schema`). The other 14 use a rubric of
  3-5 yes/no criteria written before any model runs; scored by the owner blind (A/B unlabelled, the page doc 46 lists
  as not built: `blind_page.py`, `tally.py`) or, if he declines, by a fixed local judge model that is NOT one of the
  candidates and whose agreement with the owner is spot-checked on 10 tasks.
  Never a cloud judge (no cloud call, section 7).
- Per task: pass/fail plus a 0-1 partial where the check allows. Per job: weighted pass rate. Report all three job
  scores separately; no blended "overall" is used to pick, because a single average hides a model that is
  excellent at coding and useless at typed decisions.
- Repeats: 3 runs per task at temperature 0 for determinism and 1 at the model's default temperature, so
  flakiness shows. A task that flips between runs is reported as flaky, not averaged to a half.
- Margin rule: a candidate replaces the incumbent only if it wins by at least 8 points on its job AND is not worse than
  the incumbent on typed-decision schema validity. With n = 12 to 14 per job, a smaller gap is noise (same caution as
  `docs/DEC2_EMBEDDING_COMPARISON.md`: "right size of evidence for a ranking, not for a margin").
- A run that starts under load (bench.py's 60% CPU / 10% GPU rule) is `invalid`, kept, never averaged.

## 4. What is measured per model (latency and memory)

Per model, per quantisation, recorded in one result file (reuse bench.py's schema; extend, do not fork):
- decode tok/s and time to first token at about 66, 2,000 and 8,200 prompt tokens (bench.py's three prompts);
- peak VRAM (nvidia-smi, per-second sample), peak system RAM, whether it spilled to CPU (the percentage
  Ollama reports as CPU/GPU split; doc 35 measured 14B at 41%/59% on the 8 GB card, so spill is a real axis);
- the `num_ctx` actually used, and whether quality was scored at that context (a 24K context for the 7B is a
  measured value; a larger model's is UNKNOWN until measured, per the manifest's own `num_ctx_measured` flag);
- load time cold and warm, GPU temperature and clock, start load, AC power flag;
- total wall time for the 40 tasks.
Latency alone is not a score; it is a gate. A model must hold at or above the D1 floor named in doc 46 for its job
(that value is the owner's; I did not re-read it, so the plan cites it by reference and does not restate a number).

## 5. Candidates and how they are placed

| Slot | Candidate | Status | Fits 8 GB card? |
|---|---|---|---|
| incumbent | qwen2.5:7b-instruct-q4_K_M | in manifest TIER-4, measured | yes, 5.95 GB at 24576 ctx (V in manifest) |
| incumbent | qwen2.5:14b-instruct-q4_K_M | in manifest owner node, measured | no, spills (V in manifest) |
| radar | "Qwen 8B" | UNVERIFIED name | probably, if a q4 exists |
| radar | "Qwen3.8-27B" | UNVERIFIED name | not resident; RAM spill, batch only |
| radar | "MiMo 9B" | UNVERIFIED name | borderline |
| radar | "JEV-9B" | UNVERIFIED name; unknown purpose | borderline |
| radar | "Ripple-65B" | UNVERIFIED name | no; only via the Colibri RAM path, doc 46 |

Rules: models compared on the same card, same quant class (q4_K_M where offered), same prompt text. A 65B model is
compared in a separate "does not fit, RAM path" row, never in the same latency column as an 8B. A candidate that has no
licence file readable by us, or no checkpoint on a source the owner has approved, is dropped at step A, not worked around.
Minimum to satisfy `done_when`: incumbent 7B plus one new model, on all 40 tasks.

## 6. Steps (each is a separate queue item; this PR is only step 0)

0. This design. (done by this PR; draft)
A. Verify the candidates: for each radar name, find the primary model page, read licence, parameter count, base
   model, and available quants; record URL and a V/T tag. Read-only web research; downloads need the owner's yes
   with filename, source and size stated (permission rule). Output: a table that replaces section 5's UNVERIFIED cells.
B. Owner approves the source classes (section 2.2) in one typed yes, in the desk's own chat or through a Router card
   with a "None of these: something else" option.
C. Build the 40 tasks and the key file; run `scan_payload.py`; freeze: write MANIFEST with sha256, commit.
   Also build the scorer, with a test proving it scores a known-bad answer as a fail (a scorer that cannot see its
   subject says `unknown`, not pass).
D. Run: take the heavy lock (`scripts/heavy_lock.py`) and the estate `gpu` lock; AC power; CI containers idle; one model
   at a time; load-check before each. Loopback only. Results to `F:\Leadfuel\home-node\tools\colibri-eval\results\`.
E. Score (machine first, then the blind page for the rubric items), write the table, name the picks.
F. Feed the manifest: a PR changing `node-manifest.json` roles, with `test_one_ladder.py` passing and the docs'
   quotes of thresholds updated in the same PR. Owned by the NODE desk; this plan does not edit it.

## 7. Law 9 and guards

- Every call goes to `127.0.0.1`; bench.py already refuses non-loopback hosts. No cloud model, no cloud judge, no hosted
  CI runner reads the set.
- Pulling a model is a download and a transmission of a request; it needs the owner's yes per model (step A output
  states filename, source, size). No fallback to a vendor if a local run fails: a failed run is recorded as failed.
- No mail, Fieldy, health, finance or character data in any task (section 2.2). Results quoted in mails contain
  aggregate numbers and task ids only.

## 8. Failure modes this design is built against
- Contaminated set: tasks drawn from public code the candidate was trained on. Mitigation: prefer estate-own and
  synthetic tasks; flag any `public` task; report coding score with and without them.
- A benchmark run on the wrong input (two were withdrawn on 2026-09-26). Mitigation: the MANIFEST hash is printed at the top of
  every result file; a result whose hash differs from the frozen one is invalid.
- Quiet vacuity: a scorer that returns pass for an empty answer. Mitigation: step C's known-bad test, and an empty-output
  task in the set whose only passing score is 0.
- Context cheat: a model that scores well only at a context larger than the node will run. Mitigation: record `num_ctx` and
  score at the context the manifest will actually use.

## 9. Open items for the owner (not asked in chat)
- NEEDS-NOVAH (B): the typed yes on source classes, and whether he or a local judge scores the 14 rubric tasks.
- NEEDS-NOVAH (A): a yes per model pulled, with filename, source and size.
- Whether a `typed` role belongs in the manifest (a new key beside chat / batch); a NODE-desk decision.
- Which tier the new picks target: today's measured numbers are for the 8 GB card only; TIER-1 to TIER-3, TIER-5 and TIER-6
  would each need their own run or be marked UNKNOWN.
