[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $projectRoot '.runtime\processes.json'
if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Host 'Nenhum processo iniciado pela plataforma foi registrado.' -ForegroundColor Yellow
    exit 0
}

$registered = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
function Get-ListeningProcessId([int]$port) {
    $match = netstat.exe -ano -p TCP |
        Select-String -Pattern "^\s*TCP\s+127\.0\.0\.1:$port\s+\S+\s+LISTENING\s+(\d+)\s*$" |
        Select-Object -First 1
    if (-not $match) { return $null }
    return [int]$match.Matches[0].Groups[1].Value
}

foreach ($service in @($registered.backend, $registered.frontend)) {
    if (-not $service) { continue }
    $currentListener = Get-ListeningProcessId ([int]$service.port)
    if ($currentListener -and $currentListener -ne [int]$service.listener) {
        Write-Warning "A porta $($service.port) pertence agora a outro processo e nao foi alterada."
        continue
    }
    foreach ($processId in @($service.listener, $service.launcher) | Select-Object -Unique) {
        if ($processId -and (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {
            & taskkill.exe /PID $processId /T /F 2>$null | Out-Null
        }
    }
}
Remove-Item -LiteralPath $pidFile -Force
Write-Host 'Plataforma encerrada.' -ForegroundColor Green
