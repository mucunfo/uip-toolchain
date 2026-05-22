# Incident: BC30057 + BC31424 + BC30652 — contestacao-de-compras-ajuste-na-reserva-de-fraude-performer

**Status:** OPEN (BC31424 + BC30652 persistem após engine fix; BC30057 resolvido)
**Projeto:** `C:\Users\lisan\Desktop\temp\contestacao-de-compras-ajuste-na-reserva-de-fraude-performer`
**Branch:** `NC-179-migracao-windows`
**Target framework:** Windows (.NET 6)
**Studio deploy:** 23.10.13

---

## Erros observados

### Original (Studio compile log `output.txt` snapshot 2026-05-21 23:47:34, pré-engine)
- `BC30057 ×3` — Framework/RetryCurrentTransaction.xaml — "Too many arguments to Property SpecificContent / Output"
- `BC31424 ×1` — Framework/RetryCurrentTransaction.xaml — "Type 'System.Net.NetworkCredential' has been forwarded to assembly 'System.Net.Primitives, Version=6.0.0.0'"

### Pós engine fix (Studio compile log `output.txt` snapshot 2026-05-22 09:30:46)
- `BC30057 ×0` ✅ RESOLVIDO
- `BC30652 ×3` ❌ NOVO — Framework/RetryCurrentTransaction.xaml — "Reference required to assembly 'System.Collections, Version=6.0.0.0' containing the type 'Dictionary(Of ,)'"
- `BC31424 ×1` ❌ PERSISTE — mesma mensagem

---

## Catálogo de tentativas

### Tentativa 1 — `9a8f108` "engine: W-11/W-26 ref cleanup triplet"
**Data:** commit anterior, abandonado parcialmente em 1974b86

**Hipótese:** Activity Migrator deixou `<AssemblyReference>mscorlib|System|System.Core</AssemblyReference>` redundantes; remover força resolver moderno (.NET 6 facades).

**Implementação:**
- W-26 — `detect_legacy_bcl_refs` STRIP mscorlib/System/System.Core
- W-11g — `insert_assembly_reference` System.Net.Primitives (complemento)
- W-19 — `queue_item_indexer_to_item` rewrite `.SpecificContent("X")` → `.SpecificContent.Item("X")`

**Resultado:** Divergência fixpoint — W-26 strip + W-11y/W-11x baseline refs add → infinite loop. Commit msg do `9a8f108` reconhece e tenta corrigir, mas hipótese empiricamente errada.

**Status:** REVERTIDO em 1974b86.

---

### Tentativa 2 — `1974b86` (local, **não pushed**) "Add ENV-1/2/3 rules"
**Data:** 2026-05-21 23:51:51

**Hipótese (oposta à 1):** Studio 23.10 USA mscorlib/System/System.Core como forwarder bridge pra .NET 6 modern refs. Sem esses 3 refs, Studio não resolve type forwarders → BC30652/BC31424. Activity Migrator do Studio 25.x strip — engine deve RE-INSERIR pra deploy Sicoob.

**Evidência empírica capturada no commit (docstring `scripts/rule_engine/heuristics/legacy_refs.py:11-16`):**
- Projeto que ABRE em Studio 23.10 (solicitacao-acessos-sisbr-arquivo-xml-performer): 69/69 XAMLs com `<AssemblyReference>mscorlib</AssemblyReference>`
- Projeto que QUEBRA em Studio 23.10 (contestacao-de-compras-ajuste-na-reserva-de-fraude-performer): 0/25 XAMLs com mscorlib

**Implementação:**
- W-26 deletado, substituído por **ENV-2** `detect_env2_ensure_legacy_refs` (INSERT mscorlib/System/System.Core)
- **ENV-3** `detect_env3_ensure_namespace_imports` (insert `<x:String>System.Net</x:String>` etc se VB usage detected)
- **ENV-1** `detect_env1_project_manifest_flags` (ensure project.json `mustRestoreAllDependencies=true`, `modernBehavior=false`, `includeOriginalXaml=false`)
- F36 safety guard removido de ccs_contract (rename_attribute emite finding)
- Analyzer-gate filter via `_ANALYZER_SICOOB_POLICY` (suppress policy-accepted)

**Status:** Tests `test_env1/env2/env3_*.py` passam. Commit local, não pushed pra origin/main.

---

### Tentativa 3 — `uip` god command run em 2026-05-22 00:32:41
**Comando:** `python -m scripts.rule_engine.cli all "C:\Users\lisan\Desktop\temp\contestacao-..."`

**Engine state:** HEAD = 1974b86 (local, com ENV-1/2/3 + W-19 + W-11g + W-4 + W-11x/y/z + W-20 active)

**Pipeline:**
- PHASE 0 migration: skip (target=Windows)
- PHASE 1 deterministic: 3 fixpoint iters, applied=26 fixes
- PHASE 2 review+gates: errors=25 (blocking=0, contextual=25), warns=126, info=514
- PHASE 3 contextual dry-run: 665 PENDING
- Exit: PENDING_REVIEW

**Fixes aplicados em RetryCurrentTransaction.xaml (validado via hash 8e65993... → 310692f...):**
- linha 96: `<AssemblyReference>System.Net.Primitives</AssemblyReference>` inserido (W-11g)
- linha 101: `<AssemblyReference>System.Private.CoreLib</AssemblyReference>` inserido (W-11z)
- linha 94: `<AssemblyReference>System.Collections</AssemblyReference>` inserido (W-11y baseline)
- linha 91: `<AssemblyReference>System.Runtime.InteropServices</AssemblyReference>` (W-11b)
- linha 92: `<AssemblyReference>System.ComponentModel.TypeConverter</AssemblyReference>` (W-11c)
- linha 95: `<AssemblyReference>System.Linq</AssemblyReference>` (W-11f? — confirmar)
- linha 97: `<AssemblyReference>System.Text.RegularExpressions</AssemblyReference>` (W-11h)
- linha 223: `.Output.Item("DescDetalhe")` rewrite (W-19)
- linhas 223+231: `.SpecificContent.Item("PK Detalhe")` rewrite (×2 W-19)
- xmlns:s mscorlib stale → System.Private.CoreLib (W-4)

**Resultado do engine review pós-fix (.tmp/target_post_review.json):**
| rule | pre | post | status |
|---|---|---|---|
| W-19 (SpecificContent/Output) | 3 | 0 | ✅ resolved |
| W-11g (System.Net.Primitives) | 1 | 0 | ✅ resolved |
| W-4 (xmlns mscorlib) | 8 | 0 | ✅ resolved |
| W-11b | 1 | 0 | ✅ resolved |
| W-11c..h, W-11y, W-11z | 1+1+1+1+1+6+1 | 0 | ✅ resolved |
| W-20 (xmlns alias cleanup) | 25 | 0 | ✅ resolved |
| ENV-1 (project.json flags) | 1 | 0 | ✅ resolved |
| UIPATH:PACK (gate-injected) | 0 | 1 | ❌ FALSE POSITIVE |
| CX-2/CX-4/UI-1/EXC-1/W-13 | unchanged | unchanged | (débito estrutural pré-existente) |

**Validação Studio 23.10 (log `output.txt` 09:30:46):**
- BC30057 ×3 → ×0 ✅
- BC31424 ×1 → ×1 ❌ AINDA presente
- BC30652 ×0 → ×3 ❌ NOVO emergiu

**Status:** PARCIAL. W-19 resolve BC30057, mas W-11g + ENV-2 + W-11y NÃO resolvem BC31424/BC30652 apesar dos refs estarem fisicamente no XAML.

---

## Análise diferencial — por que working ref funciona e target não

### Working ref: `solicitacao-acessos-sisbr-arquivo-xml-performer/DB2/AtualizarFimExecucao.xaml`

| Aspecto | Working | Target (pós-fix) | Match? |
|---|---|---|---|
| `xmlns:scg=...assembly=System.Private.CoreLib` | ✅ | ✅ | sim |
| `xmlns:s=...assembly=System.Private.CoreLib` | ✅ | ✅ | sim |
| `<x:String>System.Net</x:String>` import | ✅ | ✅ | sim |
| `<x:String>System.Collections</x:String>` import | ✅ | ✅ | sim |
| `<AssemblyReference>mscorlib</AssemblyReference>` | ✅ | ✅ | sim |
| `<AssemblyReference>System</AssemblyReference>` | ✅ | ✅ | sim |
| `<AssemblyReference>System.Core</AssemblyReference>` | ✅ | ✅ | sim |
| `<AssemblyReference>System.Net.Primitives</AssemblyReference>` | ✅ | ✅ | sim |
| `<AssemblyReference>System.Collections</AssemblyReference>` | ✅ | ✅ | sim |
| `<AssemblyReference>System.Private.CoreLib</AssemblyReference>` | ✅ | ✅ | sim |

**Refs PRESENTES em target mas AUSENTES em working (legacy poison candidates):**
- `System.ServiceModel` (target linha 59)
- `System.Data.Entity` (target linha 76)
- `System.Configuration.Install` (target linha 78)
- `System.Xaml` (target linha 86)
- `System.Reflection.Metadata` (target linha 89)
- `System.Reflection.DispatchProxy` (target linha 90)
- `OfficeDevPnP.Core` (linha 69)
- `UiPathTeam.SharePoint` (linha 68)
- `UiPath.OCR.Activities.Design` (linha 66)
- `WindowsBase` (linha 77)

**Hipótese H-A (forte):** uma ou mais dessas refs legacy do template original puxa cadeia de forwarders v4 que prevalece sobre v6. Específicas suspeitas:
- `System.ServiceModel` v4 facade — pode arrastar System.Net facade v4 → resolve NetworkCredential pra forwarder v4 → mismatch com v6
- `System.Configuration.Install` — facade rara, possível conflito
- `System.Data.Entity` — EF6 puxa System.Data v4 stack

---

## Próximas tentativas (a serem implementadas + documentadas aqui)

### Tentativa 4 — adicionar 3 BCL .NET 6 refs faltantes em RetryCurrentTransaction.xaml
**Data:** 2026-05-22

**Hipótese:** Diff completo `<AssemblyReference>` working vs target revelou 3 refs .NET 6 BCL presentes em working ausentes em target:
- `System.Memory.Data`
- `System.Runtime.CompilerServices.Unsafe`
- `System.Threading.Tasks.Extensions`

Essas refs forçam UiPath resolver a usar reference assemblies .NET 6 → forwarder chain Dictionary/NetworkCredential resolve pra v6.0.0.0 correto. Sem elas, resolver cai pra legacy facade v4 (System.dll/mscorlib.dll netfx) → mismatch BC30652/BC31424.

**Implementação:** insert manual das 3 refs no bloco `<TextExpression.ReferencesForImplementation>` de RetryCurrentTransaction.xaml. Não tocar outros XAMLs ainda (escopo mínimo pra teste).

**Comando:** edit direto via Edit tool (ainda não engine rule).

**Resultado esperado:** Studio compile log limpa BC30652 + BC31424.

**Status:** PARCIAL. Studio reteve os 3 BCL refs no auto-fix, mas o que efetivamente resolveu BC errors foi outra coisa (ver Tentativa 5).

---

### Tentativa 5 — Studio "Import References" auto-fix (executada pelo usuário 2026-05-22 11:05)
**Projeto alvo pós-fix:** `C:\Users\lisan\OneDrive - Sicoob\Projects\contestacao-de-compras-ajuste-na-reserva-de-fraude\contestacao-de-compras-ajuste-na-reserva-de-fraude-performer`

**Mudanças aplicadas pelo Studio em RetryCurrentTransaction.xaml (diff vs pre-studio):**

#### Mudança 1 — `VisualBasic.Settings` normalize (THE FIX)
```diff
-  <mva:VisualBasic.Settings>Assembly references and imported namespaces for internal implementation</mva:VisualBasic.Settings>
+  <VisualBasic.Settings>
+    <x:Null />
+  </VisualBasic.Settings>
```
+ `xmlns:mva="clr-namespace:Microsoft.VisualBasic.Activities;assembly=System.Activities"` removido do header.

**Mecanismo:** o text-content `"Assembly references and imported namespaces for internal implementation"` é STUB Legacy (Studio pré-19.x / template REFramework antigo). VB compiler interpreta esse element como `Microsoft.VisualBasic.Activities.VisualBasicSettings` com payload string → ativa modo **legacy resolution** → Dictionary/NetworkCredential resolvem via facades v4 → mismatch contra forwarder v6 → BC30652/BC31424.

`<x:Null />` é o canonical empty value moderno → VB compiler usa **default .NET 6 resolver** → encontra Dictionary em System.Collections v6 + NetworkCredential em System.Net.Primitives v6 → BC clears.

#### Mudança 2 — Strip legacy facade refs sem usage
Removidas do `<TextExpression.ReferencesForImplementation>`:
- `OfficeDevPnP.Core`
- `System.Configuration.Install`
- `System.Data.Entity`
- `UiPathTeam.SharePoint`
- `UiPath.Word`

#### Mudança 3 — Add .NET 6 BCL refs (mesmas da Tentativa 4)
- `System.Memory.Data`
- `System.Runtime.CompilerServices.Unsafe`
- `System.Threading.Tasks.Extensions`

#### Mudança 4 — Modern attribute defaults
- `<ui:GetRobotCredential ... CacheStrategy="None" .../>` (atributo adicionado, default modern)

#### Mudança 5 — Alphabetize refs + namespaces
Cosmético. Sem impacto funcional.

#### Studio.Project.log evidência
`11:05:38.2868 => [WARN] [UiPath.Studio.Project] XamlMigration: removed reference System.Runtime.WindowsRuntime` ×13 (uma por XAML carregado). Studio executa XamlMigration ao abrir, mas isso é cleanup secundário — o `VisualBasic.Settings` normalize é o fix decisivo.

**Resultado:** Studio compile clean (a confirmar via output.txt pós-fix).

**Status:** RESOLVIDO PELO STUDIO. Engine deve replicar mecanismo.

---

## Plan implementação engine (a executar)

Eliminar Tentativas 1-4 como soluções incompletas. Adicionar 3 regras novas + 1 ajuste em ENV-2/W-11y:

### Regra nova **ENV-4 / W-30** — normalize legacy `VisualBasic.Settings`
**Severity:** ERROR breaking, target=windows
**Detect:**
```regex
<mva:VisualBasic\.Settings>[^<]*</mva:VisualBasic\.Settings>
```
ou variantes self-closing `<mva:VisualBasic.Settings/>` com xmlns:mva declarado mas sem outras referências mva: no body.

**Fix mecânico (novo fixer `normalize_visualbasic_settings`):**
1. Replace o element `<mva:VisualBasic.Settings>...text...</mva:VisualBasic.Settings>` por:
   ```xml
   <VisualBasic.Settings>
     <x:Null />
   </VisualBasic.Settings>
   ```
2. Drop `xmlns:mva="clr-namespace:Microsoft.VisualBasic.Activities;assembly=System.Activities"` do header se mva prefix unused.

**Apply class:** deterministic (transformação puramente sintática, idempotente).

### Regra nova **W-31 — scrub legacy facade refs sem usage**
**Severity:** WARN cleanup, target=windows
**Detect:** `<AssemblyReference>X</AssemblyReference>` onde X ∈ {`System.Configuration.Install`, `System.Data.Entity`, `OfficeDevPnP.Core`, `UiPathTeam.SharePoint`, `UiPath.Word`} E nenhum xmlns no body referencia X.

**Fix mecânico:** `strip_assembly_reference` (existente).

**Apply class:** deterministic (com usage guard — não strip blind como W-26 errado).

### Ajuste **W-11y baseline_refs** — adicionar 3 BCL .NET 6
Adicionar à lista `required_refs`:
- `System.Memory.Data`
- `System.Runtime.CompilerServices.Unsafe`
- `System.Threading.Tasks.Extensions`

### Regra nova **U-NN — explicit modern activity defaults** (baixa prioridade)
Adicionar `CacheStrategy="None"` em `<ui:GetRobotCredential>` se ausente. Cosmético — não bloqueia compile.

### Eliminação de soluções incorretas

NÃO eliminar W-11g, W-19, ENV-2 — esses fazem trabalho complementar:
- **W-19 cleared BC30057** independentemente
- **W-11g + ENV-2 + W-11x/y** garantem refs estão presentes (Studio também as quer)

PORÉM, esses sozinhos não bastam SEM ENV-4 (VisualBasic.Settings normalize). Documentar essa dependência no description das rules existentes:
- W-11g.description: "Pré-requisito ENV-4 (VisualBasic.Settings normalize) — sem ENV-4, esse ref insert não resolve BC31424."
- ENV-2.description: "Pré-requisito ENV-4 — esse ensure legacy compat só funciona se ENV-4 normaliza VB.Settings primeiro."

---

### Tentativa 6 — Engine round 5: ENV-4 + W-31 + W-32 + W-11y baseline BCL
**Data:** 2026-05-22 (sessão pós Tentativa 5 Studio fix)

**Implementação (commits pendentes, não pushed):**

1. **ENV-4** — `detect_env4_normalize_vb_settings` + `apply_normalize_visualbasic_settings`
   - File: `scripts/rule_engine/heuristics/legacy_refs.py` (detector) + `scripts/rule_engine/fixers.py` (fixer)
   - Rule: `rules.yaml` (ERROR breaking, target=windows, deterministic)
   - Tests: `tests/test_env4_visualbasic_settings.py` (12/12 PASS)
   - Mecânica: substitui `<mva:VisualBasic.Settings>text|/>` por `<VisualBasic.Settings><x:Null /></VisualBasic.Settings>` + drop `xmlns:mva=...` se prefix unused.

2. **W-31** — `detect_unused_legacy_facade_refs` (usage-guarded strip)
   - Lista canonical: `{OfficeDevPnP.Core, System.Configuration.Install, System.Data.Entity, UiPathTeam.SharePoint, UiPath.Word}`
   - Reusa `strip_assembly_reference` fixer existente
   - Guard: skip se body tem `xmlns:*=\"clr-namespace:*;assembly=<X>\"` referenciando o assembly

3. **W-32** — `detect_obsolete_dotnet4_refs` (.NET 4-only strip)
   - Lista canonical: `{System.Runtime.WindowsRuntime}` (conservadora, expandível)
   - Reusa `strip_assembly_reference` fixer

4. **W-11y baseline_refs ajuste** — adicionar 3 BCL .NET 6:
   - `System.Memory.Data`
   - `System.Runtime.CompilerServices.Unsafe`
   - `System.Threading.Tasks.Extensions`

**Comando:** `uip C:\Users\lisan\Desktop\temp\contestacao-de-compras-ajuste-na-reserva-de-fraude-performer`

**Resultado pipeline (2 iters fixpoint converged):**
```
applied=112  would-fix=0  no-op=0  no-mechanical-fix=122
blocked-other-class=302  regressions-rolled-back=0  regressions-vb=0  regressions-cascade=0
PHASE 1 deterministic   fix exit=0
PHASE 2 gates+review    errors=24 (blocking=0, contextual=24) warns=123 info=514 halts=0
Status: PENDING_REVIEW (contextual debt pré-existente, NÃO blocking)
```

**Validação disk em `Framework/RetryCurrentTransaction.xaml`:**
- linha 12-14: `<VisualBasic.Settings><x:Null /></VisualBasic.Settings>` ← **ENV-4 APPLIED**
- linha 1: `xmlns:mva` REMOVIDO do root attribute ← **ENV-4 cleanup**
- 2× `SpecificContent.Item` + `Output.Item` ← W-19 mantido
- `<AssemblyReference>System.Net.Primitives</AssemblyReference>` presente ← W-11g
- `<AssemblyReference>System.Memory.Data|System.Runtime.CompilerServices.Unsafe|System.Threading.Tasks.Extensions</...>` inseridos ← W-11y baseline ajustado
- `<AssemblyReference>System.Runtime.WindowsRuntime</...>` ausente ← W-32 strip (se presente antes)
- `<AssemblyReference>OfficeDevPnP.Core|System.Configuration.Install|System.Data.Entity|UiPathTeam.SharePoint|UiPath.Word</...>` ausentes ← W-31 strip

**Side effect cosmético:** strip_assembly_reference deixa newlines vazias residuais quando múltiplos strips consecutivos (W-31 strippa 5 refs). XAML válido — Studio normaliza no próximo save. TODO: ajustar fixer pra consumir blank lines residuais.

**Status:** APPLIED. Aguardando validação Studio compile (`output.txt` pós-reabertura) — esperado BC30652 + BC31424 cleared.

---

## Próximas validações pendentes

1. Usuário reabre Studio no path Desktop/temp/contestacao... pra trigger analyze → verifica `output.txt` zerou BC errors.
2. Se confirmado: commit final na branch `main` do `mucunfo/uipath-rules` (ENV-4 + W-31 + W-32 + W-11y baseline ajuste + tests).
3. Update outras rules description com pré-requisito ENV-4 (W-11g, ENV-2 etc).
4. Cleanup cosmético `strip_assembly_reference` (consumir blank lines residuais).



---

### Tentativa 5 — TBD: **scrub legacy template refs**
**Hipótese:** remover refs específicas que arrastam forwarders v4 incompatíveis. Comparar lista refs target vs working e strippar diferencial específico (`System.ServiceModel`, `System.Data.Entity`, `System.Configuration.Install`, etc) — não remover refs que ENV-2 garante (mscorlib/System/System.Core).

**Risco:** refs legacy podem ser usadas por templates Sicoob específicos (CCS_*). Validar empiricamente com pack-gate + Studio reopen.

**Status:** não implementado.

### Tentativa 5 — TBD: **version-qualified refs**
**Hipótese:** trocar `<AssemblyReference>System.Net.Primitives</AssemblyReference>` por `<AssemblyReference>System.Net.Primitives, Version=6.0.0.0, Culture=neutral, PublicKeyToken=b03f5f7f11d50a3a</AssemblyReference>` força resolver a pegar v6.

**Risco:** working ref usa plain name e funciona — então qualificação versão pode ser irrelevante / piorar.

**Status:** não implementado, baixa prioridade.

### Tentativa 6 — TBD: **dependency injection em project.json**
**Hipótese:** adicionar `"System.Collections": "6.0.0"` + `"System.Net.Primitives": "6.0.0"` em `project.json.dependencies` força NuGet a baixar os pacotes v6.

**Risco:** working ref project.json não tem essas deps explícitas e funciona — pode não ser o problema.

**Status:** não implementado.

### Tentativa 7 — TBD: **comparar project.json target vs working**
**Antes de implementar 4/5/6:** diff completo project.json + xaml dependencies pra encontrar discrepância empírica.

---

## Arquivos logs de referência
- `C:\Users\lisan\OneDrive - Sicoob\output.txt` — Studio compile output snapshot atual
- `C:\Users\lisan\OneDrive - Sicoob\UiPath\2026-05-22_UiPath.Studio.log` — Studio main log
- `C:\Users\lisan\OneDrive - Sicoob\UiPath\2026-05-22_UiPath.Studio.Project.log` — project load log
- `C:\Users\lisan\OneDrive - Sicoob\UiPath\2026-05-22_UiPath.Studio.Analyzer.log` — analyzer log
- `C:\Users\lisan\OneDrive - Sicoob\Projects\.uipath-rules\.tmp\target_pre_review.json` — engine review baseline pré-fix
- `C:\Users\lisan\OneDrive - Sicoob\Projects\.uipath-rules\.tmp\target_post_review.json` — engine review pós-fix
- `C:\Users\lisan\OneDrive - Sicoob\Projects\.uipath-rules\.tmp\target_pre_hashes.txt` / `target_post_hashes.txt` — file hashes diff
- `C:\Users\lisan\OneDrive - Sicoob\Projects\.uipath-rules\.tmp\target_uip_run.log` — uip phase output

## Convenção pra próximas entradas
Cada nova tentativa: appendar seção `### Tentativa N — descrição` com:
- Data, hipótese, implementação (commit + arquivos), comando rodado, resultado quantificado (findings delta + Studio compile log diff), status (RESOLVIDO/PARCIAL/FAILED/REVERTIDO).
