@echo off
setlocal
cd /d "%~dp0"
title Plataforma Extensionista - Inicializador
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_platform.ps1"
if errorlevel 1 (
  echo.
  echo Nao foi possivel iniciar a plataforma. Consulte a mensagem acima.
  pause
)
endlocal
