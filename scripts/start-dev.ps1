$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$BackendEnv = Join-Path $BackendDir ".env"
$EnsureDev = Join-Path $PSScriptRoot "ensure-dev.ps1"

& $EnsureDev

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
function Wait-HttpReady {
    param(
        [string]$Url,
        [string]$Name,
        [int]$TimeoutSeconds = 45,
        [System.Diagnostics.Process]$Process
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if ($null -ne $Process -and $Process.HasExited) {
            throw "$Name server exited with code $($Process.ExitCode) before it became ready."
        }
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                Write-Host "$Name is ready: $Url"
                return
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    throw "$Name did not become ready at $Url within $TimeoutSeconds seconds. Check the server output above before using the frontend; otherwise /api requests such as /api/login may return 502."
}

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
    Wait-HttpReady -Url "http://127.0.0.1:8000/api/health" -Name "Backend" -Process $backend

    $frontend = Start-Process -FilePath $NpmCommand -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "5173") -WorkingDirectory $FrontendDir -NoNewWindow -PassThru
    Wait-HttpReady -Url "http://127.0.0.1:5173" -Name "Frontend" -Process $frontend

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
