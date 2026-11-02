#!/usr/bin/env bash
# Run runner_stall_check.sh and record the verdict. Fired every 15 minutes by the Windows
# scheduled task "NODE runner stall check" (CI-RUNNER-STALL; owner chose option A, 2026-10-06).
#
#   state/runner-stall.latest   checked_at=<UTC> exit=<0|1|2|124>, then the check's full output
#   state/runner-stall.log      one line per run, capped at 5,000 lines
#
# READERS: a `latest` older than 30 minutes means THIS WATCH IS NOT RUNNING. Treat it as
# UNKNOWN, never as the OK it may still say.
# `exit=3` / first word CAPTIVE: the Wi-Fi is behind a captive portal. Wait and read the next one;
# it is not a runner fault and nothing should be restarted on it.
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
STATE="$DIR/state"
mkdir -p "$STATE"

ts=$(date -u +%FT%TZ)
out=$(timeout 540 bash "$DIR/runner_stall_check.sh" 2>&1); rc=$?
if [ $rc -eq 124 ]; then out="UNKNOWN check timed out after 540 s"$'\n'"$out"; fi
[ -n "$out" ] || out="UNKNOWN check printed nothing"

{ echo "checked_at=$ts exit=$rc"; echo "$out"; } > "$STATE/runner-stall.latest.tmp" \
  && mv -f "$STATE/runner-stall.latest.tmp" "$STATE/runner-stall.latest"
echo "$ts exit=$rc $(head -1 <<<"$out" | cut -c1-400)" >> "$STATE/runner-stall.log"
if [ "$(wc -l < "$STATE/runner-stall.log")" -gt 5000 ]; then
  tail -n 5000 "$STATE/runner-stall.log" > "$STATE/runner-stall.log.tmp" \
    && mv -f "$STATE/runner-stall.log.tmp" "$STATE/runner-stall.log"
fi
exit $rc
