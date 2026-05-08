param(
  [string]$NugetCache = "$env:USERPROFILE\.nuget\packages",
  [string]$OutDir = "$PSScriptRoot\..\..\.tmp\activities_dump\packages",
  [string]$ConsolidatedJson = "$PSScriptRoot\..\..\.tmp\activities_dump\activities-all.json",
  [string]$StudioDir = "$env:LOCALAPPDATA\Programs\UiPathPlatform\Studio"
)

# Auto-resolve latest Studio version dir if user passed parent
if (Test-Path $StudioDir -PathType Container) {
  $sub = Get-ChildItem $StudioDir -Directory | Where-Object { $_.Name -match '^\d' } | Sort-Object Name -Descending | Select-Object -First 1
  if ($sub) { $StudioDir = $sub.FullName }
}

$ErrorActionPreference = "Continue"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$extractor = Join-Path $PSScriptRoot "extract-cecil.ps1"
$tfmPriority = @("net6.0-windows7.0","net6.0","net8.0-windows7.0","net8.0","net461","netstandard2.0")

function Get-LatestVersion([string]$pkgDir) {
  $versions = Get-ChildItem $pkgDir -Directory | Where-Object { $_.Name -match '^\d' }
  if (-not $versions) { return $null }
  # System.Version-aware sort, fallback alphabetic
  $versions | Sort-Object {
    try { [System.Management.Automation.SemanticVersion]::Parse(($_.Name -replace '-.*','')) } catch { [System.Version]"0.0" }
  } -Descending | Select-Object -First 1
}

function Get-PreferredTfmDir([string]$libDir) {
  if (-not (Test-Path $libDir)) { return $null }
  foreach ($tfm in $tfmPriority) {
    $p = Join-Path $libDir $tfm
    if (Test-Path $p) { return $p }
  }
  $first = Get-ChildItem $libDir -Directory | Select-Object -First 1
  if ($first) { return $first.FullName }
  return $null
}

$packages = Get-ChildItem $NugetCache -Directory | Where-Object { $_.Name -like "uipath*activities*" -or $_.Name -eq "uipath.system.activities" -or $_.Name -eq "uipath.uiautomation.activities" }
"Found $($packages.Count) packages"

$results = @()
foreach ($pkg in $packages) {
  $latest = Get-LatestVersion $pkg.FullName
  if (-not $latest) { continue }
  $libDir = Join-Path $latest.FullName "lib"
  $tfmDir = Get-PreferredTfmDir $libDir
  if (-not $tfmDir) { Write-Host "  SKIP $($pkg.Name) -- no lib"; continue }

  # Find candidate dll: prefer "*.Activities.dll" without sub-modifiers
  $dlls = Get-ChildItem $tfmDir -Filter "UiPath.*.dll" -File | Where-Object {
    $_.Name -notmatch "\.(Design|ViewModels|API|Package|resources)\.dll$" -and
    $_.Name -notmatch "\.resources\.dll$"
  }

  foreach ($dll in $dlls) {
    $outFile = Join-Path $OutDir ("{0}__{1}.json" -f $pkg.Name, $dll.BaseName)
    Write-Host ("EXTRACT {0}/{1}/{2}" -f $pkg.Name, $latest.Name, $dll.Name)
    try {
      $r = & $extractor -ActivityDll $dll.FullName -OutJson $outFile -StudioDir $StudioDir -ExtraSearchDirs @($tfmDir) 2>&1
      $j = Get-Content $outFile -Raw | ConvertFrom-Json
      $totalEntries = if ($j.EntryCount) { $j.EntryCount } else { $j.ActivityCount }
      if ($totalEntries -gt 0 -and $j.ActivityCount -gt 0) {
        # Capturar satellite pt-BR se existir
        $resourcesPtBr = @{}
        $satelliteDll = Join-Path $tfmDir "pt-BR\$($dll.BaseName).resources.dll"
        if (Test-Path $satelliteDll) {
          $resOut = Join-Path $OutDir ("{0}__{1}__pt-BR.resources.json" -f $pkg.Name, $dll.BaseName)
          try {
            & "$PSScriptRoot\extract-resources.ps1" -ResourceDll $satelliteDll -OutJson $resOut 2>&1 | Out-Null
            $rj = Get-Content $resOut -Raw | ConvertFrom-Json
            $rj.Entries.PSObject.Properties | ForEach-Object {
              if ($_.Value -ne "") { $resourcesPtBr[$_.Name] = $_.Value }
            }
          } catch {}
        }

        $results += [pscustomobject]@{
          Package    = $pkg.Name
          Version    = $latest.Name
          Tfm        = (Split-Path $tfmDir -Leaf)
          Dll        = $dll.Name
          Count      = $j.ActivityCount
          DataObjects = $j.DataObjectCount
          JsonFile   = $outFile
          ResourcesPtBr = $resourcesPtBr
          ResourcesBaseline = $j.ResourcesBaseline
        }
      } else {
        Remove-Item $outFile -ErrorAction SilentlyContinue
      }
    } catch {
      Write-Host ("  ERR: {0}" -f $_.Exception.Message)
    }
  }
}

# Consolidate
"`n=== Consolidating ==="
$all = @()
foreach ($r in $results) {
  $j = Get-Content $r.JsonFile -Raw | ConvertFrom-Json
  foreach ($act in $j.Activities) {
    $all += [pscustomobject]@{
      Package      = $r.Package
      PkgVersion   = $r.Version
      Assembly     = $j.Assembly
      AsmVersion   = $j.Version
      FullName     = $act.FullName
      Name         = $act.Name
      Namespace    = $act.Namespace
      Kind         = $act.Kind
      Xmlns        = $act.Xmlns
      DisplayName  = $act.DisplayName
      Category     = $act.Category
      Description  = $act.Description
      Designer     = $act.Designer
      ArgCount     = $act.Arguments.Count
      Arguments    = $act.Arguments
    }
  }
}

$pkgIndex = [ordered]@{}
foreach ($r in $results) {
  if (-not $pkgIndex.Contains($r.Package)) {
    $pkgIndex[$r.Package] = [ordered]@{
      Version            = $r.Version
      ResourcesBaseline  = $r.ResourcesBaseline
      ResourcesPtBr      = $r.ResourcesPtBr
    }
  }
}

$summary = [ordered]@{
  GeneratedAt   = (Get-Date -Format "o")
  PackageCount  = $results.Count
  ActivityCount = $all.Count
  PackageIndex  = $pkgIndex
  Packages      = $results | ForEach-Object { @{Package=$_.Package; Version=$_.Version; Count=$_.Count} }
  Activities    = $all
}

$json = $summary | ConvertTo-Json -Depth 12 -Compress:$false
[System.IO.File]::WriteAllText($ConsolidatedJson, $json, [System.Text.Encoding]::UTF8)
"OK: $ConsolidatedJson"
"Packages: $($results.Count)"
"Activities: $($all.Count)"
