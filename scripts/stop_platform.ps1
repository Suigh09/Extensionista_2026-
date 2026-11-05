[CmdletBinding()]
param()

. (Join-Path $PSScriptRoot 'platform_common.ps1')
if (Test-Path -LiteralPath $pidFile) {
    $registered = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
    if ($registered.mode -eq 'docker-postgresql' -and (Test-PlatformFrontend $registered.frontend)) {
        Stop-Process -Id ([int]$registered.frontend.listener) -Force
    } else {
        Write-Warning 'Registro antigo ou processo nao confirmado: nenhum processo local desconhecido foi encerrado.'
    }
    Remove-Item -LiteralPath $pidFile -Force
}

Assert-PlatformDocker
# stop preserves containers, PostgreSQL volume and uploads; never down -v.
Invoke-PlatformCompose -ComposeArguments @('stop', 'frontend', 'backend', 'db')
Write-Host 'Plataforma encerrada. PostgreSQL, SQLite e uploads preservados.' -ForegroundColor Green
