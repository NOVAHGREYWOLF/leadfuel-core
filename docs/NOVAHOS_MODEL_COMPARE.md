# mail2-38: one prompt across several local models, answers side by side

Item `mail2-38` (SURFACE, ROUTER #135 wave 3). Picture: [`docs/mockups/model-compare.html`](mockups/model-compare.html)
(five moments, light and dark, no network). Code: [`modelcompare/`](../modelcompare/). Tests:
[`tests/test_modelcompare.py`](../tests/test_modelcompare.py). Draft PR:
<https://github.com/NOVAHGREYWOLF/leadfuel-core/pull/97>.

**Status: built and tested against a fake engine. UNTESTED IN THE REAL WINDOW.** The package has never been
imported inside the NovahOS app, and no model was run live. Everything below that says "will" is
unverified until NODE lands it (see Integration).

## What it is

In the NovahOS chat the owner switches **Compare** on, chooses 2 to 4 local models, types one message and
presses **Compare**. The models answer **one after another**; each answer streams into its own lane of one
card in the transcript, side by side. The owner can **Skip** the lane that is running, **Stop** the rest,
**Copy all answers**, or **Use this answer** on any lane that finished. Nothing is written to the chat until
that last click. Compare is local only: it runs on this PC and nothing leaves it.

## Which models

The chat-capable models the local engine itself lists, nothing else: `LocalEngine.models()` (those with the
`completion` capability; embedding models are left out by the engine, and Ollama cloud rows are dropped by
the engine's own `catalog()`). Read from `GET 127.0.0.1:11434/api/tags` only, on this PC on 2026-11-23, that
is eight models:

| Model | Size on disk | Note |
|---|---|---|
| `qwen2.5:7b-instruct-q4_K_M` | 4.7 GB | |
| `qwen2.5:14b-instruct-q4_K_M` | 9.0 GB | labelled **slower here**: past 9.0B parameters the card spills (measured 5.5x slower, `lfdesk/engine/README.md`) |
| `mistral:7b`, `mistral-64k:7b` | 4.4 GB each | |
| `qwen3:4b-instruct-2507-q8_0`, `qwen3-64k:4b` | 4.3 GB each | |
| `qwen3.5:4b-mtp-q8_0` | 6.0 GB | can read images; images are not sent (see v1 limits) |
| `qwen3-vl:8b` | 6.2 GB | can read images; images are not sent |

Excluded by the engine: `nomic-embed-text`, `mxbai-embed-large`, `qwen3-embedding:4b`, `qwen3-embedding:8b`.

**Local only, by construction.** A model id is resolved only through an engine whose registry key and own
`.name` are both `local`. Every other engine is never asked anything (not `models`, not `available`, not
`stream`). An id that is not on the local list is refused (`not_installed`); an id that looks like a cloud
model is refused with its own sentence (`not_local`). There is no setting that adds a cloud model, and no
fallback to one. Tests: a cloud engine's call counters stay at zero (with a positive control), a cloud
engine filed under the key `local` is not used, and a cloud-looking id listed by a local engine is hidden
and refused.

## Where it sits in the chat

- A **Compare** toggle in `.composer-bar`, beside the `#model` picker. On, the send button reads
  "Compare N", chips show the chosen models (remove with the x, add with "+ Add local model"), and a count
  says "N of 4 chosen, 2 needed".
- The comparison card is drawn **in the transcript, where the assistant message would be**, under the
  owner's message (shown as "not saved until you pick an answer").
- While a comparison runs the composer is disabled, and `Api._start_turn` refuses an ordinary turn
  (`compare.busy()`), because a normal turn and a comparison would share one engine instance.

## How spend approval applies

A local lane costs **no money**: it costs card time (a model swap is about 25 s, measured). It transmits
nothing, so Law 9 has nothing to gate for the shipped feature. The package imports no network, process,
file or library-loading module; a test parses its source and fails if one appears, with a positive control
proving the scan can see one.

A **cloud lane is a separate, later decision of the owner** and is not built. If he makes it, it needs the
spend gate once per run times the number of lanes (it multiplies cost by the lane count), its own PR, and an
explicit second allow-list; the code deliberately has no switch for it. A cloud model must never become a
fallback for a local one that failed.

## Design decisions and why

- **Sequential, one lane at a time.** `LocalEngine` has one live response and one level-triggered cancel flag
  per instance, and Ollama reloads on a model swap. Parallel lanes would clobber each other's cancel and not
  be faster.
- **No tools, no files.** Each lane gets `tools=None, on_tool=None`. A tool chunk from a misbehaving engine
  is ignored and flagged `UNEXPECTED_TOOL_USE`.
- **A state is never guessed.** A lane is `done` only if its stream said so; a stream that ends with no
  terminal chunk is `incomplete`; an engine that raises is `error`; stopped lanes are `cancelled` or
  `skipped`. Only a `done` lane can be picked.
- **Nothing is written until the owner picks.** `compare_pick` writes the question, then the chosen answer,
  once. A failed write gives the claim back and can be retried: the question is not written twice and the
  half-begun answer row is finished, not duplicated. A retry for a *different* model after a part-way failure
  is refused (`retry_same_answer`), because that row is already labelled with the first model.
- **Bounded.** A lane keeps at most 200,000 characters (then says so), the card holds the last 8 runs in
  memory, a poll with an unchanged version costs a few fields.

### The one cancel window that is not closed

`LocalEngine.cancel()` is level-triggered: a cancel that arrives with no turn in flight would wait and cancel
the owner's *next* chat turn. So the code calls `engine.cancel()` only while a lane is inside the engine
(a marker held under one lock, cleared under the same lock at the terminal chunk, then the generator is
closed so the engine's own `finally` resets the flag), and `stop` / `skip` after the run ended never reach the
engine (tested: zero cancel calls, flag unset). **Residual window:** an engine that *raises* in the same few
microseconds as the owner's Stop could leave the engine's cancel flag set for the next turn. It needs both at
once; it is not closed and not tested.

## Not in v1

Memory, skills, project files, answer-style context and images are **not** added to a comparison's prompt:
they each have per-turn side effects in `Api._start_turn` that were not verified for N lanes. The chat's own
system prompt (`_chat_prompt_context`) and the chat's history are included. Also not in v1: a per-lane
timeout (Skip and Stop instead), parallel lanes, saving a comparison across a restart (it lives in memory; only
the picked answer is saved), a cloud lane, and any scoring or ranking of answers.

## Integration (for NODE, owner of `home-node/app`) — UNTESTED IN THE REAL WINDOW

This repo cannot reach the estate repo (push is disabled there by design), and the files belong to NODE, so
nothing under `F:\Leadfuel\home-node` was touched. To land it:

1. Copy `modelcompare/` to `home-node/app/assistant/modelcompare/`.
2. Add `assistant/comparegate.py` containing `from assistant.modelcompare.gate import build_gate`.
3. Append one line to `GATES` in `assistant/gate_list.py`:
   `Gate("compare", "assistant.comparegate", methods=("compare_models", "compare_start", "compare_poll", "compare_stop", "compare_skip", "compare_pick", "compare_export"))`.
   The Api attribute is the gate name, so the desk is `api.compare`.
4. In `Api._start_turn`, next to the existing "a turn is already running" refusal, return
   `{"ok": False, "error": ...}` when `getattr(self, "compare", None) is not None and self.compare.busy()`.
5. In `Api.shutdown`, call `self.compare.shutdown()` (guarded like the others).
6. The page: composer toggle and chips, the card, a 150 ms poll of `compare_poll(run_id, since)` until
   `state == "finished"`, `textContent` only (model text is a stranger's text, never HTML), **Use this answer**
   calls `compare_pick` and then `set_model(lane.model)` if the owner wants to continue with it.
7. Tests in `assistant/tests`, including a `--selftest` pass with the `fake` engine (`build_gate(api, scripted=True)`
   allows the `fake` key only then).

The gate reads `api.engines`, `api.store`, `api._turn`, `api._chat_prompt_context` and (looked up when a lane
starts, so build order does not matter) `api.panes.turn_started / turn_finished` for the GPU lease.

## What was verified, and what was not

**Verified by this desk (read from `F:\Leadfuel\home-node\app` on 2026-11-23):** the `Engine` contract and
`Chunk` shape (`lfdesk/engine/base.py`), `LocalEngine` cancel semantics, `catalog()` and `models()`
(`lfdesk/engine/local.py`), `LocalEngine.name == "local"`, `FakeEngine.name == "fake"`, `ConvStore` method
signatures, `Api._start_turn`, `_chat_prompt_context`, `_lease_watch`, `_gate_method`, `gate_list.Gate`, the
Ollama model list above, and that `tests/test_modelcompare.py` passes on a fake engine and a fake store.

**Not verified:** the package was never imported inside the real app; no model was run live (the model list
was read from `/api/tags` only); the page does not exist beyond the mockup; the engine's own GPU-yield question
(D6) may appear once per lane if a render is running, and that was not exercised; `engines["fake"]` being
registered on every run (`Assistant.py` line 275) was seen in a search, not read in context; the real
`ConvStore` was not run (a fake with the same signatures stands in); `scripts/gates.sh` does not exist in this
repo, so the static gates were not run.
