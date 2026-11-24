<#
Register (or remove) the Windows scheduled task "WATCH morning proof read". DEFAULT IS A DRY RUN: nothing is
copied or registered until -Apply is given, because a standing scheduled task is the owner's yes to give.

  .\Register-MorningProof.ps1                  dry run: show what would be copied and registered, change nothing
  .\Register-MorningProof.ps1 -Apply           copy the reader to %LOCALAPPDATA%\morning-proof and register the task
  .\Register-MorningProof.ps1 -Apply -LiveTls  the same, and the task also makes the two certificate handshakes
  .\Register-MorningProof.ps1 -Remove          show what would be unregistered (add -Apply to do it)

The task runs morning_proof.py once a day at 04:50 local (Pacific). It reads local logs, copies other machines
exposed under F:\Claude Sessions\handoff\proof\inputs, and GitHub through read-only gh verbs, and writes the dated
file F:\Claude Sessions\handoff\proof\proof-<date>.txt (and .json). Nothing leaves the machine except those gh
reads. --live-tls is OFF unless -LiveTls is given: one TLS handshake per certificate host, sending no request, and
that is the owner's call.

WHY A COPY: the task must not depend on whichever branch the shared leadfuel-core checkout happens to be on at
04:50. The reader and its one sibling (vault_sync_status.py, which it loads by path) are copied together and the
hashes are compared before the task is registered.

WHY 04:50: the 04:10 pull has finished, the 04:30 full run has started (its verdict arrives hours later and the
file says so: "EARLY"), and 04:45 is the module's own early-read line. The same equivalent, by hand:
  schtasks /Create /TN "WATCH morning proof read" /SC DAILY /ST 04:50 /TR "conhost.exe --headless python F:\Leadfuel\repos\leadfuel-core\watch\morning_proof.py run"
THE TASK'S EXIT CODE IS NOT THE VERDICT (conhost does not pass it through): the dated file is.

StartWhenAvailable is ON: a read is cheap, so a morning the PC was asleep at 04:50 gets a late read for the same
date rather than no file. Wake-to-run is off. Settings otherwise follow the WATCH nightly full run task: current
user, interactive logon, limited rights, IgnoreNew.

Runs under Windows PowerShell 5.1 (powershell.exe). Keep it ASCII and free of ternary, ??, &&.
#>
param(
    [string]$Python = 'C:\Users\novah\AppData\Local\Programs\Python\Python312\python.exe',
    [string]$SourceDir = $PSScriptRoot,
    [string]$Time = '04:50',
    [string]$TaskName = 'WATCH morning proof read',
    [switch]$LiveTls,
    [switch]$Apply,
    [switch]$Remove
)
$ErrorActionPreference = 'Stop'

if ($Remove) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        if (-not $Apply) { "DRY RUN: would unregister '$TaskName' (add -Apply to do it). The copied scripts and the dated files are left alone."; exit 0 }
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        "Unregistered '$TaskName'. The copied scripts and the dated files were left alone."
    } else {
        "No task named '$TaskName'."
    }
    exit 0
}

$names = @('morning_proof.py', 'vault_sync_status.py')
foreach ($n in $names) {
    if (-not (Test-Path -LiteralPath (Join-Path $SourceDir $n))) { throw "Not found: $(Join-Path $SourceDir $n)" }
}
if (-not (Test-Path -LiteralPath $Python)) { throw "Python not found at $Python" }
$at = [datetime]::ParseExact($Time, 'HH:mm', [Globalization.CultureInfo]::InvariantCulture)

$deployDir = Join-Path $env:LOCALAPPDATA 'morning-proof'
$deployed = Join-Path $deployDir 'morning_proof.py'
$runArgs = 'run'
if ($LiveTls) { $runArgs = 'run --live-tls' }
$argLine = '--headless "{0}" "{1}" {2}' -f $Python, $deployed, $runArgs

if (-not $Apply) {
    "DRY RUN (nothing copied, nothing registered; add -Apply to do it)"
    foreach ($n in $names) { "would copy $(Join-Path $SourceDir $n) -> $(Join-Path $deployDir $n)" }
    "would register '$TaskName': daily $Time, conhost.exe $argLine, user $env:USERNAME, interactive, limited, IgnoreNew, 30 min limit, start-when-available, no wake"
    if ($LiveTls) { "live TLS: ON (one handshake to leadfuel.cloud and one to www.leadfuel.cloud, no request sent)" } else { "live TLS: OFF (the two certificate lines read UNKNOWN until the owner approves -LiveTls)" }
    "output: F:\Claude Sessions\handoff\proof\proof-<date>.txt and .json; inputs read from F:\Claude Sessions\handoff\proof\inputs"
    exit 0
}

New-Item -ItemType Directory -Force -Path $deployDir | Out-Null
foreach ($n in $names) {
    $src = Join-Path $SourceDir $n
    $dst = Join-Path $deployDir $n
    Copy-Item -LiteralPath $src -Destination $dst -Force
    $h1 = (Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash
    $h2 = (Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash
    if ($h1 -ne $h2) { throw "The deployed copy of $n does not match the source; refusing to register." }
}

# conhost --headless: no console window flashes on the owner's desktop (the WATCH nightly full run does the same).
$action = New-ScheduledTaskAction -Execute 'conhost.exe' -Argument $argLine -WorkingDirectory $deployDir
$trigger = New-ScheduledTaskTrigger -Daily -At $at
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$settings.StartWhenAvailable = $true
$settings.WakeToRun = $false
$desc = 'WATCH p16-2: one read-only pass that writes OK, FAIL or UNKNOWN for every watcher to F:\Claude Sessions\handoff\proof\proof-<date>.txt. The dated file is the verdict, not the exit code.'
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description $desc -Force | Out-Null

$t = Get-ScheduledTask -TaskName $TaskName
$i = $t | Get-ScheduledTaskInfo
"Registered '$TaskName': daily $Time, next run $($i.NextRunTime)"
foreach ($n in $names) { "Script copy: $(Join-Path $deployDir $n)" }
"Action: conhost.exe $argLine"
