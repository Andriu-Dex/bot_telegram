$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
$env:PYTHONPATH = Join-Path $projectRoot 'backend'
& ./.venv/Scripts/alembic.exe -c backend/alembic.ini upgrade head
$apiProcess = Start-Process -FilePath (Join-Path $projectRoot '.venv/Scripts/python.exe') -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $projectRoot 'api.log') -RedirectStandardError (Join-Path $projectRoot 'api-error.log')
try {
    Set-Location (Join-Path $projectRoot 'frontend')
    npm run dev -- --host 127.0.0.1
} finally {
    Stop-Process -Id $apiProcess.Id -ErrorAction SilentlyContinue
    Set-Location $projectRoot
}
