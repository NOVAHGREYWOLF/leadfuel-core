<#
    setup-windows.ps1 - first-run setup for Personal Chat on Windows. The installer runs it
    once after copying the files; the person can run it again from the Start Menu.

    1. Runs the spec check (the bundled NodeSpec.ps1, the same file the home-node installer
       uses) and writes ONLY its tier verdict to %APPDATA%\PersonalChat\config.json. Machine
       details stay in memory; nothing is sent anywhere.
    2. Checks Ollama. If it is missing it says how to get it and, with the person's yes,
       runs `winget install Ollama.Ollama`. It never installs anything silently.
    3. Offers to download the tier's chat model with `ollama pull`, showing the size first.

    Every step that downloads asks first, unless -Yes was given (for a test machine).
#>
[CmdletBinding()]
param(
    [string]$AppDir = $PSScriptRoot,
    [string]$ConfigDir = (Join-Path $env:APPDATA 'PersonalChat'),
    [switch]$Yes,
    [switch]$NoDownloads
)
$ErrorActionPreference = 'Stop'

function Ask([string]$q) {
    if ($Yes) { return $true }
    if ($NoDownloads) { return $false }
    $a = Read-Host "$q [y/N]"
    return ($a -match '^(y|yes)$')
}

$spec = Join-Path $AppDir 'NodeSpec.ps1'
if (-not (Test-Path $spec)) { throw "NodeSpec.ps1 is missing from $AppDir; reinstall Personal Chat" }
. $spec -Quiet

Write-Host 'Checking what this computer can run...' -ForegroundColor Cyan
$s = Get-NodeSpec
$t = $s.tier

New-Item -ItemType Directory -Force -Path $ConfigDir | Out-Null
$config = [ordered]@{
    tier = [ordered]@{ tier = $t.tier; chatModel = $t.chatModel; note = $t.note }
    measuredAt = $s.collectedAt
    measuredBy = 'NodeSpec.ps1'
}
$config | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $ConfigDir 'config.json') -Encoding UTF8
Write-Host ("Tier {0}: chat model {1}" -f $t.tier, $t.chatModel) -ForegroundColor Green
Write-Host $t.note

if (-not $s.ollama.installed) {
    Write-Host ''
    Write-Host 'Personal Chat needs Ollama, the free local model server (ollama.com).' -ForegroundColor Yellow
    if ((Get-Command winget -ErrorAction SilentlyContinue) -and (Ask 'Install Ollama now with winget?')) {
        winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
    } else {
        Write-Host 'Install it from https://ollama.com/download, then run "Personal Chat setup" again.'
        exit 0
    }
}

$have = @($s.ollama.models)
if ($have -contains $t.chatModel -or $have -contains "$($t.chatModel):latest") {
    Write-Host "$($t.chatModel) is already downloaded." -ForegroundColor Green
    exit 0
}
$gb = $script:MODEL_GB[$t.chatModel]
$size = if ($gb) { "about $gb GB" } else { 'size unknown' }
if (Ask "Download the chat model $($t.chatModel) now ($size)?") {
    $ollama = (Get-Command ollama -ErrorAction SilentlyContinue).Source
    if (-not $ollama) { $ollama = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe' }
    & $ollama pull $t.chatModel
} else {
    Write-Host "Later, run: ollama pull $($t.chatModel)"
}
