param(
    [ValidateSet('runserver', 'check')]
    [string]$Action = 'runserver'
)

. (Join-Path (Split-Path $PSScriptRoot -Parent) 'scripts\platform_common.ps1')
Start-PlatformBackend
if ($Action -eq 'check') {
    Invoke-PlatformCompose -ComposeArguments @('exec', '-T', 'backend', 'python', 'manage.py', 'check')
} else {
    Write-Host 'Backend Docker pronto em http://127.0.0.1:8000/ (PostgreSQL).'
}
