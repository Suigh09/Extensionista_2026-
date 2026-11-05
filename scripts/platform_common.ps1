$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeDir = Join-Path $projectRoot '.runtime'
$pidFile = Join-Path $runtimeDir 'processes.json'

function Invoke-PlatformCompose {
    param([string[]]$ComposeArguments)
    # Explicit files/project prevent ambient COMPOSE_* variables selecting another stack.
    & docker compose --project-name plataforma_extensionista --project-directory $projectRoot `
        --env-file (Join-Path $projectRoot '.env') `
        -f (Join-Path $projectRoot 'compose.yaml') `
        -f (Join-Path $projectRoot 'docker-compose.override.yml') @ComposeArguments
    if ($LASTEXITCODE -ne 0) { throw 'Falha no Docker Compose. Nenhum banco foi removido.' }
}

function Assert-PlatformDocker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Docker nao encontrado. Instale/inicie o Docker Desktop. Nao ha fallback para SQLite.'
    }
    & docker info --format '{{.ServerVersion}}' | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker Desktop indisponivel. Inicie-o e tente novamente; SQLite nao sera usado.'
    }
}

function Start-PlatformBackend {
    Assert-PlatformDocker
    Invoke-PlatformCompose -ComposeArguments @('up', '-d', '--build', '--wait', '--wait-timeout', '120', 'db', 'backend')
    # Verify the live connection, not merely a health response on a possibly foreign port.
    Invoke-PlatformCompose -ComposeArguments @(
        'exec', '-T', 'backend', 'python', 'manage.py', 'shell', '-c',
        "from django.db import connection; connection.ensure_connection(); assert connection.vendor == 'postgresql', 'Backend deve usar PostgreSQL'; print('Banco ativo: PostgreSQL (Docker)')"
    )
}

function Get-PlatformListener([int]$port) {
    $matchesFound = @(netstat.exe -ano -p TCP | Select-String -Pattern "^\s*TCP\s+\S+:$port\s+\S+\s+LISTENING\s+(\d+)\s*$")
    return @($matchesFound | ForEach-Object { [int]$_.Matches[0].Groups[1].Value } | Select-Object -Unique)
}

function Test-PlatformFrontend($record) {
    if (-not $record -or -not $record.started_at -or -not $record.listener) { return $false }
    $process = Get-Process -Id ([int]$record.listener) -ErrorAction SilentlyContinue
    if (-not $process -or $process.ProcessName -ne 'node') { return $false }
    if ($process.StartTime.ToUniversalTime().ToString('o') -ne $record.started_at) { return $false }
    $details = Get-CimInstance Win32_Process -Filter "ProcessId = $($process.Id)"
    $vitePath = Join-Path $projectRoot 'frontend\node_modules\vite\bin\vite.js'
    return $details.CommandLine -and $details.CommandLine.Contains($vitePath)
}

function Test-PlatformUrl([string]$url) {
    try {
        $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200
    } catch { return $false }
}
