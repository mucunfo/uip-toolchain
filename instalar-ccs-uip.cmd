@echo off
setlocal EnableExtensions

cd /d "%~dp0"

echo.
echo CCS UiPath Toolchain - instalador interativo
echo.
echo Este instalador nao precisa de permissao de administrador.
echo Ele instala/atualiza os comandos ccs-uip e ccs-uip-publish para o usuario atual.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\install-ccs-uip.ps1"
set "EXITCODE=%ERRORLEVEL%"

echo.
if "%EXITCODE%"=="0" (
  echo Instalador finalizado.
) else (
  echo Instalador finalizado com erro. Veja as mensagens acima.
)
echo.
pause
exit /b %EXITCODE%
