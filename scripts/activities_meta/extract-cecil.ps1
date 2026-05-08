param(
  [Parameter(Mandatory=$true)][string]$ActivityDll,
  [Parameter(Mandatory=$true)][string]$OutJson,
  [string]$StudioDir = "$env:LOCALAPPDATA\Programs\UiPathPlatform\Studio",
  [string[]]$ExtraSearchDirs = @()
)

# Auto-resolve latest Studio version dir if user passed parent
if (Test-Path $StudioDir -PathType Container) {
  $sub = Get-ChildItem $StudioDir -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^\d' } | Sort-Object Name -Descending | Select-Object -First 1
  if ($sub) { $StudioDir = $sub.FullName }
}

$ErrorActionPreference = "Stop"

$cecilDll = Join-Path $StudioDir "Mono.Cecil.dll"
if (-not (Test-Path $cecilDll)) { throw "Mono.Cecil.dll not found in $StudioDir" }
Add-Type -Path $cecilDll -ErrorAction SilentlyContinue

$resolver = New-Object Mono.Cecil.DefaultAssemblyResolver
$searchDirs = @((Split-Path $ActivityDll -Parent), $StudioDir) + $ExtraSearchDirs
foreach ($d in $searchDirs) { if (Test-Path $d) { $resolver.AddSearchDirectory($d) } }

$readerParams = New-Object Mono.Cecil.ReaderParameters
$readerParams.AssemblyResolver = $resolver

$asm = [Mono.Cecil.AssemblyDefinition]::ReadAssembly($ActivityDll, $readerParams)

# --- baseline EN resources from main assembly (best-effort via Reflection) ---
# Reflection.Assembly.LoadFrom requer netfx-compatible. Para netcore-targeted
# DLLs, fallback silencioso: dump não inclui resources mas extractor continua.
$baselineResources = @{}
try {
  $reflAsm = [System.Reflection.Assembly]::LoadFrom($ActivityDll)
  $resNames = $reflAsm.GetManifestResourceNames() | Where-Object { $_ -like "*.resources" }
  foreach ($n in $resNames) {
    $stream = $reflAsm.GetManifestResourceStream($n)
    if ($stream) {
      try {
        $reader = New-Object System.Resources.ResourceReader $stream
        foreach ($e in $reader) {
          if ($e.Key -and $e.Value -is [string] -and $e.Value -ne "") {
            $baselineResources[[string]$e.Key] = [string]$e.Value
          }
        }
        $reader.Close()
      } finally { $stream.Close() }
    }
  }
} catch {
  # netcore assembly ou other load failure: skip resources (não fatal)
}

# --- helpers ---

function Get-BaseChain([Mono.Cecil.TypeDefinition]$t) {
  $chain = @()
  $current = $t.BaseType
  while ($current -ne $null) {
    $chain += $current.FullName
    try { $resolved = $current.Resolve() } catch { $resolved = $null }
    if ($resolved -eq $null) { break }
    $current = $resolved.BaseType
  }
  return $chain
}

$activityRoots = @(
  "System.Activities.Activity",
  "System.Activities.CodeActivity",
  "System.Activities.NativeActivity",
  "System.Activities.AsyncCodeActivity",
  "System.Activities.Statements.Sequence"
)
function Test-IsActivity([Mono.Cecil.TypeDefinition]$t) {
  if (-not $t.IsClass) { return $false }
  if ($t.IsAbstract) { return $false }
  $chain = Get-BaseChain $t
  foreach ($b in $chain) {
    foreach ($r in $activityRoots) {
      if ($b -eq $r -or $b -like "$r``1*" -or $b -like "$r``2*") { return $true }
    }
  }
  return $false
}

function Get-PropertyInfo([Mono.Cecil.PropertyDefinition]$prop) {
  # Returns @{Direction; ValueType; IsArgument}.
  # Argument-typed: Direction in (In|Out|InOut) e IsArgument=$true.
  # Plain: Direction='Plain', ValueType=tipo direto, IsArgument=$false.
  $pt = $prop.PropertyType
  $name = $pt.FullName
  $base = $name -replace '`1<.*$','' -replace '`1$',''
  $direction = $null
  $valueType = $null
  switch ($base) {
    "System.Activities.InArgument"    { $direction = "In" }
    "System.Activities.OutArgument"   { $direction = "Out" }
    "System.Activities.InOutArgument" { $direction = "InOut" }
    "System.Activities.Argument"      { $direction = "In" }
  }
  if ($direction) {
    if ($pt -is [Mono.Cecil.GenericInstanceType] -and $pt.GenericArguments.Count -gt 0) {
      $valueType = $pt.GenericArguments[0].FullName
    }
    return @{ Direction = $direction; ValueType = $valueType; IsArgument = $true }
  }
  # Plain property — usar tipo direto. Pular delegates/eventhandlers.
  if ($name -match '^System\.EventHandler' -or $name -match 'Delegate$') { return $null }
  return @{ Direction = "Plain"; ValueType = $name; IsArgument = $false }
}

function ConvertTo-PrimitiveValue($v) {
  while ($v -is [Mono.Cecil.CustomAttributeArgument]) { $v = $v.Value }
  if ($v -is [Mono.Cecil.TypeReference]) { return $v.FullName }
  if ($v -is [System.Array] -or $v -is [System.Collections.IEnumerable] -and -not ($v -is [string])) {
    $out = @()
    foreach ($i in $v) { $out += ConvertTo-PrimitiveValue $i }
    return $out
  }
  return $v
}

function Get-AttrValue([Mono.Cecil.CustomAttribute]$attr, [int]$idx = 0) {
  if ($attr.ConstructorArguments.Count -gt $idx) {
    return ConvertTo-PrimitiveValue $attr.ConstructorArguments[$idx].Value
  }
  return $null
}

function Get-NamedAttr([Mono.Cecil.CustomAttribute]$attr, [string]$name) {
  foreach ($p in $attr.Properties) { if ($p.Name -eq $name) { return ConvertTo-PrimitiveValue $p.Argument.Value } }
  foreach ($f in $attr.Fields)     { if ($f.Name -eq $name) { return ConvertTo-PrimitiveValue $f.Argument.Value } }
  return $null
}

# Assembly-level xmlns mappings
$xmlnsPairs = @()
$xmlnsClrNamespaces = @{}  # case-sensitive lookup via separate dict
foreach ($attr in $asm.CustomAttributes) {
  if ($attr.AttributeType.FullName -eq "System.Windows.Markup.XmlnsDefinitionAttribute") {
    $xmlNs = Get-AttrValue $attr 0
    $clrNs = Get-AttrValue $attr 1
    $xmlnsPairs += [pscustomobject]@{ ClrNamespace = $clrNs; Xmlns = $xmlNs }
    if ($clrNs) { $xmlnsClrNamespaces[$clrNs] = $true }
  }
}
function Get-XmlnsForClrNs([string]$clrNs) {
  $hits = $xmlnsPairs | Where-Object { $_.ClrNamespace -ceq $clrNs } | Select-Object -ExpandProperty Xmlns
  if ($hits) { return @($hits) } else { return @() }
}
function Test-NamespaceHasXmlns([string]$ns) {
  if (-not $ns) { return $false }
  foreach ($p in $xmlnsPairs) { if ($p.ClrNamespace -ceq $ns) { return $true } }
  return $false
}

function Get-AllTypes($module) {
  $stack = New-Object System.Collections.Stack
  foreach ($t in $module.Types) { $stack.Push($t) }
  while ($stack.Count -gt 0) {
    $t = $stack.Pop()
    , $t
    foreach ($n in $t.NestedTypes) { $stack.Push($n) }
  }
}

# --- main loop: types públicos com namespace mapeado em xmlns ---

$entries = @()
foreach ($t in (Get-AllTypes $asm.MainModule)) {
  if (-not $t.IsPublic) { continue }
  if ($t.IsInterface) { continue }

  $isActivity = Test-IsActivity $t
  $hasXmlns = Test-NamespaceHasXmlns $t.Namespace

  # Activity: incluir mesmo se sub-namespace não mapeado (xmlns herda do parent na hora do uso XAML).
  # Non-Activity: exige xmlns mapping E não-abstract para evitar incluir DTOs internos / classes utilitárias.
  if ($isActivity) {
    # OK
  } elseif ($hasXmlns -and -not $t.IsAbstract) {
    # data-object com xmlns
  } else {
    continue
  }

  $kind = if ($isActivity) { "Activity" } else { "DataObject" }

  $displayName = $null; $category = $null; $description = $null; $browsable = $true; $designerType = $null
  $contentProperty = $null  # F34: nome da property que recebe child element (XAML default content)
  foreach ($attr in $t.CustomAttributes) {
    switch ($attr.AttributeType.FullName) {
      "System.ComponentModel.DisplayNameAttribute" { $displayName = Get-AttrValue $attr 0 }
      "System.ComponentModel.CategoryAttribute"    { $category    = Get-AttrValue $attr 0 }
      "System.ComponentModel.DescriptionAttribute" { $description = Get-AttrValue $attr 0 }
      "System.ComponentModel.BrowsableAttribute"   { $browsable   = [bool](Get-AttrValue $attr 0) }
      "System.ComponentModel.DesignerAttribute"    { $designerType = Get-AttrValue $attr 0 }
      "System.Windows.Markup.ContentPropertyAttribute" { $contentProperty = Get-AttrValue $attr 0 }
    }
  }

  # F34: Activity shape — qual base class concrete (Activity, ActivityFunc<T>,
  # ActivityAction, NativeActivity, etc.). Determina rules de child:
  #   - ActivityAction → 1 Activity-shape child (wrap-able em Sequence)
  #   - ActivityFunc<T1..TResult> → handler signature, NÃO wrap-able
  #   - Activity / NativeActivity / Sequence → multi-child OK
  $activityShape = $null
  if ($isActivity) {
    $chain = Get-BaseChain $t
    foreach ($b in $chain) {
      switch -Regex ($b) {
        "^System\.Activities\.ActivityFunc``\d+" { $activityShape = "ActivityFunc"; break }
        "^System\.Activities\.ActivityAction(``\d+)?" { $activityShape = "ActivityAction"; break }
        "^System\.Activities\.NativeActivity"        { $activityShape = "NativeActivity"; break }
        "^System\.Activities\.AsyncCodeActivity"     { $activityShape = "AsyncCodeActivity"; break }
        "^System\.Activities\.CodeActivity"          { $activityShape = "CodeActivity"; break }
        "^System\.Activities\.Statements\.Sequence"  { $activityShape = "Sequence"; break }
        "^System\.Activities\.Activity(``\d+)?"      { $activityShape = "Activity"; break }
      }
      if ($activityShape) { break }
    }
  }

  $args = @()
  $current = $t
  $seen = @{}
  while ($current -ne $null) {
    foreach ($prop in $current.Properties) {
      if ($seen.ContainsKey($prop.Name)) { continue }
      # Aceita property pública com getter; setter opcional (collections com getter only ainda relevantes)
      if ($prop.GetMethod -eq $null -or -not $prop.GetMethod.IsPublic) { continue }
      $info = Get-PropertyInfo $prop
      if ($info -eq $null) { continue }
      $seen[$prop.Name] = $true

      $required = $false; $overloadGroup = $null; $pCat = $null; $pDesc = $null; $pDefault = $null; $pDisplay = $null; $pBrowsable = $true; $metaInfo = @()
      $collectionItemType = $null  # F34: tipo aceito pela coleção (se aplicável)
      foreach ($attr in $prop.CustomAttributes) {
        $fqn = $attr.AttributeType.FullName
        switch -Regex ($fqn) {
          "^System\.Activities\.RequiredArgumentAttribute$"  { $required = $true; break }
          "OverloadGroupAttribute$"                          { $overloadGroup = Get-AttrValue $attr 0; break }
          "(System\.ComponentModel\.CategoryAttribute|LocalizedCategoryAttribute)$" { if (-not $pCat)     { $pCat     = Get-AttrValue $attr 0 }; break }
          "(System\.ComponentModel\.DescriptionAttribute|LocalizedDescriptionAttribute)$" { if (-not $pDesc) { $pDesc = Get-AttrValue $attr 0 }; break }
          "(System\.ComponentModel\.DisplayNameAttribute|LocalizedDisplayNameAttribute)$" { if (-not $pDisplay) { $pDisplay = Get-AttrValue $attr 0 }; break }
          "^System\.ComponentModel\.DefaultValueAttribute$"  { $pDefault = Get-AttrValue $attr 0; break }
          "^System\.ComponentModel\.BrowsableAttribute$"     { $pBrowsable = [bool](Get-AttrValue $attr 0); break }
          "^System\.Windows\.Markup\.ContentWrapperAttribute$" { break }
          "CollectionItemTypeAttribute$"                     { $collectionItemType = Get-AttrValue $attr 0; break }
          "MetadataInfoAttribute$" {
            $k = $null; $v = $null
            foreach ($pa in $attr.Properties) { if ($pa.Name -eq "Key") { $k = ConvertTo-PrimitiveValue $pa.Argument.Value } elseif ($pa.Name -eq "Value") { $v = ConvertTo-PrimitiveValue $pa.Argument.Value } }
            if ($k) { $metaInfo += [pscustomobject]@{ Key = $k; Value = $v } }
            break
          }
        }
      }
      # NÃO pular Browsable=false — propriedades não-design-time ainda
      # podem aparecer em XAML (ex: BuildDataTable.TableInfo). Marcar flag.

      $args += [ordered]@{
        Name          = $prop.Name
        DisplayName   = $pDisplay
        Direction     = $info.Direction
        Type          = $info.ValueType
        IsArgument    = $info.IsArgument
        Required      = $required
        Browsable     = $pBrowsable
        Category      = $pCat
        Description   = $pDesc
        DefaultValue  = $pDefault
        OverloadGroup = $overloadGroup
        MetadataInfo  = $metaInfo
        CollectionItemType = $collectionItemType  # F34
      }
    }
    try { $current = if ($current.BaseType) { $current.BaseType.Resolve() } else { $null } } catch { $current = $null }
  }

  $clrNs = $t.Namespace
  $xmlnsCandidates = Get-XmlnsForClrNs $clrNs
  if (-not $xmlnsCandidates -or $xmlnsCandidates.Count -eq 0) {
    # Fallback: assembly-level xmlns únicos (Activity em sub-namespace herda
    # xmlns canônico do top-level package).
    $xmlnsCandidates = @($xmlnsPairs | Select-Object -ExpandProperty Xmlns -Unique)
  }

  $entries += [ordered]@{
    FullName    = $t.FullName
    Name        = $t.Name
    Namespace   = $clrNs
    Kind        = $kind
    DisplayName = $displayName
    Category    = $category
    Description = $description
    Browsable   = $browsable
    Designer    = $designerType
    Xmlns       = $xmlnsCandidates
    Arguments   = $args
    # F34: schema-driven parent-restrictive determination
    ContentProperty = $contentProperty
    ActivityShape   = $activityShape
  }
}

$result = [ordered]@{
  Assembly       = $asm.Name.Name
  Version        = $asm.Name.Version.ToString()
  TargetRuntime  = $asm.MainModule.RuntimeVersion
  XmlnsPairs     = $xmlnsPairs
  ActivityCount  = ($entries | Where-Object { $_.Kind -eq "Activity" }).Count
  DataObjectCount = ($entries | Where-Object { $_.Kind -eq "DataObject" }).Count
  EntryCount     = $entries.Count
  Activities     = $entries  # mantém chave "Activities" para compat backward; inclui DataObjects
  ResourcesBaseline = $baselineResources  # neutral culture (EN) — used by build-schema
}

try {
  $json = $result | ConvertTo-Json -Depth 10 -Compress:$false
} catch {
  Write-Warning "Bulk ConvertTo-Json failed: $($_.Exception.Message). Diagnosing per-entry..."
  $bad = @()
  for ($i = 0; $i -lt $entries.Count; $i++) {
    try { $null = $entries[$i] | ConvertTo-Json -Depth 10 -Compress:$false } catch { $bad += @{ Index = $i; Name = $entries[$i].FullName; Err = $_.Exception.Message } }
  }
  if ($bad.Count -gt 0) {
    Write-Host "Bad entries: $($bad.Count)"
    $bad | Select-Object -First 5 | ForEach-Object { Write-Host "  [$($_.Index)] $($_.Name) -- $($_.Err)" }
  }
  throw
}
[System.IO.File]::WriteAllText($OutJson, $json, [System.Text.Encoding]::UTF8)
$actCount = ($entries | Where-Object { $_.Kind -eq "Activity" }).Count
$doCount = ($entries | Where-Object { $_.Kind -eq "DataObject" }).Count
Write-Host "OK: $OutJson | $actCount activities + $doCount data-objects"
