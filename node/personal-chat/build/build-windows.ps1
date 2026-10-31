<#
    build-windows.ps1 - build the Personal Chat Windows installer, UNSIGNED, on this PC.

      .\build-windows.ps1 -Version 0.1.0
      .\build-windows.ps1 -Version 0.1.0 -SkipInstaller      # frozen app only

    Steps, each refusing rather than guessing:
      1. ladder.json from NodeSpec.ps1 (Export-Ladder.ps1; the ladder is never restated here)
      2. build_info.json: version, unsigned, and the store as NOT configured (preview build)
      3. PyInstaller one-folder freeze of app/personal_chat.py (stdlib only, console window)
      4. Inno Setup compile of personal-chat.iss
      5. SHA-256 of what came out

    HARD GATES, not switches: this script never signs, never uploads, never publishes and never
    turns the store on. Signing waits for the certificate card (V7); selling waits for the Polar
    card. A build from this script is a preview, says so in its file name, and must not be
    distributed.

    Writes only under -OutDir (default: node/personal-chat/dist, gitignored). It does not touch
    home-node/, its build venvs, or any installed NovahOS.
#>
[CmdletBinding()]
param(
    [string]$Version = '0.1.0',
    [string]$NodeSpec = 'F:\Leadfuel\home-node\installer\NodeSpec.ps1',
    [string]$OutDir,
    [string]$Python = 'python',
    [string]$Iscc = (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
    [switch]$SkipInstaller
)
$ErrorActionPreference = 'Stop'

$Build = $PSScriptRoot
$Root  = Split-Path -Parent $Build                     # node/personal-chat
$App   = Join-Path $Root 'app'
if (-not $OutDir) { $OutDir = Join-Path $Root 'dist' }
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "Version must be x.y.z, got '$Version'" }

$Stage = Join-Path $OutDir 'stage'
$Work  = Join-Path $OutDir 'work'
$Final = Join-Path $OutDir 'out'
foreach ($d in $Stage, $Work, $Final) {
    if (Test-Path $d) { Remove-Item -Recurse -Force -LiteralPath $d }
    New-Item -ItemType Directory -Path $d | Out-Null
}

Write-Host '== 1. ladder from NodeSpec.ps1' -ForegroundColor Cyan
& (Join-Path $Build 'Export-Ladder.ps1') -NodeSpec $NodeSpec -Out (Join-Path $Stage 'ladder.json')
Copy-Item -LiteralPath $NodeSpec -Destination (Join-Path $Stage 'NodeSpec.ps1')
Copy-Item -LiteralPath (Join-Path $Build 'setup-windows.ps1') -Destination $Stage
$ladder = Get-Content -Raw (Join-Path $Stage 'ladder.json') | ConvertFrom-Json

Write-Host '== 2. build_info.json (preview: store not configured, unsigned)' -ForegroundColor Cyan
$info = [ordered]@{
    version = $Version; platform = 'windows'; signed = $false
    sale_enabled = $false; store_org_id = $null; store_host = 'api.polar.sh'
    store_hosts_allowed = @('api.polar.sh'); max_seats = 3
    ladder_sha256 = $ladder.sha256
    builtAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
}
$info | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $Stage 'build_info.json') -Encoding UTF8

Write-Host '== 3. PyInstaller freeze' -ForegroundColor Cyan
& $Python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) { throw "PyInstaller is not installed for '$Python'. Install it in a build venv first." }
# Each --add-data is ONE string "src;dest". (A `"a;" + 'b',` inside an array literal is a
# trap: the comma binds tighter than +, and the first build of this script died on it.)
$static = Join-Path $App 'static'
$ladderJson = Join-Path $Stage 'ladder.json'
$infoJson = Join-Path $Stage 'build_info.json'
$pyArgs = @(
    '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--console',
    '--name', 'PersonalChat',
    '--distpath', $Stage, '--workpath', $Work, '--specpath', $Work,
    '--paths', $App,
    '--add-data', "$static;static",
    '--add-data', "$ladderJson;.",
    '--add-data', "$infoJson;.",
    (Join-Path $App 'personal_chat.py')
)
& $Python @pyArgs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed ($LASTEXITCODE)" }
$exe = Join-Path $Stage 'PersonalChat\PersonalChat.exe'
if (-not (Test-Path $exe)) { throw "PyInstaller reported success but $exe does not exist" }

if ($SkipInstaller) {
    Write-Host "Frozen app at $exe (installer skipped)" -ForegroundColor Green
    exit 0
}

Write-Host '== 4. Inno Setup' -ForegroundColor Cyan
if (-not (Test-Path $Iscc)) { throw "Inno Setup not found at $Iscc" }
& $Iscc "/DStage=$Stage" "/DAppVersion=$Version" "/DOutDir=$Final" (Join-Path $Build 'personal-chat.iss')
if ($LASTEXITCODE -ne 0) { throw "ISCC failed ($LASTEXITCODE)" }

Write-Host '== 5. result' -ForegroundColor Cyan
$setup = Get-ChildItem -LiteralPath $Final -Filter 'PersonalChat-Setup-*-UNSIGNED.exe' | Select-Object -First 1
if (-not $setup) { throw "ISCC reported success but no setup exe is in $Final" }
$h = (Get-FileHash -LiteralPath $setup.FullName -Algorithm SHA256).Hash.ToLower()
Write-Host ("{0}  {1:N0} bytes  sha256 {2}" -f $setup.Name, $setup.Length, $h) -ForegroundColor Green
Write-Host 'UNSIGNED PREVIEW. Not for distribution: signing is card V7, selling is the Polar card.' -ForegroundColor Yellow
