$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $repoRoot ".venv"

Write-Host "Bootstrapping Knowledge Workspace on Windows with Python 3.11.x"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found. Install Python 3.11.x first."
}

py -3.11 -m venv $venvPath

$activateScript = Join-Path $venvPath "Scripts\\Activate.ps1"
if (-not (Test-Path $activateScript)) {
    throw "Virtual environment activation script was not created: $activateScript"
}

& $activateScript
Set-Location $repoRoot
python -m pip install -U pip
pip install -e ".[dev]"

Write-Host ""
Write-Host "Bootstrap complete."
Write-Host "Next steps:"
Write-Host "  1. .\\.venv\\Scripts\\Activate.ps1"
Write-Host "  2. python scripts/check_python_version.py"
Write-Host "  3. cd backend"
Write-Host "  4. python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
