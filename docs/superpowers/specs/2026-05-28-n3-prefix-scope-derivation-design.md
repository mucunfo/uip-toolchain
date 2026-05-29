# N-3 — Derivação scope-aware do prefixo de log (in_StPrefixoLog)

**Data:** 2026-05-28
**Regra afetada:** N-3 + nova regra **N-3B**
**Status:** IMPLEMENTADO + validado no pilot (2026-05-28).

> ## ⚠️ SUPERSESSÃO — modelo final é N-3B (binding-seed)
>
> A seção original abaixo (cascade `add_prefixo_arg` derive-tier no binding
> Main→Process) provou-se **trigger errado** na topologia real do REFramework:
> `add_prefixo_arg` só dispara quando um workflow NÃO declara `in_StPrefixoLog`;
> todos os Sipag já declaram → nunca dispara → os bindings vazios nunca são
> tocados. Além disso o `""` real não está em Main→Process, mas nos **12
> bindings `in_StPrefixoLog=""` em Framework/Process.xaml** (Process→Sipag).
>
> **Modelo final implementado = N-3B** (detector `detect_n3_prefixo_binding`
> + fixer `seed_prefixo_binding`): opera sobre o VALOR dos bindings em
> `<ui:InvokeWorkflowFile.Arguments>`, não sobre declarações de arg:
> - Dono da transação (tem `in_TransactionItem` arg, sem `in_StPrefixoLog`) →
>   DERIVA `[in_TransactionItem.Reference + " - "]`.
> - Quem recebe o prefixo (`in_StPrefixoLog` arg) → HERDA `[in_StPrefixoLog]`.
> - Variable `TransactionItem` (Main-side) → `[TransactionItem.Reference + " - "]`.
> - UPGRADE-only: só reescreve `""`/vazio; nunca clobber valor hand-set.
> - Roda em Framework/Process.xaml (applies_to próprio que NÃO exclui Framework);
>   exclui Tests/Main/*Launch; Performer-only.
>
> Validação pilot (2026-05-28): Process.xaml 12/12 bindings `""` →
> `[in_TransactionItem.Reference + " - "]`; CapturaDadosEtapaReembolso (Sipag que
> invoca mais fundo) → `[in_StPrefixoLog]` (herda); 0 empty restante, 0
> double-space, exit 0 PASS-WITH-NOTES, 0 analyzer regressions; 2ª run applied=0
> (idempotente). Unit: tests/test_n3_prefix_scope.py 30/30. Spec/code design via
> workflow `n3-binding-seed-redesign` (9 agentes, adversarial verify 4 lentes).
>
> Mantido da seção original (válido): gate `_is_performer_project`, N-3 exclui
> Main. O derive-tier em `_cascade_arg_to_callers` ficou como greenfield inócuo.

---
## (HISTÓRICO — modelo inicial, superseded por N-3B acima)

## Problema

O fixer `add_prefixo_arg` (Path 1 da N-3) + helper `_cascade_arg_to_callers`
declaram `in_StPrefixoLog` com **default vazio `""`** em todo lugar
(fixers.py:1446 self default-block; fixers.py:1471 cascade `default_expr='""'`).

A `description` da N-3 documenta a intenção:
> "Process inicializa `in_TransactionItem.Reference + " - "` e propaga."

…mas **nenhum código implementa isso**. Resultado: `in_StPrefixoLog` fica `""`
no pilot → logs perdem a rastreabilidade da transação (que é o PROPÓSITO do
prefixo). Confirmado no pilot contestacao-de-compras.

## Decisões de arquitetura (confirmadas com usuário)

1. **Derivação em 1 ponto único: o binding `Main → Process`.** Main, ao invocar
   Process, passa `in_StPrefixoLog = [TransactionItem.Reference + " - "]`.
2. **SEM guard.** REFramework só executa o Process state após GetTransactionData
   confirmar item → `TransactionItem` é garantidamente non-null no ponto de
   invocação do Process. "Padronizar prefixo APENAS após receber TransactionItem"
   = exatamente este ponto.
3. **Process tem arg de entrada `in_StPrefixoLog`** (faz sentido — é o boundary
   per-transação). Recebe de Main, usa nos próprios logs, propaga aos filhos.
4. **Children (Process↓) propagam `[in_StPrefixoLog]`** (tier 1 já existe).
   Independe de o filho ter `in_TransactionItem` ou não — só propaga o valor
   recebido. Os 2 workflows sem `in_TransactionItem`
   (`AcoesCamposEtapaReembolso`, `ColetaExtratoReservaFraude`) propagam normal.
5. **Main NÃO tem arg de prefixo. N-3 EXCLUI Main.** Logs pré-transação do Main
   (Init/GetTransactionData) não são padronizados — não há transação ainda,
   prefixo não faz sentido.
6. **N-3 aplica SOMENTE a Performers.** Dispatchers montam a fila (sem
   TransactionItem, sem per-transação) → prefixo de `Reference` não se aplica.
   Gate project-level: se não-Performer, N-3 emite nada.

## Estrutura do pilot (grounding empírico)

- **15 workflows** têm arg `in_TransactionItem` (Process + RetryCurrentTransaction
  + SetTransactionStatus + todos Sipag_* + Consolida_* + CriaRelatorioSaida).
- **14 workflows** têm arg `in_StPrefixoLog` (incluindo Main — stale, ver Cleanup).
- Main.xaml: `<Variable x:TypeArguments="ui:QueueItem" Name="TransactionItem" />`.
- Process.xaml: `<x:Property Name="in_TransactionItem" Type="InArgument(ui:QueueItem)" />`.

## Mudanças na engine

### 0. Gate Performer-only (project-level)

`detect_n3_log_prefixo` retorna `[]` imediatamente se o projeto NÃO for
Performer. Helper `_is_performer_project(pc)` (cacheado por projeto):

```
Performer SE:
  primário:  project.json.name termina com "_Performer" (case-insensitive)
             (canonical Orchestrator mapping, per CLAUDE.md — name é fonte de
              verdade, pasta kebab-case não é)
  fallback:  Framework/Process.xaml E Framework/GetTransactionData.xaml existem
             (esqueleto REFramework Performer; Dispatcher não tem — só monta fila)
```

Dispatcher (name `_Dispatcher`, sem Framework/Process.xaml) → não-Performer →
N-3 silenciosa. Robusto contra naming inconsistente via fallback estrutural.

Lazy + cacheado: lookup de project.json/Framework roda 1× por projeto, não por
workflow.

### 1. rules.yaml — N-3 `applies_to.exclude`

Adicionar exclusão de Main (entry point, escopo framework pré-transação):

```yaml
applies_to:
  include: ["**/*.xaml"]
  exclude: ["Framework/**", "Tests/**", "**/Main.xaml", "**/main.xaml"]
```

O detector `detect_n3_log_prefixo` já usa `exclude_paths` param; adicionar
`"main.xaml"` à lista `&chain_exclude_paths` para consistência detector+loader.

### 2. `_cascade_arg_to_callers` — nova tier de derivação

Localização: `fixers.py:1362-1372` (cálculo de `caller_default`).

Heurística atual (ordem):
1. caller tem x:Property `in_StPrefixoLog` → `[in_StPrefixoLog]` (propaga)
2. caller tem Variable `vStPrefixoLog` → `[vStPrefixoLog]`
3. fallback → `default_expr` (`""`)

Heurística nova — inserir tier de derivação por transação ANTES do fallback,
com precedência sobre a propagação quando o caller é o boundary Main→Process:

```
Ordem nova:
1. callee tem arg `in_TransactionItem` E caller tem Variable `TransactionItem`
   (QueueItem)  →  [TransactionItem.Reference + " - "]   (binding Main→Process)
2. caller tem x:Property `in_StPrefixoLog`  →  [in_StPrefixoLog]   (propaga, Process↓)
3. caller tem Variable `vStPrefixoLog`      →  [vStPrefixoLog]
4. fallback                                 →  `default_expr` (`""`)
```

Tier 1 nova só dispara no edge Main→Process (caller com `TransactionItem` var +
callee com `in_TransactionItem` arg). Para Process→child, cai na tier 2 (propaga).

**Parâmetros configuráveis** (defaults REFramework), passados via spec:
- `transaction_var_name = "TransactionItem"`
- `transaction_arg_name = "in_TransactionItem"`
- formato concat: `+ " - "` (mantém o documentado na N-3).

### 3. Self default-block (Step 2 de `add_prefixo_arg`)

Workflows do subtree Process mantêm default-block `""` — recebem o valor via
binding do caller; o default só cobre invocação standalone (ex: teste unitário).
NÃO derivar no self default-block (semântica once-at-entry + redundância).

## Cleanup — Main com in_StPrefixoLog stale (secundário)

Main HOJE tem `in_StPrefixoLog` arg + LogMessages reescritos para
`[in_StPrefixoLog + "..."]` (resíduo de aplicação anterior da N-3 quando ela
ainda incluía Main). Com a N-3 excluindo Main, a engine para de tocar Main, mas
o resíduo permanece.

Impacto: cosmético — `in_StPrefixoLog` default `""` no Main → prepend de string
vazia = no-op visual nos logs. NÃO quebra compile (arg declarado + usado
consistentemente).

Decisão: **fora do escopo deste fix** (primário = derivação correta Process↓).
Remover o arg de Main exigiria reverter os LogMessages do Main (senão
identificador órfão → compile error) = mudança estrutural separada. Tratar como
cleanup manual ou rule dedicada futura. Documentar, não auto-fixar agora.

## Safety

- **Process binding** `[TransactionItem.Reference + " - "]`: VB string concat;
  `TransactionItem` non-null garantido no Process state (REFramework). Mesmo se
  `Reference` fosse Nothing, VB `Nothing + " - "` → `" - "` (sem NRE). Safe.
- **XML-escape** da expr no attribute/binding (`"` → `&quot;`, `+` literal ok).
- **Idempotência**: só injeta binding se `x:Key="in_StPrefixoLog"` ausente no
  InvokeWorkflowFile.Arguments. Re-run = no-op.
- **apply_with_gate**: XML well-form + VB orphan gate + rollback automático
  permanecem. Defesa pós-insert (key duplicada → rollback) mantida.

## Testes

Unit (`tests/test_fixers_layer2.py` ou novo):
1. cascade Main→Process: caller com `TransactionItem` var + callee com
   `in_TransactionItem` → binding `[TransactionItem.Reference + " - "]`.
2. cascade Process→child: caller com `in_StPrefixoLog` arg → `[in_StPrefixoLog]`
   (propaga, regression — comportamento inalterado).
3. cascade fallback: caller sem nenhum → `""` (regression).
4. N-3 detector exclui Main.xaml (não emite finding).
5. Idempotência: re-run cascade = no-op (key já presente).
6. **Performer gate — project.json.name `_Performer`** → N-3 emite findings.
7. **Performer gate — name `_Dispatcher` sem Framework/Process.xaml** → N-3
   emite `[]` (silenciosa).
8. **Performer gate — fallback estrutural** (name não-convencional + Framework/
   Process.xaml + GetTransactionData.xaml presentes) → detectado como Performer.

Validação pilot (target sancionado Desktop/temp):
- `uip <pilot>` rerun → in_StPrefixoLog seedado de TransactionItem.Reference no
  binding Main→Process; propagado Process↓; Main sem novo prefixo.
- Rerun 2× = no-op (idempotência).
- analyzer-gate 0 regressões.

## Critérios de sucesso

- Binding Main→Process passa `[TransactionItem.Reference + " - "]` (não `""`).
- Process↓ propaga `[in_StPrefixoLog]`.
- Main fora da N-3 (sem novo prefixo em logs pré-transação).
- Suite verde + pilot idempotente + 0 analyzer regressões.
