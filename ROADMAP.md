# ROADMAP — UiPath Schema Validator

Plano persistente entre sessões. Atualizado a cada fase concluída.
**Audience**: agente Claude retomando trabalho + dev humano.

## Estado atual

**Última atualização**: 2026-05-07 (pós F20)

**Métricas vivas** (rodar para confirmar antes de retomar):

```bash
cd .uipath-rules
python -m scripts.rule_engine.cli validate    # esperar "227 regras"
python -m pytest -q                            # esperar "237 passed"
python -m scripts.rule_engine.cli review "../importar-cadastro-avais-fiancas-honrados/importar-cadastro-avais-fiancas-honrados-performer" --format json > .tmp/m_review_check.json
python -c "import json; from collections import Counter; d=json.load(open('.tmp/m_review_check.json',encoding='utf-8')); m=[f for f in d['findings'] if f['rule_id'].startswith('M-')]; print('M-* REF:', len(m), dict(Counter(f['rule_id'] for f in m)))"  # esperar "M-* REF: 0 {}"
```

Se métricas divergem → investigar antes de avançar.

---

## Histórico — Fases concluídas

### F1-F4 — Engine schema-aware (concluído)
- Extractor Cecil + assets/activities/ + Category.METADATA + heuristic activity_meta.py + detector activity_signature
- Regras M-1 a M-7 ativas
- Status: production

### F5 — Schema completo (concluído)
- Extractor v2: plain properties + DataObjects + Browsable=false preservado
- Schema 1028→1552 entries (1028 Activities + 524 DataObjects)
- Whitelist DTO hardcode removida
- Status: production

### F6 — Plug schema nos agentes (concluído)
- `scripts/activities_meta/lookup.py` CLI (--activity, --search, --package, --list-packages)
- uipath-creator.md: workflow obrigatório consultar schema antes emitir
- uipath-reviewer.md: relata M-* enriched
- Status: production

### F7 — Display labels heurísticos (concluído)
- `ConvertTo-HumanLabel` em build-schema.ps1
- Campo `label` em ArgDef + compact JSON
- Markdowns mostram `// Workbook local path` etc
- Status: production (heurística; F13 substitui por reais)

### F8 — pre_xaml_read schema injection (concluído)
- Hook injeta schema digest antes Read .xaml
- Cap MAX_SCHEMA_REFS=12, formato compact (required + groups)
- Status: production

### F9 — M-5 type mismatch literais (concluído)
- Heurística sem compiler: literal vs schema_type
- TimeSpan literal `00:00:00` reconhecido
- Status: production

### F10 — VB-aware type inference (concluído)
- M-5 estendido: `_infer_vb_bind_type` cobre CInt/CStr/CBool/CDate/CType/New/&/.ToString
- M-8 nova: `[Nothing]` em InArgument value type → ERROR
- Distinção `{x:Null}` (skip) vs `[Nothing]` (flag)
- Status: production

### F11 — Auto-derive xmlns canônicos (concluído)
- Removido hardcode `_KNOWN_UIPATH_XMLNS`
- `ActivitySchema._canonical_xmlns` agrega URIs do schema
- `is_canonical_xmlns()` + `canonical_xmlns_set()` métodos
- Hook + `_check_unknown` usam runtime detection
- Status: production

### F12 — Fixers mecânicos M-2 + M-3 hints (concluído)
- F12.1: fixer `add_property_element` em `scripts/rule_engine/fixers.py`
- F12.2: M-3 Levenshtein suggestion
- F12.4 (M-4 mecânico): SKIPPED — judgment humano
- Status: production

### F18 — Telemetria findings (concluído)
- `cli review --telemetry` → JSONL em `.tmp/telemetry/<date>.jsonl`
- `cli stats --since 30d --top 20` agregador markdown
- Top rules + untriggered list (candidates deprecação)
- Schema: {ts, project, rule_id, severity, count, suppressed_count}
- Status: production

### F16 — Performance bench + cache invalidation (concluído)
- `scripts/perf_bench.py` timer per-file via Runner monkey-patch
- Schema mtime check em `get_schema()` → reload se file mais novo
- REF baseline: schema 36ms load, p50 22ms/file, p95 77ms, max 321ms (Dispatcher.xaml outlier)
- Status: production

### F13 — Resource keys via .resources DLL (concluído)
- `extract-resources.ps1` standalone — Reflection.Assembly + ResourceReader
- `extract-cecil.ps1` extrai EN baseline (main DLL embedded resources)
- `batch-extract.ps1` detecta satellite pt-BR e roda extract-resources
- `batch-extract.ps1` deduplica resources em PackageIndex (vs per-activity → reduziu 740MB → 21MB raw)
- `build-schema.ps1` `Resolve-Label` ordem pt-BR > EN > heurística F7
- Compact JSON 1.7MB (estável)
- Status: production

### F20 — Visualizador HTML interativo (concluído)
- `assets/activities/index.html` self-contained (~1.7MB com JSON inline)
- Search por FQN/package; filtros por kind (Activity/DataObject) e package
- Toggle "only with required args"
- Detail pane: tabela args com REQUIRED, OverloadGroup, Plain flags + label PT-BR
- Cap render 500 items (refine search se exceder)
- Built-in `build-schema.ps1` (sem step extra)
- Status: production

---

## Plano em aberto — Fases F14+

### F14 — Compiler headless M-5 full type check
**Esforço**: 3-5 dias | **Valor**: médio | **Risco**: baixo

Substitui heurística F7 por labels reais (PT-BR via satellite assemblies).

**Implementação**:
1. `extract-cecil.ps1`: ler `EmbeddedResource` do main + `.resources.dll` satellites por idioma
2. Parse `.resources` binary via `[System.Resources.ResourceReader]` em PS 5.1
3. Schema dump ganha `displayLabels: { "en-US": "Workbook path", "pt-BR": "Caminho do workbook" }`
4. `compact-schema.ps1` escolhe label preferido (config: `pt-BR`)
5. `lookup.py` + markdowns usam label real
6. Heurística F7 vira fallback para resource keys não encontradas

**Risco**: PreserializedResourceWriter (.NET 5+) tem formato binário ligeiramente diferente. Fallback: heurística + log warning.

**Como retomar**:
- Inspecionar `*.resources.dll` em `~/.nuget/packages/uipath.excel.activities/<ver>/lib/<tfm>/<lang>/`
- Snippet PS 5.1: `[Reflection.Assembly]::LoadFrom + GetManifestResourceStream + System.Resources.ResourceReader`
- Mapear chaves `WorkbookLocalPathDisplayName` → string traduzida

---

### F14 — Compiler headless M-5 full type check
**Esforço**: 1-2 semanas | **Valor**: alto | **Risco**: alto (performance)

Validação de tipo autoritativa via `UiPath.ActivityCompiler.CommandLine.exe`.

**Implementação**:
1. Wrapper Python: `compile_xaml(xaml_path) → list[CompileError]`
2. Cache por checksum SHA1(xaml + project.json)
3. Mapear erros compile (`BC30311`, `BC30512`, etc) para findings M-5
4. Modo opt-in: `cli review --deep` (default heurística atual)
5. Performance: 5-30s por XAML, paralelizável

**Bloqueador**: compiler precisa runtime + project.json + nuget cache válidos. Sem isso, fallback heurística.

**Como retomar**:
- Studio dir tem `UiPath.ActivityCompiler.CommandLine.exe` — testar `--help` ver flags
- Pesquisar formato de output (JSON?) ou parsear texto stderr
- Implementar bench: compile ReviewBaseline 15 XAMLs → tempo total

---

### F15 — Custom package on-demand schema
**Esforço**: 1 semana | **Valor**: baixo (Sicoob declarou atípico) | **Risco**: baixo

Validação args para libraries proprietárias.

**Trigger**: aparecer caso real onde lib custom Sicoob é usada e bug passa.

**Implementação**:
1. ProjectContext lê `project.json::dependencies`
2. Para xmlns clr-namespace+assembly não-UiPath: localizar `.nupkg` em nuget cache
3. Rodar `extract-cecil.ps1` on-demand, cachear `.tmp/custom_schemas/<package_id>__<version>.json`
4. Schema custom merged ao runtime na inicialização do detector
5. Cache invalidation: mtime do .nupkg vs cache

**Como retomar**:
- ProjectContext.project_json já tem deps em loader
- Iterar deps não-UiPath, lookup `~/.nuget/packages/<pkg>/<ver>/`
- Reusa `extract-cecil.ps1` (já genérico)

---

### F16 — Performance bench + cache invalidation
**Esforço**: 2 dias | **Valor**: baixo | **Risco**: zero

**Trigger**: user reportar review lento ou hook bloqueante.

**Implementação**:
1. `scripts/perf_bench.py`: timer por XAML em REF (15+ files)
2. cProfile schema lookup, regex parse, hook overhead
3. Cache invalidation: schema reload se `activities-compact.json` mtime > singleton load time
4. Hook pre_xaml_read: timeout 2s; skip se overrun

**Done**: review sub-segundo por XAML médio + bench reproducible.

---

### F17 — Multi-version Studio support
**Esforço**: 3 dias | **Valor**: médio | **Risco**: médio (migração schema layout)

**Trigger**: empresa migrar Studio version; máquinas dev em versões diferentes.

**Implementação**:
1. Schema dump nomeado: `assets/activities/<studio_major>/`
2. ProjectContext.studio_version (já existe via project.json)
3. Loader escolhe baseado em version; fallback latest
4. Migração compat: layout antigo `assets/activities/*.md` → `assets/activities/26.0/*.md`

**Como retomar**:
- Verificar `project_json.studioVersion` em projetos REF
- Decidir granularidade: major (26, 25, 24) vs minor (26.0, 25.10)

---

### F18 — Telemetria findings
**Esforço**: 2 dias | **Valor**: médio | **Risco**: zero

**Implementação**:
1. `cli review --telemetry` salva counts em `.tmp/telemetry/<date>.jsonl`
2. Schema: `{date, project, rule_id, severity, count}`
3. Aggregator: `cli stats --since 30d` markdown report
4. Dashboard simples (ranking regras, trend)

**Done**: identificar regras nunca disparam (candidatas deprecação) e regras dominantes (candidates apply_class deterministic).

---

### F19 — LLM evaluation harness
**Esforço**: 1-2 semanas | **Valor**: alto (mede ROI real) | **Risco**: custo runs LLM

**Implementação**:
1. Conjunto fixo prompts: 5-10 ("crie workflow excel + email", etc)
2. Dois modos: A=sem schema injection, B=com schema injection
3. Métrica: # M-* findings, # ERROR/HALT, tokens, tempo até zero-violations
4. Reporter delta antes/depois
5. Iterar prompts agent baseado em resultados

**Bloqueador**: precisa F18 baseline funcionando.

**Como retomar**:
- Definir prompts em `tests/llm_eval/prompts/`
- Wrapper `run_llm.py` (Anthropic API)
- Métrica em CSV; comparação manual primeiro, automatizar depois

---

### F20 — Visualizador HTML interativo
**Esforço**: 3-5 dias | **Valor**: baixo (CLI já cobre) | **Risco**: zero

HTML self-contained gerado por `build-schema.ps1`. Search box, filtros, deep-link por activity.

**Implementação**:
1. Template Vue.js inline (sem build) ou DataTables
2. JSON inline no HTML
3. Output `assets/activities/index.html`

---

## F21+ — Engine Layer 2 + Fixers (sessão 2026-05-07)

Contexto: sessão adicionou Layer 2 (Studio Analyzer gate via uipcli) + fixer N-5 com lxml. Trabalho restante mapeado abaixo.

**Status**:
- F21 ✅ — N-3 detector lookahead bug fix
- F22 ✅ — Walker multi-line (já coberto pelo N-5 paired-tag walker)
- F23 ✅ — Fixer N-10 remove anticipatory log
- F24 ✅ — Wrap em Sequence p/ N-5 em parents wrap-able. Whitelist suffix expandida: `.Then`/`.Else`/`.Action`/`.Body`/`.ActivityBody`/`.RetryAction`/`.Entry`/`.Exit`. Non-qualified ActivityAction também wrap-able (delegate body). Genuine restritivos (Assign.Value, MultipleAssign.AssignOperations, ActivityFunc, collections) permanecem no-op — by design (type contract não permite wrap).
- F25 ✅ — Fixer N-3 add_prefixo_arg + caller default-value awareness em A-19b
- F26 ✅ — Layer 2 default-on (`--no-analyzer-gate` opt-out)
- F27 ✅ — Layer 2 baseline cache via SHA1(project signature)
- F28 ✅ — Per-loop rollback via Layer 2: snapshot pre-loop bytes, rollback files com new errors. Auto-revert quando gate detecta regression.
- F31 ✅ — `tests/test_fixers_layer2.py`: 12 tests pra fixers novos (insert_trace_log restrictive parent, idempotency, prefixo-aware, DisplayName uniqueness, F24 wrap em .Then, F24 skip Assign.Value; remove_anticipatory_log basic + idempotent; add_prefixo_arg full pipeline + idempotent; duplicate_id skip_patterns). Total suite: 249 passed.
- F32 ✅ — ARCHITECTURE.md atualizado com Layer 2

- F34 ✅ partial — Schema-driven parent classification via CoreWF/Community.Activities decorators:
  - `extract-cecil.ps1` estendido captura `ContentPropertyAttribute`, `CollectionItemTypeAttribute`, `ActivityShape` (Activity/ActivityFunc/ActivityAction/etc.).
  - `build-schema.ps1` emite novos campos em activities-compact.json.
  - `activity_meta.py` loader consume + helper `classify_parent_for_logmessage()` retorna 'open'|'wrap_able'|'restrictive'|'unknown'.
  - N-5 fixer consults schema first, fallback hardcoded lists em 'unknown'.
  - Tests adicionados (3 novos) — total 252 passed (15 layer2 + 237 base).
  - **Pendente**: re-rodar `batch-extract.ps1 + build-schema.ps1` pra popular novos campos no schema atual. Engine ready.

**Pendentes** (Tier 2-3):
- **F33 partial done** — Reconciliation rules ↔ Layer 2:
  - ✅ X-1 detector skip auto-generated IdRefs (`<TypeName>``\d+_\d+`). 3 FPs eliminated em REF (Layer 2 silent, Studio aceita).
  - ✅ A-19b detector ignora `this:<Class>.<arg>` defaults (cascade fixed em F25).
  - **Gaps remaining** (Layer 2 catches, engine não tem rule):
    - `ST-SEC-007` / `ST-SEC-008` / `ST-SEC-009` — SecureString misuse patterns.
    - `UI-REL-001` — Selector restritivo IDX limit.
    - `ST-USG-009` / `ST-USG-020` — usage patterns.
    Decisão: NÃO adicionar como Layer 1 rules. Layer 2 ground truth captura. Engine focus = Sicoob conventions only.
  - **Confirmado** (snapshot 2026-04): rules ERRORs restantes em REF (W-1, W-11a, N-11, W-12, J-1) eram intencionais (escopo migração técnica apenas). Golden project manifest removido em 2026-05 (vide chore/remove-golden-project) — smoke E2E + uipcli gates substituem cobertura.
- F24 — Wrap em Sequence pra desbloquear N-5 em parents restritivos. Design phase: distinguir wrap-able single-child slot (If.Then/Else, ActivityFunc/Action) vs collection-typed (não wrap). Esforço 2-3 dias.
- F28 — Per-iter rollback via Layer 2 (snapshot bytes pré-iter, revert se errors novos). Esforço 2 dias.
- F29 — Outros fixers contextual/structural com lxml (N-4 args→Dict, N-9 enriquecer Message, W-2 null guards). Esforço 1 semana.
- F30 — Symbol table cross-file. Esforço 1 semana.
- F31 (residual) — Fixer-specific tests com fixtures.

### F21 — Bug detector N-3: lookahead falso positivo
**Esforço**: meio dia | **Valor**: alto | **Risco**: zero

`heuristics/logs.py:detect_n3_log_prefixo` parte 2 (linha ~62-78): regex `_RE_LOG_MESSAGE_TEXT` busca `<InArgument x:TypeArguments="x:String">` em até 800 chars APÓS o `<ui:LogMessage>`. Bug: quando Message é attribute (`Message="..."`) sem property-element form, lookahead pega `<InArgument>` da PRÓXIMA activity (Assign, etc.).

**Reprodução**: 4 FPs nesta sessão (Main.xaml, Process.xaml, LogDescDetalhe.xaml, Listar_Dossies_Filtra.xaml). Todos tinham `Message="[in_StPrefixoLog + ...]"` e flag fired wrong.

**Implementação**:
1. Em `_RE_LOG_MESSAGE_TEXT` busca, primeiro extrair attribute `Message=` do `<ui:LogMessage>` open tag.
2. Se Message é attribute: testar `prefixo_arg in attribute_value`. Se sim, OK.
3. Só fallback pra property-element lookahead se Message não está em attribute.
4. Lookahead deve LIMITAR ao próprio LogMessage (parar em `</ui:LogMessage>` ou next `<ui:LogMessage>` ou next `<*>` outro que não property-element do LogMessage).

**Done**: 4 suppressões dessa sessão removíveis; FP=0 contra REF.

**Como retomar**: ler `_RE_LOG_MESSAGE_TEXT` + `detect_n3_log_prefixo`. Refatorar p/ checar attribute primeiro. Adicionar fixture `tests/fixtures/n3_message_attribute.xaml`.

---

### F22 — Walker multi-line LogMessage
**Esforço**: meio dia | **Valor**: médio | **Risco**: baixo

`fixers.py:_FULLTAG_RE` + scripts ad-hoc desta sessão assumem LogMessage self-closed em uma linha. Multi-line forms (`<ui:LogMessage ...>\n  <ui:LogMessage.Message>...</ui:LogMessage.Message>\n</ui:LogMessage>`) escapam.

**Reprodução**: 3 N-10 findings não removíveis pelo script (Main.xaml:405, VerificarRestricaoProcessamento.xaml:209, DownloadFileSharePoint.xaml:125).

**Implementação**:
1. Walker aceita LogMessage open + property-element children.
2. `find_element_end` já suporta paired tags — confirmar caminho funciona pra `<ui:LogMessage>...</ui:LogMessage>`.
3. Testar: 3 findings residuais no projeto-alvo.

**Done**: N-10 fixer (F23) cobre 100% dos forms.

---

### F23 — Fixer N-10 (remove anticipatory logs)
**Esforço**: 1 dia | **Valor**: alto | **Risco**: baixo

Hoje: removido via script ad-hoc (`.tmp/_remove_n10.py`) — não está no engine.

**Implementação**:
1. Detector N-10 emite `fix_mechanical={type: "remove_anticipatory_log", line, parent_qual}`.
2. Fixer novo `apply_remove_anticipatory_log`:
   - Localiza LogMessage por line (cobrindo single-line + multi-line via F22).
   - Confirma parent matches finding's parent_qual.
   - Confirma sibling-prev não é executable activity (defensive — sem isso, log já é OK).
   - Remove element + linha vazia leftover.
3. Declarar `apply_class: structural` em rules.yaml N-10.
4. Cuidado: cascade — remover log pode amplificar N-5 nos siblings que perdem cobertura.

**Done**: 39 N-10 restantes resolvidos via engine. Cascade N-5 reposto via F24 (S-10 wrap) ou re-run N-5 fixer.

---

### F24 — Fixer S-10 (wrap em Sequence) + desbloqueio N-5 restritivo
**Esforço**: 2-3 dias | **Valor**: muito alto | **Risco**: médio (compile)

S-10 detecta LogMessage em parent restritivo. Fix: envolver activity + log em `<Sequence>`. Permite N-5 fixer inserir Trace dentro do wrap.

**Implementação**:
1. Detector S-10 já existe; revisar.
2. Fixer novo `apply_wrap_in_sequence`:
   - Recebe spec com offset/local-name da activity restritiva.
   - Lxml: identifica activity + parent (single-child slot tipo `If.Then`).
   - Substitui activity por `<Sequence><activity-original/></Sequence>`.
   - Validação: parent semântica preservada (Sequence implementa mesma interface single-activity).
3. Cascade: N-5 fixer no próximo iter detecta Sequence parent (não-restritivo), insere Trace.

**Done**: 118 N-5 restantes do projeto-alvo cobertos. Maioria do longtail INFO eliminada.

**Como retomar**: parents alvo são `If.Then`, `If.Else`, `ActivityFunc`, `ActivityAction`, `Transition.Action`. Wrap testado já em padrão Sicoob (Sequence comum).

---

### F25 — Fixer N-3 (declare arg + propagate callers)
**Esforço**: 2 dias | **Valor**: alto | **Risco**: médio (cross-file)

Hoje: workflows que ganharam Trace mas não declaram `in_StPrefixoLog` viram findings N-3. Fix manual exige declaração + propagation em callers.

**Implementação**:
1. Reusar infraestrutura `apply_rename_argument` (cross-file logic).
2. Fixer novo `apply_declare_prefixo_arg`:
   - Adiciona `<x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />` em `<x:Members>`.
   - Adiciona default value via `<this:<Class>.in_StPrefixoLog><Literal Value=""/></this:<Class>.in_StPrefixoLog>`.
   - Propaga em callers via `<ui:InvokeWorkflowFile>` que apontem ao callee: adicionar `<InArgument x:Key="in_StPrefixoLog">[in_StPrefixoLog]</InArgument>`.
3. Detect `apply_class: structural`.
4. Cuidado callers que não declaram `in_StPrefixoLog` (top-of-chain): usar literal "".

**Done**: 5 N-3 cascade resolvidos automaticamente. Padrão Sicoob propaga corretamente.

---

### F26 — Layer 2 default-on (CLI flag invertida)
**Esforço**: meio dia | **Valor**: médio | **Risco**: baixo

Hoje: `--analyzer-gate` opt-in. Devs perdem feedback de compile sem decisão consciente.

**Implementação**:
1. `cli.py fix`: trocar `--analyzer-gate` por `--no-analyzer-gate` (opt-out).
2. Default behavior: roda gate se uipcli encontrado; skip silencioso se não.
3. Atualizar README + docstrings.

**Done**: produzir compile-safe by default.

---

### F27 — Layer 2 cache baseline
**Esforço**: 1 dia | **Valor**: médio | **Risco**: zero

Hoje: re-run consecutivos pagam 30-60s baseline cada vez.

**Implementação**:
1. Cachear baseline em `.tmp/analyzer_baseline_<project_hash>.json`.
2. Hash = SHA1(project.json mtime + count XAMLs + max XAML mtime).
3. Hit: load JSON, skip uipcli.
4. Miss: run uipcli, save.
5. Invalidação automática quando project muda.

**Done**: sessions consecutivas instant.

---

### F28 — Per-iteration rollback via Layer 2
**Esforço**: 2 dias | **Valor**: alto | **Risco**: médio

Hoje: gate só REPORTA new errors. Não rollback.

**Implementação**:
1. Pré-iter: snapshot mtimes + bytes de TODOS XAML modificáveis (já temos pre_mtimes em safety.py, ampliar p/ pre_bytes).
2. Pós-iter: run analyzer, diff vs baseline pré-iter.
3. Se new errors: identificar files modificados pelo iter (mtime delta). Reverter bytes.
4. Re-detect → próxima iter (sem fixes responsáveis pelos errors).

**Done**: gate self-healing. Bug em fixer não polui projeto.

**Risco**: analyzer per-iter (não per-fix-run) ainda aceitável: 8 iters × 30s = 4 min. Compromise vs 1 baseline+post (1 min).

---

### F29 — Outros fixers contextual/structural com lxml
**Esforço**: 1 semana | **Valor**: médio | **Risco**: baixo

Padrão N-5 fixer (lxml + walker tag-name-exact + restrictive list mínima + Layer 2 gate) replicável para:
- N-4 refactor args→Dictionary (signatures + propagation).
- N-9 enriquecer LogMessage mensagem mecânica.
- W-2 null guards inline (substituir minha regex VB-rewrite atual).

**Implementação**: caso a caso. Reusar helpers `_FULLTAG_RE`, `_n5_walk_to_element_end`, `_n5_find_immediate_parent_via_lxml`, `_unique_*` helpers.

---

### F30 — Symbol table cross-file
**Esforço**: 1 semana | **Valor**: médio | **Risco**: médio

Hoje: rename refactors usam grep+regex. Quebra em edge cases (variable shadowing, partial match).

**Implementação**:
1. Pré-scan project: build map `{xaml: {variables, args, callees, callers}}`.
2. Lxml-based, parse once por XAML.
3. Cache por SHA1(file content).
4. Fixers de rename consultam tabela ao invés de grep.

**Done**: rename refactors robustos. F25 N-3 declare beneficia.

---

### F31 — Test suite anti-regression contra REF project
**Esforço**: meio dia | **Valor**: alto | **Risco**: zero

**Implementação**:
1. `tests/test_engine_no_regression.py`: roda `cli review` em REF, asserta count baseline (esperado: zero `category=breaking`).
2. CI hook (PR): rodar suite + `--analyzer-gate` em REF.
3. Falha CI se findings novos vs baseline known.

**Done**: regressions caçadas em PR, não em produção.

---

### F32 — Documentar Layer 2 em ARCHITECTURE.md
**Esforço**: 2 horas | **Valor**: alto (onboarding) | **Risco**: zero

ARCHITECTURE.md atual descreve Layer 1 (XML/VB ref↔decl gate). Falta Layer 2.

**Implementação**: adicionar seção:
- "Layer 2 — Studio Analyzer gate"
- discover_uipcli paths (env var, PATH, well-known install)
- Diff-based gate rationale
- Studio version mismatch handling
- Quando usar `--analyzer-gate` (sempre por default após F26)
- `_N5_RESTRICTIVE_PARENT_NAMES` mínimo + heurística `.` + `_COLLECTION_LOCAL_NAMES` + Layer 2 ground truth

---

## Sequência recomendada

```
Concluído: F1-F13, F16, F18, F20

Pendente (todas trigger-driven ou estratégicas):
  F15 custom package (caso real Sicoob)         ← atípico
  F17 multi-version Studio (3d)                 ← migração
  F14 compiler M-5 full type check (1-2 sem)    ← alto esforço
  F19 LLM eval harness (1-2 sem)                ← mede ROI
```

**Estado atual: produção pronta.** Próximas fases dependem de triggers reais.

## Dependências

```
F11 ─┐
F18 ─┴─► F19 (eval precisa baseline + telemetria)
F13 ─────► F20 (viewer fica melhor com labels reais)
F11 ─────► F12 (auto-derive xmlns útil pro fixer M-1 sugestão)
F14 ─────► F19 (eval valida ganho compiler)
```

## Como retomar este plano após interrupção

1. **Primeiro**: rodar bloco "Métricas vivas" no topo. Confirma sistema funcional.
2. **Identificar fase em andamento**: olhar TaskList Claude Code OU últimos commits/edits em arquivos relevantes.
3. **Cada fase tem subseção "Como retomar"** com pista do código + arquivos a modificar.
4. **Atualizar este ROADMAP** ao concluir cada fase: marcar concluído, mover para "Histórico", recompute "Plano em aberto".

## Convenções

- Cada fase nova: criar entrada com Esforço/Valor/Risco + Implementação + Done + Como retomar
- Pattern testes: `tests/test_heuristic_activity_meta.py` para M-*; `tests/test_fixers.py` para fixers
- Pattern fixtures: `tests/fixtures/activity_meta/{ok|bad}_<scenario>.xaml`
- Sempre rodar `pytest -q` + REF check antes commit
- ROADMAP commit junto com mudanças da fase

## Riscos transversais

1. **Schema drift**: UiPath atualiza package, schema fica stale. Mitigação: F18 tracking + lembrete README
2. **Performance degradar**: F12 fixer cascade, F14 compiler. Mitigar via F16
3. **Tests REF regressão**: 236 tests + REF review zero M-*. Cada PR roda ambos
4. **OneDrive sync size**: assets atual 1.76MB. F13 +PT-BR ~3MB. F17 multi-version × 3 versões ~10MB. Aceitável.
