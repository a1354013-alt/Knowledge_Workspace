param(
    [string]$PythonVersion = "3.11"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

Write-Host "Knowledge Workspace backend bootstrap"

$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv) {
    Write-Host "Using uv with Python $PythonVersion"
    uv python install $PythonVersion
    uv venv --python $PythonVersion .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    uv pip install -e ".[dev]"
} else {
    $python = Get-Command py -ErrorAction SilentlyContinue
    if ($python) {
        py -$PythonVersion -m venv .venv
    } else {
        python -m venv .venv
    }
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
}

$version = .\.venv\Scripts\python.exe -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
if (-not $version.StartsWith("3.11.")) {
    Write-Warning "Created Python $version. This project supports Python 3.11.x; install Python 3.11 and rerun this script if checks fail."
}

Write-Host ""
Write-Host "Next commands:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  python scripts\run_backend_checks.py"
Write-Host "  python scripts\export_openapi.py"
Write-Host "  cd frontend; npm run generate:api-types"
Write-Host "  cd backend; python -m uvicorn app.main:app --reload"
