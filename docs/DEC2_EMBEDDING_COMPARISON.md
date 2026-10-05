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
2. **Prepare, no downtime:** create the 1024-d chunk side tables (see step 3; additive, so nothing
   breaks). Do not alter the 768 column in place.
3. **Re-embed in batches** into the chunk tables with `mxbai-embed-large`, resumable by a
   not-yet-chunked cursor, at about 6.5 items/s on long text (the 12 h figure is an
   extrapolation; re-measure on the first 5,000 rows and re-quote the estimate before committing).
   Use the query prefix `Represent this sentence for searching relevant passages: ` on queries only.
   **Long items are split into chunks, not truncated (owner answer Q64).** Chunk at about 1,100
   chars (comfortably inside 512 tokens), split on paragraph then sentence boundaries, with about
   150 chars of overlap; every chunk is embedded separately. This makes embeddings one-to-many, so
   a single new column on the row is not enough; use a side table per source table, `<table>_chunk_embedding(row_id, chunk_no, embedding vector(1024))`, with a unique key
   on `(row_id, chunk_no)`. Short items (the large majority) are one chunk.
   Search returns the best-scoring chunk per row and de-duplicates by row. `brain.py` search
   and every writer must change to match, which is a code change for the owning desk, not this plan.
   **Measured read-only on the local DB:** 197,261 embedded `user_memory` rows, median content 43
   chars, 95th percentile 1,797 chars, 6.6% longer than 1,500 chars; at about 1,100 chars per chunk
   that is roughly **226,000 chunks**, about 15% more embeds than rows. Because most rows are short,
   the 12 h figure (measured on 300+ char texts) is likely a high bound; re-measure on the first 5,000.
   Open: apply the same chunking to the `document` table (long files); not measured.
4. **Verify before cutover:** every row with a 768 embedding has at least one chunk row; re-run
   this PR's sample test against the DB vectors; spot-check retrieval on the known queries.
5. **Cutover (one short window):** set `OSS_EMBED_MODEL=mxbai-embed-large` and `VOYAGE_DIM=1024`,
   (switch search and writers to the chunk tables in one deploy; the old 768 column stays untouched
   as the rollback). New ingests embed with mxbai from this point.
   Stop ingest during the swap, or backfill rows ingested during the run.
6. **Cleanup after a soak (suggest 7 days):** drop the old 768 column, then reclaim its storage.

## Rollback
Until step 6, rollback is the reverse rename plus the old env values (`nomic-embed-text`, 768). It is
instant and loses nothing but rows ingested after the cutover, which need re-embedding with nomic
(small). After step 6, rollback means a fresh 4.2 h nomic re-embed.

## Risks
Disk: roughly +33% over the current vectors while both columns exist. A second embed model is not
kept resident, so Ollama load time at start. The 512-token window (above). Cloud nodes must run the
same model and dimension: the node spec must change with it.

## Chunk size vs the 512-token limit (checked, not a re-embed)
Real token counts from Ollama (`truncate:false`, mxbai-embed-large) on 3,336 chunks of about 1,100
chars: 1,500 uniformly sampled rows (1,788 chunks) plus 500 rows over 1,500 chars (1,548 chunks).
Median 17 and 265 tokens; p99 364 and 451; largest passing chunk 489. **But 9 chunks (0.27%) were
rejected as over the context limit**, down to 0.44 chars per token (dense, non-prose text). So
about 1,100 chars is safe for typical prose and not guaranteed. **Rule for the chunker: size by tokens,
not characters.** Count tokens per chunk and re-split any chunk above about 450, or cap dense text
near 500 chars. Silent truncation otherwise returns no error. Sample is 2,000 rows, not the 5,000
asked for: the box was starved and the first 5,000-row run did not finish.
