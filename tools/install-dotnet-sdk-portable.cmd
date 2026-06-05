@echo off
setlocal EnableExtensions

set "DOTNET_CHANNEL=6.0"
set "DOTNET_DIR=%USERPROFILE%\.dotnet"
set "DOTNET_INSTALL=%TEMP%\uip-toolchain-dotnet-install.ps1"

echo [1/4] Baixando instalador portable oficial do .NET...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='Continue'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri 'https://dot.net/v1/dotnet-install.ps1' -OutFile '%DOTNET_INSTALL%'"
if errorlevel 1 goto :fail

echo [2/4] Instalando .NET SDK %DOTNET_CHANNEL% em "%DOTNET_DIR%" sem admin...
powershell -NoProfile -ExecutionPolicy Bypass -File "%DOTNET_INSTALL%" -Channel "%DOTNET_CHANNEL%" -InstallDir "%DOTNET_DIR%" -NoPath -Verbose
if errorlevel 1 goto :fail

echo [3/4] Gravando variaveis de usuario...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Environment]::SetEnvironmentVariable('DOTNET_ROOT', '%DOTNET_DIR%', 'User'); [Environment]::SetEnvironmentVariable('UIP_TOOLCHAIN_DOTNET_ROOT', '%DOTNET_DIR%', 'User'); $userPath = [Environment]::GetEnvironmentVariable('PATH', 'User'); if (-not (($userPath -split ';') -contains '%DOTNET_DIR%')) { [Environment]::SetEnvironmentVariable('PATH', '%DOTNET_DIR%;' + $userPath, 'User') }"
if errorlevel 1 goto :fail

echo [4/4] Validando SDK instalado...
"%DOTNET_DIR%\dotnet.exe" --list-sdks
if errorlevel 1 goto :fail

echo.
echo OK. Abra um novo PowerShell antes de rodar ccs-uip-publish.
echo Nesta janela, se quiser usar agora, rode:
echo   $env:DOTNET_ROOT = "%DOTNET_DIR%"
echo   $env:UIP_TOOLCHAIN_DOTNET_ROOT = "%DOTNET_DIR%"
echo   $env:PATH = "%DOTNET_DIR%;$env:PATH"
exit /b 0

:fail
echo.
echo FALHA na instalacao portable do .NET SDK.
echo Se a ultima linha indicou proxy/rede, tente conectado na VPN ou baixe em outra rede.
exit /b 1
