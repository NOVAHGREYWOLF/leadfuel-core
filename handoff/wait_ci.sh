#!/bin/sh
# usage: wait_ci.sh <repo> <pr> <sha> [max_minutes]
# Waits until every check run on <sha> has completed. Prints each run's name/conclusion.
# Reports UNKNOWN if no check runs ever appear (a check that cannot see its subject is not a pass).
repo=$1; pr=$2; sha=$3; max=${4:-120}
i=0
while [ $i -lt $((max*2)) ]; do
  out=$(gh api "repos/NOVAHGREYWOLF/$repo/commits/$sha/check-runs?per_page=100" -q '.check_runs[] | "\(.status) \(.conclusion) \(.name)"' 2>/dev/null)
  n=$(printf '%s\n' "$out" | grep -c .)
  pending=$(printf '%s\n' "$out" | grep -vc '^completed')
  if [ "$n" -gt 0 ] && [ "$pending" -eq 0 ] && [ $i -ge 4 ]; then
    printf '%s\n' "$out"
    bad=$(printf '%s\n' "$out" | grep -v 'completed success' | grep -v 'completed skipped' | grep -v 'completed neutral')
    if [ -z "$bad" ]; then echo "VERDICT GREEN $repo#$pr $sha"; else echo "VERDICT RED $repo#$pr $sha"; fi
    exit 0
  fi
  i=$((i+1)); sleep 30
done
printf '%s\n' "$out"
echo "VERDICT UNKNOWN(timeout or no runs) $repo#$pr $sha"
