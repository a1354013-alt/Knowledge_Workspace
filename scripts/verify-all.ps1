$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    throw "Missing .venv. Run .\scripts\bootstrap-dev.ps1 first."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm was not found. Install Node.js 20 LTS or newer, then run .\scripts\bootstrap-dev.ps1."
}

Write-Host "Running full Knowledge Workspace verification..."
& $VenvPython (Join-Path $RepoRoot "scripts\verify_all.py")
if ($LASTEXITCODE -ne 0) {
    throw "Full verification failed. See the command output above."
}
