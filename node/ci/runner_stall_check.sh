#!/usr/bin/env bash
# Is a hub runner stall happening right now, and why?  READ-ONLY: it starts, stops and
# restarts nothing, and never reads or prints GH_TOKEN.
#
# Written after CI-RUNNER-STALL (2026-10-05): from ~16:55Z to ~18:10Z something on this
# machine's network answered TLS for *.github.com / *.actions.githubusercontent.com with the
# wrong certificate (RemoteCertificateNameMismatch, RemoteCertificateChainErrors). Runner-1's
# entrypoint could not mint a registration token, so config.sh got an empty one ("Invalid
# configuration provided for token") and the container restart-looped once a minute; runner-2's
# listener sat in "Runner connect error ... Retrying until reconnected". Nothing said so: the
# containers read "Up", `docker logs --since` returned NOTHING for the window (the json log is
# unbounded and docker's reader gives up on it), and the restart count grows by design anyway.
#
# Prints ONE verdict line first, then evidence:
#   OK                 every probe ran and none found a problem          (exit 0)
#   STALLED <why>      a probe positively saw a stall or its cause       (exit 1)
#   UNKNOWN <why>      a probe could not run, and nothing proved a stall (exit 2)
#   CAPTIVE <why>      this PC's Wi-Fi is behind a captive portal: WAIT   (exit 3)
# A probe that cannot see its subject says UNKNOWN. It never reads as OK.
#
# CAPTIVE (CAPTIVE-WAIT, owner q290 = C, 2026-10-06). The 10-05 and 10-06 "interceptor" was the
# Wi-Fi's captive portal: it answers every HTTPS request with its own self-signed certificate for
# seconds to hours, and Windows logs it. While it is up, a runner that cannot mint a token, a
# container that is "restarting" and a `gh` that hangs are SYMPTOMS of the network, not runner
# faults. So captive_probe.py (Windows' own NCSI verdict + one plain-HTTP GET, no TLS, nothing
# submitted) runs first and again at the end. Captive means: say CAPTIVE, skip or hold back the
# findings (they are printed as held back, never dropped), and check again at the next run. Never
# restart, stop, recreate or deregister anything on that evidence: this script does none of those.
# The probe saying UNKNOWN, or not running at all, changes nothing: the verdict is whatever the
# runner probes found, as before.
set -uo pipefail
export MSYS_NO_PATHCONV=1

REPO="${REPO:-NOVAHGREYWOLF/novahub}"
CONTAINERS="${CONTAINERS:-novah-runner-novahub novah-runner-novahub-2}"
STALE_MIN="${STALE_MIN:-20}"     # a run QUEUED (waiting for a runner) longer than this is a stall
LOOP_MIN="${LOOP_MIN:-10}"       # look for token-mint failures in listener logs this recent

CALL_S="${CALL_S:-30}"           # cap on any one docker/gh call (exit 124 = it hung)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The captive-portal probe: a command, run as `timeout PROBE_S $CAPTIVE_PROBE`. Source of truth is
# leadfuel-core node/captive_probe.py; the copy beside this script is what runs on this PC.
CAPTIVE_PROBE="${CAPTIVE_PROBE:-python $DIR/captive_probe.py}"
PROBE_S="${PROBE_S:-60}"

stalled=(); unknown=(); evidence=()

# Every outside call is capped. During the 10-06 02:00Z outage three of four scheduled runs hit
# the wrapper's whole-run limit and said nothing but "timed out": gh has no timeout of its own,
# and docker exec into a restarting container can block. Capped, a hung probe makes only ITS
# answer UNKNOWN and the other probes still report.
dk()  { timeout "$CALL_S" docker "$@"; }
ghx() { timeout "$CALL_S" gh "$@"; }

# Ask the captive-portal probe. Sets PROBE_VERDICT (CAPTIVE|ONLINE|UNKNOWN) and PROBE_LINES. An
# answer that is not exactly one of the three words, or a probe that crashes, hangs or is missing,
# is UNKNOWN: only a clear CAPTIVE changes this script's verdict.
# shellcheck disable=SC2086
captive_probe() {
  local out rc word
  out=$(timeout "$PROBE_S" $CAPTIVE_PROBE 2>&1); rc=$?
  word=${out%%[[:space:]]*}
  case "$word" in
    CAPTIVE|ONLINE|UNKNOWN) PROBE_VERDICT=$word ;;
    *) PROBE_VERDICT=UNKNOWN
       out="UNKNOWN captive probe gave no verdict (rc $rc): ${out:0:200}" ;;
  esac
  PROBE_LINES=$(printf '%s\n' "$out" | cut -c1-400)
}

# The probe's first line without its leading verdict word, so "CAPTIVE <why>" is not doubled.
probe_first_line() { local l=${PROBE_LINES%%$'\n'*}; l=${l#"$PROBE_VERDICT"}; echo "${l# }"; }

# 0. Behind a captive portal right now? Then docker exec and gh would only hang or lie, so do not
#    run them. Report CAPTIVE and let the next run look again.
captive_probe
if [ "$PROBE_VERDICT" = CAPTIVE ]; then
  echo "CAPTIVE $(probe_first_line)"
  echo "  runner probes skipped while captive: they would hang or mislead. Nothing was restarted."
  echo "  wait and retry later; the portal is the network's, not the runners'"
  printf '%s\n' "$PROBE_LINES" | tail -n +2
  exit 3
fi

for c in $CONTAINERS; do
  state=$(dk inspect -f '{{.State.Status}}' "$c" 2>/dev/null) || { unknown+=("$c: docker inspect failed"); continue; }
  evidence+=("$c: container $state")
  [ "$state" = running ] || { stalled+=("$c not running ($state)"); continue; }

  # 1. Can this container complete TLS to GitHub? Unauthenticated HEAD-style probes, no token.
  #    curl exit 60 = certificate problem: the 2026-10-05 failure.
  for url in https://api.github.com/ https://broker.actions.githubusercontent.com/; do
    out=$(dk exec "$c" curl -sS -o /dev/null --max-time 20 -w '%{http_code}' "$url" 2>&1); rc=$?
    case $rc in
      0)  evidence+=("$c: TLS to $url ok (http ${out})") ;;
      60|35|51|58|77|83|90|91) stalled+=("$c: TLS to $url fails (curl $rc: ${out##*curl: })") ;;
      124) unknown+=("$c: probe of $url hung > ${CALL_S}s (docker exec or curl)") ;;
      126|127) unknown+=("$c: cannot run curl in container (rc $rc)") ;;
      *)  unknown+=("$c: $url unreachable (curl $rc: ${out##*curl: })") ;;
    esac
  done

  # 2. What did the listener itself say recently? Its _diag logs survive ephemeral restarts.
  recent=$(dk exec "$c" sh -c "find /home/runner/_diag -maxdepth 1 -name 'Runner_*.log' -mmin -${LOOP_MIN} 2>/dev/null") \
    || { unknown+=("$c: cannot list _diag"); continue; }
  if [ -z "$recent" ]; then
    # An idle listener holds one log open for hours; no new file is normal. Read the newest.
    recent=$(dk exec "$c" sh -c "ls -t /home/runner/_diag/Runner_*.log 2>/dev/null | head -1")
  fi
  [ -n "$recent" ] || { unknown+=("$c: no listener log to read"); continue; }
  nlogs=$(echo "$recent" | wc -l)
  recent=$(echo "$recent" | tr '\n' ' ')   # one line: it is spliced into an sh -c string
  # shellcheck disable=SC2086
  tok=$(dk exec "$c" sh -c "grep -l 'Invalid configuration provided for token' $recent 2>/dev/null | wc -l")
  # shellcheck disable=SC2086
  # Judge by each line's own timestamp: an idle listener keeps one log open for hours, so an
  # error in its tail can be long over (seen: a 23:52Z "Connection refused" read at 01:10Z).
  cut=$(date -u -d "-${LOOP_MIN} min" '+%Y-%m-%d %H:%M:%S')
  # shellcheck disable=SC2086
  cert=$(dk exec "$c" sh -c "cat $recent 2>/dev/null | awk -v t='$cut' 'substr(\$0,2,19) >= t' | grep -c -E 'RemoteCertificate|Runner connect error'")
  case "$tok$cert" in *[!0-9]*|'') unknown+=("$c: could not read listener logs"); continue;; esac
  evidence+=("$c: listener logs read: $nlogs; token-mint failures: ${tok:-?}; cert/connect errors in tail: ${cert:-?}")
  [ "${tok:-0}" -gt 0 ] && stalled+=("$c: entrypoint could not mint a registration token ${tok}x in ${LOOP_MIN} min (restart loop)")
  [ "${cert:-0}" -gt 0 ] && stalled+=("$c: listener logging certificate/connect errors")
done

# 3. GitHub's side: is anything QUEUED for a runner (not merely pending on the concurrency
#    group) for longer than STALE_MIN? If gh cannot answer, that is UNKNOWN, not "no queue".
#    gh's own --jq does the arithmetic: the host has no jq, and a missing jq once printed an
#    empty count here instead of failing.
lim=$((STALE_MIN*60))
if q=$(ghx api "repos/${REPO}/actions/runs?status=queued&per_page=50" --jq \
        "(.workflow_runs|length|tostring), (.workflow_runs[] | select((now - (.created_at|fromdateiso8601)) > ${lim}) | \"\(.id) \(.name) since \(.created_at)\")" 2>/dev/null) \
   && [[ "$(head -1 <<<"$q")" =~ ^[0-9]+$ ]]; then
  old=$(tail -n +2 <<<"$q")
  evidence+=("github: $(head -1 <<<"$q") run(s) queued")
  [ -n "$old" ] && stalled+=("github: queued > ${STALE_MIN} min: $(echo "$old" | tr '\n' ';')")
else
  unknown+=("github: gh api failed (host TLS or auth?), queue not visible")
fi

# 4. Something looks wrong: did a captive portal start while we were looking? Ask again, because
#    the slow calls above can take minutes and portals come and go. If so the findings are the
#    network's symptoms: report CAPTIVE and keep the findings as held back, not as a runner fault.
if [ ${#stalled[@]} -gt 0 ] || [ ${#unknown[@]} -gt 0 ]; then
  captive_probe
  if [ "$PROBE_VERDICT" = CAPTIVE ]; then
    echo "CAPTIVE $(probe_first_line)"
    echo "  the checks below found trouble while the portal was up; they are NOT a runner verdict."
    echo "  wait and retry later. Nothing was restarted."
    for e in "${stalled[@]}"; do echo "  held back (would be STALLED): $e"; done
    for e in "${unknown[@]}"; do echo "  held back (would be UNKNOWN): $e"; done
    for e in "${evidence[@]}"; do echo "  $e"; done
    printf '%s\n' "$PROBE_LINES" | tail -n +2
    exit 3
  fi
fi

if [ ${#stalled[@]} -gt 0 ]; then
  echo "STALLED $(IFS='|'; echo "${stalled[*]}")"; rc=1
elif [ ${#unknown[@]} -gt 0 ]; then
  echo "UNKNOWN $(IFS='|'; echo "${unknown[*]}")"; rc=2
else
  echo "OK"; rc=0
fi
for e in "${evidence[@]}" "${unknown[@]}"; do echo "  $e"; done
echo "  captive probe: $PROBE_VERDICT $(probe_first_line)"
exit $rc
