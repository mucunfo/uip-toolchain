# Studio API Notes — Fase 1 Spike Findings (2026-05-22)

Spike goal: identificar API canonical para invocar Studio "Import References"
auto-fix via Python (pythonnet) e validar viabilidade de Fase 2 production
integration.

Studio versions testadas:
- **26.0.193-cloud.23060** (net8.0) — dev convenience (pré-instalado local)
  Path: `C:\Users\lisan\AppData\Local\Programs\UiPathPlatform\Studio\26.0.193-cloud.23060`
- **23.10.13** (net6.0) — **Sicoob deploy target (D-1 pin)**
  Path: `C:\Users\lisan\Documents\UiPathStudio23x\UiPath\Studio`

Spike scripts aceitam `UIPATH_STUDIO_DIR` env var para apontar para uma
versão específica. Default = 26.0.193.

```powershell
# Probe Studio 23.10 (Sicoob target):
$env:UIPATH_STUDIO_DIR = "C:\Users\lisan\Documents\UiPathStudio23x\UiPath\Studio"
python spike/studio_import_refs_spike.py
```

## Stack tecnico validado

| Component | Status | Notes |
|-----------|--------|-------|
| pythonnet 3.0.5 + clr_loader 0.2.10 | ✓ instalado | `pip install pythonnet` |
| Studio coreclr boot via `pythonnet.load("coreclr", runtime_config=...)` | ✓ funciona | net8.0 runtime detectado |
| Reflection enumerate types | ✓ funciona | `ReflectionTypeLoadException` parcial em alguns DLLs (Plugin.Workflow.dll) — usar `e.Types` workaround |
| Construct types com null deps | ✓ parcialmente | XamlMigrationProjectEndpoint(null, null) OK |
| Invoke ApplyMigration(filename) com null deps | ✗ NRE | `_xamlFileMigration.ApplyMigration(...)` NPE — null dep called |
| Resolve via empty Autofac ServiceLocatorAutofac | ✗ ComponentNotRegistered | Empty container, sem registrations |

## API map descoberta

### Camada 1 — Shell (IPC proxy, processo UI)
```
IXamlMigrationShellService (interface)
  Task ApplyMigration(String filename)

XamlMigrationShellEndpoint : OneWayShellEndpointBase<IXamlMigrationServiceProjectEndpoint>, IXamlMigrationShellService
  .ctor(IProjectProcessController appDomainController)
  Task ApplyMigration(String fileName)  // forwards via IPC to Project endpoint
  Task Connect(IXamlMigrationServiceProjectEndpoint innerService)
  Task Disconnect()
```

### Camada 2 — Project endpoint (executa em sandbox Project process)
```
IXamlMigrationService (interface)
  Void ApplyMigration(ActivityBuilder activityBuilder)
  Void ApplyMigration(Activity activity)
  Void LoadMigrations(IAssemblyContainer assemblyContainer)
  IEnumerable<ImportReference> ImportReferences { get; }

XamlMigrationProjectEndpoint : OneWayProjectEndpointBase, IXamlMigrationService, IXamlMigrationServiceProjectEndpoint
  .ctor(IXamlFileMigration xamlFileMigration, ITextExpressionClassMethods textExpression)
  Task<bool> ApplyMigration(String fileName)  // async, reads/writes file
  // + same methods as interface
```

### Camada 3 — File-level worker
```
IXamlFileMigration (interface, Plugin.Workflow.dll)
XamlFileMigration : IXamlFileMigration
  .ctor(IWorkflowContentExtractor contentExtractor, IFileSystem fileSystem)
  Void ApplyMigration(String fileName, XamlMigrationArgs migrationArgs)
```

### Args payload
```
XamlMigrationArgs (POCO)
  List<ImportReference> ImportReferenceToAdd { get; set; }
  List<AssemblyReference> AssemblyReferencesToRemove { get; set; }
  List<String> NamespacesToRemove { get; set; }
```

**Esta é a estrutura de delta** que ENV-4 + W-31 + W-32 implementam manualmente:
- `ImportReferenceToAdd` = W-11y baseline (ensure refs)
- `AssemblyReferencesToRemove` = W-31 + W-32 (strip legacy facades)
- `NamespacesToRemove` = ENV-3 (drop unused namespaces) + ENV-4 (drop xmlns:mva)

## Arquitetura Studio (descoberta)

Studio = **Shell process** (UI WPF) + **Project process** (sandbox AppDomain).
Comunicação via IPC named pipes (`IIpcProxy`).

```
[Shell Process]                              [Project Process]
 IXamlMigrationShellService          IPC      XamlMigrationProjectEndpoint
   .ApplyMigration(file)  ─────────────────►   .ApplyMigration(file)
                                                  │
                                                  ▼
                                              XamlFileMigration
                                              ApplyMigration(file, args)
```

Auto-detection de delta: `IXamlMigrationService.ImportReferences` (property)
+ `LoadMigrations(IAssemblyContainer)`. Migrations carregadas de assemblies
do project (UiPath.* + custom packages). É aí que reside o knowledge "Studio
sabe o que precisa migrar".

## DI graph para production integration

Para invocar `XamlMigrationProjectEndpoint.ApplyMigration(filename)` sem
NPE, precisa instanciar com deps reais:

```
XamlMigrationProjectEndpoint
├── IXamlFileMigration → XamlFileMigration
│   ├── IWorkflowContentExtractor → ?? (recursivo, precisa probar)
│   └── IFileSystem → System.IO.Abstractions.FileSystem
└── ITextExpressionClassMethods → ?? (UiPath.Studio.Analyzer.Wrappers.* OR
                                       UiPath.Workflow.Operations.Handling.*)

Plus LoadMigrations precisa:
IAssemblyContainer → UiPath.LanguageModel.Workflow.Interfaces.IAssemblyContainer
                  OR UiPath.Studio.Shared.Assemblies.IAssemblyContainer
                  (carregar migrations dos assemblies do projeto)
```

Cada level requer mais probes. Studio DI = Autofac (`ServiceLocatorAutofac`).
Production path = boot Studio container completo via `CliApplication.Start([])`,
hook `LoadingCompleted` event, resolve `IXamlMigrationShellService` via
`IServiceLocator`.

## Custos estimados Fase 2

| Etapa | Estimate |
|-------|----------|
| Bootstrap CliApplication + hook LoadingCompleted | 2-3 dias |
| Resolve IServiceLocator + IXamlMigrationShellService | 1-2 dias |
| IPC Shell→Project setup (Connect endpoint) | 2-4 dias |
| Tests + error handling | 2-3 dias |
| CI integration (Studio install em runner) | 2-5 dias |
| **Total** | **~2 semanas** |

Manutenção contínua: Studio API interna sem garantia de estabilidade. Cada
nova versão Studio (mensal cloud, semestral on-prem) pode quebrar API.

## Alternativas mais leves consideradas

### Alt A — Hybrid: engine delta + Studio write
- Engine detecta delta (ENV-4/W-31/W-32 já fazem isso)
- Passar XamlMigrationArgs pre-populado pra XamlFileMigration.ApplyMigration
- Skip auto-detection (LoadMigrations)
- **Beneficio**: Studio escreve canonical XAML (writer perfeito)
- **Custo**: ainda precisa IWorkflowContentExtractor + IFileSystem deps. Médio.

### Alt B — uipcli `manage` apenas
- `uipcli manage --add-ref pkg,version` adiciona package em project.json
- NÃO rewrite XAML metadata. Insuficiente pra Import References auto-fix.
- **Rejeitada**: scope mismatch.

### Alt C — Out-of-band Studio UI validation
- Engine roda como hoje
- Usuário roda Studio UI manualmente quando precisar verificar
- **Beneficio**: zero engineering cost. Status quo.
- **Custo**: manual, não-automatizável.

## API drift detectado entre versões

Re-probe Studio 23.10 (Sicoob D-1 pin) vs 26.0 (cloud) revelou:

| Type | Studio 23.10 ctor | Studio 26.0 ctor | Status |
|------|-------------------|------------------|--------|
| `XamlMigrationProjectEndpoint` | `(IXamlFileMigration)` | `(IXamlFileMigration, ITextExpressionClassMethods)` | **drift — 1 param vs 2** |
| `XamlMigrationArgs` | `.ctor()` | `.ctor()` | idêntico |
| `XamlFileMigration` | `(IWorkflowContentExtractor, IFileSystem)` | `(IWorkflowContentExtractor, IFileSystem)` | idêntico |
| `IXamlMigrationService` interface | 4 methods | 4 methods | idêntico |
| `CSharpHelper.GetAllImportReferences(Activity, Boolean, IList&, IList&)` | ✓ | (não probado) | 23.10 has potential extra entry point |

DLLs ausentes em 23.10 (presentes em 26.0):
- UiPath.Studio.ProjectMigration.dll (Activity Migrator feature 26.x only)
- UiPath.Studio.Workflow.CodeAnalysis.dll
- UiPath.Studio.WorkflowCompiler.Shared.dll
- UiPath.Studio.ActivitiesInformation.dll
- UiPath.Studio.ActivitiesMetadata.dll
- UiPath.Studio.Project.Desktop.dll

**Implicação production**: alvo Sicoob = 23.10 (estável até upgrade
aprovado). Wrapper production precisa version-dispatch (`get_endpoint_ctor()`
inspecionar `GetParameters().Length` ou similar) caso D-1 pin mude.

## Recomendação

**Pause Fase 2 production integration.** Continuar com engine atual + Alt C
out-of-band validation. Reavaliar quando:
1. Engine apresentar gap concreto que requer Studio oracle (não-hipotético)
2. Sicoob padronizar Studio version (D-1 pin já força 23.10 — Studio API
   provavelmente estável dentro do pin)
3. Múltiplos incidents recorrentes do mesmo tipo justificarem investimento

Atualmente engine cobre:
- ENV-1 (Studio compat policy)
- ENV-2 (legacy bridge forwarders)
- ENV-3 (namespace imports)
- ENV-4 (VB.Settings normalize)  ← root cause BC30652/BC31424
- W-11g (insert refs)
- W-11y (BCL baseline)
- W-19 (strip mscorlib alias)
- W-26 (DEPRECATED — wrong hypothesis)
- W-31 (legacy facade strip)
- W-32 (.NET 4-only strip)

ROI atual: 5 ERROR-class fixes deterministic + 2 WARN cleanups + baseline
expansion. Cobertura empirica = 100% nos 4 BC errors do incident.

## Spike artifacts (kept)

```
spike/
├── probe_studio_api.py            # broad keyword scan over Studio DLLs
├── probe_specific_types.py        # dump methods/props/ctors of given types
├── probe_migration_invokers.py    # find migration-related types
├── probe_di_access.py             # find DI container access patterns
├── locate_types.py                # find DLL containing a given type
├── try_direct_construct.py        # T1/T2/T3 viability tests
└── studio_import_refs_spike.py    # full spike — NRE on null deps (expected)
```

Reuso futuro: se decidir prosseguir Fase 2, scripts servem de starting point.

## Open follow-ups

- [ ] Probe full DI graph: IWorkflowContentExtractor, ITextExpressionClassMethods, IAssemblyContainer concretos + ctors recursivos
- [ ] Test Alt A (hybrid): popular XamlMigrationArgs manualmente + chamar XamlFileMigration.ApplyMigration
- [ ] Test boot CliApplication.Start([]) — observar se completa sem hang + se IServiceLocator é accessível pós-Start
- [ ] Avaliar viabilidade test em Studio 23.10 (pin Sicoob). Possivelmente Sicoob tem 23.10 install em algum lugar OR baixar standalone.
