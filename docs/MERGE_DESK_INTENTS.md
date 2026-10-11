# Merge desk: intent rows, feed and refresh

The Merge desk is a claude.ai Artifact (a third owner page beside the Conductor desk and the Router
desk). This file is the contract between the page, the local feeder and anything that acts on a
request (the merge train, a router, a desk). The page's own buttons never merge, ready a draft or
send a message. They write one intent row.

Public repo: ids, titles and PR numbers only.

## Parts

| Part | Where | Does |
|---|---|---|
| Page | the Artifact "Merge Desk" (its URL is on the Build Board, doc `router/desks`) | shows rows, writes `intents/*` |
| Feeder | `watch/merge_desk_feeder.py` | reads `gh` and the slot locks, writes `snapshot.json` locally. Writes nothing else, runs no CI |
| Refresh runner | a short routine that runs the feeder and copies files to and from the page database | the only thing that writes `feed/current` |
| Consumers | merge train, router, desks | read exported intents, write acks |

## The page database

* `feed/current` (one document, written only by the refresh runner): the whole `snapshot.json`.
  Fields: `refreshed_at`, `stale_after_min` (15), `errors[]`, `ci{repo:{median_min,n}}`, `summary{}`,
  `rows[]`. The page says **Stale** when `refreshed_at` is older than `stale_after_min`, and **Unknown**
  when it cannot read it.
* `intents/<intent_id>` (written by the page when a viewer clicks, one document per click, never
  edited by the page afterwards): the intent row below.

### Row fields (`rows[]`)

`id` (`<repo>~pr<N>`, `task~<KEY>`), `kind` (`pr`, `task`, `merged`), `repo`, `number`, `title`, `url`,
`lane`, `stage`, `since` + `since_basis`, `holder` + `holder_basis`, `slot{lock,ahead,held_by}`,
`batch`, `eta_min` + `eta_basis`.

`stage` is one of `no-pr`, `draft`, `ci-red`, `ci-running`, `green-waiting`, `in-train`, `merged`,
`unknown`. `unknown` means the checks could not be read; it is never shown as green.

**ETA rule.** `eta_min` is `null` ("unknown") unless every input exists. For `green-waiting`: holder time
left + (PRs ahead in the slot queue + 1) x the repo's median CI minutes, with at least 3 measured runs.
For `ci-running`: median CI minutes minus elapsed (floor 0) + one slot hold. Draft, red, no PR and
in-train are always unknown. `eta_basis` states the arithmetic or the missing input.

## Intent row (the format to adopt)

```json
{
  "intent_id": "20261004T203423Z-novahub-pr751-faster",
  "row_id": "novahub~pr751",
  "repo": "novahub",
  "pr": 751,
  "task_key": null,
  "intent": "faster",
  "ts": "2026-10-04T20:34:23Z",
  "who": "<opaque viewer id>",
  "status": "recorded"
}
```

* `intent`: `faster`, `ready`, `hold`, `unhold`.
* `pr` is an integer for a PR row and `null` for a task row (then `task_key` is set).
* `intent_id` is `<UTC compact timestamp>-<repo>-pr<N or task>-<intent>`; it is the document id and the
  exported file name.
* Latest row per `(repo, pr)` wins. A `hold` beats `faster` until a later `unhold`.
* `status` starts as `recorded`. The page shows "recorded, waiting for the merge train" until an ack
  changes it.

### Who reads which intent

* `faster`, `hold`, `unhold`: the merge train (moves the PR to the front of the batch order; skips a held PR).
* `ready`: a request to the PR's desk to take it out of draft. The train does not act on it (it acks
  `ignored`). The router or the owning desk reads these from the same export directory.

## Local export and acks (file-based, one file per row)

The refresh runner copies the database to disk so local scripts need no artifact access:

* `F:\Claude Sessions\merge-desk\intents\<intent_id>.json`: every intent row, written once, never rewritten.
* `F:\Claude Sessions\merge-desk\acks\<intent_id>.json`, written by the consumer, once per intent:
  `{"intent_id","status":"honoured"|"declined"|"ignored","note","ts"}`. The runner copies `status` and
  `note` onto the page's intent document, which then shows the outcome.

## Merge-train state (read by the feeder)

`F:\Claude Sessions\merge-train\state.json`, written by the train:

```json
{"updated":"...Z",
 "batch":{"id":3,"prs":["novahub#751"],"stage":"ci","tested_sha":"..."},
 "prs":{"novahub#751":{"stage":"in-train","batch":3,"tested_sha":"..."}}}
```

Keys are `repo#N` (several repos share numbers). The feeder shows a PR as **In train, batch N** when
`prs[...].stage` is `in-train`. Absent file means the page notes that the train is not running.

## Refresh (every few minutes)

1. `python watch/merge_desk_feeder.py --queue-dir <dir>` where `<dir>` holds the Conductor desk export
   (`picks/` queued with `choice == now`, and `desks/`). Takes about a minute.
2. Write `snapshot.json` into the page database as `feed/current`.
3. Export new `intents/*` rows to disk; import new `acks/*` onto the intent documents.

Only the page's own database is written. The feeder runs no CI and takes no lock.
