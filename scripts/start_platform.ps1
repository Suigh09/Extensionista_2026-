[CmdletBinding()]
param([switch]$NoBrowser)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $projectRoot 'backend'
$frontendDir = Join-Path $projectRoot 'frontend'
$runtimeDir = Join-Path $projectRoot '.runtime'
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
$localEnv = Join-Path $projectRoot '.env.local-launcher'
$pidFile = Join-Path $runtimeDir 'processes.json'

function Write-Step([string]$message) {
    Write-Host "`n>> $message" -ForegroundColor Cyan
}

function Test-Url([string]$url) {
    try {
        $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    } catch {
        return $false
    }
}

function Wait-Url([string]$url, [int]$attempts = 45) {
    for ($attempt = 1; $attempt -le $attempts; $attempt++) {
        if (Test-Url $url) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Get-ListeningProcessId([int]$port) {
    $match = netstat.exe -ano -p TCP |
        Select-String -Pattern "^\s*TCP\s+127\.0\.0\.1:$port\s+\S+\s+LISTENING\s+(\d+)\s*$" |
        Select-Object -First 1
    if (-not $match) { return $null }
    return [int]$match.Matches[0].Groups[1].Value
}

function Stop-StartedProcess($process) {
    if ($null -ne $process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
}

New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null

if ((Test-Url 'http://127.0.0.1:8000/api/v1/health/') -and (Test-Url 'http://127.0.0.1:5173/')) {
    Write-Host 'A plataforma ja esta em execucao. Abrindo no navegador...' -ForegroundColor Green
    if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:5173/' }
    exit 0
}

Write-Step 'Verificando os pre-requisitos'
$systemPython = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $systemPython) { $systemPython = Get-Command py.exe -ErrorAction SilentlyContinue }
if (-not $systemPython) { throw 'Python 3.11 ou superior nao foi encontrado. Instale o Python e tente novamente.' }
if (-not (Get-Command node.exe -ErrorAction SilentlyContinue)) { throw 'Node.js nao foi encontrado. Instale o Node.js e tente novamente.' }
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { throw 'npm nao foi encontrado. Reinstale o Node.js e tente novamente.' }

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Step 'Preparando o ambiente Python (somente na primeira execucao)'
    if ($systemPython.Name -eq 'python.exe') {
        & $systemPython.Source -m venv (Join-Path $projectRoot '.venv')
    } else {
        & $systemPython.Source -3 -m venv (Join-Path $projectRoot '.venv')
    }
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar o ambiente Python.' }
}

$requirementsFile = Join-Path $projectRoot 'requirements.txt'
$requirementsHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $requirementsFile).Hash
$requirementsMarker = Join-Path $runtimeDir 'requirements.sha256'
if (-not (Test-Path $requirementsMarker) -or (Get-Content $requirementsMarker -Raw).Trim() -ne $requirementsHash) {
    Write-Step 'Instalando dependencias Python'
    & $venvPython -m pip install --disable-pip-version-check -r $requirementsFile
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar as dependencias Python.' }
    Set-Content -LiteralPath $requirementsMarker -Value $requirementsHash -Encoding ascii
}

$packageHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $frontendDir 'package-lock.json')).Hash
$packageMarker = Join-Path $runtimeDir 'package-lock.sha256'
if (-not (Test-Path (Join-Path $frontendDir 'node_modules')) -or -not (Test-Path $packageMarker) -or (Get-Content $packageMarker -Raw).Trim() -ne $packageHash) {
    Write-Step 'Instalando dependencias da interface'
    & npm.cmd ci --prefix $frontendDir --cache (Join-Path $frontendDir '.npm-cache')
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar as dependencias da interface.' }
    Set-Content -LiteralPath $packageMarker -Value $packageHash -Encoding ascii
}

if (-not (Test-Path -LiteralPath $localEnv)) {
    $randomBytes = New-Object byte[] 48
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($randomBytes) } finally { $generator.Dispose() }
    $secret = [Convert]::ToBase64String($randomBytes)
    Set-Content -LiteralPath $localEnv -Value "DJANGO_SECRET_KEY=$secret" -Encoding utf8
}
$secretLine = Get-Content -LiteralPath $localEnv | Where-Object { $_ -like 'DJANGO_SECRET_KEY=*' } | Select-Object -First 1
if (-not $secretLine) { throw 'A chave local do Django esta ausente ou invalida.' }
$env:DJANGO_SECRET_KEY = $secretLine.Substring('DJANGO_SECRET_KEY='.Length)
$env:DATABASE_ENGINE = 'sqlite'
$env:DJANGO_ENV = 'development'
$env:DJANGO_ALLOWED_HOSTS = 'localhost,127.0.0.1'
$env:DJANGO_CORS_ALLOWED_ORIGINS = 'http://127.0.0.1:5173,http://localhost:5173'
$env:DJANGO_CSRF_TRUSTED_ORIGINS = 'http://127.0.0.1:5173,http://localhost:5173'

Write-Step 'Atualizando o banco de dados local'
& $venvPython (Join-Path $backendDir 'manage.py') migrate --noinput
if ($LASTEXITCODE -ne 0) { throw 'Falha ao aplicar as atualizacoes do banco local.' }

Write-Step 'Iniciando backend e interface'
$backendOut = Join-Path $runtimeDir 'backend.log'
$backendErr = Join-Path $runtimeDir 'backend-error.log'
$frontendOut = Join-Path $runtimeDir 'frontend.log'
$frontendErr = Join-Path $runtimeDir 'frontend-error.log'
$backendProcess = $null
$frontendProcess = $null
try {
    # --nothreading: o SQLite local serializa escritas; sem isso, requisições
    # concorrentes (E2E, abas) geram "database is locked" intermitente.
    # Produção usa gunicorn + PostgreSQL e não é afetada.
    $backendProcess = Start-Process -FilePath $venvPython -ArgumentList @(
        (Join-Path $backendDir 'manage.py'), 'runserver', '127.0.0.1:8000', '--noreload', '--nothreading'
    ) -WorkingDirectory $backendDir -WindowStyle Hidden -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr -PassThru
    $frontendProcess = Start-Process -FilePath 'npm.cmd' -ArgumentList @(
        'run', 'dev', '--', '--host', '127.0.0.1'
    ) -WorkingDirectory $frontendDir -WindowStyle Hidden -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr -PassThru

    if (-not (Wait-Url 'http://127.0.0.1:8000/api/v1/health/')) {
        throw "O backend nao respondeu. Consulte $backendErr"
    }
    if (-not (Wait-Url 'http://127.0.0.1:5173/')) {
        throw "A interface nao respondeu. Consulte $frontendErr"
    }
    $backendListener = Get-ListeningProcessId 8000
    $frontendListener = Get-ListeningProcessId 5173
    if (-not $backendListener -or -not $frontendListener) {
        throw 'Nao foi possivel identificar com seguranca os processos locais iniciados.'
    }
    @{
        backend = @{ launcher = $backendProcess.Id; listener = $backendListener; port = 8000 }
        frontend = @{ launcher = $frontendProcess.Id; listener = $frontendListener; port = 5173 }
    } | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $pidFile -Encoding utf8
} catch {
    Stop-StartedProcess $frontendProcess
    Stop-StartedProcess $backendProcess
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    throw
}

Write-Host "`nPlataforma pronta em http://127.0.0.1:5173/" -ForegroundColor Green
Write-Host 'Para encerrar, use "Parar Plataforma.bat".'
if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:5173/' }
exit 0
