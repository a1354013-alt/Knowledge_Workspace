$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$FrontendNodeModules = Join-Path $RepoRoot "frontend\node_modules"
$BackendEnv = Join-Path $RepoRoot "backend\.env"

function Fail($Message) {
    throw "Development preflight failed: $Message`nRun .\scripts\bootstrap-dev.ps1 from the repo root, then retry F5 or .\scripts\start-dev.ps1."
}

if (-not (Test-Path $VenvPython)) {
    Fail "missing .venv\Scripts\python.exe"
}

$pythonVersion = & $VenvPython -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'); raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)"
if ($LASTEXITCODE -ne 0) {
    Fail ".venv uses Python $pythonVersion, but this project requires Python 3.11.x"
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Fail "Node.js was not found on PATH"
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Fail "npm was not found on PATH"
}

if (-not (Test-Path $FrontendNodeModules)) {
    Fail "missing frontend\node_modules"
}

if (-not (Test-Path $BackendEnv)) {
    Fail "missing backend\.env"
}

Write-Host "Development preflight passed."
