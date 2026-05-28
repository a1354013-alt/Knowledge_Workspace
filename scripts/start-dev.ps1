$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"
$VenvPython = Join-Path $RepoRoot ".venv311\Scripts\python.exe"
$BackendEnv = Join-Path $BackendDir ".env"

if (-not (Test-Path $VenvPython)) {
    throw "Missing .venv311. Run .\scripts\bootstrap-dev.ps1 first."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm was not found. Install Node.js 20 LTS or newer, then run .\scripts\bootstrap-dev.ps1."
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
        if ($null -ne $process -and -not $process.HasExited) {
            taskkill /F /T /PID $process.Id *> $null
        }
    }
}
