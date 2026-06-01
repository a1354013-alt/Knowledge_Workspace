$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$BackendEnv = Join-Path $BackendDir ".env"

if (-not (Test-Path $VenvPython)) {
    throw "Missing .venv. Run .\scripts\bootstrap-dev.ps1 first, or create it with: py -3.11 -m venv .venv"
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm was not found. Install Node.js 20 LTS or newer, then run .\scripts\bootstrap-dev.ps1."
}
if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
    throw "Missing frontend\node_modules. Run .\scripts\bootstrap-dev.ps1 first so npm ci installs the locked frontend dependencies."
}
$NpmCommand = if (Get-Command npm.cmd -ErrorAction SilentlyContinue) {
    (Get-Command npm.cmd).Source
} else {
    (Get-Command npm).Source
}

if (Test-Path $BackendEnv) {
    Get-Content $BackendEnv | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $parts = $line.Split("=", 2)
            [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
        }
    }
}

Write-Host "Starting Knowledge Workspace development servers..."
Write-Host "Backend API: http://127.0.0.1:8000"
Write-Host "API Docs:    http://127.0.0.1:8000/docs"
Write-Host "Frontend:    http://127.0.0.1:5173"
Write-Host "Press Ctrl+C to stop both services."

$backend = $null
$frontend = $null
function Stop-ProcessTree {
    param([System.Diagnostics.Process]$Process)
    if ($null -eq $Process -or $Process.HasExited) {
        return
    }
    try {
        Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
    } catch {
        # taskkill handles child processes such as uvicorn reload workers and Vite.
    }
    taskkill /F /T /PID $Process.Id *> $null
}

try {
    $backend = Start-Process -FilePath $VenvPython -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload") -WorkingDirectory $BackendDir -NoNewWindow -PassThru
    $frontend = Start-Process -FilePath $NpmCommand -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "5173") -WorkingDirectory $FrontendDir -NoNewWindow -PassThru

    while ($true) {
        Start-Sleep -Seconds 1
        if ($backend.HasExited) {
            throw "Backend server exited with code $($backend.ExitCode)."
        }
        if ($frontend.HasExited) {
            throw "Frontend server exited with code $($frontend.ExitCode)."
        }
    }
} finally {
    foreach ($process in @($backend, $frontend)) {
        Stop-ProcessTree $process
    }
}
