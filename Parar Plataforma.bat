@echo off
setlocal
cd /d "%~dp0"
title Plataforma Extensionista - Encerramento
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop_platform.ps1"
if errorlevel 1 pause
endlocal
