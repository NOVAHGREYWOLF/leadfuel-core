<#
Local backup of the three trees that have no git remote, to a second physical drive.
Nothing leaves the machine (Law 9: no cloud, no network path).

  .\Backup-Leadfuel.ps1                 mirror F:\Leadfuel, F:\Claude Sessions, F:\novah -> C:\LeadfuelBackup
  .\Backup-Leadfuel.ps1 -RestoreTest    restore one sample folder to a temp dir and compare it to the source

Logs list counts and sizes only, never file names (/NFL /NDL), so credential files are never
printed. Credential files ARE copied: a backup without them is not a restore.
The destination holds secrets; keep it on a drive only the owner reads.
#>
param(
    [string]$Dest = 'C:\LeadfuelBackup',
    [switch]$RestoreTest
)
$ErrorActionPreference = 'Stop'

$sources = @(
    @{ Src = 'F:\Leadfuel';        Name = 'Leadfuel' },
    @{ Src = 'F:\Claude Sessions'; Name = 'Claude Sessions' },
    @{ Src = 'F:\novah';           Name = 'novah' }
)
# Rebuildable: dependencies and caches. .git is kept: F:\Leadfuel and F:\Claude Sessions have no
# remote and carry unpushed commits, so their history exists nowhere else.
$excludeDirs = @('node_modules', '.venv', 'venv', 'venv-assistant', '__pycache__', '.ruff_cache', '.pytest_cache', '.mypy_cache')

$logDir = Join-Path $Dest '_logs'
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir ("backup-{0:yyyyMMdd-HHmmss}.log" -f (Get-Date))

# Refuse to run on the same physical disk as the source.
$srcDisk = (Get-Partition -DriveLetter 'F').DiskNumber
$dstDisk = (Get-Partition -DriveLetter $Dest.Substring(0,1)).DiskNumber
if ($srcDisk -eq $dstDisk) { throw "Destination is on the same physical disk (#$dstDisk) as the source." }

if ($RestoreTest) {
    $sample = Join-Path $Dest 'Leadfuel\home-node\installer'
    $orig   = 'F:\Leadfuel\home-node\installer'
    $tmp    = Join-Path $env:TEMP ("restore-test-{0:yyyyMMddHHmmss}" -f (Get-Date))
    robocopy $sample $tmp /E /R:1 /W:1 /NFL /NDL /NP /NJH | Out-Null
    $h = { param($p) Get-ChildItem $p -Recurse -File | Sort-Object FullName | ForEach-Object { '{0}|{1}' -f $_.FullName.Substring($p.Length), (Get-FileHash $_.FullName -Algorithm SHA256).Hash } }
    $diff = Compare-Object (& $h $orig) (& $h $tmp)
    Remove-Item $tmp -Recurse -Force
    if ($diff) { "RESTORE TEST FAILED: $($diff.Count) differences"; exit 1 }
    "RESTORE TEST OK: $sample restored and matched $orig by SHA256"
    exit 0
}

$bad = 0
foreach ($s in $sources) {
    $to = Join-Path $Dest $s.Name
    "== $($s.Src) -> $to" | Add-Content $log
    robocopy $s.Src $to /MIR /XD @excludeDirs /R:1 /W:1 /MT:4 /NFL /NDL /NP /LOG+:$log | Out-Null
    # robocopy exit codes >= 8 are failures
    if ($LASTEXITCODE -ge 8) { $bad++; "FAILED $($s.Src) exit=$LASTEXITCODE" | Add-Content $log }
}
"DONE failures=$bad" | Add-Content $log
exit $bad
