<#
Register (or update, or remove) the Windows scheduled task "WATCH nightly full run".

  .\Register-NightlyFullRun.ps1              copy nightly_full_run.py to %LOCALAPPDATA%\nightly-full-run and register the task
  .\Register-NightlyFullRun.ps1 -Remove      unregister the task (the copied script and the log are left alone)
  .\Register-NightlyFullRun.ps1 -StartOn 2026-10-12   first night is that date (default: the next 05:30)
  .\Register-NightlyFullRun.ps1 -WhatIf      show what would be registered, change nothing

The task runs ONE full serial bare pytest on the hub's origin/main, on this PC, every night, under the
estate's heavy-slot lock, and appends one result line to the log (see nightly_full_run.py for the rules).
Nothing leaves the machine (Law 9): the only network use is the inbound git fetch from the hub's own origin.

WHY 05:30 LOCAL (decided 2026-10-11 from measurements, not taste):
  * hub CI starts its quietest hours between 05:00 and 08:00 Pacific. Of the last 1000 workflow runs
    (2026-10-01 to 2026-10-11), "tests" runs began 6, 2, 8 and 2 times in the four hours 05-08, against
    62 in 12:00-13:59 and 54 in 02:00-04:59.
  * the other scheduled work is finished by then: NovahOS daily backup 02:30, the weekly LeadfuelBackup
    Sunday 03:30 (about 6 min; the owner asked for 03:30-04:00 to stay clear), VAULT private sync 04:30
    (about 8 min).
  * a serial run is about 30-60 min and the slot wait is capped at 90 min, so the worst case ends before 08:00,
    before the daytime desks and CI wake up.

Settings follow the LeadfuelBackup task: current user, interactive logon, limited rights, IgnoreNew.
StartWhenAvailable is OFF on purpose: a night the PC was off is simply a night with no log line (read as UNKNOWN),
never a 4-hour suite starting at 11:00 on top of the owner's day. Wake-to-run is off.

Runs under Windows PowerShell 5.1 (powershell.exe). Keep it ASCII and free of ternary, ??, &&.
#>
param(
    [string]$Python = 'C:\Users\novah\AppData\Local\Programs\Python\Python312\python.exe',
    [string]$Script = (Join-Path $PSScriptRoot 'nightly_full_run.py'),
    [string]$Time = '05:30',
    [string]$StartOn = '',
    [string]$TaskName = 'WATCH nightly full run',
    [switch]$Remove,
    [switch]$WhatIf
)
$ErrorActionPreference = 'Stop'

if ($Remove) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        if ($WhatIf) { "WHATIF: would unregister '$TaskName'"; exit 0 }
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        "Unregistered '$TaskName'. The copied script and the log were left alone."
    } else {
        "No task named '$TaskName'."
    }
    exit 0
}

if (-not (Test-Path -LiteralPath $Python)) { throw "Python not found at $Python" }
if (-not (Test-Path -LiteralPath $Script)) { throw "Script not found at $Script" }
$at = [datetime]::ParseExact($Time, 'HH:mm', [Globalization.CultureInfo]::InvariantCulture)
if ($StartOn -ne '') {
    $day = [datetime]::ParseExact($StartOn, 'yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture)
    $at = $day.Date.Add($at.TimeOfDay)
}
if ($at.Hour -eq 3 -and $at.Minute -ge 30) { throw "$Time is inside the LeadfuelBackup window (03:30-04:00); pick another time." }

$deployDir = Join-Path $env:LOCALAPPDATA 'nightly-full-run'
$deployed = Join-Path $deployDir 'nightly_full_run.py'
$argLine = '--headless "{0}" "{1}"' -f $Python, $deployed

if ($WhatIf) {
    "WHATIF: would copy $Script -> $deployed"
    "WHATIF: would register '$TaskName': daily $Time (first at $at), conhost.exe $argLine, user $env:USERNAME, interactive, limited, IgnoreNew, 5 h limit, no start-when-available, no wake"
    exit 0
}

New-Item -ItemType Directory -Force -Path $deployDir | Out-Null
Copy-Item -LiteralPath $Script -Destination $deployed -Force
$h1 = (Get-FileHash -LiteralPath $Script -Algorithm SHA256).Hash
$h2 = (Get-FileHash -LiteralPath $deployed -Algorithm SHA256).Hash
if ($h1 -ne $h2) { throw 'The deployed copy does not match the source; refusing to register.' }

# conhost --headless: no console window flashes on the owner's desktop (the NODE runner-stall task does the same).
$action = New-ScheduledTaskAction -Execute 'conhost.exe' -Argument $argLine -WorkingDirectory $deployDir
$trigger = New-ScheduledTaskTrigger -Daily -At $at
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 5)
$settings.StartWhenAvailable = $false
$settings.WakeToRun = $false
$desc = 'WATCH Q354: one full serial bare pytest on the hub origin/main, under the heavy-slot lock; one result line per night in F:\Claude Sessions\handoff\nightly-full-run.log. Nothing leaves the machine.'
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description $desc -Force | Out-Null

$t = Get-ScheduledTask -TaskName $TaskName
$i = $t | Get-ScheduledTaskInfo
"Registered '$TaskName': daily $Time, next run $($i.NextRunTime)"
"Script copy: $deployed (sha256 $h2)"
"Action: conhost.exe $argLine"
