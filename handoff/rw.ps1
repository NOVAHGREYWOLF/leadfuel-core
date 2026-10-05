param([string]$Repo, [string]$Ref, [ValidateSet('plan','apply')][string]$Mode = 'plan')
# Plan (or apply) a repo's .railway/railway.ts at $Ref, from the repo's linked checkout via --file.
# $env:_ points the railway/iac SDK's version check at the real exe (it cannot launch railway.cmd).
$ErrorActionPreference = 'Stop'
$base = 'C:\Users\novah\AppData\Local\Temp\claude\F--Leadfuel-repos-leadfuel-core--claude-worktrees-hungry-neumann-8e77fa\62af3aac-0599-430b-8aff-1df4d842262f\scratchpad'
$W = Join-Path $base "rw-$Repo"
$C = "F:\Leadfuel\repos\$Repo"
$env:_ = "C:\Users\novah\AppData\Roaming\npm\node_modules\@railway\cli\bin\railway.exe"
git -C $C fetch -q origin
if (-not (Test-Path "$W\.git")) { git -C $C worktree add -q --detach $W $Ref } else { git -C $W checkout -q --detach $Ref }
if (-not (Test-Path "$W\node_modules")) { New-Item -ItemType Junction -Path "$W\node_modules" -Target "$C\node_modules" | Out-Null }
"ref: " + (git -C $W log -1 --format='%H %s')
Set-Location $C
if ($Mode -eq 'plan') {
  & $env:_ config plan --verbose --file "$W\.railway\railway.ts" 2>&1 | Select-String -Pattern 'Plan:|Update|Create|Delete|Destroy|Remove|└|Project |Environment |rror' | Out-String
} else {
  & $env:_ config apply --yes --file "$W\.railway\railway.ts" 2>&1 | Select-String -Pattern 'Project |Environment |Changes|✓|✗|rror|refus|destruct' | Out-String
  "exit=$LASTEXITCODE"
  '--- post-apply plan ---'
  & $env:_ config plan --file "$W\.railway\railway.ts" 2>&1 | Select-String -Pattern 'Plan:|Update|└|No changes' | Out-String
}
