<#
OWNER STEP (NODE, task desks-3-6). Stops file-system scans that a session left running.

WHY. On 2026-11-23 two `find /` processes launched from Git Bash by agent sessions were running for
2 hours and 24 minutes. In Git Bash `/` includes every drive mount, so each one walks all of F:\
(300+ worktrees). The older one had used 3,965 CPU-seconds, about one core, and was still going. A
`find` that has run for more than 30 minutes with `/` or a drive root as its search root is a leak,
not a search anyone is waiting for. `python node/cpu_who.py` measures how much of the machine such
scans hold and names the sessions that left them.

WHAT IT DOES. Lists GNU `find.exe` processes whose search root is `/` or a drive root and that are
older than -MinAgeMinutes (default 30). By DEFAULT IT ONLY PRINTS. It stops them only with -Apply.
It touches no other process, no file, no setting. It needs no administrator rights for processes
that are yours. The rule is the same as node/cpu_who.py (find_leaks); tests/test_stop_leaked_scans.py
holds both to one table of cases.

    Stop-LeakedScans.cmd                                        # look (double-click works)
    Stop-LeakedScans.cmd -Apply                                 # stop what it listed

The .cmd is there because a plain `powershell -File Stop-LeakedScans.ps1` is refused on GREYWOLF
("running scripts is disabled", measured 2026-11-23: every execution-policy scope is Undefined, so
the Windows client default, Restricted, applies). The .cmd adds `-ExecutionPolicy Bypass` for that
one process; it changes no setting. Without the .cmd:

    powershell -NoProfile -ExecutionPolicy Bypass -File Stop-LeakedScans.ps1 -Apply

What it will NOT stop, and says so:
  - The Windows text filter (System32\find.exe): it has no search root.
  - A `find` whose command line or start time it could not read: printed as UNKNOWN, never as clean.
  - A `find /x` it cannot tell from a Windows switch (no executable path): printed as AMBIGUOUS.
  - A pid that has changed hands since the list was made: it re-reads the start time before it stops.

If a session was waiting on one of those finds, that session's command ends with an error and the
session carries on: the scan was already beyond any useful time.
#>
param(
    [int]$MinAgeMinutes = 30,
    [switch]$Apply
)

$ErrorActionPreference = 'Stop'

# Space-separated; double quotes group; a backslash is just a backslash. Same rule as cpu_who.tokenize.
function Split-CommandLine([string]$cmd) {
    $out = New-Object System.Collections.Generic.List[string]
    $cur = New-Object System.Text.StringBuilder
    $quoted = $false
    $started = $false
    foreach ($ch in $cmd.ToCharArray()) {
        if ($ch -eq '"') { $quoted = -not $quoted; $started = $true }
        elseif ([char]::IsWhiteSpace($ch) -and -not $quoted) {
            if ($started) { $out.Add($cur.ToString()); [void]$cur.Clear(); $started = $false }
        }
        else { [void]$cur.Append($ch); $started = $true }
    }
    if ($started) { $out.Add($cur.ToString()) }
    return , $out.ToArray()
}

# The search roots of a GNU find command line: everything before the first expression.
function Get-SearchRoots([string]$cmd) {
    $toks = Split-CommandLine $cmd
    $roots = @()
    for ($i = 1; $i -lt $toks.Count; $i++) {
        $t = $toks[$i]
        if ($t -in '-H', '-L', '-P') { continue }
        if ($t.StartsWith('-') -or $t -in '(', '!', ')') { break }
        $roots += $t
    }
    return $roots     # callers wrap the call in @(...): an empty or one-item result is still an array
}

function Test-Root([string]$p) { return ($p -eq '/' -or $p -eq '//' -or $p -match '^[A-Za-z]:[\\/]+$') }

# A Git Bash drive mount (/c, /f/). For GNU find it is a drive root; it is also spelled like a
# Windows find switch (/c /i /n /v), so it only counts when the executable is known not to be one.
function Test-MsysDrive([string]$p) { return ($p -match '^/[A-Za-z]/*$') }

function Test-WindowsFind([string]$exe) { return ($exe -match '\\(system32|syswow64|sysnative)\\') }

function Get-Leaks([object[]]$procs, [int]$minAge) {
    $leaks = @(); $ambiguous = @(); $unreadable = @()
    foreach ($p in $procs) {
        $exe = [string]$p.ExecutablePath
        if ($exe -and (Test-WindowsFind $exe)) { continue }
        $cmd = [string]$p.CommandLine
        if (-not $cmd -or -not $p.CreationDate) { $unreadable += $p; continue }
        $age = [math]::Round(((Get-Date) - $p.CreationDate).TotalMinutes, 0)
        if ($age -lt $minAge) { continue }
        $roots = @(Get-SearchRoots $cmd)
        if (@($roots | Where-Object { Test-Root $_ }).Count -gt 0) { $leaks += $p }
        elseif (@($roots | Where-Object { Test-MsysDrive $_ }).Count -gt 0) {
            if ($exe) { $leaks += $p } else { $ambiguous += $p }
        }
    }
    return [pscustomobject]@{ Leaks = $leaks; Ambiguous = $ambiguous; Unreadable = $unreadable }
}

# Dot-sourcing this file (the tests do) loads the functions and runs nothing.
if ($MyInvocation.InvocationName -ne '.') {
    $procs = @(Get-CimInstance Win32_Process -Filter "Name='find.exe'")
    if ($procs.Count -eq 0) { Write-Output 'No find.exe is running. Nothing to do.'; exit 0 }
    $r = Get-Leaks $procs $MinAgeMinutes

    if ($r.Unreadable.Count -gt 0) {
        Write-Output "UNKNOWN for $($r.Unreadable.Count) find.exe: command line or start time not readable from here (pids $(($r.Unreadable | ForEach-Object ProcessId) -join ', ')). They are NOT cleared."
    }
    if ($r.Ambiguous.Count -gt 0) {
        Write-Output "AMBIGUOUS for $($r.Ambiguous.Count) find.exe with a /x root and no executable path (pids $(($r.Ambiguous | ForEach-Object ProcessId) -join ', ')). Not listed as leaks."
    }
    if ($r.Leaks.Count -eq 0) {
        Write-Output "No find older than $MinAgeMinutes minutes searches from / or a drive root."
        exit 0
    }

    foreach ($l in $r.Leaks) {
        $age = [math]::Round(((Get-Date) - $l.CreationDate).TotalMinutes, 0)
        $roots = (@(Get-SearchRoots ([string]$l.CommandLine)) | Where-Object { (Test-Root $_) -or (Test-MsysDrive $_) }) -join ' '
        if (-not $Apply) {
            Write-Output "WOULD STOP pid $($l.ProcessId) (age $age min, root $roots)"
            continue
        }
        # The pid may have been reused since the list was made: stop it only if it is still the same process.
        $now = Get-CimInstance Win32_Process -Filter "ProcessId=$($l.ProcessId)"
        if ($null -eq $now) { Write-Output "pid $($l.ProcessId) already gone."; continue }
        if ($now.Name -ne 'find.exe' -or $now.CreationDate -ne $l.CreationDate) {
            Write-Output "pid $($l.ProcessId) is no longer the same process; left alone."
            continue
        }
        try {
            Stop-Process -Id $l.ProcessId -Force
            Write-Output "Stopped pid $($l.ProcessId) (age $age min, root $roots)"
        } catch {
            Write-Output "Could not stop pid $($l.ProcessId): $($_.Exception.Message)"
        }
    }
    if (-not $Apply) { Write-Output 'Nothing was stopped. Re-run with -Apply to stop the lines above.' }
}
