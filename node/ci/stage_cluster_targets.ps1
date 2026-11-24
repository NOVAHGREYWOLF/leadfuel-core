<#
.SYNOPSIS
  Stage the R620 and R710 as targets of node/cluster_route.py. Dry-run by default.

.DESCRIPTION
  NODE cluster-job-router. The repo's node/cluster_targets.json ships the R620 and R710 disabled and
  names them by ssh alias only. This script writes a LOCAL override targets file (on this PC, outside
  any repo) that enables them by user@address, and prints the one environment variable that points
  cluster_route.py at it. It changes nothing on the R620, the R710 or VM 102: a routed job there runs
  in a mktemp directory as nobody, under nice and timeout, and the directory is removed after.

  Without -Apply it only prints what it would write and the read-only checks it would run.
  -Apply writes the override file and runs the read-only checks (hostname, nproc, loadavg, runuser).
  -Remove deletes the override file again (the whole change is that one file).

  The addresses are parameters. Defaults are the private LAN addresses from the 2026-11-18 hosts map,
  reached from this PC with the existing root key (read 2026-11-23); cluster_route.py refuses any
  address that is not loopback, private or tailnet.

.EXAMPLE
  powershell -File node\ci\stage_cluster_targets.ps1              # dry-run: prints the plan
  powershell -File node\ci\stage_cluster_targets.ps1 -Apply       # write the override, check access
  powershell -File node\ci\stage_cluster_targets.ps1 -Remove      # undo
#>
param(
  [switch]$Apply,
  [switch]$Remove,
  [string]$R620 = "root@10.20.0.52",
  [string]$R710 = "root@10.20.0.51",
  [string]$Out = (Join-Path $env:LOCALAPPDATA "cluster_route\targets.json"),
  [string]$RepoTargets = (Join-Path $PSScriptRoot "..\cluster_targets.json")
)
$ErrorActionPreference = "Stop"

if ($Remove) {
  if (Test-Path $Out) { Remove-Item $Out; "removed $Out" } else { "nothing to remove at $Out" }
  "unset CLUSTER_ROUTE_TARGETS in any shell that set it"
  exit 0
}

$doc = Get-Content $RepoTargets -Raw | ConvertFrom-Json
foreach ($t in $doc.targets) {
  if ($t.id -eq "r620") { $t.ssh = $R620; $t.enabled = $true }
  if ($t.id -eq "r710") { $t.ssh = $R710; $t.enabled = $true }
}
$doc.about = "LOCAL override written by stage_cluster_targets.ps1 on $(Get-Date -Format s). Undo: -Remove."
$json = $doc | ConvertTo-Json -Depth 5

$checks = foreach ($h in $R620, $R710) {
  ,@("ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", $h,
     "hostname; nproc; cat /proc/loadavg; command -v runuser timeout nice mktemp tar python3")
}

if (-not $Apply) {
  "DRY-RUN. Would write $Out :"
  $json
  ""
  "Would run these read-only checks:"
  $checks | ForEach-Object { "  " + ($_ -join " ") }
  ""
  "Then: `$env:CLUSTER_ROUTE_TARGETS = '$Out'; python node\cluster_route.py probe"
  exit 0
}

New-Item -ItemType Directory -Force (Split-Path $Out) | Out-Null
Set-Content -Path $Out -Value $json -Encoding utf8
"wrote $Out"
foreach ($c in $checks) {
  "== $($c[5])"
  & $c[0] $c[1..($c.Length - 1)]
  if ($LASTEXITCODE -ne 0) { "check failed (exit $LASTEXITCODE): this target will probe as unknown" }
}
"Next: `$env:CLUSTER_ROUTE_TARGETS = '$Out'; python node\cluster_route.py probe"
