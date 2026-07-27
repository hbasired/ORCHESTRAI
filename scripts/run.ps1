# scripts/run.ps1
#
# PowerShell wrapper for the project's bash-based lifecycle scripts.
#
# Background: on Windows, typing `bash` in PowerShell resolves to
# `C:\Windows\System32\bash.exe` (the WSL launcher), which on this dev host
# defaults to the `docker-desktop` WSL distro — a minimal image without a
# usable `/bin/bash`. So `bash scripts/audit-task.sh 2` fails with:
#   WSL (...) ERROR: CreateProcessCommon:798: execvpe(/bin/bash) failed: No such file or directory
#
# This wrapper finds Git Bash and delegates the call to it, so the operator
# can run any project shell script from PowerShell without worrying about
# the bash resolution order.
#
# Usage examples:
#   .\scripts\run.ps1 audit-task 2
#   .\scripts\run.ps1 audit
#   .\scripts\run.ps1 init
#   .\scripts\run.ps1 close-task 2
#   .\scripts\run.ps1 start-task 3 ws_broker
#
# To pass --auto-route to init.sh:
#   .\scripts\run.ps1 init --auto-route

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Script,

    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$ScriptArgs
)

# Find Git Bash. Standard install locations in priority order.
$candidates = @(
    "C:\Program Files\Git\bin\bash.exe",
    "C:\Program Files\Git\usr\bin\bash.exe",
    "C:\Program Files (x86)\Git\bin\bash.exe"
)

$gitBash = $null
foreach ($c in $candidates) {
    if (Test-Path $c) { $gitBash = $c; break }
}

if (-not $gitBash) {
    Write-Host "ERROR: Git Bash not found in standard locations." -ForegroundColor Red
    Write-Host "Install Git for Windows from https://git-scm.com/download/win" -ForegroundColor Red
    exit 2
}

# Resolve the target script. Accept either the short name (e.g. "audit-task")
# or the full filename (e.g. "audit-task.sh").
$repoRoot = (Resolve-Path "$PSScriptRoot\..").Path
$shortName = $Script
if ($shortName -notlike "*.sh" -and $shortName -notlike "*.py") {
    $shortName += ".sh"
}

# Map short names to script paths.
$candidatePaths = @(
    (Join-Path $repoRoot "scripts" $shortName),
    (Join-Path $repoRoot ".claude\hooks" $shortName)
)

$scriptPath = $null
foreach ($p in $candidatePaths) {
    if (Test-Path $p) { $scriptPath = $p; break }
}

if (-not $scriptPath) {
    Write-Host "ERROR: Script not found: $shortName" -ForegroundColor Red
    Write-Host "Tried:" -ForegroundColor Red
    foreach ($p in $candidatePaths) { Write-Host "  $p" -ForegroundColor Red }
    exit 2
}

# Convert the Windows path to a Git Bash compatible path.
# Git Bash accepts forward-slash Windows paths (e.g. D:/ai-embodied-agent/scripts/audit-task.sh).
$bashPath = $scriptPath -replace '\\', '/'

# Invoke. Pass args through. Set working dir to repo root.
Push-Location $repoRoot
try {
    & $gitBash $bashPath @ScriptArgs
    $exit = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $exit
