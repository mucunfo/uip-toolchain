# N-3 Scope-Aware Prefix Derivation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** N-3 deriva `in_StPrefixoLog = TransactionItem.Reference + " - "` no binding Main→Process (não `""`), propaga Process↓, exclui Main, aplica só a Performers.

**Architecture:** Gate Performer-only no detector. Derivação única no caller Main (var `TransactionItem`) ao invocar callee com arg `in_TransactionItem`. Demais callers propagam `[in_StPrefixoLog]`. Mudança em `logs.py` (gate + exclude) + `fixers.py` (cascade tier) + `rules.yaml` (exclude + params).

**Tech Stack:** Python 3.13, pytest, regex-based XAML edit (raw-string surgical), engine `uip_engine`.

**Validação:** SOMENTE no pilot sancionado `C:\Users\lisan\Desktop\temp\contestacao-de-compras-ajuste-na-reserva-de-fraude\contestacao-de-compras-ajuste-na-reserva-de-fraude-performer`. NUNCA em projetos dentro de `Projects/`.

**Spec:** `docs/superpowers/specs/2026-05-28-n3-prefix-scope-derivation-design.md`

---

## File Structure

- `src/uip_engine/heuristics/logs.py` — add `_is_performer_project(pc)` helper + Performer gate + main.xaml exclude no detector N-3.
- `src/uip_engine/fixers.py` — `_cascade_arg_to_callers` ganha tier de derivação transação; `apply_add_prefixo_arg` thread novos params.
- `rules.yaml` — N-3 `applies_to.exclude` += Main; `chain_exclude_paths` += main.xaml; detect params += transaction_var_name/transaction_arg_name.
- `tests/test_heuristic_logs.py` — testes do gate Performer + exclude Main.
- `tests/test_fixers_layer2.py` — testes da tier de derivação no cascade.

---

## Task 1: Helper `_is_performer_project` + gate no detector N-3

**Files:**
- Modify: `src/uip_engine/heuristics/logs.py` (after `_is_in_chain`, ~line 45; gate em `detect_n3_log_prefixo` ~line 54)
- Test: `tests/test_heuristic_logs.py`

- [ ] **Step 1: Write failing tests para o helper + gate**

Adicionar em `tests/test_heuristic_logs.py`:

```python
def test_is_performer_by_name(tmp_path):
    from uip_engine.heuristics.logs import _is_performer_project
    from uip_engine.context import ProjectContext
    (tmp_path / "project.json").write_text(
        '{"name":"FooBar_Performer","targetFramework":"Windows"}', encoding="utf-8")
    pc = ProjectContext.find_root(tmp_path)
    assert _is_performer_project(pc) is True


def test_is_performer_dispatcher_name_no_framework(tmp_path):
    from uip_engine.heuristics.logs import _is_performer_project
    from uip_engine.context import ProjectContext
    (tmp_path / "project.json").write_text(
        '{"name":"FooBar_Dispatcher","targetFramework":"Windows"}', encoding="utf-8")
    pc = ProjectContext.find_root(tmp_path)
    assert _is_performer_project(pc) is False


def test_is_performer_structural_fallback(tmp_path):
    from uip_engine.heuristics.logs import _is_performer_project
    from uip_engine.context import ProjectContext
    # name não-convencional, mas REFramework Performer skeleton presente
    (tmp_path / "project.json").write_text(
        '{"name":"LegacyBotNoSuffix","targetFramework":"Windows"}', encoding="utf-8")
    fw = tmp_path / "Framework"
    fw.mkdir()
    (fw / "Process.xaml").write_text("<Activity/>", encoding="utf-8")
    (fw / "GetTransactionData.xaml").write_text("<Activity/>", encoding="utf-8")
    pc = ProjectContext.find_root(tmp_path)
    assert _is_performer_project(pc) is True


def test_is_performer_none_pc():
    from uip_engine.heuristics.logs import _is_performer_project
    assert _is_performer_project(None) is False
```

- [ ] **Step 2: Run tests, verify fail**

Run: `python -m pytest tests/test_heuristic_logs.py::test_is_performer_by_name tests/test_heuristic_logs.py::test_is_performer_structural_fallback -v`
Expected: FAIL — `ImportError: cannot import name '_is_performer_project'`.

- [ ] **Step 3: Implement `_is_performer_project` helper**

Em `src/uip_engine/heuristics/logs.py`, após a função `_is_in_chain` (linha ~45), adicionar:

```python
def _is_performer_project(pc) -> bool:
    """True se o projeto é um Performer REFramework.

    Primário: project.json.name termina com '_Performer' (canonical Orchestrator
    mapping — name é fonte de verdade, pasta kebab-case não é).
    Fallback estrutural: Framework/Process.xaml E Framework/GetTransactionData.xaml
    existem (esqueleto REFramework Performer; Dispatcher só monta fila, não tem).
    """
    if pc is None:
        return False
    name = (pc.project_json.get("name") or "").strip()
    if name.lower().endswith("_performer"):
        return True
    fw = pc.root / "Framework"
    return (fw / "Process.xaml").is_file() and (fw / "GetTransactionData.xaml").is_file()
```

- [ ] **Step 4: Run helper tests, verify pass**

Run: `python -m pytest tests/test_heuristic_logs.py::test_is_performer_by_name tests/test_heuristic_logs.py::test_is_performer_dispatcher_name_no_framework tests/test_heuristic_logs.py::test_is_performer_structural_fallback tests/test_heuristic_logs.py::test_is_performer_none_pc -v`
Expected: 4 PASS.

- [ ] **Step 5: Add gate no `detect_n3_log_prefixo`**

Em `src/uip_engine/heuristics/logs.py`, dentro de `detect_n3_log_prefixo`, logo após `prefixo_arg = p.get(...)` (linha ~53) e ANTES de `if not _is_in_chain(...)`, inserir:

```python
    if not _is_performer_project(pc):
        return []
```

- [ ] **Step 6: Commit**

```bash
git add src/uip_engine/heuristics/logs.py tests/test_heuristic_logs.py
git commit -F <msg-file>
```
Mensagem: `feat(n3): gate Performer-only no detector de prefixo de log`

---

## Task 2: N-3 exclui Main.xaml

**Files:**
- Modify: `rules.yaml` (N-3 `applies_to.exclude` ~linha 3233; `chain_exclude_paths` anchor ~linha 3240)
- Test: `tests/test_heuristic_logs.py`

- [ ] **Step 1: Write failing test — Main excluído**

Adicionar em `tests/test_heuristic_logs.py`:

```python
def test_n3_excludes_main(tmp_path):
    import yaml
    from uip_engine.loader import load_rules
    from uip_engine.context import FileContext, ProjectContext
    from pathlib import Path as _P
    # Performer project skeleton
    (tmp_path / "project.json").write_text(
        '{"name":"FooBar_Performer","targetFramework":"Windows"}', encoding="utf-8")
    main = tmp_path / "Main.xaml"
    main.write_text(
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:ui="http://schemas.uipath.com/workflow/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">'
        '<x:Members></x:Members>'
        '<ui:LogMessage Level="Info" Message="[&quot;oi&quot;]" /></Activity>',
        encoding="utf-8")
    rules_path = _P(__file__).resolve().parents[1] / "rules.yaml"
    rules = load_rules(str(rules_path))
    n3 = next(r for r in rules if r.id == "N-3")
    fc = FileContext(main)
    pc = ProjectContext.find_root(tmp_path)
    from uip_engine.heuristics.logs import detect_n3_log_prefixo
    findings = detect_n3_log_prefixo(n3, fc, pc)
    assert findings == []
```

- [ ] **Step 2: Run test, verify fail**

Run: `python -m pytest tests/test_heuristic_logs.py::test_n3_excludes_main -v`
Expected: FAIL — findings não-vazio (Main ainda detectado).

- [ ] **Step 3: Add main.xaml ao `chain_exclude_paths` no rules.yaml**

Em `rules.yaml`, no bloco N-3 `detect.params.exclude_paths` (anchor `&chain_exclude_paths`, ~linha 3240), adicionar entradas:

```yaml
        exclude_paths: &chain_exclude_paths
          - "framework/"
          - "tests/"
          - "/launch.xaml"
          - "launch.xaml"
          - "/main.xaml"
          - "main.xaml"
```

- [ ] **Step 4: Add Main globs ao `applies_to.exclude` da N-3**

Em `rules.yaml`, no bloco N-3 `applies_to.exclude` (~linha 3233):

```yaml
    applies_to:
      include: ["**/*.xaml"]
      exclude: ["Framework/**", "Tests/**", "**/Main.xaml", "**/main.xaml"]
```

- [ ] **Step 5: Run test, verify pass**

Run: `python -m pytest tests/test_heuristic_logs.py::test_n3_excludes_main -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add rules.yaml tests/test_heuristic_logs.py
git commit -F <msg-file>
```
Mensagem: `feat(n3): exclui Main.xaml (logs pré-transação sem prefixo)`

---

## Task 3: Cascade — tier de derivação transação (Main→Process)

**Files:**
- Modify: `src/uip_engine/fixers.py` (`_cascade_arg_to_callers` assinatura ~1320; bloco `caller_default` ~1361-1372)
- Test: `tests/test_fixers_layer2.py`

- [ ] **Step 1: Write failing tests pro cascade derive-tier**

Adicionar em `tests/test_fixers_layer2.py`:

```python
def test_cascade_main_derives_from_transactionitem(tmp_path):
    from uip_engine.fixers import _cascade_arg_to_callers
    # callee Process: tem arg in_TransactionItem + in_StPrefixoLog
    proc = tmp_path / "Process.xaml"
    proc.write_text(
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
        'xmlns:ui="http://schemas.uipath.com/workflow/activities">'
        '<x:Members>'
        '<x:Property Name="in_TransactionItem" Type="InArgument(ui:QueueItem)" />'
        '<x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />'
        '</x:Members></Activity>', encoding="utf-8")
    # caller Main: tem Variable TransactionItem + invoca Process com Arguments block
    main = tmp_path / "Main.xaml"
    main.write_text(
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
        'xmlns:ui="http://schemas.uipath.com/workflow/activities">'
        '<Variable x:TypeArguments="ui:QueueItem" Name="TransactionItem" />'
        '<ui:InvokeWorkflowFile WorkflowFileName="Process.xaml">'
        '<ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile></Activity>', encoding="utf-8")
    n = _cascade_arg_to_callers(tmp_path, proc, "in_StPrefixoLog",
                                default_expr='""', dry_run=False)
    assert n == 1
    out = main.read_text(encoding="utf-8")
    assert 'x:Key="in_StPrefixoLog">[TransactionItem.Reference + " - "]</InArgument>' in out


def test_cascade_process_child_propagates(tmp_path):
    from uip_engine.fixers import _cascade_arg_to_callers
    # callee child: tem in_StPrefixoLog (sem in_TransactionItem relevante p/ derive)
    child = tmp_path / "Child.xaml"
    child.write_text(
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">'
        '<x:Members><x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />'
        '</x:Members></Activity>', encoding="utf-8")
    # caller Process: tem ARG in_TransactionItem (não Variable TransactionItem) +
    # já declara in_StPrefixoLog → propaga [in_StPrefixoLog]
    proc = tmp_path / "Process.xaml"
    proc.write_text(
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
        'xmlns:ui="http://schemas.uipath.com/workflow/activities">'
        '<x:Members>'
        '<x:Property Name="in_TransactionItem" Type="InArgument(ui:QueueItem)" />'
        '<x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />'
        '</x:Members>'
        '<ui:InvokeWorkflowFile WorkflowFileName="Child.xaml">'
        '<ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile></Activity>', encoding="utf-8")
    n = _cascade_arg_to_callers(tmp_path, child, "in_StPrefixoLog",
                                default_expr='""', dry_run=False)
    assert n == 1
    out = proc.read_text(encoding="utf-8")
    assert 'x:Key="in_StPrefixoLog">[in_StPrefixoLog]</InArgument>' in out


def test_cascade_fallback_empty(tmp_path):
    from uip_engine.fixers import _cascade_arg_to_callers
    callee = tmp_path / "Callee.xaml"
    callee.write_text(
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">'
        '<x:Members><x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />'
        '</x:Members></Activity>', encoding="utf-8")
    # caller sem TransactionItem var, sem in_StPrefixoLog, sem vStPrefixoLog
    caller = tmp_path / "Caller.xaml"
    caller.write_text(
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
        'xmlns:ui="http://schemas.uipath.com/workflow/activities">'
        '<x:Members></x:Members>'
        '<ui:InvokeWorkflowFile WorkflowFileName="Callee.xaml">'
        '<ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile></Activity>', encoding="utf-8")
    n = _cascade_arg_to_callers(tmp_path, callee, "in_StPrefixoLog",
                                default_expr='""', dry_run=False)
    assert n == 1
    out = caller.read_text(encoding="utf-8")
    assert 'x:Key="in_StPrefixoLog">""</InArgument>' in out
```

- [ ] **Step 2: Run tests, verify fail**

Run: `python -m pytest tests/test_fixers_layer2.py::test_cascade_main_derives_from_transactionitem -v`
Expected: FAIL — caller_default cai em `""` (tier de derivação ainda não existe); assert da expr Reference falha.

- [ ] **Step 3: Add params à assinatura + detecção callee transaction-arg**

Em `src/uip_engine/fixers.py`, alterar assinatura de `_cascade_arg_to_callers` (linha 1320):

```python
def _cascade_arg_to_callers(project_root: Path, callee_file: Path,
                             arg_name: str, default_expr: str = '""',
                             dry_run: bool = True,
                             transaction_var_name: str = "TransactionItem",
                             transaction_arg_name: str = "in_TransactionItem") -> int:
```

Logo após `if project_root is None or not project_root.exists(): return 0` (linha ~1337), adicionar leitura do callee + flag:

```python
    try:
        callee_content = callee_file.read_text(encoding="utf-8-sig")
    except OSError:
        callee_content = ""
    callee_has_txn_arg = bool(
        re.search(rf'<x:Property\b[^>]*Name="{re.escape(transaction_arg_name)}"',
                  callee_content)
    )
```

- [ ] **Step 4: Add derive-tier no bloco `caller_default` (precedência)**

Em `src/uip_engine/fixers.py`, substituir o bloco de cálculo de `caller_default` (linha ~1361-1372) por:

```python
        # Determine default-expr para esse caller (uma vez). Ordem de precedência:
        # 0. Derivação transação (Main→Process): callee tem arg in_TransactionItem
        #    E caller tem Variable TransactionItem (QueueItem). Sem guard —
        #    REFramework só roda Process state após TransactionItem recebido.
        # 1. caller declara in_StPrefixoLog → propaga [in_StPrefixoLog]
        # 2. caller tem Variable vStPrefixoLog → [vStPrefixoLog]
        # 3. fallback default_expr ("")
        if callee_has_txn_arg and re.search(
            rf'<Variable\b[^>]*\bName="{re.escape(transaction_var_name)}"', ctext
        ):
            caller_default = f'[{transaction_var_name}.Reference + " - "]'
        elif re.search(rf'<x:Property\b[^>]*Name="{re.escape(arg_name)}"', ctext):
            caller_default = f"[{arg_name}]"
        else:
            short = re.sub(r'^(in|out|io)_', '', arg_name)
            var_candidate = f"v{short}"
            if re.search(rf'<Variable\b[^>]*\bName="{re.escape(var_candidate)}"', ctext):
                caller_default = f"[{var_candidate}]"
            else:
                caller_default = default_expr
```

- [ ] **Step 5: Run cascade tests, verify pass**

Run: `python -m pytest tests/test_fixers_layer2.py::test_cascade_main_derives_from_transactionitem tests/test_fixers_layer2.py::test_cascade_process_child_propagates tests/test_fixers_layer2.py::test_cascade_fallback_empty -v`
Expected: 3 PASS.

- [ ] **Step 6: Commit**

```bash
git add src/uip_engine/fixers.py tests/test_fixers_layer2.py
git commit -F <msg-file>
```
Mensagem: `feat(n3): cascade deriva prefixo de TransactionItem.Reference no binding Main->Process`

---

## Task 4: Thread params detector→fixer + idempotência

**Files:**
- Modify: `src/uip_engine/heuristics/logs.py` (fix_mechanical spec do detector ~linha 64)
- Modify: `src/uip_engine/fixers.py` (`apply_add_prefixo_arg` ~linha 1460-1475: passar params ao cascade)
- Modify: `rules.yaml` (N-3 detect.params += transaction_var_name/transaction_arg_name)
- Test: `tests/test_fixers_layer2.py`

- [ ] **Step 1: Write failing idempotency test**

Adicionar em `tests/test_fixers_layer2.py`:

```python
def test_cascade_main_derive_idempotent(tmp_path):
    from uip_engine.fixers import _cascade_arg_to_callers
    proc = tmp_path / "Process.xaml"
    proc.write_text(
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
        'xmlns:ui="http://schemas.uipath.com/workflow/activities">'
        '<x:Members>'
        '<x:Property Name="in_TransactionItem" Type="InArgument(ui:QueueItem)" />'
        '<x:Property Name="in_StPrefixoLog" Type="InArgument(x:String)" />'
        '</x:Members></Activity>', encoding="utf-8")
    main = tmp_path / "Main.xaml"
    main.write_text(
        '<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" '
        'xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" '
        'xmlns:ui="http://schemas.uipath.com/workflow/activities">'
        '<Variable x:TypeArguments="ui:QueueItem" Name="TransactionItem" />'
        '<ui:InvokeWorkflowFile WorkflowFileName="Process.xaml">'
        '<ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile.Arguments>'
        '</ui:InvokeWorkflowFile></Activity>', encoding="utf-8")
    _cascade_arg_to_callers(tmp_path, proc, "in_StPrefixoLog", dry_run=False)
    first = main.read_text(encoding="utf-8")
    n2 = _cascade_arg_to_callers(tmp_path, proc, "in_StPrefixoLog", dry_run=False)
    second = main.read_text(encoding="utf-8")
    assert n2 == 0          # já passa o arg → no-op
    assert first == second  # byte-idêntico
```

- [ ] **Step 2: Run test, verify pass (idempotência já coberta pelo guard x:Key existente)**

Run: `python -m pytest tests/test_fixers_layer2.py::test_cascade_main_derive_idempotent -v`
Expected: PASS — o check `if re.search(rf'\bx:Key="{re.escape(arg_name)}"', body): return m.group(0)` (linha ~1389) já garante no-op no 2º run. Se FALHAR, investigar antes de prosseguir.

- [ ] **Step 3: Thread params no detector fix_mechanical**

Em `src/uip_engine/heuristics/logs.py`, `detect_n3_log_prefixo`, no branch `if not has_prefixo:` (linha ~62-67), expandir o spec:

```python
        fix_mech_spec = {
            "type": "add_prefixo_arg",
            "prefixo_arg": prefixo_arg,
            "transaction_var_name": p.get("transaction_var_name") or "TransactionItem",
            "transaction_arg_name": p.get("transaction_arg_name") or "in_TransactionItem",
        }
```

- [ ] **Step 4: Consumir params em `apply_add_prefixo_arg`**

Em `src/uip_engine/fixers.py`, `apply_add_prefixo_arg` (após `prefixo_arg = spec.get(...)` linha ~1460), adicionar:

```python
    txn_var = spec.get("transaction_var_name") or "TransactionItem"
    txn_arg = spec.get("transaction_arg_name") or "in_TransactionItem"
```

`apply_add_prefixo_arg` tem EXATAMENTE 2 chamadas a `_cascade_arg_to_callers`,
ambas dentro da função (linhas 1470 e 1558 — confirmado via grep; `guard_linq`
em 1568+ NÃO chama cascade). Em AMBAS, adicionar os kwargs novos:

```python
            modified = _cascade_arg_to_callers(
                project_root, file, prefixo_arg, default_expr='""',
                dry_run=dry_run,
                transaction_var_name=txn_var, transaction_arg_name=txn_arg,
            )
```

(A chamada em 1470 já usa `default_expr='""'` explícito; a de 1558 — confirmar
assinatura atual via `grep -n -A3 "_cascade_arg_to_callers" src/uip_engine/fixers.py`
e preservar os args posicionais existentes, só acrescentando os 2 kwargs.)

- [ ] **Step 5: Add params no rules.yaml N-3 detect**

Em `rules.yaml`, N-3 `detect.params` (~linha 3236-3239), adicionar após `prefixo_arg_name`:

```yaml
        prefixo_arg_name: in_StPrefixoLog
        transaction_var_name: TransactionItem
        transaction_arg_name: in_TransactionItem
```

- [ ] **Step 6: Run full touched-files suite**

Run: `python -m pytest tests/test_heuristic_logs.py tests/test_fixers_layer2.py -v`
Expected: ALL PASS (novos + regression).

- [ ] **Step 7: Commit**

```bash
git add src/uip_engine/heuristics/logs.py src/uip_engine/fixers.py rules.yaml tests/test_fixers_layer2.py
git commit -F <msg-file>
```
Mensagem: `feat(n3): thread transaction params detector->fixer + idempotência cascade`

---

## Task 5: Validação no pilot (sancionado Desktop/temp)

**Files:** nenhum (validação read+run).

- [ ] **Step 1: Baseline review do pilot ANTES (captura estado in_StPrefixoLog atual)**

Run:
```bash
python -m uip_engine.cli review "C:/Users/lisan/Desktop/temp/contestacao-de-compras-ajuste-na-reserva-de-fraude/contestacao-de-compras-ajuste-na-reserva-de-fraude-performer" --format json > .uip-toolchain/.tmp/n3_baseline.json 2>&1 || true
```
Expected: JSON gerado em `.tmp/` (gitignored).

- [ ] **Step 2: Rodar god command `uip` no pilot (1ª run)**

Run (de fora, alias resolve):
```bash
"C:/Users/lisan/AppData/Roaming/Python/Python313/Scripts/uip.exe" "C:/Users/lisan/Desktop/temp/contestacao-de-compras-ajuste-na-reserva-de-fraude/contestacao-de-compras-ajuste-na-reserva-de-fraude-performer" > .uip-toolchain/.tmp/n3_run1.txt 2>&1
```
Expected: exit 0 (PASS ou PASS-WITH-NOTES). Sem analyzer regressions.

- [ ] **Step 3: Verificar binding Main→Process semeado**

Run:
```bash
grep -n 'x:Key="in_StPrefixoLog"' "C:/Users/lisan/Desktop/temp/contestacao-de-compras-ajuste-na-reserva-de-fraude/contestacao-de-compras-ajuste-na-reserva-de-fraude-performer/Main.xaml"
```
Expected: linha com `[TransactionItem.Reference + " - "]` no Invoke do Process (não `""`).

- [ ] **Step 4: Rerun (2ª run) — idempotência**

Run:
```bash
"C:/Users/lisan/AppData/Roaming/Python/Python313/Scripts/uip.exe" "C:/Users/lisan/Desktop/temp/contestacao-de-compras-ajuste-na-reserva-de-fraude/contestacao-de-compras-ajuste-na-reserva-de-fraude-performer" > .uip-toolchain/.tmp/n3_run2.txt 2>&1
```
Expected: exit 0, `applied=0` (no-op), 0 analyzer regressions.

- [ ] **Step 5: Cleanup tmp + final full suite**

Run:
```bash
rm -f .uip-toolchain/.tmp/n3_baseline.json .uip-toolchain/.tmp/n3_run1.txt .uip-toolchain/.tmp/n3_run2.txt
python -m pytest -q
```
Expected: full suite verde (≥ contagem anterior, 0 failed).

- [ ] **Step 6: Commit final (se houver ajuste) + parar pra review humana**

Sem auto-commit de mudança no pilot (pilot é projeto UiPath — git read-only por política). Reportar resultado.

---

## Notas de execução

- **Git:** commits diretos em `main` (repo interno), mas aprovação por turno exigida — NÃO auto-commit. Usar `git commit -F <file>` (hook `commit-validate` do pro-workflow buga com `-m "$(cat heredoc)"`).
- **Pilot:** único target de validação. NUNCA rodar engine em `Projects/`.
- **Main cleanup deferido:** in_StPrefixoLog stale no Main (+ logs reescritos) fica como dívida separada — não tratar neste plano.
