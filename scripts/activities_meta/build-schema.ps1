param(
  [string]$Source = "$PSScriptRoot\..\..\.tmp\activities_dump\activities-all.json",
  [string]$OutDir = "$PSScriptRoot\..\..\assets\activities",
  [switch]$IncludeBrowsableFalse
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$j = Get-Content $Source -Raw | ConvertFrom-Json
$pkgIndex = if ($j.PackageIndex) { $j.PackageIndex } else { @{} }

function Format-Type($t) {
  if (-not $t) { return "?" }
  $t = $t -replace 'System\.','' -replace '`1<','<' -replace '`2<','<' -replace '>$','>'
  return $t
}

function Format-Default($v) {
  if ($null -eq $v) { return $null }
  if ($v -is [bool])   { return $v.ToString().ToLower() }
  if ($v -is [string]) { return '"' + ($v -replace '"','\"') + '"' }
  return [string]$v
}

function Resolve-Label($displayKey, $resourcesBaseline, $resourcesPtBr) {
  # Preference order:
  #   1. pt-BR satellite (non-empty)
  #   2. EN baseline (main DLL .resources)
  #   3. heuristic split CamelCase
  if (-not $displayKey) { return $null }
  if ($resourcesPtBr) {
    $v = $resourcesPtBr.$displayKey
    if ($v) { return $v }
  }
  if ($resourcesBaseline) {
    $v = $resourcesBaseline.$displayKey
    if ($v) { return $v }
  }
  return ConvertTo-HumanLabel $displayKey
}

function ConvertTo-HumanLabel([string]$key) {
  # Heuristic: resource key like 'WorkbookLocalPathDisplayName' → 'Workbook local path'.
  # Strip suffixes (DisplayName/Description/Tooltip), split CamelCase, lowercase tail.
  if (-not $key) { return $null }
  $clean = $key -replace '(DisplayName|Description|Tooltip|Hint|Name)$',''
  if (-not $clean) { return $null }
  # Insert space before capital letters: 'WorkbookLocalPath' → 'Workbook Local Path'
  $spaced = [System.Text.RegularExpressions.Regex]::Replace($clean, '([a-z])([A-Z])', '$1 $2')
  $spaced = [System.Text.RegularExpressions.Regex]::Replace($spaced, '([A-Z]+)([A-Z][a-z])', '$1 $2')
  # Lowercase except first letter: "Workbook Local Path" → "Workbook local path"
  if ($spaced.Length -gt 1) {
    $spaced = $spaced.Substring(0,1).ToUpper() + $spaced.Substring(1).ToLower()
  }
  return $spaced.Trim()
}

# --- per-package compact markdown ---
$byPkg = $j.Activities | Group-Object Package
foreach ($g in $byPkg) {
  $pkgName = $g.Name
  $md = New-Object System.Text.StringBuilder
  [void]$md.AppendLine("# $pkgName")
  $first = $g.Group | Select-Object -First 1
  [void]$md.AppendLine("Assembly: $($first.Assembly) v$($first.AsmVersion)")
  [void]$md.AppendLine("PackageVersion: $($first.PkgVersion)")
  [void]$md.AppendLine("ActivityCount: $($g.Count)")
  [void]$md.AppendLine("")

  foreach ($act in ($g.Group | Sort-Object FullName)) {
    [void]$md.AppendLine("## $($act.FullName)")
    if ($act.Xmlns -and $act.Xmlns.Count -gt 0) {
      [void]$md.AppendLine("- xmlns: ``$($act.Xmlns -join ', ')``")
    }
    if ($act.Category)    { [void]$md.AppendLine("- category: $($act.Category)") }
    if ($act.DisplayName) { [void]$md.AppendLine("- displayName: $($act.DisplayName)") }
    if ($act.Description) { [void]$md.AppendLine("- description: $($act.Description)") }

    $req = @($act.Arguments | Where-Object { $_.Required })
    $opt = @($act.Arguments | Where-Object { -not $_.Required })

    if ($req.Count -gt 0) {
      [void]$md.AppendLine("- required:")
      foreach ($a in $req) {
        $pkgRes = $pkgIndex.($act.Package)
        $resB = if ($pkgRes) { $pkgRes.ResourcesBaseline } else { $null }
        $resP = if ($pkgRes) { $pkgRes.ResourcesPtBr } else { $null }
        $human = Resolve-Label $a.DisplayName $resB $resP
        $labelHint = if ($human) { "  // $human" } else { "" }
        $line = "  - **$($a.Name)** : $(Format-Type $a.Type) [$($a.Direction)]"
        if ($a.OverloadGroup) { $line += "  @group=$($a.OverloadGroup)" }
        $line += $labelHint
        [void]$md.AppendLine($line)
      }
    }
    if ($opt.Count -gt 0) {
      [void]$md.AppendLine("- optional:")
      foreach ($a in $opt) {
        $def = Format-Default $a.DefaultValue
        $pkgRes = $pkgIndex.($act.Package)
        $resB = if ($pkgRes) { $pkgRes.ResourcesBaseline } else { $null }
        $resP = if ($pkgRes) { $pkgRes.ResourcesPtBr } else { $null }
        $human = Resolve-Label $a.DisplayName $resB $resP
        $labelHint = if ($human) { "  // $human" } else { "" }
        $line = "  - $($a.Name) : $(Format-Type $a.Type) [$($a.Direction)]"
        if ($def) { $line += " = $def" }
        if ($a.OverloadGroup) { $line += "  @group=$($a.OverloadGroup)" }
        $line += $labelHint
        [void]$md.AppendLine($line)
      }
    }
    [void]$md.AppendLine("")
  }

  $safe = $pkgName -replace '[^A-Za-z0-9._-]','_'
  [System.IO.File]::WriteAllText((Join-Path $OutDir "$safe.md"), $md.ToString(), [System.Text.Encoding]::UTF8)
}

# --- single compact JSON for programmatic use ---
$compact = @()
foreach ($act in $j.Activities) {
  $compact += [pscustomobject]@{
    fqn         = $act.FullName
    pkg         = $act.Package
    kind        = if ($act.Kind) { $act.Kind } else { "Activity" }
    xmlns       = if ($act.Xmlns) { @($act.Xmlns)[0] } else { $null }
    category    = $act.Category
    # F34: schema-driven parent restrictiveness fields
    contentProperty = $act.ContentProperty
    activityShape   = $act.ActivityShape
    args        = @(
      foreach ($a in $act.Arguments) {
        $pkgRes = $pkgIndex.($act.Package)
        $resB = if ($pkgRes) { $pkgRes.ResourcesBaseline } else { $null }
        $resP = if ($pkgRes) { $pkgRes.ResourcesPtBr } else { $null }
        $human = Resolve-Label $a.DisplayName $resB $resP
        $entry = [ordered]@{
          n = $a.Name
          t = Format-Type $a.Type
          d = $a.Direction
          a = [bool]$a.IsArgument
          r = [bool]$a.Required
          g = $a.OverloadGroup
          v = $a.DefaultValue
        }
        if ($human) { $entry.l = $human }
        # F34: collection item type — restritivo se item type específico
        if ($a.CollectionItemType) { $entry.cit = $a.CollectionItemType }
        $entry
      }
    )
  }
}
$compactPath = Join-Path $OutDir "activities-compact.json"
($compact | ConvertTo-Json -Depth 8 -Compress) | Set-Content $compactPath -Encoding UTF8

# --- master index ---
$indexLines = @()
$indexLines += "# UiPath Activities - Master Index"
$indexLines += "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
$indexLines += "Total: $($j.ActivityCount) activities across $($j.PackageCount) packages"
$indexLines += ""
foreach ($g in ($byPkg | Sort-Object Name)) {
  $safe = $g.Name -replace '[^A-Za-z0-9._-]','_'
  $indexLines += "- [$($g.Name)]($safe.md) ($($g.Count))"
}
[System.IO.File]::WriteAllLines((Join-Path $OutDir "INDEX.md"), $indexLines, [System.Text.Encoding]::UTF8)

# --- HTML viewer (F20) ---
$htmlTemplate = @'
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>UiPath Activities Explorer</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 0; background: #f5f5f5; color: #222; }
  header { background: #1e293b; color: white; padding: 14px 20px; display: flex; gap: 16px; align-items: center; }
  header h1 { font-size: 18px; margin: 0; }
  header .meta { font-size: 12px; opacity: 0.7; margin-left: auto; }
  .controls { background: white; padding: 12px 20px; border-bottom: 1px solid #e2e8f0; display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
  .controls input, .controls select { padding: 6px 10px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 13px; }
  .controls input { flex: 1; min-width: 200px; }
  .controls .stats { font-size: 12px; color: #64748b; }
  main { display: grid; grid-template-columns: 1fr 2fr; gap: 0; height: calc(100vh - 120px); }
  .list { background: white; overflow-y: auto; border-right: 1px solid #e2e8f0; }
  .list .item { padding: 10px 16px; border-bottom: 1px solid #f1f5f9; cursor: pointer; font-size: 13px; }
  .list .item:hover { background: #f8fafc; }
  .list .item.selected { background: #dbeafe; }
  .list .item .fqn { font-weight: 500; font-family: ui-monospace, "SF Mono", Consolas, monospace; }
  .list .item .pkg { font-size: 11px; color: #64748b; }
  .list .item .kind-Activity { color: #2563eb; }
  .list .item .kind-DataObject { color: #7c3aed; }
  .detail { padding: 24px; overflow-y: auto; background: #fafafa; }
  .detail h2 { font-size: 18px; font-family: ui-monospace, "SF Mono", Consolas, monospace; margin: 0 0 12px; }
  .detail .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-right: 6px; background: #e2e8f0; }
  .detail .badge.kind-Activity { background: #dbeafe; color: #1e40af; }
  .detail .badge.kind-DataObject { background: #ede9fe; color: #6b21a8; }
  .detail .meta-line { color: #475569; font-size: 13px; margin: 6px 0; }
  .detail .meta-line code { background: #f1f5f9; padding: 1px 4px; border-radius: 3px; }
  .detail h3 { font-size: 14px; margin: 20px 0 8px; color: #334155; text-transform: uppercase; letter-spacing: 0.05em; }
  .detail table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .detail th, .detail td { text-align: left; padding: 8px; border-bottom: 1px solid #e2e8f0; }
  .detail th { background: #f1f5f9; font-weight: 500; }
  .detail .arg-required { font-weight: 600; color: #b91c1c; }
  .detail .arg-group { background: #fef3c7; padding: 1px 6px; border-radius: 3px; font-size: 11px; }
  .detail .arg-label { color: #64748b; font-style: italic; font-size: 12px; }
  .empty { padding: 40px; text-align: center; color: #94a3b8; }
</style>
</head>
<body>
<header>
  <h1>UiPath Activities Explorer</h1>
  <span class="meta" id="meta"></span>
</header>
<div class="controls">
  <input id="q" placeholder="Search by FQN, name, package..." autofocus>
  <select id="kind"><option value="">All kinds</option><option value="Activity">Activity</option><option value="DataObject">DataObject</option></select>
  <select id="pkg"><option value="">All packages</option></select>
  <label><input type="checkbox" id="onlyReq"> Only with required args</label>
  <span class="stats" id="stats"></span>
</div>
<main>
  <div class="list" id="list"></div>
  <div class="detail" id="detail"><div class="empty">Select an activity to inspect.</div></div>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
(function(){
  var raw = document.getElementById("data").textContent;
  var data = JSON.parse(raw);
  var qEl = document.getElementById("q");
  var kindEl = document.getElementById("kind");
  var pkgEl = document.getElementById("pkg");
  var reqEl = document.getElementById("onlyReq");
  var listEl = document.getElementById("list");
  var detailEl = document.getElementById("detail");
  var statsEl = document.getElementById("stats");
  var metaEl = document.getElementById("meta");

  var pkgs = Array.from(new Set(data.map(function(d){return d.pkg;}))).sort();
  pkgs.forEach(function(p){ var o=document.createElement("option"); o.value=p; o.textContent=p; pkgEl.appendChild(o); });
  metaEl.textContent = data.length + " entries / " + pkgs.length + " packages";

  var selected = null;

  function filtered(){
    var q = qEl.value.toLowerCase();
    var k = kindEl.value;
    var p = pkgEl.value;
    var onlyReq = reqEl.checked;
    return data.filter(function(d){
      if (k && d.kind !== k) return false;
      if (p && d.pkg !== p) return false;
      if (onlyReq && !d.args.some(function(a){return a.r;})) return false;
      if (q && (d.fqn.toLowerCase().indexOf(q) < 0 && d.pkg.toLowerCase().indexOf(q) < 0)) return false;
      return true;
    });
  }

  function escapeHtml(s){ return (s==null?"":String(s)).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }

  function renderList(){
    var items = filtered();
    statsEl.textContent = items.length + " match" + (items.length===1?"":"es");
    var maxRender = 500;
    var html = items.slice(0, maxRender).map(function(d){
      var sel = (selected && d.fqn === selected.fqn) ? " selected" : "";
      return '<div class="item'+sel+'" data-fqn="'+escapeHtml(d.fqn)+'">'+
        '<div class="fqn"><span class="kind-'+d.kind+'">●</span> '+escapeHtml(d.fqn.split(".").pop())+'</div>'+
        '<div class="pkg">'+escapeHtml(d.pkg)+' · '+d.args.length+' args</div></div>';
    }).join("");
    if (items.length > maxRender) {
      html += '<div class="item" style="opacity:0.5">... '+(items.length-maxRender)+' more (refine search)</div>';
    }
    listEl.innerHTML = html;
    listEl.querySelectorAll(".item[data-fqn]").forEach(function(el){
      el.addEventListener("click", function(){
        var fqn = el.getAttribute("data-fqn");
        selected = data.find(function(d){return d.fqn===fqn;});
        renderDetail();
        renderList();
      });
    });
  }

  function renderDetail(){
    if (!selected) { detailEl.innerHTML = '<div class="empty">Select an activity to inspect.</div>'; return; }
    var d = selected;
    var rows = d.args.map(function(a){
      var flags = [];
      if (a.r) flags.push('<span class="arg-required">REQUIRED</span>');
      if (a.g) flags.push('<span class="arg-group">group='+escapeHtml(a.g)+'</span>');
      if (a.a===false) flags.push('<span class="badge">plain</span>');
      var def = a.v != null && a.v !== "" ? '<code>'+escapeHtml(a.v)+'</code>' : '';
      var label = a.l ? '<div class="arg-label">'+escapeHtml(a.l)+'</div>' : '';
      return '<tr><td><strong>'+escapeHtml(a.n)+'</strong>'+label+'</td>'+
             '<td><code>'+escapeHtml(a.t||"?")+'</code></td>'+
             '<td>'+escapeHtml(a.d||"")+'</td>'+
             '<td>'+def+'</td>'+
             '<td>'+flags.join(" ")+'</td></tr>';
    }).join("");
    detailEl.innerHTML =
      '<h2>'+escapeHtml(d.fqn)+'</h2>'+
      '<span class="badge kind-'+d.kind+'">'+d.kind+'</span>'+
      '<span class="badge">'+escapeHtml(d.pkg)+'</span>'+
      (d.category ? '<span class="badge">'+escapeHtml(d.category)+'</span>' : '')+
      (d.xmlns ? '<div class="meta-line">xmlns: <code>'+escapeHtml(d.xmlns)+'</code></div>' : '')+
      '<h3>Arguments ('+d.args.length+')</h3>'+
      (d.args.length === 0 ? '<p>(no args)</p>' :
        '<table><thead><tr><th>Name</th><th>Type</th><th>Direction</th><th>Default</th><th>Flags</th></tr></thead><tbody>'+rows+'</tbody></table>');
  }

  qEl.addEventListener("input", renderList);
  kindEl.addEventListener("change", renderList);
  pkgEl.addEventListener("change", renderList);
  reqEl.addEventListener("change", renderList);
  renderList();
})();
</script>
</body>
</html>
'@

$htmlPath = Join-Path $OutDir "index.html"
$htmlOut = $htmlTemplate -replace '__DATA__', ([Regex]::Escape("DATA_PLACEHOLDER") -replace 'DATA_PLACEHOLDER', '__DATA__')
# Replace placeholder with real JSON (escape </script> sequences)
$dataJson = ($compact | ConvertTo-Json -Depth 8 -Compress) -replace '</', '<\/'
$htmlOut = $htmlTemplate.Replace('__DATA__', $dataJson)
[System.IO.File]::WriteAllText($htmlPath, $htmlOut, [System.Text.UTF8Encoding]::new($true))
"Wrote $htmlPath ($([math]::Round((Get-Item $htmlPath).Length/1KB,1)) KB)"

$srcSize = (Get-Item $Source).Length
$compactSize = (Get-Item $compactPath).Length
"Wrote $($byPkg.Count) markdown files + activities-compact.json + INDEX.md to $OutDir"
"Source JSON: $([math]::Round($srcSize/1KB,1)) KB"
$pct = [math]::Round(100*$compactSize/$srcSize)
"Compact JSON: $([math]::Round($compactSize/1KB,1)) KB ($pct percent of source)"
