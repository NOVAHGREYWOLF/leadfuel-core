<#
Local backup of the three trees that have no git remote, to a second physical drive.
Nothing leaves the machine (Law 9: no cloud, no network path).

  .\Backup-Leadfuel.ps1                 mirror F:\Leadfuel, F:\Claude Sessions, F:\novah -> C:\LeadfuelBackup
  .\Backup-Leadfuel.ps1 -Verify         compare each tree with its backup, list-only (robocopy /L): counts and bytes
  .\Backup-Leadfuel.ps1 -RestoreTest    restore a random folder and a random sample of files from each tree to a
                                        temp dir and compare them to the source by SHA256

Logs and reports list counts and sizes only, never file names (/NFL /NDL), so credential files are never
printed. Credential files ARE copied: a backup without them is not a restore.
The destination holds secrets; keep it on a drive only the owner reads.

Runs under Windows PowerShell 5.1 (powershell.exe), which is what the scheduled task uses. Keep it ASCII,
and keep out anything 5.1 lacks (no ternary, no ??, no &&).
#>
param(
    [string]$Dest = 'C:\LeadfuelBackup',
    [switch]$Verify,
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

# Refuse to run on the same physical disk as any source. This runs BEFORE anything is created or
# written, so a refused run leaves no trace on the wrong disk. If the disk cannot be established the
# answer is "unknown", and unknown refuses too.
function Get-DiskNumbers([string]$Path) {
    @(Get-Partition -DriveLetter $Path.Substring(0, 1) | ForEach-Object { $_.DiskNumber })
}
$dstDisks = Get-DiskNumbers $Dest
if ($dstDisks.Count -eq 0) { throw "Cannot establish which physical disk holds $Dest; refusing (unknown is not safe)." }
foreach ($s in $sources) {
    $srcDisks = Get-DiskNumbers $s.Src
    if ($srcDisks.Count -eq 0) { throw "Cannot establish which physical disk holds $($s.Src); refusing (unknown is not safe)." }
    foreach ($d in $srcDisks) {
        if ($dstDisks -contains $d) { throw "Destination is on the same physical disk (#$d) as the source $($s.Name)." }
    }
}

# Summary row of a robocopy /L run: total, copied (would copy), skipped, mismatch, failed, extras.
function Get-RoboRow([object[]]$Output, [string]$Row) {
    $line = $Output | Where-Object { "$_" -match "^\s*$Row\s*:\s*\d" } | Select-Object -Last 1
    if (-not $line) { return $null }
    $n = [regex]::Matches("$line", '\d+') | ForEach-Object { [int64]$_.Value }
    @{ Total = $n[0]; Copied = $n[1]; Skipped = $n[2]; Mismatch = $n[3]; Failed = $n[4]; Extras = $n[5] }
}
function Get-TreeScan([string]$From, [string]$To) {
    # /L = list only: nothing is copied, deleted or created. /NFL /NDL: no file or folder names.
    $out = robocopy $From $To /L /MIR /XD @excludeDirs /R:0 /W:0 /NFL /NDL /NJH /NP /BYTES 2>&1
    $code = $LASTEXITCODE
    $f = Get-RoboRow $out 'Files'
    $b = Get-RoboRow $out 'Bytes'
    if (-not $f -or -not $b -or $code -ge 8) { throw "Scan of $From could not be read (robocopy exit $code); that is unknown, not clean." }
    @{ Files = $f; Bytes = $b; Exit = $code }
}

if ($Verify) {
    $differ = 0
    foreach ($s in $sources) {
        $to = Join-Path $Dest $s.Name
        if (-not (Test-Path -LiteralPath $to)) { "VERIFY $($s.Name): backup folder is missing"; $differ++; continue }
        # Source vs backup: Total is the source's count; Copied/Mismatch/Extras are what would still change.
        $a = Get-TreeScan $s.Src $to
        # Backup alone (against a name that does not exist; /L never creates it): the backup's own count.
        $z = Get-TreeScan $to (Join-Path $env:TEMP 'verify-no-such-dir')
        $pending = $a.Files.Copied + $a.Files.Mismatch + $a.Files.Extras
        "VERIFY {0}: source files={1} bytes={2} | backup files={3} bytes={4} | would-copy={5} mismatch={6} extras={7}" -f `
            $s.Name, $a.Files.Total, $a.Bytes.Total, $z.Files.Total, $z.Bytes.Total, $a.Files.Copied, $a.Files.Mismatch, $a.Files.Extras
        if ($pending -ne 0 -or $a.Files.Total -ne $z.Files.Total -or $a.Bytes.Total -ne $z.Bytes.Total) { $differ++ }
    }
    if ($differ -eq 0) { 'VERIFY OK: every tree matches its backup' } else { "VERIFY DIFFERENCES in $differ tree(s); the trees are live, so small counts can be edits made since the backup" }
    exit $differ
}

if ($RestoreTest) {
    # One restored file against its source: ok, drift (the source changed or went away since the backup,
    # so it cannot be compared), or bad (the restored copy is missing or its SHA256 differs from an
    # unchanged source).
    function Compare-Restored($Backup, [string]$Restored, [string]$Source) {
        if (-not (Test-Path -LiteralPath $Restored)) { return 'bad' }
        if (-not (Test-Path -LiteralPath $Source)) { return 'drift' }
        $si = Get-Item -LiteralPath $Source -Force
        if ($si.LastWriteTime -ne $Backup.LastWriteTime -or $si.Length -ne $Backup.Length) { return 'drift' }
        $hr = (Get-FileHash -LiteralPath $Restored -Algorithm SHA256).Hash
        $hs = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash
        if ($hr -eq $hs) { return 'ok' } else { return 'bad' }
    }
    $tmp = Join-Path $env:TEMP ("restore-test-{0:yyyyMMddHHmmss}" -f (Get-Date))
    $fail = 0
    # Only files older than two days and under 50 MB are drawn, so live edits and big files do not
    # turn the test into noise or into a heavy job.
    $cut = (Get-Date).AddDays(-2)
    try {
        foreach ($s in $sources) {
            $to = Join-Path $Dest $s.Name
            $pool = @(Get-ChildItem -LiteralPath $to -Recurse -File -Force -ErrorAction SilentlyContinue -ErrorVariable enumErr |
                Where-Object { $_.LastWriteTime -lt $cut -and $_.Length -le 50MB })
            if ($pool.Count -eq 0) { "RESTORE TEST FAILED ($($s.Name)): no files to draw from, so nothing was tested"; $fail++; continue }

            # 1. Folder restore: one random folder holding 5-50 files, restored the way a real restore
            #    would be (robocopy), every file compared with its source.
            $dirs = @($pool | Group-Object DirectoryName | Where-Object { $_.Count -ge 5 -and $_.Count -le 50 })
            if ($dirs.Count -eq 0) { "RESTORE TEST FAILED ($($s.Name)): no folder of 5-50 files to restore"; $fail++ }
            else {
                $d = $dirs | Get-Random
                $dst = Join-Path $tmp ($s.Name + '-folder')
                robocopy $d.Name $dst /R:1 /W:1 /NFL /NDL /NP /NJH /NJS | Out-Null
                if ($LASTEXITCODE -ge 8) { "RESTORE TEST FAILED ($($s.Name)): folder restore, robocopy exit $LASTEXITCODE"; $fail++ }
                else {
                    $r = @{ ok = 0; drift = 0; bad = 0 }
                    foreach ($f in $d.Group) {
                        $rel = $f.FullName.Substring($to.Length)
                        $r[(Compare-Restored $f (Join-Path $dst $f.Name) ($s.Src + $rel))]++
                    }
                    "tree {0} folder restore: files={1} matched={2} drift={3} mismatch={4}" -f $s.Name, $d.Count, $r.ok, $r.drift, $r.bad
                    if ($r.bad -gt 0 -or $r.ok -eq 0) { "RESTORE TEST FAILED ($($s.Name)): folder restore"; $fail++ }
                }
            }

            # 2. File sample: up to 150 random files, copied out of the backup one by one and compared.
            $pick = @($pool | Get-Random -Count ([Math]::Min(150, $pool.Count)))
            $r = @{ ok = 0; drift = 0; bad = 0 }; $err = 0
            foreach ($f in $pick) {
                $rel = $f.FullName.Substring($to.Length)
                $out = Join-Path (Join-Path $tmp $s.Name) $rel.TrimStart('\')
                try {
                    New-Item -ItemType Directory -Force (Split-Path $out) | Out-Null
                    Copy-Item -LiteralPath $f.FullName -Destination $out -Force
                    $r[(Compare-Restored $f $out ($s.Src + $rel))]++
                } catch { $err++ }
            }
            "tree {0} file sample: drawn={1} of {2} eligible | matched={3} drift={4} mismatch={5} errors={6} | unreadable-during-listing={7}" -f `
                $s.Name, $pick.Count, $pool.Count, $r.ok, $r.drift, $r.bad, $err, @($enumErr).Count
            if ($r.bad -gt 0 -or $err -gt 0 -or $r.ok -eq 0) { "RESTORE TEST FAILED ($($s.Name)): file sample"; $fail++ }
        }
    } finally {
        if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Recurse -Force }
    }
    if ($fail -gt 0) { "RESTORE TEST FAILED: $fail check(s) failed"; exit 1 }
    'RESTORE TEST OK: a folder and a file sample from each tree restored and matched the source by SHA256'
    exit 0
}

$logDir = Join-Path $Dest '_logs'
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir ("backup-{0:yyyyMMdd-HHmmss}.log" -f (Get-Date))

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
