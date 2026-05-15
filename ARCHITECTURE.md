# .uipath-rules — Arquitetura

Manual operacional da engine de regras UiPath. Lê quando ficar com dúvida sobre
qual arquivo modificar para qual tipo de mudança.

## Topologia de arquivos

| Arquivo | Função | Quando humano mexe |
|---------|--------|--------------------|
| `rules.yaml` | Todas as regras (id, severity, category, target, description, applies_to, detect, fix). | **Sempre. Único.** |
| `projects.yaml` | REF + golden projects para regression baseline. | Raramente (novo projeto âncora) |
| `ARCHITECTURE.md` | Este arquivo. | Quando arquitetura mudar |
| `pyproject.toml` | Deps + scripts. | Raramente |
| `scripts/rule_engine/loader.py` | Parse YAML + schema validation. | Nunca (só se schema mudar) |
| `scripts/rule_engine/_types.py` | Rule, Finding, Severity, Category, Target. | Quando schema mudar |
| `scripts/rule_engine/encoding.py` | BOM detect + decode. | Nunca |
| `scripts/rule_engine/context.py` | FileContext, ProjectContext. | Nunca |
| `scripts/rule_engine/suppressions.py` | rule-disable parser. | Nunca |
| `scripts/rule_engine/detectors.py` | Registry de detectores. Cada `detect.type` em rules.yaml mapeia para função aqui. | Só se aparecer **novo tipo de detecção** |
| `scripts/rule_engine/fixers.py` | Registry de fixers mecânicos. | Só se aparecer **novo tipo de fix** |
| `scripts/rule_engine/runner.py` | Orquestrador: itera regras × arquivos. | Nunca |
| `scripts/rule_engine/cli.py` | CLI: `review`, `fix`, `list`, `validate`. | Nunca |
| `scripts/rule_engine/heuristics/*.py` | Escape hatches python para regras `detect.type: python`. | Quando regra precisar de lógica não-declarativa |
| `scripts/rule_engine/safety.py` | Post-fix gate (XML well-formedness + VB ref↔decl). Snapshot+rollback. | Só se gate strategy mudar |
| `scripts/rule_engine/vb_validator.py` | VB ref orphan detector (BC30451-class). | Quando whitelist mudar |
| `scripts/rule_engine/classify.py` | apply_class taxonomy (deterministic/contextual/structural). | Só se schema mudar |
| `tests/*` | Unit + integration. | Quando adicionar cenário novo |

## Mudanças que NÃO requerem tocar arquivos além de rules.yaml

- Adicionar regra (mesmo tipo de detect já registrado).
- Editar texto, severidade, exemplos.
- Promover/rebaixar severidade.
- Deletar regra.
- Mudar `target` de regra (W-* virar `all`).
- Mudar fix prose.
- Mudar regex de detecção.

## Mudanças que requerem tocar OUTRO arquivo

- Schema novo (campo) → `loader.py` + `_types.py`.
- Novo TIPO de detecção → `detectors.py` ganha função, YAML usa.
- Novo TIPO de fix mecânico → `fixers.py` ganha função, YAML usa.
- Bug no engine → arquivo correspondente.
- Hook precisa mudar formato → `cli.py` ou `hooks/`.

## Decision tree para agente

```
Pedido envolve regra (criar/editar/deletar/severity/fix)?
├── SIM → tocar SÓ rules.yaml.
│   └── Detector type já existe?
│       ├── SIM → done
│       └── NÃO → criar detector em detectors.py + adicionar regra em rules.yaml
└── NÃO → consultar matriz acima
```

## Schema rules.yaml — referência rápida

Campos obrigatórios: `id`, `severity`, `category`, `target`, `title`, `description`, `detect`.
Opcionais: `applies_to`, `fix`, `references`, `examples`, `deprecated_at`, `replaced_by`.

Bloco `fix` (todos opcionais):
- `apply_class`: `deterministic` | `contextual` | `structural` — controla se `--apply` aplica auto.
- `mechanical`: bloco com `type: <fixer_name>` + params específicos. Presença implica `deterministic` por default.
- `auto_apply: false` (legado) — equivalente a `apply_class: contextual`.
- `prose`: instruções textuais p/ humano. Sempre exibido em review/fix.

Severities: `HALT | ERROR | WARN | INFO`.
Categories: `breaking | architectural | testing | agent_behavior`.
Targets: `all | windows | legacy`.

Detectors disponíveis: ver `scripts/rule_engine/detectors.py` REGISTRY.

Fixers disponíveis (`scripts/rule_engine/fixers.py` REGISTRY):
- `regex_replace` — substituição regex pattern→replacement.
- `rename_attribute` — whole-word rename case-insensitive (VB-aware) com orphan check.
- `rename_argument` — rename arg + cascade callers (`<ui:InvokeWorkflowFile>` blocks + `this:Class.arg` propertyelement).
- `rename_xclass` — rename `x:Class` + propaga `this:Old.*` same-file. Cross-project com collision check.
- `rename_invoke_arg_key` — rename `x:Key` em invoke block (consumed_candidates tracking).
- `set_attribute` — adiciona attr se ausente (skip se presente). Self-close preservado.
- `force_attribute` — set/replace attr para canonical value (idempotente).
- `set_json_field` — set JSON field at dot-path. Preserva BOM.
- `delete_variable` — remove `<Variable Name="X">` (self-close + open+close forms).
- `delete_empty_element` — remove element vazio por tag (open+close whitespace-only ou self-close).
- `dedupe_idref` — renomeia IdRefs duplicados (suffix `_dedup_<n>`).
- `xmlns_assembly_resolve` — add_package em project.json (versão D-1*) ou remove xmlns+activities.
- `arg_default_to_element_form` — converte `this:Class.arg="value"` em element form com type lookup.
- `delete_element` — remover elementos por pattern.

## Naming wrong_prefix_map convention

Mapping `wrong → expected` em `rules.yaml` (rules N-1/N-2). Usado por
`_detect_wrong_prefix` p/ identificar prefixos antigos a substituir.

**CamelCase boundary check**: prefixo só matcha quando seguido de char
uppercase ou fim da string. Sem isso, prefixos curtos (`Nu`, `Ui`)
matchearam dentro de palavras (`vNumero` → strip `Nu` → corromperia
`meroX`). Boundary `vNu[Upper]` valida discrete prefix.

**Mapping value semantic:** o expected (value) é placeholder em
mapeamentos genéricos como `Nu: Int`. Rename real usa `expected_prefix`
do tipo da variável (Int32→Int, Int64→Lng, Double→Dbl). Value só
importa em double-stack guard (rare).

## Apply-class taxonomy

| Classe | Critério | Default behavior |
|---|---|---|
| `deterministic` | Output mecânico único, sem judgment. | `--apply` aplica auto. |
| `contextual` | Exige interpretação semântica (qual mensagem, qual valor). | `--apply` bloqueia, mostra prose. |
| `structural` | Reorganiza estrutura (split/extract/move workflow). | `--apply` bloqueia, mostra prose. |

Default derivation (sem `apply_class`):
1. `auto_apply: false` (legado) → `contextual`
2. `mechanical:` declarado em YAML → `deterministic`
3. Sem ambos → `contextual`

**Importante:** Se rule usa heuristic-emitted `fix_mechanical` (detector retorna mechanical sem ter `mechanical:` em YAML), DEVE declarar `apply_class: deterministic` explicitamente, senão fica bloqueada.

## Pin enforcement (D-1*, D-PINALERT)

Activity Migrator GA do Studio v25.10 replica o botão Migrate-to-Windows headless mas **NÃO** respeita pin Sicoob — pega `latest stable` de cada pacote UiPath durante a migração, ignorando o range declarado em `project.json::dependencies`. Engine atua como guardrail em duas camadas.

### Camada 1 — Strict pin (D-1a..D-1o, detector `nuget_version_check`)

15 regras pinam pacotes core (System, UIAutomation, Excel, Database, WebAPI, Cryptography, DocumentUnderstanding, IntelligentOCR, Mail, MicrosoftOffice365, OCR, PDF, Testing, SharePoint, XML). Todas são severity **ERROR** category **breaking** com `apply_class: deterministic`.

Detector `nuget_version_check` (em `scripts/rule_engine/detectors.py`) aceita dois params mutuamente exclusivos com precedência:

- `exact: "X.Y.Z"` — exige versão idêntica; qualquer drift (maior OU menor) viola. **Usado pelos D-1*.** Caso real: UIA pinado 25.10.8, Migrator instalou 25.10.21 — sem `exact:`, version drift `> pin` passava silente porque `min:` só checa lower bound.
- `min: "X.Y.Z"` — legado/backward compat; só flagueia `actual < min`.

Fixer `set_dependency_pin` (já existente em `fixers.py`) escreve `[X.Y.Z]` no `project.json::dependencies`. `fix --apply` realinha drift automaticamente.

### Camada 2 — API-version exclusive alert (D-PINALERT)

Realinhar o pin (D-1*) é seguro só se o XAML também não usa APIs introduzidas depois do pin. Activity Migrator pode ter injetado, durante a migração pré-realinhamento, atributos/activities exclusivas de versão `> pin` (ex: `RetryScope.LogRetriedExceptions` introduzido em UIA 25.10.21; pin Sicoob 25.10.8 não conhece). Após D-1* realinhar, essas APIs ficam órfãs no XAML → `UIPATH:LOAD ERROR` no Studio analyzer.

**D-PINALERT** cruza `project.json::dependencies` com `assets/version_exclusive_apis.yaml` (catálogo `package -> [{pattern, introduced_in, fix}]`). Para cada package onde `pinned < introduced_in` AND o XAML contém o `pattern`, emite finding ERROR `breaking` com fix prose.

- Detector: heuristic em `scripts/rule_engine/heuristics/pin_alert.py::detect_pin_alert` (registrado via `type: python`).
- `apply_class: contextual` — fix depende da API (remover atributo vs substituir activity); não há fixer mecânico genérico.

### Pipeline pós-Activity-Migrator

Ordem operacional recomendada (caller: agente migração ou humano):

1. `review` baseline antes de qualquer fix — captura D-1* drift + D-PINALERT (se Migrator já injetou APIs).
2. `fix --apply` — só `apply_class: deterministic` por default; realinha D-1*.
3. `review` pós-fix — confirma D-1* zerados; D-PINALERT remanescentes apontam APIs órfãs introduzidas pelo Migrator.
4. Cleanup XAML manual seguindo `fix_prose` de cada D-PINALERT.
5. `review` final — esperado: 0 D-1* + 0 D-PINALERT.

### Como adicionar/atualizar pin

- **Bump pin de package existente** — editar `version:` no `mechanical:` da regra D-1*, `exact:` no `params:`, `title:` e `description:`. Tests/CI cobrem regressões.
- **Novo package pinado** — adicionar nova regra `D-1X` no bloco D-1* em `rules.yaml`, copiando shape (severity ERROR, category breaking, `detect.type: nuget_version_check`, `params.exact:`, `fix.mechanical.type: set_dependency_pin`).
- **Nova API exclusiva** — adicionar entry em `assets/version_exclusive_apis.yaml`. Nada mais — detector já consome.

### Cobertura preventiva pós-Migrator — S-18 (ActivityFunc body vazio) + S-5b (PostMigration markers)

Activity Migrator emite property elements `<uix:NApplicationCard.OCREngine>`
(e equivalente `.CVEngine`) com `<ActivityFunc>` placeholder contendo APENAS
`<ActivityFunc.Argument>` (DelegateInArgument). Body sem activity child →
Studio compile falha com `OCR Engine must be set` / `CV Engine must be set`.

**S-18** (detector `empty_activityfunc.py`, severity ERROR breaking, target
windows) flagueia cada ocorrência. `apply_class: structural` — engine
expõe alerta + prose; correção exige decidir qual engine plugar
(`UiPathScreenOCR` é default Sicoob; `UiPathDocumentOCR` / `MicrosoftOCR`
em casos específicos). Detector cobre `.OCREngine` e `.CVEngine` em
qualquer parent prefix/owner XAML.

**S-5b** (regex `sap2010:Annotation.AnnotationText="[PostMigration Action
Required]`, severity ERROR breaking, target windows) flagueia annotations
TODO injetadas pelo Activity Migrator em TryCatch (e outras activities) ao
migrar Legacy→Windows. Diferente da S-5 (annotations gerais, exclui
REFramework template), S-5b ataca SOMENTE markers do Migrator em QUALQUER
arquivo — Migrator injeta em Main/Framework justamente. `apply_class:
deterministic` — fixer reusa `strip_annotation_text` com `text_prefix:
"[PostMigration Action Required]"`, removendo só os markers (preserva
annotations legítimas no mesmo file).

## Pre-publish gate (`review` = canonical)

`review` é o **canonical pre-publish gate**: SEMPRE roda o pipeline completo
sem opt-out. Se passa, projeto é publish-safe garantido.

### Pipeline de gates

| # | Gate | Função | Implementação |
|---|------|--------|---------------|
| 1 | Rules Sicoob | Regras locais YAML (A-*, S-*, N-*, W-*, D-*, etc.). | `runner.run` |
| 2 | Lib-contract override | Downgrade findings que conflitam com contrato CCS_* exposto. | `_apply_sicoob_lib_overrides` |
| 3 | Studio Analyzer | uipcli `analyze` — ST-* oficiais, contrato lib NuGet, Roslyn compile, SecureString flow. Findings `UIPATH:<code>`. | `_inject_analyzer_findings` |
| 4 | NuGet restore | `nuget restore project.json` — peer dep resolution. Emite `NUGET:NU<NNNN>` por code. NU1101/1102/1107/1605/3026/5048 promoted ERROR (blocking publish). | `_run_nuget_restore_gate` |
| 5 | uipcli pack (publish dry-run) | `uipcli publish -o Process -f <tmpdir>` — equivalent a pack dry-run sem upload. Captura BC* compile errors + validation que só aparecem no flow de publish. Emite `UIPATH:PACK`. | `_run_uipcli_pack_gate` |

### Cobertura por gate

| Concern | Gate primário |
|---|---|
| Sicoob conventions (naming, log patterns, prefixo) | 1 |
| Activity contracts (args required, OverloadGroup) | 3 |
| VB compile errors em XAML (BC30002/BC30451/etc.) | 5 (publish dry-run força full compile) |
| Peer dep resolution (Sicoob feed visible) | 4 |
| Package signing / metadata | 4 |
| Final publish-safety | 5 (autoritativo) |

### Opt-out

Sem opt-out via CLI. `--no-analyzer-gate` flag mantida apenas como deprecation
warning — emite `[WARNING] --no-analyzer-gate is deprecated and ignored; review always runs analyzer gate.` e ignora.

**Env override (test harness apenas)**: `UIPATH_RULES_DISABLE_EXTERNAL_GATES=1`
pula gates 3/4/5 (não invoca uipcli/nuget). Usado pelo pytest harness (em
`tests/conftest.py`) para evitar dependência de binaries externos durante
unit tests. NÃO usar em produção.

### Graceful degradation

Cada gate falha graceful se binary não disponível:
- Analyzer (uipcli ausente): warn stderr `[analyzer-gate] uipcli not found — gate skipped`. Set `UIPATH_STUDIO_CLI`.
- NuGet (nuget.exe ausente): warn `[NUGET-GATE] nuget binary not found; skipping`. Set `UIPATH_NUGET_CLI` ou install nuget.exe / dotnet SDK. Se só dotnet disponível, skipa silente (dotnet restore não suporta UiPath project.json).
- Pack (uipcli ausente): warn `[PACK-GATE] uipcli not found — gate skipped`.

### Tempo total

Esperado ~30s–2min per project (varia com tamanho + cache analyzer baseline).

## Pipeline de defesa (`fix --apply`)

### Layer 1 — Engine internal (fast feedback ~1-2s)

1. **Pre-fix snapshot** — bytes do primary file lidos antes.
2. **Apply fixer** — fixer escreve, registra mtimes de cascade files.
3. **XML well-formedness gate** — `xml.etree.ElementTree.parse`. Se quebrou parse, rollback.
4. **VB ref↔declaration gate** — `vb_validator.diff_orphans`. Se introduziu ref órfã, rollback.
5. **Cascade detection** — files com mtime delta validados; falhas log only (não auto-rollback nesta versão).
6. **Fixpoint loop** — re-detect+apply até `applied=0` (max 20 iter). Garante idempotência em rules que precisam multi-pass (N-6/N-7 emitem 1 finding por attr).

### Layer 2 — Studio Analyzer gate (ground truth ~30-60s)

Executa antes (baseline) e depois (post-diff) do fix loop. Captura o que Layer 1 não vê:
- **Roslyn VB compile errors** (BC30109/BC30451/etc.): identifiers undeclared, type mismatches.
- **XAML schema violations** via assembly metadata reflection: activity contracts, collection item types, single-child slots.
- **Activity property required**: args missing, type incompatibilities.
- **NuGet package resolution**: missing dependencies.

**Implementação**: `analyzer.py`. Invoca `UiPath.Studio.CommandLine.exe analyze -p <project.json>`. Parser captura `#json{...}#json` block + `NU\d+:` package errors.

**Diff-based gate**: erros NOVOS (post − baseline) bloqueiam (exit non-zero). Pré-existentes ignorados.

**Studio version mismatch**: uipcli respeita `project.json.targetFramework`. Local Studio v26.x analisando project Windows-5.x carrega rules compat. Diff gate elimina falsos positivos vindos de rules-novas em Studio local.

**Cache** (F27): baseline cacheado em `.uipath-rules/.tmp/analyzer_cache/<project_sig>/analyzer_baseline_<content_sig>.json`. `project_sig`=SHA1(absolute path do project_root, 16 hex chars) isola per-project. `content_sig`=SHA1(project.json mtime + xaml count + max xaml mtime) invalida quando projeto muda materialmente. Aloja em engine `.tmp/` (gitignored, descartável) — NÃO polui o working dir do projeto UiPath. Re-runs consecutivos pulam baseline (~30-60s economizados).

**Discovery**: ordem de busca uipcli:
1. Env var `UIPATH_STUDIO_CLI`
2. PATH lookup
3. Well-known paths: `%LocalAppData%\Programs\UiPathPlatform\Studio\*\UiPath.Studio.CommandLine.exe`, etc.

**Graceful degradation**: skip silencioso se não encontrado.

**Default**: ON. Flag `--no-analyzer-gate` desativa explicitamente.

### Layer separation rationale

| Concern | Layer |
|---|---|
| Sicoob conventions (naming, log patterns, prefixo) | 1 (engine) |
| Fast iteration (dev loop) | 1 (regex/lxml) |
| XAML schema authority | 2 (assembly metadata) |
| VB compile authority | 2 (Roslyn) |
| Compile-safe pre-PR gate | 2 |

**Hardcoded restrictive parent lists** em fixers (ex: `_N5_RESTRICTIVE_PARENT_NAMES`): mantidas mínimas (~11 entries) para reduzir write-rollback churn. Layer 2 é authoritative pra gaps.

## REF project — uso como oráculo

`projects.yaml.golden_projects` lista projetos âncora. Engine garante
findings `category=breaking` = 0 nesses projetos (exceto known_exceptions).

REF atual: `importar-cadastro-avais-fiancas-honrados-performer` (Windows target).
Escopo migração foi só técnico — regras `architectural` podem disparar em REF
sem problema.

## Política de versionamento

Engine, hooks, agentes e CLI **NUNCA** rodam `git add/commit/push` em projetos UiPath.
Edits ficam locais; usuário commita manualmente.

`.uipath-rules/` é repo git próprio (`mucunfo/uipath-rules`, branch `main`) com
CI windows-latest rodando `cli validate` + `pytest` em push/PR. Branch
protection desativada (private free tier). Mudanças no engine seguem fluxo
PR padrão.

## Suppressões inline

```xml
<!-- rule-disable: A-7 -->          (silencia A-7 nas próximas linhas)
<!-- rule-disable: A-7, S-8 -->     (múltiplas)
<!-- rule-disable-file: A-3 -->     (file scope, no <Activity> root)
```

`rtk-disable` é alias legado aceito. Só silencia WARN/INFO. ERROR/HALT não silenciáveis.

## CLI exit codes

| Code | Significado |
|------|-------------|
| 0 | Sem findings |
| 1 | WARN/INFO findings |
| 2 | ERROR findings |
| 3 | HALT findings |
| ≥10 | Erro interno (parse, schema, encoding) |

## Phase-out Legacy

Quando 100% projetos forem Windows, executar `cli.py phase-out windows-only`
(implementação Plan 4) que universaliza W-3, W-10, W-12, W-16, W-17 para `target: all`.
W-1, W-2, W-4, W-11, W-13, W-14, W-15 ficam `target: windows` (relevância histórica).

## Como adicionar regra nova

1. Editar `rules.yaml` adicionando entrada nova com schema completo.
2. Verificar detector type já existe via `python -m scripts.rule_engine.cli list`.
   - Se sim → done.
   - Se não → adicionar função em `detectors.py` (registrar em REGISTRY).
3. Validar: `python -m scripts.rule_engine.cli validate`.
4. Testar contra REF: `python -m scripts.rule_engine.cli review <REF_PATH>`.
5. Confirmar regra `breaking` zera em REF (ou registrar em `projects.yaml.known_exceptions`).

## Como deprecar regra

1. Adicionar `deprecated_at: 2026-MM-DD` na regra.
2. Opcional: `replaced_by: A-XX` se substituída.
3. Manter no YAML por 1-2 ciclos para histórico antes de remover.

## Activity metadata layer (categoria `metadata`)

Engine cruza XAML contra schema autoritativo dos packages NuGet UiPath
instalados, gerado offline via Mono.Cecil reflection.

### Fonte de verdade

`assets/activities/activities-compact.json` (~1.7 MB, commitado).
Markdown human-readable por package em `assets/activities/uipath.<pkg>.md` +
índice `INDEX.md`. 20 packages indexados, ~1560 entries (Activities +
DataObjects). Inclui `uipath.ocr.activities` (UiPathScreenOCR /
UiPathDocumentOCR / ExtendedLanguagesOCR / CjkOCR; xmlns canônico
`http://schemas.uipath.com/workflow/activities/ocr`).

NOTA companion-dirs: extract-cecil precisa do Cecil resolver ver os pacotes
`*.contracts` siblings (ex: `uipath.ocr.contracts` p/ resolver
`OCRAsyncCodeActivity` base class). `batch-extract.ps1::Get-CompanionSearchDirs`
adiciona automaticamente — sem isso, classes derivadas resolvem `BaseType=null`
em Cecil e caem em `Kind=DataObject` por falsa-falha de `Test-IsActivity`.

### Como regenerar

```powershell
cd scripts/activities_meta
.\batch-extract.ps1   # sweep ~/.nuget/packages/uipath.* via Cecil
.\build-schema.ps1    # compacta + gera markdown
```

Pré-requisito: UiPath Studio instalado + packages alvo abertos pelo menos
uma vez (popula nuget cache). Detalhes em `scripts/activities_meta/README.md`.

Quando regenerar:
- Adicionou package novo / atualizou versão.
- Onboarding em máquina nova.
- Suspeita de divergência schema vs Studio real.

NÃO rodar em CI/hook (depende de cache local).

### Detector

Heuristic Python `scripts/rule_engine/heuristics/activity_meta.py` carrega
schema em singleton, indexa por FQN + (xmlns, local_name) + variantes
generic-arity.

Cada regra M-* declara `detect.type: python` apontando para função top-level
do módulo (mesmo padrão de S-11, T-5, etc).

### Regras M-*

| ID | Sev | Detecta |
|---|---|---|
| M-1 | ERROR | Activity FQN inexistente (xmlns canônico) |
| M-2 | ERROR | Required arg ausente (respeita OverloadGroup) |
| M-3 | WARN | Arg desconhecido (typo ou removido) |
| M-4 | ERROR | OverloadGroup conflito (alternativas misturadas) |
| M-5 | WARN | Literal/expressão VB incompatível com tipo do arg |
| M-6 | ERROR | xmlns de prefix UiPath não declarado no root |
| M-7 | INFO | DefaultValue redundante |
| M-8 | ERROR | `[Nothing]` (VB) em InArgument tipo valor — runtime crash |

**M-5 cobre**:
- Literais: string em Boolean/numérico/DateTime/TimeSpan; numérico em Boolean/DateTime
- Bind expressions VB: `[CInt(...)]`, `[CStr(...)]`, `[CBool(...)]`, `[CDate(...)]`,
  `[CType(x, T)]`, `[New T(...)]`, concat `&`/`+`, `.ToString()`
- Skip: bind sem cast óbvio, markup extensions (`{Binding}`, `{x:Null}`)

**M-8 cobre**:
- `[Nothing]` em InArgument tipo valor (Integer, Boolean, DateTime, etc)
- Skip: `{x:Null}` (significa "arg não fornecido"), Nullable<T>, reference types

### Schema model

`activities-compact.json` indexa entries com:
- `fqn`: FullName .NET
- `kind`: `Activity` | `DataObject` (DTO/argument class)
- `xmlns`: URI canônico XAML
- `args[]`: properties capturadas com:
  - `n`: nome
  - `t`: tipo
  - `d`: direção (`In|Out|InOut|Plain`)
  - `a`: IsArgument (true para `*Argument<T>`, false para property pura)
  - `r`: required
  - `g`: OverloadGroup
  - `v`: default value

Activities = tipos herdando `System.Activities.Activity` family.
DataObjects = tipos públicos não-abstract em namespaces canônicos UiPath
(referenciados em XAML como property values: Target, *Modification,
*OperationArgument, etc).

Properties com `[Browsable(false)]` são incluídas mesmo assim (Studio
serializa em XAML mesmo não exibindo no painel design-time).

### Limitações remanescentes

1. **Custom packages**: M-* só dispara em xmlns canônicos UiPath
   (`_KNOWN_UIPATH_XMLNS`). Libraries proprietárias (clr-namespace) precisam
   cross-validação com `project.json::dependencies` — fase 6.
2. **Type checking semântico** (M-5): não implementado. Requer parser de
   expressão VB/C# ou integração com `UiPath.ActivityCompiler.CommandLine.exe`
   headless.
3. **xmlns canônico whitelist** (`_KNOWN_UIPATH_XMLNS`) é hardcoded. Se UiPath
   adicionar novo URI canônico, precisa update manual. Auto-derivar do
   schema (campo `xmlns` aggregated) é trivial — mas só vale fazer quando
   houver evidência de drift.

## Hooks — contrato

`scripts/hooks/post_xaml_edit.py` + `post_project_json_edit.py`:
- Input: stdin JSON (Claude Code PostToolUse format).
- Action: `python -m scripts.rule_engine.cli review <project> --format json`.
- Output formato compacto p/ LLM:
  ```
  [SEV] [rule_id] linha N: <message>
        why: <description 1ª linha>
        fix: <fix.prose 1ª linha — fallback description quando prose ausente>
  ```
- Exit code: ignorado por Claude Code (hook não bloqueia).

JSON output do CLI inclui `description` (full) + `fix.prose` (full) por finding —
hook usa só 1ª linha p/ compactness, ferramentas externas têm acesso completo.

## Documentação derivada

`cli docs --llm-only --out <path>.md` gera markdown agrupado por prefix ID
listando só rules LLM-dependentes (apply_class != deterministic). Catálogo é
**sempre regenerado** de `rules.yaml` — nunca editar à mão. Útil p/ onboarding,
review humano, prompt injection externa.

`cli docs --out <path>.md` (sem `--llm-only`) emite catálogo completo.

## LLM-rule documentation strategy

Princípio: `rules.yaml` é fonte única. LLM consome rules **JIT via findings**,
não via catálogo carregado no system prompt. Custo base de contexto = 0.

Campos por rule consumidos pelo LLM (em ordem de prioridade):
1. `fix.prose` — imperativo direto (≤3 linhas). Backfill opt-in caso a caso.
2. `description` — fallback quando prose ausente. Hook renderiza 1ª linha.
3. `examples` — só em review humano, não inline em hook.

Não fragmentar prose em arquivos paralelos. Se prose precisa expandir, vive
inline em `rules.yaml` no campo `fix.prose`.
