# HANDOFF — Studio Oracle Integration + Engine Professionalization

**Criado:** 2026-05-22
**Contexto:** sessão pós-resolução incidente `contestacao-fraude-bc-errors` (ver `.uip-toolchain/.docs/incidents/contestacao-fraude-bc-errors.md`)
**Audiência:** próxima sessão Claude (limpa, sem contexto da conversa anterior)

---

## Executive summary

Engine rule_engine atualmente opera por **hipóteses + tentativa-erro** pra produzir fixes mecânicos em XAMLs UiPath migrados Legacy→Windows. Workflow real:
1. Engine roda regras (W-11g, W-19, ENV-2, ENV-3, ENV-4, W-31, W-32, etc)
2. Usuário abre Studio
3. Studio aponta BC errors restantes
4. Sessão diagnóstica + propõe nova regra
5. Loop

Esse ciclo gerou 4 rounds errados de hipóteses (W-26 strip → ENV-2 ensure → W-11g insert → ENV-4 normalize). **Real root cause** (legacy `<mva:VisualBasic.Settings>` text-content) só foi descoberta quando usuário rodou Studio "Import References" auto-fix manualmente e nós fizemos diff.

**Mudança proposta:** incorporar Studio "Import References" mechanism DIRETAMENTE no engine como **canonical oracle**. Engine atual permanece como fallback + telemetria de drift.

---

## Estado atual engine (HEAD = local commit pós-1974b86 + ENV-4 changes não-commitadas)

### Regras implementadas hoje (2026-05-22 sessão):
- **ENV-4** (`detect_env4_normalize_vb_settings` + `apply_normalize_visualbasic_settings`): normaliza `<mva:VisualBasic.Settings>text</...>` → `<VisualBasic.Settings><x:Null/></VisualBasic.Settings>` + drop xmlns:mva se unused. **CRÍTICO — fixou BC30652/BC31424 root cause.**
- **W-31** (`detect_unused_legacy_facade_refs`): usage-guarded strip de `{OfficeDevPnP.Core, System.Configuration.Install, System.Data.Entity, UiPathTeam.SharePoint, UiPath.Word}`.
- **W-32** (`detect_obsolete_dotnet4_refs`): strip `{System.Runtime.WindowsRuntime}` (.NET 4-only facade, Studio XamlMigration log redundante).
- **W-11y baseline_refs**: adicionados 3 BCL .NET 6: `System.Memory.Data`, `System.Runtime.CompilerServices.Unsafe`, `System.Threading.Tasks.Extensions`.

### Tests adicionados:
- `tests/test_env4_visualbasic_settings.py` (12/12 PASS)
- ENV-1/2/3 tests pré-existentes (43/43 total ENV tests PASS)

### NÃO commitado ainda:
Tudo acima está working tree. Status branch `main` ahead origin/main por 1 commit (`1974b86 Add ENV-1/2/3 rules`) + working tree changes (ENV-4 + W-31 + W-32 + W-11y).

### Bugs cosméticos pendentes:
- `strip_assembly_reference` deixa blank lines residuais quando múltiplos strips consecutivos (W-31 strippa 5 refs adjacentes). Studio normaliza no save. TODO: consume blanks no fixer.

### Pipeline run validado em target:
- Path: `C:\Users\lisan\Desktop\temp\contestacao-de-compras-ajuste-na-reserva-de-fraude-performer`
- Result: 112 fixes aplicados em 2 iters fixpoint, 0 regressions, exit=PENDING_REVIEW (apenas 24 contextual pré-existentes não-blocking)
- Studio compile validation: pendente confirmação usuário (esperado BC30652 + BC31424 = 0)

---

## Plano fase-a-fase

### Fase 0 — Cleanup + commit estado atual (próxima sessão, primeira ação)

**Objetivo:** branch `main` limpa antes de qualquer mudança arquitetural.

**Steps:**
1. `git status` — confirmar working tree changes (rules.yaml, fixers.py, heuristics/legacy_refs.py, tests/test_env4_*.py)
2. Run full test suite: `cd .uip-toolchain && python -m pytest -x` (deve passar 100%)
3. Lint check rules.yaml: `python -m uip_engine.cli validate rules.yaml`
4. Commit message sugerido:
   ```
   feat(engine): ENV-4 normalize VisualBasic.Settings + W-31/W-32 ref cleanup

   ROOT CAUSE BC30652/BC31424 isolated empiricamente (2026-05-22):
   - <mva:VisualBasic.Settings>text</...> ativa VB compiler legacy mode
   - Replace com canonical <VisualBasic.Settings><x:Null/></...> → BC clears
   - Studio "Import References" auto-fix valida mecanismo

   Mudanças:
   - ENV-4: detect + fix VB.Settings legacy text-content + drop xmlns:mva unused
   - W-31: usage-guarded strip legacy facade refs (OfficeDevPnP.Core etc)
   - W-32: strip System.Runtime.WindowsRuntime (.NET 4-only)
   - W-11y baseline: +3 BCL .NET 6 (Memory.Data, CompilerServices.Unsafe, Tasks.Extensions)
   - 12 novos tests test_env4_visualbasic_settings.py
   - Incident doc .docs/incidents/contestacao-fraude-bc-errors.md
   - Handoff doc .docs/HANDOFF_STUDIO_ORACLE.md
   ```
5. Push branch (uso `GH_TOKEN=$GH_TOKEN_MUCUNFO`).
6. Abrir PR contra `main`. Aguardar CI Windows passar. **NÃO merge sem CI green.**

---

### Fase 1 — Spike Studio integration via pythonnet (3-5 dias)

**Objetivo:** validar empíricamente que dá pra invocar `ImportReferencesCommand` do Studio via Python.

**Setup:**
1. `pip install pythonnet` no env Python da engine
2. Inspecionar assemblies Studio em `C:\Users\lisan\AppData\Local\Programs\UiPathPlatform\Studio\<version>\`:
   - `UiPath.Studio.Workflow.dll`
   - `UiPath.Studio.Workflow.Activities.dll`
   - `UiPath.Studio.WorkflowDesigner.dll`
3. Identificar internal type que executa "Import References":
   - Likely: `UiPath.Studio.Workflow.Designers.WorkflowDesignerHost.ImportReferences()`
   - Ou: `UiPath.Studio.Plugin.Workflow.Services.ReferenceImporter`
   - Usar dotPeek/ILSpy pra descobrir o entry point real (free tools)

**Spike code (1 XAML test):**
```python
# spike/studio_import_refs_spike.py
import clr
import sys

STUDIO_PATH = r"C:\Users\lisan\AppData\Local\Programs\UiPathPlatform\Studio\26.0.193-cloud.23060"
sys.path.append(STUDIO_PATH)

clr.AddReference("UiPath.Studio.Workflow")
clr.AddReference("System.Activities")

from UiPath.Studio.Workflow import WorkflowDesigner  # exact namespace TBD via ILSpy

def studio_import_references(xaml_path: str) -> str:
    """Invoke Studio's Import References on XAML. Returns canonical XAML."""
    designer = WorkflowDesigner.Load(xaml_path)
    designer.ImportReferences()  # API name TBD
    return designer.Serialize()

if __name__ == "__main__":
    canonical = studio_import_references(sys.argv[1])
    print(canonical)
```

**Validação:**
- Rodar spike em `RetryCurrentTransaction.xaml` pre-fix (cópia em `.tmp/RetryCurrentTransaction.pre-studio.xaml`).
- Comparar output spike vs `Projects/contestacao-de-compras-ajuste-na-reserva-de-fraude/.../RetryCurrentTransaction.xaml` (Studio UI fix output).
- **Critério sucesso:** diff vazio (ou apenas cosmético — whitespace/alphabetization).

**Riscos do spike:**
- Studio assemblies podem requerer COM apartment threading → pythonnet exige `[STAThread]` setup
- WorkflowDesigner UI components → headless WPF needed (`System.Threading.Thread.SetApartmentState(ApartmentState.STA)`)
- License: uso interno OK, redistribuição = revisar licença UiPath Enterprise
- Studio version drift: API interna sem garantia de estabilidade

**Output Fase 1:**
- `spike/studio_import_refs_spike.py` working
- `.docs/STUDIO_API_NOTES.md` documentando API real descoberta (namespace, classes, methods)
- Decisão go/no-go Fase 2 baseado em estabilidade do spike

---

### Fase 2 — Production integration `phase1_5_studio_oracle` (1-2 semanas)

**Pré-requisito:** Fase 1 spike funcional.

**Arquitetura:**

Adicionar PHASE 1.5 no pipeline `cli all` (entre PHASE 1 deterministic engine fixes e PHASE 2 review):

```
PHASE 0  migration (Activity Migrator se tf != Windows)
PHASE 1  deterministic engine rules (atual)
PHASE 1.5  Studio oracle dispatch:    ← NOVA
           if studio_available:
               studio_import_references(each xaml)
               capture diff vs engine output
               emit telemetry "studio_drift" events
           else:
               log warn "Studio unavailable; engine rules best-effort"
PHASE 2  review + gates (analyzer + pack)
PHASE 3  contextual
PHASE 4  decisão
```

**Decisão chave:** Studio oracle é AUTHORITATIVE (sobrescreve engine output) OU é VERIFICATION (só compara + reporta drift)?

Recomendação: **AUTHORITATIVE em produção, VERIFICATION em modo `--engine-only`** (debug + CI lite).

**Implementação:**
1. `src/uip_engine/studio_oracle.py` — wrapper pythonnet
   - `class StudioOracle`: discover_studio(), load_workflow(), import_references(), serialize()
   - `available() -> bool` — feature detection
2. `src/uip_engine/cli.py` — adicionar `_phase1_5_studio_oracle(project)` no loop iterativo de `cmd_all`
3. Env var `UIP_TOOLCHAIN_DISABLE_STUDIO_ORACLE=1` pra opt-out (CI lite, debug)
4. Telemetria: cada drift event vai pra `.uip-toolchain/.tmp/telemetry/studio_drift_<date>.jsonl`
5. Tests: `tests/test_studio_oracle.py` — mock + real (skip se Studio unavailable)

**CI handling:**
- `.github/workflows/ci.yml` já roda em `windows-latest`. Adicionar step que instala Studio em runner OR usa pre-baked image. Custos:
  - Studio install é ~2GB + 3-5min boot
  - Microsoft hosted runner timeout 6h ok
  - Alternativa: self-hosted runner com Studio pré-instalado (Windows VM Azure)
- Se CI sem Studio = engine roda em modo VERIFICATION (alerta drift) sem fail. Production = AUTHORITATIVE.

**Migration de regras existentes:**
- ENV-4, W-11g, W-19, W-31, W-32, W-11y, ENV-2, ENV-3 continuam existindo MAS marcadas `provenance.replaceable_by_studio_oracle: true`
- Se Studio oracle confirma fix correto, engine rules atuam como **redundância safety net** + visibility (Studio é black box)
- Se Studio oracle diverge de regras engine → emit `RULE_DRIFT` finding → human review

---

### Fase 3 — Golden corpus regression (1 semana)

**Objetivo:** todo incident vira test case automatizado.

**Estrutura:**
```
.uip-toolchain/.golden/
  contestacao-fraude/
    pre/                       # XAML pre-fix snapshot (immutable)
    studio_canonical/          # XAML pós Studio Import References (oracle ground truth)
    engine_expected/           # XAML pós engine rules (deve ser igual a studio_canonical modulo cosmetic)
    metadata.json              # incident link, dates, Studio version
    test_assertions.yaml       # cosmetic-allowed diffs, etc
  solicitacao-acessos/         # working ref usado pra diffs comparativos
    canonical/
  <novo-incident>/...
```

**Test runner:**
```python
# tests/test_golden_corpus.py
@pytest.mark.parametrize("incident", discover_golden_incidents())
def test_engine_matches_studio_oracle(incident):
    pre = load_xaml(f".golden/{incident}/pre/")
    expected = load_xaml(f".golden/{incident}/studio_canonical/")
    actual = run_engine_pipeline(pre)
    assert_xaml_semantically_equal(actual, expected,
                                    allow_cosmetic=True)
```

**Workflow novo incident:**
1. Engine reporta BC error → user roda Studio fix
2. Comando helper: `uip-capture-incident <incident-name> <project-pre> <project-studio-fixed>`
3. Helper copia XAMLs pre + post pra `.golden/<incident-name>/`
4. Gera test case template
5. Engine vê test failing → developer implementa rule
6. Test passa → PR

---

### Fase 4 — Provenance + governance (ongoing)

**Schema YAML extension:**
```yaml
- id: ENV-4
  severity: ERROR
  category: breaking
  target: windows
  provenance:                                    # NOVO obrigatório
    incident: contestacao-fraude-bc-errors.md
    studio_oracle_validated: 2026-05-22
    studio_version_tested: ["23.10.13", "25.10.x", "26.0.193"]
    working_ref_diff: solicitacao-acessos-sisbr-arquivo-xml-performer
    deprecates: []                                # rules erradas substituídas
    replaceable_by_studio_oracle: true            # Studio faz mesma coisa
  ...
```

**Loader enforcement:**
- `loader.py` valida `provenance` field obrigatório
- Boot warn se rule sem `provenance.incident` link existente
- `RULE_INDEX.md` auto-gerado por `scripts/gen_rule_index.py`

**Deprecation policy `.docs/DEPRECATION_POLICY.md`:**
- Rule wrong hypothesis (W-26 case): provenance `deprecated_at: <date>, reason: <empirical evidence>, replaced_by: <new-rule>`
- 30 dias migration period emit WARN
- Delete + test migration entry no CHANGELOG

---

### Fase 5 — Boot self-audit (1-2 dias)

CLI command `python -m uip_engine.cli doctor`:
```
=== Engine Self-Audit ===
Rules total:          270
With provenance:      52 / 270   ← rest ainda precisa retroactive provenance
With test coverage:   180 / 270
Studio-oracle-redundant: 24 / 270
Deterministic w/o idempotency test: 8 (WARN)
Schema errors:        0
Provenance broken links: 3 (rule-id → missing incident file)
```

Boot CLI emit summary line:
```
[ENGINE BOOT] 270 rules / 180 tested / 52 provenance / Studio oracle: AVAILABLE
```

---

### Fase 6 — Documentation + onboarding (ongoing)

**`.docs/ARCHITECTURE.md`** atualizar com:
- PHASE 1.5 Studio oracle dispatch diagram
- Engine philosophy: "Studio is canonical oracle. Engine rules are mechanical replicators + redundancy safety net."
- Decision tree: when to add engine rule vs trust Studio oracle vs both

**`.docs/INCIDENT_PLAYBOOK.md`** create:
- Step-by-step pra qualquer BC error
- Pre-snapshot → Studio fix → diff capture → rule extract → test → PR
- Templates incident doc + golden corpus entry

**`.docs/RULE_AUTHORING.md`** create:
- TDD discipline
- Provenance requirements
- Naming convention (ENV-N policy/env, W-NN cleanup, D-N pin, etc)
- Apply class semantics (deterministic vs contextual vs structural)

**README.md** at repo root:
- Quick start
- `uip` god command usage
- Studio oracle setup
- CI integration

---

## Riscos + mitigações

| Risco | Mitigação |
|---|---|
| Studio pythonnet API instável entre versões | Wrapper isola: 1 file `studio_oracle.py` muda; resto engine intacto. Version-dispatch interno. |
| License redistribuição Studio assemblies | Uso interno (Sicoob org) → OK. Distribuição pública = fork sem Studio integration, ENV-4/W-31/etc continuam funcionais standalone. |
| Studio install em CI custoso | Self-hosted runner Windows VM com Studio pré-instalado. Alternativa: cache image GitHub Actions. |
| Engine rules ficam stale se Studio oracle prevalece | Engine rules ATIVAS como redundancy + drift detection. Rule deprecação só após evidence empírica multi-incident. |
| Pythonnet performance overhead | Lazy load Studio assemblies (só se PHASE 1.5 dispatched). Cache WorkflowDesigner instance per session. |

---

## Open questions (decisão necessária)

1. **Studio oracle = AUTHORITATIVE ou VERIFICATION?** Recomendação: AUTHORITATIVE prod, VERIFICATION debug. User decide.
2. **CI strategy**: self-hosted runner ou pre-baked image? Custo + complexidade trade-off.
3. **Deprecation timeline regras existentes**: imediato após Studio oracle stable? Ou indefinido (mantém ambas)?
4. **Telemetria drift events**: local jsonl ou push pra observability backend Sicoob?
5. **CCS_* libs Sicoob** (CCS_Controle, CCS_SipagDirect, CCS_SipagNet) — Studio oracle entende custom activity refs? Spike precisa testar.

---

## Arquivos relevantes referência

- `.docs/incidents/contestacao-fraude-bc-errors.md` — incident origem desta sessão (Tentativas 1-6 documentadas)
- `src/uip_engine/heuristics/legacy_refs.py` — ENV-2, ENV-3, ENV-4, W-31, W-32 detectors
- `src/uip_engine/fixers.py` — normalize_visualbasic_settings (linha ~3093), insert_assembly_reference (linha ~2916), strip_assembly_reference (linha ~3093+wrap)
- `rules.yaml` — ENV-4 definição (busca `^  - id: ENV-4`)
- `tests/test_env4_visualbasic_settings.py` — 12 tests passando
- `.tmp/target_uip_run_v2.log` — last run output (referência)
- `.tmp/target_post_review.json` — last engine review state
- `C:\Users\lisan\OneDrive - Sicoob\UiPath\` — Studio logs (Project, Analyzer, Studio.log)
- `C:\Users\lisan\OneDrive - Sicoob\output.txt` — Studio compile output snapshot

## Próxima sessão — primeira ação

1. Ler este HANDOFF + incident doc + git log -10
2. Confirmar working tree state (`git status`)
3. Executar Fase 0 (commit + PR)
4. Após CI green merge → iniciar Fase 1 spike Studio integration
5. Apenas DEPOIS de Fase 0 estável + Fase 1 spike validado, mover Fase 2

**NÃO pular Fase 0.** Commit pendente é prerequisito.

---

## Update — Fase 0 + Fase 1 concluídos (2026-05-22 PM)

**Fase 0 — MERGED to main:**
- PR #11: ENV-1..4 rules + W-31/W-32 ref cleanup + W-11y baseline (1907482)
- PR #12: hook timeout 60→180s (4e2f7b6)
- PR #13: analyzer-gate verbose log NameError fix (b370c17)
- Studio compile validation: PACK-GATE exit 0, BC30652=0 + BC31424=0 ✓
- 25 errors restantes em target = pre-existing contextual/structural debt
  (CX-2/CX-4/EXC-1/UI-1/W-13/ENV-1), out-of-scope

**Fase 1 — Spike concluído, Fase 2 PAUSADA:**
- pythonnet + coreclr boot validado em Studio 26.0 (net8.0) e 23.10 (net6.0)
- API map completa descoberta — ver `.docs/STUDIO_API_NOTES.md`
- API drift detected entre 23.10 e 26.0 (XamlMigrationProjectEndpoint ctor
  signature: 1 param vs 2 params). Studio internal API NOT stable.
- D-1 pin (Sicoob = 23.10 imutável) mitiga drift risk
- Custo Fase 2 estimado: ~2 semanas + manutenção drift contínua
- Decision (user 2026-05-22): pause Fase 2. Engine atual cobre 100% incident.
  Studio = out-of-band manual oracle quando precisar.
- Spike artifacts preservados em `spike/` para reuso futuro

---

## Glossário decisões empíricas

- **Studio 23.10 = deploy Sicoob imutável** (D-1 pins enforcement)
- **`<mva:VisualBasic.Settings>` text-content = ROOT CAUSE legacy mode** (ENV-4)
- **mscorlib/System/System.Core como AssemblyReference body = bridge forwarders** (ENV-2 ensure, NÃO strip — W-26 errado)
- **`<x:Null />` em VisualBasic.Settings = modern empty marker** (canonical .NET 6)
- **3 BCL .NET 6 refs essenciais** = System.Memory.Data + System.Runtime.CompilerServices.Unsafe + System.Threading.Tasks.Extensions (W-11y baseline)
- **Engine = mechanical replicator, Studio = oracle** (filosofia pós-Tentativa 5)

## Fora de escopo desta refatoração

- Refactor estrutural (CX-2 nesting depth, CX-4 activity count, CX-5 god workflow) — débito Sipag_Net contextual, **não** causado pela engine
- Análise UIA pinning policy (D-1 enforcement) — separado de Studio oracle integration
- N-5 LogMessage rastreabilidade — contextual classe, opt-in via --apply-contextual
- Activity Migrator behavior (PHASE 0) — externo, fora controle engine
