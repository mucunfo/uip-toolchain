param(
    [switch]$DiagnosticsOnly,
    [switch]$NoPrompt
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$LogDir = Join-Path $RepoRoot ".tmp"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogPath = Join-Path $LogDir ("install-ccs-uip-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
$script:InstalledToolchain = $false

try {
    Start-Transcript -Path $LogPath -Force | Out-Null
} catch {
    Write-Host "[WARN] Nao foi possivel iniciar log: $($_.Exception.Message)" -ForegroundColor Yellow
}

function Write-Title($Text) {
    Write-Host ""
    Write-Host "== $Text ==" -ForegroundColor Cyan
}

function Write-Ok($Text) {
    Write-Host "[OK] $Text" -ForegroundColor Green
}

function Write-Warn($Text) {
    Write-Host "[AVISO] $Text" -ForegroundColor Yellow
}

function Write-Fail($Text) {
    Write-Host "[ERRO] $Text" -ForegroundColor Red
}

function Ask-YesNo($Question, [bool]$DefaultYes = $false) {
    if ($NoPrompt) {
        return $DefaultYes
    }
    $suffix = if ($DefaultYes) { "[S/n]" } else { "[s/N]" }
    while ($true) {
        $answer = Read-Host "$Question $suffix"
        if ([string]::IsNullOrWhiteSpace($answer)) {
            return $DefaultYes
        }
        switch ($answer.Trim().ToLowerInvariant()) {
            "s" { return $true }
            "sim" { return $true }
            "y" { return $true }
            "yes" { return $true }
            "n" { return $false }
            "nao" { return $false }
            "no" { return $false }
            default { Write-Warn "Responda s ou n." }
        }
    }
}

function Get-ArgsTail([string[]]$Command) {
    if ($Command.Count -le 1) {
        return @()
    }
    return @($Command[1..($Command.Count - 1)])
}

function Invoke-External {
    param(
        [Parameter(Mandatory = $true)][string[]]$Command,
        [switch]$AllowFail
    )

    $exe = $Command[0]
    $args = Get-ArgsTail $Command
    Write-Host ("> " + ($Command -join " ")) -ForegroundColor DarkGray
    & $exe @args
    $code = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }
    if ($code -ne 0 -and -not $AllowFail) {
        throw "Command failed with exit ${code}: $($Command -join ' ')"
    }
    return $code
}

function Invoke-Capture {
    param([Parameter(Mandatory = $true)][string[]]$Command)
    $exe = $Command[0]
    $args = Get-ArgsTail $Command
    $output = & $exe @args 2>&1
    $code = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }
    return [pscustomobject]@{
        Code = $code
        Output = (($output | ForEach-Object { "$_" }) -join "`n")
    }
}

$script:PythonCommand = $null

function Find-Python {
    $candidates = @(
        @("py", "-3"),
        @("python")
    )
    foreach ($candidate in $candidates) {
        $result = Invoke-Capture -Command ($candidate + @("--version"))
        if ($result.Code -eq 0) {
            $script:PythonCommand = [string[]]$candidate
            Write-Ok "Python encontrado: $($result.Output.Trim())"
            return $true
        }
    }
    return $false
}

function Invoke-Python {
    param([Parameter(Mandatory = $true)][string[]]$Args)
    return Invoke-External -Command ($script:PythonCommand + $Args)
}

function Invoke-PythonCapture {
    param([Parameter(Mandatory = $true)][string[]]$Args)
    return Invoke-Capture -Command ($script:PythonCommand + $Args)
}

function Add-UserPath {
    param([Parameter(Mandatory = $true)][string]$PathToAdd)
    $resolved = [Environment]::ExpandEnvironmentVariables($PathToAdd)
    if (-not (Test-Path $resolved)) {
        New-Item -ItemType Directory -Force -Path $resolved | Out-Null
    }

    $sessionParts = @($env:PATH -split ";" | Where-Object { $_ })
    if ($sessionParts -notcontains $resolved) {
        $env:PATH = "$resolved;$env:PATH"
    }

    $userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    $userParts = @($userPath -split ";" | Where-Object { $_ })
    if ($userParts -notcontains $resolved) {
        $newPath = if ([string]::IsNullOrWhiteSpace($userPath)) {
            $resolved
        } else {
            "$resolved;$userPath"
        }
        [Environment]::SetEnvironmentVariable("PATH", $newPath, "User")
        Write-Ok "PATH do usuario atualizado: $resolved"
    } else {
        Write-Ok "PATH do usuario ja contem: $resolved"
    }
}

function Ensure-PythonToolchain {
    Write-Title "Python e comandos CCS"
    if (-not (Find-Python)) {
        Write-Fail "Python 3 nao foi encontrado."
        Write-Host "Instale Python 3.11+ no escopo do usuario e rode este instalador novamente."
        Write-Host "Download: https://www.python.org/downloads/windows/"
        throw "Python 3 not found"
    }

    $pip = Invoke-PythonCapture -Args @("-m", "pip", "--version")
    if ($pip.Code -ne 0) {
        Write-Warn "pip nao encontrado. Tentando habilitar com ensurepip."
        Invoke-Python -Args @("-m", "ensurepip", "--upgrade") | Out-Null
    } else {
        Write-Ok $pip.Output.Trim()
    }

    $userBase = Invoke-PythonCapture -Args @("-m", "site", "--user-base")
    if ($userBase.Code -ne 0 -or [string]::IsNullOrWhiteSpace($userBase.Output)) {
        throw "Nao foi possivel descobrir o Python user-base."
    }
    $scriptsPath = Join-Path $userBase.Output.Trim() "Scripts"
    Add-UserPath $scriptsPath

    Write-Host "Instalando/atualizando pacote local em modo editavel..."
    Invoke-Python -Args @("-m", "pip", "install", "--user", "-e", $RepoRoot) | Out-Null
    $script:InstalledToolchain = $true

    $ccs = Invoke-Capture -Command @("ccs-uip", "--help")
    if ($ccs.Code -ne 0) {
        throw "ccs-uip nao ficou disponivel no PATH."
    }
    Write-Ok "ccs-uip disponivel"

    $publish = Invoke-Capture -Command @("ccs-uip-publish", "--help")
    if ($publish.Code -ne 0) {
        throw "ccs-uip-publish nao ficou disponivel no PATH."
    }
    Write-Ok "ccs-uip-publish disponivel"
}

function Ensure-UipCli {
    Write-Title "CLI oficial UiPath"
    $existing = Get-Command "uip" -ErrorAction SilentlyContinue
    if ($existing) {
        $version = Invoke-Capture -Command @("uip", "--version")
        if ($version.Code -eq 0) {
            Write-Ok "uip encontrado: $($version.Output.Trim())"
            return
        }
        Write-Warn "uip foi encontrado, mas nao respondeu a --version."
    }

    Write-Warn "CLI oficial UiPath uip nao encontrada."
    $npm = Get-Command "npm" -ErrorAction SilentlyContinue
    if (-not $npm) {
        Write-Warn "Node.js/npm nao encontrado. Instale Node.js LTS e rode o instalador novamente."
        Write-Host "Download: https://nodejs.org/"
        return
    }
    Write-Ok "npm encontrado: $($npm.Source)"

    if (-not (Ask-YesNo "Instalar/atualizar @uipath/cli@1 para o usuario atual?" $true)) {
        Write-Warn "Instalacao do uip pulada. Publish nao funcionara ate o uip existir."
        return
    }

    $npmPrefix = Join-Path $env:APPDATA "npm"
    New-Item -ItemType Directory -Force -Path $npmPrefix | Out-Null
    Invoke-External -Command @("npm", "config", "set", "prefix", $npmPrefix) | Out-Null
    Add-UserPath $npmPrefix
    Invoke-External -Command @("npm", "install", "-g", "@uipath/cli@1") | Out-Null

    $versionAfter = Invoke-Capture -Command @("uip", "--version")
    if ($versionAfter.Code -eq 0) {
        Write-Ok "uip instalado: $($versionAfter.Output.Trim())"
    } else {
        Write-Warn "npm terminou, mas uip ainda nao respondeu nesta janela. Abra um novo PowerShell e teste: uip --version"
    }
}

function Ensure-DotNet {
    Write-Title ".NET SDK"
    $dotnet = Get-Command "dotnet" -ErrorAction SilentlyContinue
    $homeDotnet = Join-Path $HOME ".dotnet\dotnet.exe"
    if (-not $dotnet -and (Test-Path $homeDotnet)) {
        [Environment]::SetEnvironmentVariable("DOTNET_ROOT", (Split-Path $homeDotnet), "User")
        [Environment]::SetEnvironmentVariable("UIP_TOOLCHAIN_DOTNET_ROOT", (Split-Path $homeDotnet), "User")
        Add-UserPath (Split-Path $homeDotnet)
        $dotnet = Get-Command "dotnet" -ErrorAction SilentlyContinue
    }

    if ($dotnet) {
        $sdks = Invoke-Capture -Command @("dotnet", "--list-sdks")
        if ($sdks.Code -eq 0 -and -not [string]::IsNullOrWhiteSpace($sdks.Output)) {
            Write-Ok ".NET SDK encontrado:"
            Write-Host $sdks.Output
            return
        }
        Write-Warn "dotnet existe, mas nao listou SDK instalado."
    } else {
        Write-Warn ".NET SDK nao encontrado."
    }

    Write-Host "O publish pode falhar no uip rpa pack sem SDK compativel."
    if (Ask-YesNo "Instalar .NET SDK portable em %USERPROFILE%\.dotnet agora?" $false) {
        $installer = Join-Path $RepoRoot "tools\install-dotnet-sdk-portable.cmd"
        if (-not (Test-Path $installer)) {
            throw "Instalador portable nao encontrado: $installer"
        }
        Invoke-External -Command @("cmd.exe", "/c", $installer) | Out-Null
        Add-UserPath (Join-Path $HOME ".dotnet")
    }
}

function Run-Doctor {
    Write-Title "Diagnostico final"
    if (-not $script:PythonCommand) {
        if (-not (Find-Python)) {
            Write-Warn "Python ausente; diagnostico interno pulado."
            return
        }
    }
    $code = Invoke-External -Command (
        $script:PythonCommand + @("-m", "uip_engine.cli", "doctor-uipath-cli")
    ) -AllowFail
    if ($code -ne 0) {
        Write-Warn "Diagnostico apontou pendencias. A instalacao da toolchain pode estar OK, mas o publish pode exigir ajustes."
    }
}

function Run-RecommendedInstall {
    Ensure-PythonToolchain
    Ensure-UipCli
    Ensure-DotNet
    Run-Doctor
}

try {
    Write-Host ""
    Write-Host "CCS UiPath Toolchain - instalador interativo" -ForegroundColor Cyan
    Write-Host "Pasta da toolchain: $RepoRoot"
    Write-Host "Log: $LogPath"
    Write-Host ""

    if ($DiagnosticsOnly) {
        Run-Doctor
    } elseif ($NoPrompt) {
        Run-RecommendedInstall
    } else {
        Write-Host "Escolha uma opcao:"
        Write-Host "  1. Instalacao recomendada"
        Write-Host "  2. Diagnostico apenas"
        Write-Host "  3. Instalar/atualizar somente a CLI oficial uip"
        Write-Host "  4. Instalar somente .NET SDK portable"
        Write-Host "  0. Sair"
        $choice = Read-Host "Opcao [1]"
        if ([string]::IsNullOrWhiteSpace($choice)) {
            $choice = "1"
        }

        switch ($choice.Trim()) {
            "1" { Run-RecommendedInstall }
            "2" { Run-Doctor }
            "3" { Ensure-UipCli }
            "4" { Ensure-DotNet }
            "0" { Write-Host "Saindo."; exit 0 }
            default { throw "Opcao invalida: $choice" }
        }
    }

    Write-Title "Pronto"
    if ($script:InstalledToolchain) {
        Write-Ok "Comandos instalados para o usuario atual."
    } else {
        Write-Ok "Acao concluida."
    }
    Write-Host "Abra um novo PowerShell se algum comando nao aparecer nesta janela."
    Write-Host ""
    Write-Host "Teste:"
    Write-Host "  ccs-uip-publish --help"
    Write-Host ""
    Write-Host "Publish DEV:"
    Write-Host '  ccs-uip-publish minor "C:\Users\lisan\Desktop\NC-179\3. done"'
    exit 0
} catch {
    Write-Fail $_.Exception.Message
    Write-Host ""
    Write-Host "Log da instalacao: $LogPath"
    exit 1
} finally {
    try {
        Stop-Transcript | Out-Null
    } catch {
    }
}
