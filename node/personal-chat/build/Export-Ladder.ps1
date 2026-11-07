<#
    Export-Ladder.ps1 - write the capability-tier ladder as ladder.json, FROM NodeSpec.ps1.

    NodeSpec.ps1 (home-node/installer, estate repo) holds the ONLY copy of the ladder. This
    script does not restate a single threshold or model name: it dot-sources NodeSpec.ps1 and
    serialises what it finds, plus the SHA-256 of the file it read, so a build can say exactly
    which ladder it shipped. Dot-sourcing NodeSpec.ps1 without -OutDir runs no inspection.

    Runs on Windows PowerShell 5.1 and on pwsh 7 (so a Mac can run it too, if pwsh is there).

    .\Export-Ladder.ps1 -NodeSpec F:\Leadfuel\home-node\installer\NodeSpec.ps1 -Out ladder.json
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$NodeSpec,
    [Parameter(Mandatory)][string]$Out
)
$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $NodeSpec)) { throw "NodeSpec.ps1 not found at $NodeSpec" }
$specPath = (Resolve-Path -LiteralPath $NodeSpec).Path
$sha = (Get-FileHash -LiteralPath $specPath -Algorithm SHA256).Hash.ToLower()

. $specPath -Quiet

if (-not $script:TIERS -or $script:TIERS.Count -lt 1) {
    throw "NodeSpec.ps1 was read but defined no tiers; refusing to write an empty ladder"
}
if (-not (Get-Command Get-NodeTier -ErrorAction SilentlyContinue)) {
    throw "NodeSpec.ps1 defines no Get-NodeTier; refusing to guess the CPU-only row"
}

$tiers = foreach ($t in $script:TIERS) {
    [ordered]@{ tier = $t.Tier; minVramGB = $t.MinVram; chatModel = $t.Chat
                batchModel = $t.Batch; note = $t.Note }
}
# The CPU-only row is not in $TIERS; ask NodeSpec's own function for it.
$cpu = Get-NodeTier -HasNvidia $false -VramGB 0

$ladder = [ordered]@{
    source      = 'home-node/installer/NodeSpec.ps1'
    sha256      = $sha
    exportedAt  = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
    tiers       = @($tiers)
    cpuOnly     = [ordered]@{ tier = $cpu.tier; chatModel = $cpu.chatModel; note = $cpu.note }
    embed       = [ordered]@{ model = $script:EMBED_MODEL; dim = $script:EMBED_DIM }
    modelGB     = $script:MODEL_GB
}
$dir = Split-Path -Parent $Out
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
$ladder | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $Out -Encoding UTF8
Write-Host "ladder.json: $($tiers.Count) tiers + $($cpu.tier) from $specPath (sha256 $($sha.Substring(0,12)))"
