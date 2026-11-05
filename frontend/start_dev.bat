@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\scripts\start_platform.ps1" %*
exit /b %errorlevel%
