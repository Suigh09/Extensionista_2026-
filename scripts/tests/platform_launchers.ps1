# Dependency-free regression tests: no daemon, containers or databases are changed.
$ErrorActionPreference = 'Stop'
. (Join-Path (Split-Path $PSScriptRoot -Parent) 'platform_common.ps1')
$script:dockerCalls = @()
$script:dockerExitCode = 0
function docker {
    $script:dockerCalls += ,@($args)
    $global:LASTEXITCODE = $script:dockerExitCode
}
function Assert-Test($condition, [string]$message) {
    if (-not $condition) { throw $message }
}

Start-PlatformBackend
Assert-Test ($script:dockerCalls.Count -eq 3) 'Expected daemon check, startup and live PostgreSQL check.'
$startup = $script:dockerCalls[1] -join ' '
Assert-Test ($startup.Contains('--project-name plataforma_extensionista')) 'Project must be explicit.'
Assert-Test ($startup.Contains('--env-file')) 'Environment file must be explicit.'
Assert-Test ($startup.Contains('up -d --build --wait --wait-timeout 120 db backend')) 'Startup must wait for db/backend.'
$liveCheck = $script:dockerCalls[2] -join ' '
Assert-Test ($liveCheck.Contains('connection.ensure_connection()')) 'Verify a live database connection.'
Assert-Test ($liveCheck.Contains("connection.vendor == 'postgresql'")) 'Reject SQLite connections.'

$script:dockerExitCode = 1
$failed = $false
try { Assert-PlatformDocker } catch { $failed = $true }
Assert-Test $failed 'Docker failure must stop startup without falling back to SQLite.'
$failed = $false
try { Invoke-PlatformCompose -ComposeArguments @('stop', 'backend') } catch { $failed = $true }
Assert-Test $failed 'Compose errors must propagate.'

Assert-Test (-not (Test-PlatformFrontend $null)) 'Missing PID record cannot authorize stopping.'
Assert-Test (-not (Test-PlatformFrontend @{listener = $PID})) 'Legacy PID record cannot authorize stopping.'
Assert-Test (-not (Test-PlatformFrontend @{listener = $PID; started_at = 'invalid'})) 'Unknown process cannot authorize stopping.'

$files = @('platform_common.ps1', 'start_platform.ps1', 'stop_platform.ps1')
foreach ($file in $files) {
    $tokens = $null
    $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile(
        (Join-Path (Split-Path $PSScriptRoot -Parent) $file), [ref]$tokens, [ref]$parseErrors
    ) | Out-Null
    Assert-Test ($parseErrors.Count -eq 0) "Syntax error in $file."
}
Write-Host 'OK: PostgreSQL startup, explicit Compose scope, failure propagation, PID safety and PowerShell syntax.'
