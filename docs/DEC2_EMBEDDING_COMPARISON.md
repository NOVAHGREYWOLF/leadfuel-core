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
