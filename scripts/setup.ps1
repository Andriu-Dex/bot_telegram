$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path -LiteralPath '.env')) {
    $sessionSecret = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
    $internalToken = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
    $adminPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(12))
    $postgresPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(20))
    $config = Get-Content -LiteralPath '.env.example' -Raw
    $config = $config.Replace('ADMIN_PASSWORD=', "ADMIN_PASSWORD=$adminPassword").Replace('SESSION_SECRET=', "SESSION_SECRET=$sessionSecret").Replace('INTERNAL_API_TOKEN=', "INTERNAL_API_TOKEN=$internalToken")
    $config += "`nPOSTGRES_PASSWORD=$postgresPassword`n"
    Set-Content -LiteralPath '.env' -Value $config -Encoding utf8
    Write-Host 'Se creó .env con credenciales aleatorias. Consulta ADMIN_PASSWORD en ese archivo para iniciar sesión.'
}
uv venv
uv pip install -r backend/requirements.txt
& ./.venv/Scripts/alembic.exe -c backend/alembic.ini upgrade head
Push-Location frontend
try { npm install } finally { Pop-Location }
Write-Host 'Listo. Ejecuta scripts/start.ps1 y abre http://localhost:5173'
