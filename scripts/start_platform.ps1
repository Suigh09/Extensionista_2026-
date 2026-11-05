[CmdletBinding()]
param([switch]$NoBrowser)

. (Join-Path $PSScriptRoot 'platform_common.ps1')
$frontendDir = Join-Path $projectRoot 'frontend'
New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null

if (-not (Get-Command node.exe -ErrorAction SilentlyContinue)) { throw 'Node.js nao encontrado.' }
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw 'npm nao encontrado.' }

# Refuse to reuse an unverified frontend, including stale PID files from SQLite mode.
$registered = $null
if (Test-Path -LiteralPath $pidFile) {
    $registered = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
}
$listeners = @(Get-PlatformListener 5173)
$reuseFrontend = $false
if ($listeners.Count -gt 0) {
    $reuseFrontend = $registered.mode -eq 'docker-postgresql' -and `
        (Test-PlatformFrontend $registered.frontend) -and `
        $listeners.Count -eq 1 -and $listeners[0] -eq $registered.frontend.listener
    if (-not $reuseFrontend) {
        throw 'Porta 5173 ocupada por processo nao confirmado. Processo preservado; nao iniciaremos outra interface.'
    }
}

Write-Host '>> Iniciando backend Docker + PostgreSQL (sem SQLite)' -ForegroundColor Cyan
Start-PlatformBackend

if (-not $reuseFrontend) {
    $packageHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $frontendDir 'package-lock.json')).Hash
    $packageMarker = Join-Path $runtimeDir 'package-lock.sha256'
    if (-not (Test-Path (Join-Path $frontendDir 'node_modules')) -or
        -not (Test-Path $packageMarker) -or (Get-Content $packageMarker -Raw).Trim() -ne $packageHash) {
        & npm.cmd ci --prefix $frontendDir --cache (Join-Path $frontendDir '.npm-cache')
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependencias da interface.' }
        Set-Content -LiteralPath $packageMarker -Value $packageHash -Encoding ascii
    }

    # The interface always uses the proxy to the Docker backend on localhost:8000.
    $env:VITE_API_BASE_URL = '/api/v1'
    $vitePath = Join-Path $frontendDir 'node_modules\vite\bin\vite.js'
    $frontendProcess = Start-Process -FilePath (Get-Command node.exe).Source -ArgumentList @(
        ('"' + $vitePath + '"'), '--host', '127.0.0.1', '--port', '5173', '--strictPort'
    ) -WorkingDirectory $frontendDir -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $runtimeDir 'frontend.log') `
        -RedirectStandardError (Join-Path $runtimeDir 'frontend-error.log') -PassThru
    try {
        $ready = $false
        for ($attempt = 0; $attempt -lt 45; $attempt++) {
            if ($frontendProcess.HasExited) { throw 'Interface encerrou antes de ficar disponivel.' }
            if ((Test-PlatformUrl 'http://127.0.0.1:5173/') -and
                (Test-PlatformUrl 'http://127.0.0.1:5173/api/v1/health/')) {
                $ready = $true
                break
            }
            Start-Sleep -Seconds 1
        }
        if (-not $ready) { throw 'Interface/proxy indisponivel. Consulte .runtime/frontend-error.log.' }
        $listeners = @(Get-PlatformListener 5173)
        if ($listeners.Count -ne 1 -or $listeners[0] -ne $frontendProcess.Id) {
            throw 'Nao foi possivel confirmar o processo da interface.'
        }
        @{
            mode = 'docker-postgresql'
            frontend = @{
                listener = $frontendProcess.Id
                port = 5173
                started_at = $frontendProcess.StartTime.ToUniversalTime().ToString('o')
            }
        } | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $pidFile -Encoding utf8
    } catch {
        if (-not $frontendProcess.HasExited) { Stop-Process -Id $frontendProcess.Id -Force }
        throw
    }
} elseif (-not (Test-PlatformUrl 'http://127.0.0.1:5173/api/v1/health/')) {
    throw 'A interface existente nao alcanca o backend Docker.'
}

Write-Host 'Plataforma pronta: http://127.0.0.1:5173/ | Banco: PostgreSQL Docker' -ForegroundColor Green
Write-Host 'Use Parar Plataforma.bat para encerrar. SQLite preservado e fora da execucao normal.'
if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:5173/' }
