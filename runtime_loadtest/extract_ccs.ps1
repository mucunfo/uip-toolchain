# extract_ccs.ps1
# ---------------------------------------------------------------------------
# Phase 1A.2 helper — extrai DLLs CCS_*.nupkg lib/net6.0-windows7.0/ para
# runtime_loadtest/ccs_libs/ pra closure de assembly em runtime XAML load.
#
# Idempotente: regenera ccs_libs/ from scratch sem mexer no .nupkgs/ source.
# Output flat: todos *.dll direto em ccs_libs/ (NÃO subfolders), pra que
# Directory.GetFiles(binDir, "*.dll") + PreloadXmlnsBearingAssemblies()
# (Program.cs) enxergue eles depois do MSBuild copy.
#
# Usage:
#   pwsh -File extract_ccs.ps1
#   pwsh -File extract_ccs.ps1 -CcsDir "C:\custom\.nupkgs"  # override
# ---------------------------------------------------------------------------
[CmdletBinding()]
param(
    [string]$CcsDir = "C:\Users\lisan\OneDrive - Sicoob\Projects\.nupkgs"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$outDir = Join-Path $PSScriptRoot "ccs_libs"
if (Test-Path $outDir) {
    Remove-Item -Recurse -Force $outDir
}
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$total = 0
foreach ($nupkg in (Get-ChildItem -Path $CcsDir -Filter "CCS_*.nupkg" | Sort-Object Name)) {
    $zip = [System.IO.Compression.ZipFile]::OpenRead($nupkg.FullName)
    try {
        foreach ($entry in $zip.Entries) {
            if (-not $entry.FullName.ToLower().EndsWith(".dll")) { continue }
            # Aceita lib/net6.0-windows7.0/ E lib/net6.0-windows/ (fallback).
            if ($entry.FullName -notmatch "(?i)lib/net6\.0-windows(7\.0)?/") { continue }
            $destPath = Join-Path $outDir ([System.IO.Path]::GetFileName($entry.FullName))
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $destPath, $true)
            $total++
        }
    } finally {
        $zip.Dispose()
    }
}

# Marker pra MSBuild target idempotência.
$marker = Join-Path $outDir ".extracted.marker"
Set-Content -Path $marker -Value (Get-Date -Format "o") -Encoding utf8

Write-Host "Extracted $total CCS DLLs to $outDir"
Get-ChildItem -Path $outDir -Filter "*.dll" | Sort-Object Name | Select-Object -ExpandProperty Name
