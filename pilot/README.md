# Next Clients pilot harness (WEB-H1)

Local only. Reads one customer's own LinkedIn export, ranks their people with the hub's own
routing rules (`relationship_route.routes`, loaded read-only from the hub checkout), and writes
the "25" into that customer's folder. Nothing in it sends, logs in, or reaches another machine.

## Where the data lives

`LEADFUEL_PILOT_ROOT`, default `%LOCALAPPDATA%\leadfuel-pilot`. One folder per customer:

```
<root>/<customer>/meta.json          import, delivery and delete_after dates
<root>/<customer>/consent.jsonl      every consent event, latest per scope wins
<root>/<customer>/offer.json         what they sell (from the intake call)
<root>/<customer>/raw/               Connections.csv, messages.csv (nothing else is kept)
<root>/<customer>/out/top25.csv      the sheet
<root>/<customer>/out/voice_samples.txt
<root>/<customer>/out/run.json       counts, scorer path and sha256, egress
<root>/<customer>/calibration.jsonl  baseline at ranking, then sent / replied / conversation
<root>/ledger.jsonl                  ids and events only
<root>/calibration_aggregate.jsonl   de-identified rows kept after deletion
```

The harness refuses a root inside any git working tree. Customer ids are slugs, never names.

## Run it (the owner's own export first)

```
python pilot/warm_pilot.py init owner
python pilot/warm_pilot.py consent owner local_processing --by owner --method "own data"
python pilot/warm_pilot.py import owner "C:\path\to\Basic_LinkedInDataExport.zip"
# edit <root>\owner\offer.json: roles / keywords of who you want to reach
python pilot/warm_pilot.py rank owner                       # stub drafts, no model
python pilot/warm_pilot.py consent owner local_model --by owner --method "own data"
python pilot/warm_pilot.py rank owner --drafts ollama --ollama-model qwen3-64k:4b
python pilot/warm_pilot.py deliver owner                    # delete_after = now + 30 days
python pilot/warm_pilot.py calibrate owner <profile url> sent   # at the 14-day check-in
python pilot/warm_pilot.py sweep                            # deletes what is due; exit 1 if it could not
```

The CLI prints counts, never people. `--me-url` names the owner's profile when the export does
not make it plain (the harness refuses to guess below 90% conversation coverage).

## Rules it enforces

- **Consent before anything.** `import` and `rank` need `local_processing`; local drafting
  needs `local_model`. Revoking `local_processing` makes the folder due for deletion at once.
- **Loopback only.** The model URL must be 127.0.0.1, ::1 or localhost, and proxies are off.
- **No cloud path.** `--drafts cloud` raises even with `cloud_model` consent recorded: drafting
  off this machine is the owner's decision (card 4) and would be its own gated build.
- **No fallback.** If the local model fails, the run fails; it never substitutes anything.
- **Deletion at 30 days after delivery** (30 days after import if never delivered). `sweep`
  checks the folder is gone and reports `still_present` (exit 1) if not.
- **Drafts are drafts.** A small local model invents details; every note is read and edited
  by the customer before they send it themselves.

The ranking weights are the hub's and are **uncalibrated** (the hub says so). The calibration
log is how that changes.
