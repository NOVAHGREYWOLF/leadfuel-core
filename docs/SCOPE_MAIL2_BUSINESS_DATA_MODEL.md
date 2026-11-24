# mail-2 fit note: training a model on a business's own data (against K01 and W06)

SCOPE ONLY, 2026-11-23 Pacific. Nothing built, pulled, trained or sent; no mailbox read. Task mail-2, INTELLIGENCE, for ROUTER #138. Source: SELF-MAIL.md mail-2.
**NovahOS home: an ITEM (retrieval half, build). Fine-tuning half: DROPPED for now.**

## What he asked
A mail to himself on 2026-11-21, subject "Train ai model for business". The body is one Instagram reel link; it needs his login and was not opened. So the ask is the subject only: a model that knows a business's own data, for his business, for what ETG sells ("AI you own: the hardware, the setup and the training" is already the etg.ai preview tagline), or both. One design serves both.

## Answer in one line
Give each business a local model that knows its data by **retrieval** (index it, search it, answer with the passage cited). Do not fine-tune first.

| | Retrieval | Fine-tuning (LoRA, QLoRA) |
|---|---|---|
| Good at | facts: prices, policies, past jobs | tone, output format, one narrow label task |
| New data | re-index a folder | retrain |
| Forget a document | delete a file | cannot be promised |
| Cites its source | yes, path and line | no |
| Private data sits in | one local file, tier `secret` | the weights, which inherit the tier (`local_only`) |
| On this PC | exists (`lfdesk/rag`, gate `ragdocs`) | no stack installed |

## Fit
- **W06 is the proof.** Private corpus, local embedder (`qwen3-embedding:4b`, owner's pick 2026-11-19, tied best in a 160-question local bake-off), local generator, scored against Sonnet with `rubric.py`, nothing leaves. Its embedding pass now reads DONE (61 shards; the queue's "6 of 61" is stale). Its insight layer is unbuilt: the resident 7B invented names and took pronouns for people on a sample (reported). A business assistant hits the same limit, so answers must be extractive and cited. Tuning does not fix that first.
- **K01 does not gate it.** K01 is the owner's cloud brain; phases 0 and 1 concern the hub's store. A business index is its own local file with a loopback embedder and never touches that path. K01 does supply what must come first for any corpus holding other people's words: fence stored documents against prompt injection (BRAIN R10-F3, R10-F4, R8-F1), list unreadable files rather than count them as covered, test recall on held-out questions.

## What the local GPU can honestly do (RTX 3070 Laptop, 8 GB)
- **Serve:** yes. The 7B q4 is resident, 100 percent GPU, about 60 tok/s. The 14B (8.4 GB file) never fits: about 2.5 tok/s split CPU and GPU, batch only.
- **Train:** not today. No `peft`, `trl`, `bitsandbytes` or `unsloth` in the three Python environments I checked; installing is a download, the owner's yes. QLoRA on 4B or less is plausible, 7B borderline, 14B out (general knowledge, not measured here). It holds the whole card for hours; two models sharing it already cost 8 times the time (reported).
- **Free first:** a small classifier on the frozen embeddings, labelled by his past decisions.
- **Rented GPU:** leaves the machine, so Law 9, a decision and never a fallback. Parity row C10 already specifies local training and a rented run that prints a quote only.

## Privacy
Each business is one index file, tier `secret`. Embedder and engine must be local; the code refuses otherwise (read, not run). Fieldy stays 100 percent local, no cloud model ever (owner, 2026-11-19). One business never mixes with another or with his own corpus, client data stays out of public repos, and deleting the file forgets the business. Weights trained on private data would be `local_only`, like his image LoRAs.

## Build first: NovahOS item "Business knowledge" (working title)
Reuses `lfdesk/rag` and `memstore`. Small steps, stated not built (the files are NODE's):
1. One index per named business: the four `rag_*` gate methods take a `corpus` name, stored under `%LOCALAPPDATA%\Novah\Business\<name>\` (today one `rag.db`).
2. Read PDF, Word and Excel through the `memstore` extractors; `rag` takes text-like files only.
3. Embed each index with `qwen3-embedding:4b`; never mix vector widths.
4. A held-out set of 40 to 100 questions per business with the right source marked: top-5 hit rate plus `rubric.py`. Live only when it passes.
5. A Settings switch "Business knowledge", off by default, showing size, files skipped, last run.
Order: after W06's insight scoring (same rubric, same GPU slot); parallel to K01.

## What it does not do
No fine-tuning, hub, Railway, Voyage or cloud model. No download. Does not open the reel, and no customer data was touched. Does not promise a client a "trained" model. Serving several staff at once is not measured.

## Recommendation
**Build as a NovahOS item, retrieval first.** Suggested queue entry, not created here: INTELLIGENCE (pipeline, test set) and NODE (app side), after W06; owner step only for the first real client corpus and any download. **Drop fine-tuning for now.** Revisit only if the rubric shows a format or name error that a bigger local model and schema-bound output cannot close; then a gated experiment in a separate environment, in the GPU slot, on the held-out set, weights `local_only`.

## Checked and trusted
Verified today: no training libraries (import check, 3 interpreters, torch present so the check can see); 8 GB card, 4.8 GB in use by the resident 7B; `embed.log` ends DONE, 61 shard files; `rag` code refuses a non-loopback embedder and a non-local engine and takes text-like files only; `memstore` has PDF, Word, Excel extractors. Trusted from named files: bake-off and invented-names findings (INTELLIGENCE part 3 and 4 notes), tok/s and the 14B split (`node-manifest.json`), K01 findings (ROUTER-135 K01 SCOPE.md), the 8 times. Not checked: the reel, QLoRA fit on 8 GB, PyMuPDF installed. For the W06 desk: `.locks\gpu` still reads held by leadfuel-offer part 4 since 2026-11-20 though the pass is done.
