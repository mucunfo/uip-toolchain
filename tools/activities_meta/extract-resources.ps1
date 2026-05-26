param(
  [Parameter(Mandatory=$true)][string]$ResourceDll,
  [Parameter(Mandatory=$true)][string]$OutJson
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ResourceDll)) { throw "ResourceDll not found: $ResourceDll" }

$asm = [System.Reflection.Assembly]::LoadFrom($ResourceDll)
$resNames = $asm.GetManifestResourceNames() | Where-Object { $_ -like "*.resources" }

$entries = @{}
foreach ($name in $resNames) {
  $stream = $asm.GetManifestResourceStream($name)
  if (-not $stream) { continue }
  try {
    $reader = New-Object System.Resources.ResourceReader $stream
    foreach ($e in $reader) {
      if ($e.Key -and $e.Value -is [string]) {
        # Last-write-wins se chave repetida entre múltiplos resource names (raro)
        $entries[[string]$e.Key] = [string]$e.Value
      }
    }
    $reader.Close()
  } finally {
    $stream.Close()
  }
}

$result = [ordered]@{
  Assembly  = $asm.GetName().Name
  Culture   = $asm.GetName().CultureInfo.Name
  Version   = $asm.GetName().Version.ToString()
  Count     = $entries.Count
  Entries   = $entries
}

$json = $result | ConvertTo-Json -Depth 5 -Compress:$false
[System.IO.File]::WriteAllText($OutJson, $json, [System.Text.Encoding]::UTF8)
Write-Host "OK: $OutJson | $($entries.Count) entries (culture=$($asm.GetName().CultureInfo.Name))"
