$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $RepoRoot ".venv311"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$FrontendDir = Join-Path $RepoRoot "frontend"
$BackendEnvPath = Join-Path $RepoRoot "backend\.env"
$RootEnvPath = Join-Path $RepoRoot ".env"

function Fail($Message) {
    throw "Bootstrap failed: $Message"
}

function Set-PythonCommand($Executable, $Arguments) {
    $script:PythonExecutable = $Executable
    $script:PythonArguments = $Arguments
}

function Invoke-SelectedPython($Arguments) {
    & $script:PythonExecutable @script:PythonArguments @Arguments
}

function Test-PythonCommand($Executable, $Arguments) {
    try {
        & $Executable @Arguments -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function New-EnvSecret {
    return (([guid]::NewGuid().ToString("N")) + ([guid]::NewGuid().ToString("N")))
}

function Write-RootEnvIfMissing {
    if (Test-Path $RootEnvPath) {
        Write-Host ".env already exists; leaving it unchanged."
        return
    }
    $secret = New-EnvSecret
    @"
# Backend runtime
JWT_SECRET=$secret
DEFAULT_OWNER_PASSWORD=ChangeMe123!
DATABASE_PATH=backend/documents.db
UPLOAD_DIR=backend/uploads
PHOTO_DIR=backend/photos
CHROMA_DB_PATH=backend/chroma_db

# AutoTest is simulated by default. Real command execution requires both flags.
AUTOTEST_MODE=simulated
KW_AUTOTEST_REAL_MODE=0
AUTOTEST_STALE_RUN_MINUTES=30

# LLM provider
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
"@ | Set-Content -Path $RootEnvPath -Encoding UTF8
    Write-Host "Created .env with safe local defaults."
}

function Write-BackendEnvIfMissing {
    if (Test-Path $BackendEnvPath) {
        Write-Host "backend\.env already exists; leaving it unchanged."
        return
    }
    $secret = New-EnvSecret
    @"
JWT_SECRET=$secret
DEFAULT_OWNER_PASSWORD=ChangeMe123!
ALLOWED_ORIGINS=http://localhost:5173
DATABASE_PATH=documents.db
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=52428800
PHOTO_DIR=./photos
CHROMA_DB_PATH=./chroma_db
AUTOTEST_DIR=./autotest_uploads
AUTOTEST_MODE=simulated
KW_AUTOTEST_REAL_MODE=0
AUTOTEST_TIMEOUT_SECONDS=120
AUTOTEST_MAX_FILES=500
AUTOTEST_MAX_UNZIPPED_BYTES=52428800
AUTOTEST_RLIMIT_CPU_SECONDS=30
AUTOTEST_RLIMIT_AS_MB=512
AUTOTEST_RLIMIT_FSIZE_MB=64
AUTOTEST_STALE_RUN_MINUTES=30
OCR_ENABLED=true
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
"@ | Set-Content -Path $BackendEnvPath -Encoding UTF8
    Write-Host "Created backend\.env with safe local defaults."
}

Write-Host "Bootstrapping Knowledge Workspace with Python 3.11..."

if ((Get-Command py -ErrorAction SilentlyContinue) -and (Test-PythonCommand "py" @("-3.11"))) {
    Set-PythonCommand "py" @("-3.11")
} elseif ((Get-Command python3.11 -ErrorAction SilentlyContinue) -and (Test-PythonCommand "python3.11" @())) {
    Set-PythonCommand "python3.11" @()
} elseif ((Get-Command python -ErrorAction SilentlyContinue) -and (Test-PythonCommand "python" @())) {
    Set-PythonCommand "python" @()
} else {
    Fail "Python 3.11 was not found. Install Python 3.11.x and retry."
}

Invoke-SelectedPython @("-m", "venv", $VenvPath)
if (-not (Test-Path $VenvPython)) {
    Fail "virtual environment was not created at $VenvPath"
}

& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { Fail "pip upgrade failed" }

& $VenvPython -m pip install -e "${RepoRoot}[dev]"
if ($LASTEXITCODE -ne 0) { Fail "backend dev dependency installation failed" }

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Fail "npm was not found. Install Node.js 20 LTS or newer and retry."
}

Push-Location $FrontendDir
try {
    npm ci
    if ($LASTEXITCODE -ne 0) { Fail "frontend dependency installation failed" }
} finally {
    Pop-Location
}

Write-RootEnvIfMissing
Write-BackendEnvIfMissing

Write-Host ""
Write-Host "Bootstrap complete."
Write-Host "Next: .\scripts\start-dev.ps1"
