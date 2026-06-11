$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvPath = Join-Path $RepoRoot ".venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$FrontendDir = Join-Path $RepoRoot "frontend"
$BackendEnvPath = Join-Path $RepoRoot "backend\.env"
$RootEnvPath = Join-Path $RepoRoot ".env"

function Fail($Message) {
    throw "Bootstrap failed: $Message"
}

function Get-FrontendNodeProcesses {
    $frontendPath = [System.IO.Path]::GetFullPath($FrontendDir).TrimEnd("\")
    $repoPath = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd("\")
    Get-CimInstance Win32_Process -Filter "Name = 'node.exe' OR Name = 'npm.exe' OR Name = 'npm.cmd'" -ErrorAction SilentlyContinue |
        Where-Object {
            $commandLine = $_.CommandLine
            if ([string]::IsNullOrWhiteSpace($commandLine)) {
                return $false
            }
            $normalized = $commandLine -replace '/', '\'
            return $normalized.Contains($frontendPath) -or ($normalized.Contains($repoPath) -and $normalized -match '\bvite\b')
        }
}

function Assert-NoFrontendDevProcesses {
    $processes = @(Get-FrontendNodeProcesses)
    if ($processes.Count -eq 0) {
        return
    }

    Write-Host "Frontend dev server is still running. Stop it before running npm ci."
    Write-Host ""
    Write-Host "Processes using this project's frontend:"
    foreach ($process in $processes) {
        Write-Host ("- PID {0}: {1}" -f $process.ProcessId, $process.CommandLine)
    }
    Write-Host ""
    Write-Host "Windows EPERM unlink errors during npm ci usually mean node_modules is locked by a Node/Vite process, an editor, antivirus, or OneDrive sync."
    Write-Host "Close the dev server and terminals that are using frontend\node_modules, then retry .\scripts\bootstrap-dev.ps1."
    Fail "frontend node_modules is in use"
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

function Write-Utf8NoBomFile {
    param(
        [string]$Path,
        [string]$Content
    )
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Remove-Utf8BomIfPresent {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        return
    }
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        if ($bytes.Length -eq 3) {
            [System.IO.File]::WriteAllBytes($Path, [byte[]]@())
        } else {
            [System.IO.File]::WriteAllBytes($Path, $bytes[3..($bytes.Length - 1)])
        }
        Write-Host "$Path had a UTF-8 BOM; normalized encoding without changing values."
    }
}

function Write-RootEnvIfMissing {
    if (Test-Path $RootEnvPath) {
        Remove-Utf8BomIfPresent $RootEnvPath
        Write-Host ".env already exists; leaving it unchanged."
        return
    }
    $secret = New-EnvSecret
    $content = @"
# Backend runtime
JWT_SECRET=$secret
DEFAULT_OWNER_PASSWORD=ChangeMe123!
DATABASE_PATH=./documents.db
UPLOAD_DIR=./uploads
PHOTO_DIR=./photos
CHROMA_DB_PATH=./chroma_db

# AutoTest defaults to simulated execution; uploaded code does not run until explicitly enabled.
AUTOTEST_MODE=simulated
KW_AUTOTEST_REAL_MODE=0
KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=0
AUTOTEST_SANDBOX_BACKEND=disabled
AUTOTEST_STALE_RUN_MINUTES=30

# LLM provider
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
"@
    Write-Utf8NoBomFile -Path $RootEnvPath -Content $content
    Write-Host "Created .env with safe local defaults."
}

function Write-BackendEnvIfMissing {
    if (Test-Path $BackendEnvPath) {
        Remove-Utf8BomIfPresent $BackendEnvPath
        Write-Host "backend\.env already exists; leaving it unchanged."
        return
    }
    $secret = New-EnvSecret
    $content = @"
JWT_SECRET=$secret
DEFAULT_OWNER_PASSWORD=ChangeMe123!
ALLOWED_ORIGINS=http://localhost:5173
DATABASE_PATH=./documents.db
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=52428800
PHOTO_DIR=./photos
CHROMA_DB_PATH=./chroma_db
AUTOTEST_DIR=./autotest_uploads
AUTOTEST_MODE=simulated
KW_AUTOTEST_REAL_MODE=0
KNOWLEDGE_WORKSPACE_ENABLE_REAL_AUTOTEST=0
AUTOTEST_SANDBOX_BACKEND=disabled
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
"@
    Write-Utf8NoBomFile -Path $BackendEnvPath -Content $content
    Write-Host "Created backend\.env with safe local defaults."
}

function Remove-PackagingArtifacts {
    Get-ChildItem -Path (Join-Path $RepoRoot "backend") -Force -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "*.egg-info" -or $_.Name -like "*.dist-info" } |
        Remove-Item -Recurse -Force
}

function Remove-ViteOptimizeCache {
    $cachePaths = @(
        (Join-Path $FrontendDir "node_modules\.vite"),
        (Join-Path $FrontendDir ".vite")
    )
    foreach ($cachePath in $cachePaths) {
        if (Test-Path $cachePath) {
            Remove-Item -LiteralPath $cachePath -Recurse -Force
            Write-Host "Removed Vite optimize cache: $cachePath"
        }
    }
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
Remove-PackagingArtifacts

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Fail "npm was not found. Install Node.js 20 LTS or newer and retry."
}

Assert-NoFrontendDevProcesses

Push-Location $FrontendDir
try {
    npm ci
    if ($LASTEXITCODE -ne 0) {
        Fail "frontend dependency installation failed. On Windows, EPERM unlink errors usually mean a Node/Vite process, editor, antivirus, or OneDrive sync is locking frontend\node_modules. Stop dev servers, close terminals using node_modules, restart VS Code if needed, then retry."
    }
} finally {
    Pop-Location
}
Remove-ViteOptimizeCache

Write-RootEnvIfMissing
Write-BackendEnvIfMissing

Write-Host ""
Write-Host "Bootstrap complete."
Write-Host "Next: .\scripts\start-dev.ps1"
