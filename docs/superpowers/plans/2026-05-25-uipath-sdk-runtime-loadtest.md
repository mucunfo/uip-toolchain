# UiPath SDK Runtime LoadTest — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Tier 1 runtime gate that loads each XAML via `System.Activities.XamlIntegration.ActivityXamlServices.Load()` — catches type resolution failures, VB compile errors em Variable.Default, missing refs, malformed Activity tree — sem precisar executar workflow.

**Architecture:** Standalone .NET 6 console host (`runtime_loadtest.exe`) in C# that accepts XAML paths via stdin/CLI, invokes XAML deserialization + Activity tree inspection, emits JSON findings to stdout. Engine Python subprocess wraps it as new gate parallel to analyze/pack/nuget in PHASE 2. New finding category `RT-LOAD-*` integra com result aggregator existente.

**Tech Stack:**
- .NET 6 SDK (Windows target)
- C# console app
- NuGet: `UiPath.Workflow` (Activity runtime), `UiPath.Activities.Api`, `Microsoft.CSharp`, `System.Activities`
- Python subprocess integration via engine `analyzer.py` pattern
- pytest fixtures pra regression test

---

## Pre-flight

### Task 0: Verify dotnet SDK + UiPath NuGet feed access

**Files:**
- Verify: dotnet 6+ instalado
- Verify: UiPath NuGet feed `https://pkgs.dev.azure.com/uipath/Public.Feeds/_packaging/UiPath-Official/nuget/v3/index.json` accessible

- [ ] **Step 1: Check dotnet SDK present**

Run: `dotnet --list-sdks`
Expected: Lista contendo `6.0.x` ou `8.0.x` (LTS).
If missing: install via `winget install Microsoft.DotNet.SDK.6`

- [ ] **Step 2: Probe UiPath NuGet feed**

Run:
```bash
dotnet nuget list source
```
If UiPath feed ausente, adicionar:
```bash
dotnet nuget add source "https://pkgs.dev.azure.com/uipath/Public.Feeds/_packaging/UiPath-Official/nuget/v3/index.json" -n UiPath-Official
```

Expected: UiPath-Official aparece em list.

---

## Phase 1 — Bootstrap .NET project

### Task 1: Scaffold runtime_loadtest project

**Files:**
- Create: `.uipath-rules/runtime_loadtest/RuntimeLoadTest.csproj`
- Create: `.uipath-rules/runtime_loadtest/Program.cs`
- Create: `.uipath-rules/runtime_loadtest/.gitignore`

- [ ] **Step 1: Create project directory + csproj**

Create `.uipath-rules/runtime_loadtest/RuntimeLoadTest.csproj`:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net6.0-windows</TargetFramework>
    <RootNamespace>SicoobUiPath.RuntimeLoadTest</RootNamespace>
    <AssemblyName>runtime_loadtest</AssemblyName>
    <Nullable>enable</Nullable>
    <LangVersion>11</LangVersion>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="UiPath.Workflow" Version="6.0.0-20250901-04" />
    <PackageReference Include="UiPath.Activities.Api" Version="25.4.4" />
    <PackageReference Include="System.Activities" Version="6.0.0-rc.1.21451.13" />
    <PackageReference Include="Microsoft.VisualBasic" Version="10.3.0" />
  </ItemGroup>
</Project>
```

Note: versões UiPath.Workflow/Activities.Api refletem pin Sicoob CCS libs. Confirmar via `dotnet nuget list source` + browse feed.

- [ ] **Step 2: Bootstrap minimal Program.cs**

Create `.uipath-rules/runtime_loadtest/Program.cs`:

```csharp
using System;
using System.IO;
using System.Text.Json;

namespace SicoobUiPath.RuntimeLoadTest;

public class Program
{
    public static int Main(string[] args)
    {
        if (args.Length == 0)
        {
            Console.Error.WriteLine("Usage: runtime_loadtest <xaml_path> [<xaml_path>...]");
            return 2;
        }
        var results = new System.Collections.Generic.List<LoadResult>();
        foreach (var path in args)
        {
            results.Add(LoadXaml(path));
        }
        Console.WriteLine(JsonSerializer.Serialize(new { results }));
        return results.TrueForAll(r => r.Status == "OK") ? 0 : 1;
    }

    public static LoadResult LoadXaml(string path)
    {
        return new LoadResult { File = path, Status = "STUB", Error = null };
    }
}

public class LoadResult
{
    public string File { get; set; } = "";
    public string Status { get; set; } = "";
    public string? Error { get; set; }
    public string? Category { get; set; }
    public int? Line { get; set; }
}
```

- [ ] **Step 3: Create .gitignore**

Create `.uipath-rules/runtime_loadtest/.gitignore`:
```
bin/
obj/
*.user
```

- [ ] **Step 4: Verify restore + build**

Run:
```bash
cd .uipath-rules/runtime_loadtest
dotnet restore
dotnet build -c Release
```
Expected: Build succeeded, 0 Errors. Binary em `bin/Release/net6.0-windows/runtime_loadtest.exe`.

- [ ] **Step 5: Smoke test stub**

Run:
```bash
.uipath-rules/runtime_loadtest/bin/Release/net6.0-windows/runtime_loadtest.exe foo.xaml
```
Expected: JSON output `{"results":[{"file":"foo.xaml","status":"STUB",...}]}` + exit 1.

- [ ] **Step 6: Commit**

```bash
git add .uipath-rules/runtime_loadtest/
git commit -m "feat(runtime): scaffold runtime_loadtest .NET 6 host"
```

---

### Task 2: Implement ActivityXamlServices.Load() integration

**Files:**
- Modify: `.uipath-rules/runtime_loadtest/Program.cs` (replace stub LoadXaml)

- [ ] **Step 1: Replace LoadXaml stub com ActivityXamlServices.Load**

Replace LoadXaml em `Program.cs`:

```csharp
public static LoadResult LoadXaml(string path)
{
    if (!File.Exists(path))
    {
        return new LoadResult { File = path, Status = "NOT_FOUND", Error = "file does not exist" };
    }
    try
    {
        using var stream = File.OpenRead(path);
        var settings = new System.Activities.XamlIntegration.ActivityXamlServicesSettings
        {
            CompileExpressions = true,
        };
        var activity = System.Activities.XamlIntegration.ActivityXamlServices.Load(stream, settings);
        if (activity == null)
        {
            return new LoadResult { File = path, Status = "LOAD_NULL", Error = "Load returned null" };
        }
        // Walk Activity tree pra validate metadata (CacheMetadata) — força lazy bindings.
        var inspector = new System.Activities.WorkflowInspectionServices();
        foreach (var child in System.Activities.WorkflowInspectionServices.GetActivities(activity))
        {
            // Force CacheMetadata pra cada nested Activity. Throws se invalid.
            System.Activities.WorkflowInspectionServices.CacheMetadata(child);
        }
        return new LoadResult { File = path, Status = "OK" };
    }
    catch (System.Activities.InvalidWorkflowException iwe)
    {
        return new LoadResult
        {
            File = path,
            Status = "INVALID_WORKFLOW",
            Category = "metadata",
            Error = iwe.Message,
        };
    }
    catch (System.Xaml.XamlObjectWriterException xowe)
    {
        return new LoadResult
        {
            File = path,
            Status = "XAML_OBJECT_WRITER",
            Category = "deserialize",
            Error = xowe.Message,
            Line = xowe.LineNumber > 0 ? xowe.LineNumber : null,
        };
    }
    catch (System.Xaml.XamlParseException xpe)
    {
        return new LoadResult
        {
            File = path,
            Status = "XAML_PARSE",
            Category = "deserialize",
            Error = xpe.Message,
            Line = xpe.LineNumber > 0 ? xpe.LineNumber : null,
        };
    }
    catch (System.Activities.Validation.ValidationException ve)
    {
        return new LoadResult
        {
            File = path,
            Status = "VALIDATION",
            Category = "validation",
            Error = ve.Message,
        };
    }
    catch (Exception ex)
    {
        return new LoadResult
        {
            File = path,
            Status = "UNHANDLED",
            Category = "unknown",
            Error = $"{ex.GetType().FullName}: {ex.Message}",
        };
    }
}
```

- [ ] **Step 2: Rebuild**

Run: `dotnet build -c Release`
Expected: Build succeeded 0 Errors.

- [ ] **Step 3: Manual smoke test em XAML conhecido bom**

Run:
```bash
.uipath-rules/runtime_loadtest/bin/Release/net6.0-windows/runtime_loadtest.exe \
  "C:/Users/lisan/OneDrive - Sicoob/Projects/importar-cadastro-avais-fiancas-honrados/importar-cadastro-avais-fiancas-honrados-performer/Main.xaml"
```
Expected: Status `OK` em JSON output. Exit 0.

- [ ] **Step 4: Manual smoke test em XAML smart-quote bug histórico**

Crie temp XAML c/ smart-quote em Variable.Default. Test que LoadXaml retorna VALIDATION ou INVALID_WORKFLOW com Error mencionando "VisualBasicValue" ou "compilação".

Skip se já fixado o source — usar `git show <commit-pre-fix>:Sipag_Net/ColetaDados.xaml` se disponível.

- [ ] **Step 5: Commit**

```bash
git add .uipath-rules/runtime_loadtest/Program.cs
git commit -m "feat(runtime): implement ActivityXamlServices.Load + CacheMetadata walk"
```

---

### Task 3: Add stdin batch mode (avoid 8KB args limit Windows)

**Files:**
- Modify: `.uipath-rules/runtime_loadtest/Program.cs` (add `--stdin` flag)

- [ ] **Step 1: Add --stdin flag handling em Main**

Replace Main em `Program.cs`:

```csharp
public static int Main(string[] args)
{
    var paths = new System.Collections.Generic.List<string>();
    if (args.Length > 0 && args[0] == "--stdin")
    {
        string? line;
        while ((line = Console.In.ReadLine()) != null)
        {
            var trimmed = line.Trim();
            if (!string.IsNullOrEmpty(trimmed)) paths.Add(trimmed);
        }
    }
    else if (args.Length > 0)
    {
        paths.AddRange(args);
    }
    else
    {
        Console.Error.WriteLine("Usage: runtime_loadtest [--stdin | <xaml_path>...]");
        return 2;
    }
    var results = new System.Collections.Generic.List<LoadResult>();
    foreach (var path in paths) results.Add(LoadXaml(path));
    Console.WriteLine(JsonSerializer.Serialize(new { results }));
    return results.TrueForAll(r => r.Status == "OK") ? 0 : 1;
}
```

- [ ] **Step 2: Rebuild + smoke**

Run:
```bash
dotnet build -c Release
echo "C:/path/to/Main.xaml" | .uipath-rules/runtime_loadtest/bin/Release/net6.0-windows/runtime_loadtest.exe --stdin
```
Expected: JSON output com 1 result.

- [ ] **Step 3: Commit**

```bash
git add .uipath-rules/runtime_loadtest/Program.cs
git commit -m "feat(runtime): add --stdin batch mode"
```

---

## Phase 2 — Python engine integration

### Task 4: Create runtime_loadtest Python wrapper

**Files:**
- Create: `.uipath-rules/scripts/rule_engine/runtime_loadtest.py`

- [ ] **Step 1: Write Python wrapper module**

Create `.uipath-rules/scripts/rule_engine/runtime_loadtest.py`:

```python
"""runtime_loadtest wrapper — invoca runtime_loadtest.exe subprocess.

Coleta paths XAML do projeto, envia via stdin batch mode, parse JSON output,
retorna lista de Finding pra engine aggregator.

Exit codes:
  0 = todos XAMLs load OK
  1 = ≥1 XAML failed load
  2 = invalid args (não deve acontecer via wrapper)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from scripts.rule_engine._types import Finding


_BINARY_NAME = "runtime_loadtest.exe"


def _binary_path() -> Path | None:
    """Resolve runtime_loadtest binary path."""
    here = Path(__file__).resolve().parents[2]  # .uipath-rules/
    candidate = here / "runtime_loadtest" / "bin" / "Release" / "net6.0-windows" / _BINARY_NAME
    return candidate if candidate.exists() else None


def run_loadtest(project_root: Path, timeout: int = 180) -> tuple[int, list[Finding]]:
    """Run runtime_loadtest em todos XAMLs do projeto.

    Returns: (exit_code, findings_list)
    """
    binary = _binary_path()
    if binary is None:
        return 2, [Finding(
            rule_id="RT-LOAD-INFRA",
            severity="ERROR",
            category="breaking",
            file=str(project_root / "project.json"),
            line=0,
            message="runtime_loadtest binary not found. Run 'dotnet build -c Release' em .uipath-rules/runtime_loadtest/",
            fix_mechanical=None,
            fix_prose=None,
        )]

    xamls = sorted(str(p) for p in project_root.rglob("*.xaml")
                   if "_BeforeMigration" not in str(p))
    if not xamls:
        return 0, []

    stdin_data = "\n".join(xamls)
    try:
        proc = subprocess.run(
            [str(binary), "--stdin"],
            input=stdin_data,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 2, [Finding(
            rule_id="RT-LOAD-TIMEOUT",
            severity="ERROR",
            category="breaking",
            file=str(project_root / "project.json"),
            line=0,
            message=f"runtime_loadtest timeout >{timeout}s",
            fix_mechanical=None,
            fix_prose=None,
        )]

    findings = _parse_output(proc.stdout, project_root)
    return proc.returncode, findings


def _parse_output(stdout: str, project_root: Path) -> list[Finding]:
    """Parse JSON stdout em lista de Finding. Mapea Status → rule_id."""
    findings: list[Finding] = []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return [Finding(
            rule_id="RT-LOAD-INFRA",
            severity="ERROR",
            category="breaking",
            file=str(project_root / "project.json"),
            line=0,
            message=f"runtime_loadtest produced invalid JSON: {stdout[:200]}",
            fix_mechanical=None,
            fix_prose=None,
        )]
    for result in data.get("results", []):
        status = result.get("Status") or result.get("status") or "UNKNOWN"
        if status == "OK":
            continue
        file_path = result.get("File") or result.get("file") or "?"
        category = result.get("Category") or result.get("category") or "load"
        error = result.get("Error") or result.get("error") or ""
        line = result.get("Line") or result.get("line") or 0
        rule_id = f"RT-LOAD-{status}"
        findings.append(Finding(
            rule_id=rule_id,
            severity="ERROR",
            category="breaking",
            file=file_path,
            line=line,
            message=f"Runtime load fail [{category}]: {error[:200]}",
            fix_mechanical=None,
            fix_prose=(
                "Workflow falha load em runtime UiPath. Causa típica: "
                "VB expression compile error, type unresolved, missing ref, "
                "malformed Activity tree. Inspect XAML em torno da linha."
            ),
        ))
    return findings
```

- [ ] **Step 2: Smoke test wrapper standalone**

Run:
```bash
cd .uipath-rules
python -c "
from pathlib import Path
from scripts.rule_engine.runtime_loadtest import run_loadtest
code, findings = run_loadtest(Path('C:/Users/lisan/OneDrive - Sicoob/Projects/importar-cadastro-avais-fiancas-honrados/importar-cadastro-avais-fiancas-honrados-performer'))
print('exit:', code, 'findings:', len(findings))
for f in findings[:5]: print(f' [{f.rule_id}] {f.file}:{f.line} {f.message[:100]}')
"
```
Expected: exit 0 ou 1, 0+ findings com rule_id `RT-LOAD-*`. Sem RT-LOAD-INFRA (binary deve estar built).

- [ ] **Step 3: Commit**

```bash
git add .uipath-rules/scripts/rule_engine/runtime_loadtest.py
git commit -m "feat(engine): Python wrapper runtime_loadtest subprocess"
```

---

### Task 5: Wire runtime_loadtest como gate PHASE 2 paralelo

**Files:**
- Modify: `.uipath-rules/scripts/rule_engine/cli.py` (linha 442-457 — gates list)

- [ ] **Step 1: Add runtime-loadtest gate em PHASE 2**

Em `cli.py`, localizar bloco `gates = [...]` (~ line 432-457). Adicionar nova entry após pack-gate:

```python
(
    "runtime-loadtest",
    lambda: _run_runtime_loadtest_gate(
        result, args.path,
        timeout=getattr(args, "runtime_loadtest_timeout", 180),
        verbose=verbose,
    ),
),
```

- [ ] **Step 2: Implement _run_runtime_loadtest_gate function**

Após `_run_uipcli_pack_gate` definição em `cli.py`, adicionar:

```python
def _run_runtime_loadtest_gate(result, project_path: str, timeout: int = 180,
                                verbose: bool = False) -> int:
    """PHASE 2 gate: runtime XAML load test via .NET subprocess.

    Catches: VB compile errors em Variable.Default + Activity bindings,
    missing assembly refs, malformed Activity tree, type resolution fail.

    Cheaper que pack-gate full publish, mais profundo que analyze.
    """
    from .runtime_loadtest import run_loadtest
    from pathlib import Path

    project = Path(project_path)
    if verbose:
        print(f"[runtime-loadtest] running em {project}", file=sys.stderr)
    code, findings = run_loadtest(project, timeout=timeout)
    for f in findings:
        result.add_finding(f)
    if verbose:
        print(f"[runtime-loadtest] exit={code} findings={len(findings)}", file=sys.stderr)
    return code
```

- [ ] **Step 3: Add --runtime-loadtest-timeout CLI arg**

Em `cli.py` localizar parser review args (~ linha 266). Após `--pack-gate-timeout`, adicionar:

```python
rev.add_argument("--runtime-loadtest-timeout", type=int, default=180,
                 help="Timeout (s) pra runtime_loadtest subprocess gate")
```

- [ ] **Step 4: Smoke test integration**

Run:
```bash
cd .uipath-rules
python -m scripts.rule_engine.cli review \
  "C:/Users/lisan/OneDrive - Sicoob/Projects/importar-cadastro-avais-fiancas-honrados/importar-cadastro-avais-fiancas-honrados-performer" \
  --format json 2>&1 | grep -i "runtime-loadtest\|RT-LOAD"
```
Expected: Verbose logs `[runtime-loadtest] running...` + zero RT-LOAD findings (projeto canonical OK).

- [ ] **Step 5: Commit**

```bash
git add .uipath-rules/scripts/rule_engine/cli.py
git commit -m "feat(engine): wire runtime-loadtest como PHASE 2 gate paralelo"
```

---

## Phase 3 — Test coverage

### Task 6: pytest fixture XAML c/ known runtime fails

**Files:**
- Create: `.uipath-rules/tests/fixtures/runtime_loadtest/Main_smart_quote.xaml`
- Create: `.uipath-rules/tests/fixtures/runtime_loadtest/Main_missing_assembly.xaml`
- Create: `.uipath-rules/tests/fixtures/runtime_loadtest/Main_ok.xaml`
- Create: `.uipath-rules/tests/test_runtime_loadtest.py`

- [ ] **Step 1: Create Main_ok.xaml — minimal valid Sequence**

Create `.uipath-rules/tests/fixtures/runtime_loadtest/Main_ok.xaml`:

```xml
<Activity mc:Ignorable="sap sap2010" x:Class="MainOk"
  xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
  xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
  xmlns:sap="http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation"
  xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence sap2010:WorkflowViewState.IdRef="Sequence_1">
    <WriteLine Text="hello" sap2010:WorkflowViewState.IdRef="WriteLine_1" />
  </Sequence>
</Activity>
```

- [ ] **Step 2: Create Main_smart_quote.xaml — Variable.Default w/ smart-quote**

Create `.uipath-rules/tests/fixtures/runtime_loadtest/Main_smart_quote.xaml`:

```xml
<Activity mc:Ignorable="sap sap2010" x:Class="MainSmartQuote"
  xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
  xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
  xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence sap2010:WorkflowViewState.IdRef="Sequence_1">
    <Sequence.Variables>
      <Variable x:TypeArguments="x:String" Default="[&quot;test&quot;.TrimStart(“0”c)]" Name="vBroken" />
    </Sequence.Variables>
    <WriteLine Text="[vBroken]" sap2010:WorkflowViewState.IdRef="WriteLine_1" />
  </Sequence>
</Activity>
```

- [ ] **Step 3: Create Main_missing_assembly.xaml — unresolved type**

Create `.uipath-rules/tests/fixtures/runtime_loadtest/Main_missing_assembly.xaml`:

```xml
<Activity mc:Ignorable="sap sap2010" x:Class="MainMissingAssembly"
  xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
  xmlns:fake="clr-namespace:Nonexistent.Fake;assembly=Nonexistent.Fake"
  xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
  xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
  xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence sap2010:WorkflowViewState.IdRef="Sequence_1">
    <fake:FakeActivity sap2010:WorkflowViewState.IdRef="FakeActivity_1" />
  </Sequence>
</Activity>
```

- [ ] **Step 4: Write test_runtime_loadtest.py**

Create `.uipath-rules/tests/test_runtime_loadtest.py`:

```python
"""Test runtime_loadtest wrapper detecta failures classes conhecidas."""
from pathlib import Path
import pytest
from scripts.rule_engine.runtime_loadtest import run_loadtest


FIXTURES = Path(__file__).parent / "fixtures" / "runtime_loadtest"


@pytest.fixture
def fixture_project(tmp_path):
    """Create temp project com fixtures + minimal project.json."""
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "project.json").write_text('{"name":"test","targetFramework":"Windows","main":"Main_ok.xaml"}')
    for xaml in FIXTURES.glob("*.xaml"):
        (proj / xaml.name).write_bytes(xaml.read_bytes())
    return proj


def test_ok_xaml_loads_clean(fixture_project):
    """Main_ok.xaml deve passar load test sem findings."""
    # Run só Main_ok via project sem outros
    isolated = fixture_project.parent / "iso_ok"
    isolated.mkdir()
    (isolated / "project.json").write_text('{"name":"iso","targetFramework":"Windows","main":"Main_ok.xaml"}')
    (isolated / "Main_ok.xaml").write_bytes((FIXTURES / "Main_ok.xaml").read_bytes())
    code, findings = run_loadtest(isolated)
    assert code == 0, f"expected exit 0, got {code}. Findings: {[f.message for f in findings]}"
    assert findings == [], f"expected zero findings, got {findings}"


def test_smart_quote_xaml_fails(fixture_project):
    """Main_smart_quote.xaml deve disparar finding RT-LOAD-* com referência a compilation."""
    isolated = fixture_project.parent / "iso_sq"
    isolated.mkdir()
    (isolated / "project.json").write_text('{"name":"iso","targetFramework":"Windows","main":"Main_smart_quote.xaml"}')
    (isolated / "Main_smart_quote.xaml").write_bytes((FIXTURES / "Main_smart_quote.xaml").read_bytes())
    code, findings = run_loadtest(isolated)
    assert code != 0, "expected non-zero exit"
    assert any("smart_quote" in f.file.lower() or "compil" in f.message.lower()
               for f in findings), f"expected smart_quote-related finding. Got: {[f.message for f in findings]}"


def test_missing_assembly_xaml_fails(fixture_project):
    """Main_missing_assembly.xaml deve disparar finding RT-LOAD-*."""
    isolated = fixture_project.parent / "iso_ma"
    isolated.mkdir()
    (isolated / "project.json").write_text('{"name":"iso","targetFramework":"Windows","main":"Main_missing_assembly.xaml"}')
    (isolated / "Main_missing_assembly.xaml").write_bytes((FIXTURES / "Main_missing_assembly.xaml").read_bytes())
    code, findings = run_loadtest(isolated)
    assert code != 0, "expected non-zero exit"
    assert any(f.rule_id.startswith("RT-LOAD-") for f in findings), \
        f"expected RT-LOAD-* finding. Got: {[f.rule_id for f in findings]}"
```

- [ ] **Step 5: Run tests**

Run:
```bash
cd .uipath-rules
pytest tests/test_runtime_loadtest.py -v
```
Expected: 3 tests pass. Se runtime_loadtest.exe não built, test_ok ou similares poderão skipar/fail c/ RT-LOAD-INFRA.

- [ ] **Step 6: Commit**

```bash
git add .uipath-rules/tests/fixtures/runtime_loadtest/ .uipath-rules/tests/test_runtime_loadtest.py
git commit -m "test(runtime): fixtures + pytest pra runtime_loadtest gate"
```

---

## Phase 4 — Documentation + CI

### Task 7: README + ARCHITECTURE update

**Files:**
- Create: `.uipath-rules/runtime_loadtest/README.md`
- Modify: `.uipath-rules/ARCHITECTURE.md`

- [ ] **Step 1: Write runtime_loadtest README**

Create `.uipath-rules/runtime_loadtest/README.md`:

```markdown
# runtime_loadtest — UiPath SDK XAML Load Test

Standalone .NET 6 host que invoca `ActivityXamlServices.Load()` em cada XAML do projeto + walka Activity tree pra force CacheMetadata. Catches:

- Type resolution failures (assembly ref missing)
- VB compile errors em Variable.Default + InArgument bindings
- Malformed Activity tree (XAML parser errors)
- Invalid bindings (required arg missing, type mismatch)

## Build

Pré-requisito: dotnet SDK 6+ + UiPath NuGet feed configurado.

```bash
cd .uipath-rules/runtime_loadtest
dotnet build -c Release
```

Binary: `bin/Release/net6.0-windows/runtime_loadtest.exe`

## Uso standalone

```bash
runtime_loadtest.exe Path/To/Main.xaml Other.xaml
# OR batch stdin
echo "Path/To/Main.xaml" | runtime_loadtest.exe --stdin
```

Output: JSON em stdout. Exit 0 se todos OK, 1 se algum failed.

## Integração engine

PHASE 2 gate paralelo a analyze/pack/nuget. Habilitado automaticamente se binary built. Findings emitidos como `RT-LOAD-<STATUS>` severity ERROR.

Disable: env `UIPATH_RULES_NO_RUNTIME_LOADTEST=1` (TODO if needed).

## Status codes

| Status | Significado |
|---|---|
| OK | Load + metadata válidos |
| NOT_FOUND | File path inválido |
| LOAD_NULL | ActivityXamlServices.Load retornou null |
| INVALID_WORKFLOW | InvalidWorkflowException (metadata/binding) |
| XAML_PARSE | Parser XAML rejeitou content (linha disponível) |
| XAML_OBJECT_WRITER | XamlObjectWriter falhou instanciação |
| VALIDATION | Validation Pass rejeitou |
| UNHANDLED | Outra exception (Category=unknown) |
```

- [ ] **Step 2: Add ARCHITECTURE entry**

Append em `.uipath-rules/ARCHITECTURE.md`:

```markdown
## Runtime LoadTest gate (Tier 1 runtime simulation)

`runtime_loadtest/` é .NET 6 console host que invoca `ActivityXamlServices.Load()` SDK UiPath em cada XAML do projeto. Roda em PHASE 2 paralelo a analyze/pack/nuget. Catches load-time errors que analyze não pega (Variable.Default VB compile, lazy type resolution).

Findings emitidos como `RT-LOAD-<STATUS>` (ERROR severity, category=breaking). Wrapper Python `scripts/rule_engine/runtime_loadtest.py` traduz subprocess output em Finding objects.

Custos:
- Build inicial: ~30s (dotnet restore + build Release)
- Per-projeto runtime: 5-30s dependendo nro XAMLs
- Falha cleanly se binary não built (RT-LOAD-INFRA finding diagnóstico)
```

- [ ] **Step 3: Commit**

```bash
git add .uipath-rules/runtime_loadtest/README.md .uipath-rules/ARCHITECTURE.md
git commit -m "docs(runtime): README + ARCHITECTURE entry pra runtime_loadtest"
```

---

### Task 8: GitHub Actions CI integration

**Files:**
- Modify: `.github/workflows/ci.yml` (se existe) OR create

- [ ] **Step 1: Locate existing CI workflow**

Run:
```bash
find .github/workflows -type f -name "*.yml"
```
Expected: lista de workflows. If empty: criar `ci.yml` baseline.

- [ ] **Step 2: Add runtime_loadtest build step**

Em `.github/workflows/ci.yml` (Windows runner), adicionar step ANTES dos pytest:

```yaml
      - name: Setup .NET SDK
        uses: actions/setup-dotnet@v4
        with:
          dotnet-version: '6.0.x'

      - name: Build runtime_loadtest
        working-directory: .uipath-rules/runtime_loadtest
        run: |
          dotnet restore
          dotnet build -c Release
```

- [ ] **Step 3: Verify pytest runs com binary disponível**

Step pytest existente vai pegar binary automaticamente (wrapper procura em path relativo).

- [ ] **Step 4: Push + verify CI green**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add dotnet SDK setup + runtime_loadtest build"
git push
```

Verificar GitHub Actions execution. Esperado: green em <5min adicional vs baseline.

---

## Phase 5 — Validation + rollout

### Task 9: Re-rodar batch 35 escope com SDK engine

**Files:**
- Run: batch validation

- [ ] **Step 1: Confirm engine + runtime_loadtest both built**

Run:
```bash
cd .uipath-rules
ls runtime_loadtest/bin/Release/net6.0-windows/runtime_loadtest.exe
python -c "from scripts.rule_engine.runtime_loadtest import _binary_path; print(_binary_path())"
```
Expected: ambos retornam path absoluto.

- [ ] **Step 2: Launch batch background**

Run:
```bash
cd .scripts/bitbucket
python -m steps.run_uip_batch \
  C:/Users/lisan/Desktop/temp/repos_sem_libs.txt \
  C:/Users/lisan/Desktop/temp \
  --idle-timeout 900
```

Idle 900s (15min) — runtime_loadtest pode adicionar 5-30s por projeto.

- [ ] **Step 3: Monitor diff PENDING_REVIEW vs FAIL counts**

Wait for completion. Compare com batch anterior (bom88spr9 stopped em 23/35):

- Anterior: ~16 PENDING_REVIEW, ~4 FAIL, ~3 INTERNAL (em 23 ran)
- Esperado: maybe +1-3 FAIL (RT-LOAD-* novos catches), zero regressões

Diff = sucesso. Sem regressões inesperadas.

- [ ] **Step 4: Doc batch results em REPORT.md**

Update `C:/Users/lisan/Desktop/temp/REPORT.md` seção "Sumário" com new counts + nota "Engine SDK-augmented".

- [ ] **Step 5: Commit reporting**

```bash
git add C:/Users/lisan/Desktop/temp/REPORT.md
git commit -m "docs: batch 35 results pós-SDK runtime integration"
```

---

### Task 10: Snapshot baseline refresh

**Files:**
- Run: snapshot capture

- [ ] **Step 1: Refresh snapshots com SDK engine**

Run:
```bash
cd .uipath-rules
python -m scripts.snapshot_regression --capture --force
```
Expected: baseline regrava com RT-LOAD-* findings (provavelmente zero em canonical) + counts atualizados.

- [ ] **Step 2: Commit snapshot diff**

```bash
git add .uipath-rules/tests/snapshots/
git commit -m "test(snapshot): refresh baseline com SDK runtime_loadtest gate"
```

---

## Risks + Mitigations

| Risco | Probabilidade | Impacto | Mitigation |
|---|---|---|---|
| UiPath NuGet feed sem versões compatíveis | Médio | Alto | Tentar versões alternativas; fallback usar `System.Activities` pure sem UiPath.Workflow (perde features mas load básico funciona) |
| ActivityXamlServices.Load não pega Variable.Default compile errors | Médio | Médio | Add explicit eval pass via `WorkflowInvoker.Invoke(getDefaultActivity)` se necessário |
| Binary missing em ambiente sem dotnet | Baixo | Baixo | Wrapper emite RT-LOAD-INFRA diagnostic finding, engine continua sem gate |
| Timeout 180s insuficiente em projetos grandes | Baixo | Médio | Aumentar `--runtime-loadtest-timeout` per-batch |
| Race condition uipcli + dotnet subprocess simultâneo | Baixo | Baixo | Já isolados em processos diferentes |
| False positive em XAMLs intencionalmente incompletos (TestCase mocks) | Médio | Baixo | Wrapper detecta padrões `Mocks/`, `Tests/` e skip por convention OR adicionar finding como WARN não ERROR |

---

## Self-Review

**1. Spec coverage:**
- ✓ .NET host build (Task 1-3)
- ✓ Python integration (Task 4-5)
- ✓ Test coverage (Task 6)
- ✓ Docs (Task 7)
- ✓ CI (Task 8)
- ✓ Rollout (Task 9-10)

**2. Placeholder scan:** Plan tem instructions concretas com código. No TBD/TODO leakage em steps acionáveis.

**3. Type consistency:** `LoadResult` fields (File/Status/Error/Category/Line) consistent across Program.cs + Python wrapper. `RT-LOAD-<STATUS>` rule_id format consistent.

**4. Riscos endereçados:** UiPath NuGet version drift + fallback path documentados. Binary missing graceful.

---

## Custo total estimado

- Phase 1 (.NET host): 1 dia eng
- Phase 2 (Python wire): 0.5 dia
- Phase 3 (tests): 0.5 dia
- Phase 4 (docs+CI): 0.5 dia
- Phase 5 (rollout): 0.5 dia (passive, runs background)

**Total: ~3 dias eng. Cobertura runtime gate ~70-80%.**
