<#
OWNER STEP (NODE, task desks-3-6). Stops file-system scans that a session left running.

WHY. On 2026-11-23 two `find /` processes launched from Git Bash by agent sessions were running for
2 hours and 24 minutes. In Git Bash `/` includes every drive mount, so each one walks all of F:\
(300+ worktrees). The older one had used 3,965 CPU-seconds, about one core, and was still going. A
`find` that has run for more than 30 minutes with `/` or a drive root as its search root is a leak,
not a search anyone is waiting for.

WHAT IT DOES. Lists `find.exe` processes whose search root is `/` or a drive root and that are older
than -MinAgeMinutes (default 30). By DEFAULT IT ONLY PRINTS. It stops them only with -Apply. It
touches no other process, no file, no setting. It needs no administrator rights.

    powershell -NoProfile -File Stop-LeakedScans.ps1            # look
    powershell -NoProfile -File Stop-LeakedScans.ps1 -Apply     # stop what it listed

If a session was waiting on one of those finds, that session's command ends with an error and the
session carries on: the scan was already beyond any useful time.
#>
param(
    [int]$MinAgeMinutes = 30,
    [switch]$Apply
)

$ErrorActionPreference = 'Stop'

function Get-SearchRoot([string]$cmd) {
    # First argument after the executable that is not an option. `find / -iname x` -> '/'.
    $m = [regex]::Match($cmd, '^\s*"?[^"]*find(\.exe)?"?\s+(?<rest>.*)$', 'IgnoreCase')
    if (-not $m.Success) { return $null }
    foreach ($tok in ($m.Groups['rest'].Value -split '\s+')) {
        if ($tok -eq '') { continue }
        if ($tok.StartsWith('-')) { return $null }   # options before any path: root is '.', not a leak
        return $tok.Trim('"')
    }
    return $null
}

$rows = @()
$procs = Get-CimInstance Win32_Process -Filter "Name='find.exe'"
if ($null -eq $procs) { Write-Output 'No find.exe is running. Nothing to do.'; exit 0 }
foreach ($p in $procs) {
    $cmd = [string]$p.CommandLine
    $root = Get-SearchRoot $cmd
    $age = [math]::Round(((Get-Date) - $p.CreationDate).TotalMinutes, 0)
    $isRoot = $root -and ($root -eq '/' -or $root -match '^[A-Za-z]:[\\/]?$' -or $root -match '^/[a-z]/?$')
    $rows += [pscustomobject]@{ Pid = $p.ProcessId; AgeMin = $age; Root = $root; Leak = ($isRoot -and $age -ge $MinAgeMinutes); Cmd = $cmd }
}

$rows | Format-Table Pid, AgeMin, Root, Leak -AutoSize | Out-String | Write-Output
$leaks = @($rows | Where-Object Leak)
if ($leaks.Count -eq 0) { Write-Output "No find older than $MinAgeMinutes minutes searches from / or a drive root."; exit 0 }
foreach ($l in $leaks) {
    if ($Apply) {
        Stop-Process -Id $l.Pid -Force
        Write-Output "Stopped pid $($l.Pid) (age $($l.AgeMin) min): $($l.Cmd)"
    } else {
        Write-Output "WOULD STOP pid $($l.Pid) (age $($l.AgeMin) min): $($l.Cmd)"
    }
}
if (-not $Apply) { Write-Output 'Nothing was stopped. Re-run with -Apply to stop the lines above.' }
