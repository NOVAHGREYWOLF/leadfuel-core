<#
Register (or remove) the Windows scheduled task "WATCH surface parity", weekly.

  .\Register-SurfaceParity.ps1 -Config C:\path\parity-config.json     register (Monday 06:10 local)
  .\Register-SurfaceParity.ps1 -Remove                                unregister
  .\Register-SurfaceParity.ps1 -Config ... -WhatIf                    show only

NOT REGISTERED BY THE PR THAT ADDS IT. The config names the commands that reach the web, the
connector and the arm, so it decides what leaves the machine (Law 9): the owner writes it and runs this.
The task writes %LOCALAPPDATA%\surface-parity\status.json; state ok, failed or unknown (see surface_parity.py).
Runs under Windows PowerShell 5.1. Keep it ASCII and free of ternary, ??, &&.
#>
param(
    [string]$Config = '',
    [string]$Python = 'C:\Users\novah\AppData\Local\Programs\Python\Python312\python.exe',
    [string]$Script = (Join-Path $PSScriptRoot 'surface_parity.py'),
    [string]$Time = '06:10',
    [string]$TaskName = 'WATCH surface parity',
    [switch]$Remove,
    [switch]$WhatIf
)
$ErrorActionPreference = 'Stop'
if ($Remove) {
    if ($WhatIf) { Write-Host "Would unregister $TaskName"; return }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    return
}
if (-not $Config -or -not (Test-Path $Config)) { throw 'Pass -Config with an existing parity-config.json' }
$arg = '"' + $Script + '" --config "' + $Config + '" --write'
$action = New-ScheduledTaskAction -Execute $Python -Argument $arg
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At $Time
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 1)
if ($WhatIf) { Write-Host "Would register $TaskName : $Python $arg weekly Monday $Time"; return }
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings | Out-Null
