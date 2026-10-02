# Dec-2 / B3: embedding model comparison (nomic-embed-text vs mxbai-embed-large)

Status: comparison only. Nothing was re-embedded or migrated. All embedding ran locally through
Ollama on the RTX 3070 Laptop (8 GB); no data left the machine. Aggregate numbers only.

## Method (what I measured myself)
- Sample: 959 items from the local `user_memory` corpus, stratified over 10 source/kind groups
  (<=120 each), each with >=300 chars of content; text capped at 1,500 chars.
- Task A, title to content: 464 items that have a distinct title; query = title, pool = 959 contents.
- Task B, first half to second half: 959 items; query = first half, pool = all second halves.
- Each model used with its recommended query/document prefix. Metrics: recall@1, recall@10, MRR.
- Speed: documents per second embedding the 959 items (batch 32, 1,500-char cap).

## Results
| | nomic-embed-text | mxbai-embed-large |
|---|---|---|
| Dimensions | 768 | 1024 |
| Title to content, R@1 / R@10 / MRR | 0.276 / 0.513 / 0.358 | 0.313 / 0.530 / 0.390 |
| Half to half, R@1 / R@10 / MRR | 0.340 / 0.694 / 0.433 | 0.487 / 0.736 / 0.580 |
| Speed on this sample | 19.4 items/s | 6.5 items/s |
| Max context | 2,048+ tokens | 512 tokens |

## Reading it
- mxbai is better on both tasks, clearly on half-to-half (R@1 +15 points, MRR +0.15), modestly on
  title-to-content (+4 points R@1; the R@10 gap is within noise at n=464).
- It is about 3x slower on long text and 33% larger per vector. Scaling the existing measure
  (13.2 items/s, 4.2 h) by the measured ratio gives roughly 12 h to re-embed 200,701 items.
  That ratio is an extrapolation, not a full-corpus measurement.
- Its 512-token window truncates long items (chatgpt, fieldy transcripts) that nomic would keep.
- Both tasks are self-supervised proxies, not human-labelled relevance, and not the production
  ask/search workload. They are the right size of evidence for a ranking, not for a margin.

## Cost of switching (nomic to mxbai)
Full re-embed (about 12 h, free, GPU exclusive) + pgvector column change 768 to 1024 on
`user_memory`, `document`, `knowledge` (rebuild indexes) + `VOYAGE_DIM`-style dimension setting
+ roughly 33% more vector storage. Not done here.

## Recommendation
Keep nomic-embed-text unless retrieval quality is the bottleneck. If the owner wants the quality
gain, mxbai-embed-large is the better of the two but the gain is real-but-moderate and costs about
3x the re-embed time and a schema migration; decide before the corpus grows further, since the cost
scales with it. Not tested: a third model (e.g. bge-m3), because pulling it is a download that needs
approval, and production query-side behaviour (hybrid/keyword search could narrow the gap).

---

# Migration plan: switch to mxbai-embed-large (owner answer Q60: SWITCH)

**NOT STARTED. No run without the owner's explicit go.** The `novahub` and `hub` code owners (not this
desk) perform it; this is the plan only.

Facts checked read-only on the local DB: three `vector(768)` columns (`user_memory.embedding`,
`document.embedding`, `knowledge.embedding`); **no vector indexes exist** (no hnsw/ivfflat), so
there are no indexes to rebuild; 199,041 `user_memory` rows, of which about 1,780 live rows currently
have no embedding. `brain.py` takes the dimension from `VOYAGE_DIM` and the model from
`OSS_EMBED_MODEL`, and states that vectors from different models cannot be searched together.

## Steps
1. **Take the `gpu` lock** (estate lock, `mkdir`) for the whole run, about 12 h, and say so in
   `WORK_QUEUE.md`. Nothing else may use the GPU or Ollama. No CI hold needed unless code is merged.
2. **Prepare, no downtime:** add `embedding_v2 vector(1024)` to the three tables (an additive
   migration, so nothing breaks). Do not alter the 768 column in place.
3. **Re-embed in batches** into `embedding_v2` with `mxbai-embed-large`, resumable by a
   `WHERE embedding_v2 IS NULL` cursor, at about 6.5 items/s on long text (the 12 h figure is an
   extrapolation; re-measure on the first 5,000 rows and re-quote the estimate before committing).
   Use the query prefix `Represent this sentence for searching relevant passages: ` on queries only.
   Cap text at about 1,500 chars (512-token window): long items such as chatgpt and fieldy transcripts
   are truncated, so decide chunking or truncation first. That decision is open and affects recall.
4. **Verify before cutover:** `embedding_v2` non-null count equals `embedding` non-null count; re-run
   this PR's sample test against the DB vectors; spot-check retrieval on the known queries.
5. **Cutover (one short window):** set `OSS_EMBED_MODEL=mxbai-embed-large` and `VOYAGE_DIM=1024`,
   and point reads and writes at `embedding_v2` (rename columns in one transaction: `embedding` to
   `embedding_old`, `embedding_v2` to `embedding`). New ingests embed with mxbai from this point.
   Stop ingest during the swap, or backfill rows ingested during the run.
6. **Cleanup after a soak (suggest 7 days):** drop `embedding_old`, which reclaims the extra storage.

## Rollback
Until step 6, rollback is the reverse rename plus the old env values (`nomic-embed-text`, 768). It is
instant and loses nothing but rows ingested after the cutover, which need re-embedding with nomic
(small). After step 6, rollback means a fresh 4.2 h nomic re-embed.

## Risks
Disk: roughly +33% over the current vectors while both columns exist. A second embed model is not
kept resident, so Ollama load time at start. The 512-token window (above). Cloud nodes must run the
same model and dimension: the node spec must change with it.
