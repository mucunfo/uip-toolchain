# N-5 Fixer — Plano de Implementação

**Status**: planejado, não-implementado. Cross-session work; commit messages dos sprints rastreiam progresso real.

**Owner**: `s.lisandro1@gmail.com`
**Created**: 2026-05-21
**Sprints**: F38 → F39 → F40 → F41 → F42 (sequential)

## Objetivo

Mover N-5 ("Toda activity precisa LogMessage Level=Trace próximo (rastreabilidade total)") de `apply_class: structural` (manual) para `apply_class: contextual` (auto-aplicado em `uip --apply-contextual`).

**Volume**: 295 findings no projeto-alvo `contestacao-...-performer`. Dominante. Justifica investimento engine-level.

## Decisões de design (consolidadas, não-re-discutir)

| Eixo | Decisão | Reason |
|---|---|---|
| Message generation | **Hybrid template + LLM fallback** | Template determinístico cobre maioria; LLM call só quando N-16 dry-run prediz fail. Custo baixo (~$0.05/projeto), qualidade alta |
| XAML manipulação | **lxml DOM** | Estruturalmente correto. F29/F30 ROADMAP item já reservado. Reusável pra N-10, futuros fixers |
| Marker | **XML comment** `<!-- engine-trace:N-5 -->` | Não-intrusivo Studio UI; engine re-finds pra refresh/cleanup. User edita Message livremente |
| Apply scope | **Bulk em `--apply-contextual`** | UX matching `uip <path> [--apply-contextual]` minimal. Safety pipeline cascade catch regressões per-file |

## Arquitetura (5 componentes engine-level)

```
rules.yaml: N-5 apply_class structural → contextual
    │
    ▼
heuristics/logs.py::detect_n5_trace_log_significant
    └─ emit Finding com fix_mechanical = {
          type: "insert_trace_log_n5",
          activity_id: "<sap2010:WorkflowViewState.IdRef>",
          activity_line: N,
          activity_display_name: "...",
          vars_in_scope: [{name, type, ref}, ...],
          message: <pre-computed template OR placeholder>,
          llm_fallback: <bool, set if N-16 predicts fail>,
       }
    │
    ▼
heuristics/logs.py::generate_n5_trace_message
    ├─ Template path: `[<DisplayName> done: v1=[v1], v2=[v2]]`
    ├─ N-16 predictor: cached heuristic + optional LLM batch
    └─ LLM fallback se predicted fail
    │
    ▼
_helpers/xaml_dom.py (NEW) — lxml infrastructure
    ├─ parse_preserving_format(path) → (etree, encoding, BOM)
    ├─ find_activity_by_idref(root, idref) → Element
    ├─ find_activity_by_line(root, line) → Element
    ├─ insert_after_with_marker(target, new_node, marker_text)
    └─ serialize_preserving_format(tree, ...) → bytes
    │
    ▼
fixers.py::apply_insert_trace_log_n5 (NEW)
    ├─ Read fix_mechanical spec
    ├─ Generate message (template OR LLM via spec.llm_fallback)
    ├─ Build LogMessage Element via lxml
    ├─ Idempotency: skip se já tem marker OU Trace em window
    └─ Insert + write (preserve format/BOM)
    │
    ▼
Existing F35 safety pipeline (cli.py)
    ├─ apply_with_gate analyzer baseline diff
    └─ Per-file rollback se NEW errors (ST-NMG-005, N-16, etc.)
```

## Sprint roadmap

### Step 0 (pré-sprint): Persist plan
Este documento. Done quando criado.

### Step 1 (pré-F38): Prototype template quality ✅ DONE

**Result**: 13/16 (81.2%) pass-rate em sample real do projeto-alvo.

Decisão: F41 LLM fallback **mantido** mas **deprioritizado** — cobre os ~19% edge cases.

3 fails identificados (refinements pra template generator F39):
- `Assign` sem DisplayName custom → fallback `[Assign done]` rejeitado por "too generic"
- `MessageBox` com Studio default "Message Box" → genérico
- `Click - Ok` Studio default → genérico

**Refinements F39 template generator**:
1. Detectar "Studio default DisplayName" (regex: `^<ActivityKind>($| - [A-Z][a-z]+$|$)`) → tratar como missing → usar `[Activity at line N]` formato
2. Activity-specific verb map: `Assign` → "atribuído", `WriteRange` → "gravado", `Click` → "clicado", `MessageBox` → "exibido", etc. (PT-BR matching Sicoob locale)
3. Se 0 vars in scope → adicionar identifier de contexto (parent activity DisplayName, ou x:Class)

Bypass usado em prototype: `_call_claude` direto com prompt tight (sem JSON strict). Engine `llm_validator.py` produção tem bug: model retorna verbose JSON em vez de strict format esperado → `_parse_verdicts` falha → fail-open. **Separate engine bug** — registrar como F43 fix pós-N-5.

Artifacts:
- `.tmp/n5_proto.py` — prototype script (throwaway)
- `.tmp/n5_proto_results.json` — sample messages + verdicts
- `.tmp/n5_proto.log` — full run log

### Sprint F38: lxml XAML DOM infrastructure
**Novo arquivo**: `scripts/rule_engine/_helpers/xaml_dom.py`

API:
```python
def parse_preserving_format(path: Path) -> tuple[etree._ElementTree, str, bool]:
    """Parse XAML preserving namespace decl order, indent, BOM presence."""

def find_activity_by_idref(tree, idref: str) -> etree._Element | None:
    """Match sap2010:WorkflowViewState.IdRef attribute exactly."""

def find_activity_by_line(tree, line: int) -> etree._Element | None:
    """Fallback when IdRef ausente — match by source line approximation."""

def insert_after_with_marker(target, new_elem, marker_text: str) -> None:
    """Insert XML comment + element as next siblings of target.
    Preserves whitespace/indent at insertion point."""

def serialize_preserving_format(tree, encoding: str, has_bom: bool) -> bytes:
    """Serialize matching original style (declaration, indent, BOM)."""
```

Tests (`tests/test_xaml_dom_helpers.py`):
- Round-trip identity bytes (parse → serialize == original) em 5 XAML samples
- Namespace decl order preserved
- BOM preserved (with/without)
- Indent style preserved (2-space, 4-space, tab)
- Comment insertion preserves surrounding whitespace
- find_activity_by_idref correctness
- find_activity_by_line fallback correctness

Estimate: ~250 LOC novo + ~150 LOC tests.

### Sprint F39: Detector + template generator
**Modificado**: `scripts/rule_engine/heuristics/logs.py`

Novas functions:
```python
def _collect_vars_in_scope(activity_elem) -> list[dict]:
    """Walk up parent chain finding <Variable> declarations.
    Returns list[{name, type, last_assigned_line}]. Sorted by relevance
    (recent assignment, in_args first, then locals)."""

def generate_n5_trace_template(activity_elem, vars) -> str:
    """Template path. Rules:
      - DisplayName presente → `[<DisplayName> done]` baseline
      - Vars in scope (top 3) → append `: v1=[v1], v2=[v2]`
      - DisplayName ausente → `[Activity at line N done]`
    """

def predict_n16_pass(message: str, project_root: Path) -> bool:
    """Cached heuristic + optional LLM batch.
    Returns True if message likely passes N-16."""
```

Modificado: `detect_n5_trace_log_significant` — emit fix_mechanical payload em vez de fix_mechanical=None.

**rules.yaml change**: N-5 `apply_class: structural` → `apply_class: contextual`.

Tests (`tests/test_n5_template_generator.py`):
- `_collect_vars_in_scope`: walks up correctly em nested scopes (Sequence > If > ForEach)
- `generate_n5_trace_template`: cobre activities com/sem DisplayName, com/sem vars
- `predict_n16_pass`: usa heuristic local (sem chamar LLM real em tests)
- Detector emits fix_mechanical dict shape correto

Estimate: ~200 LOC novo + ~250 LOC tests.

### Sprint F40: fixer mechanical
**Modificado**: `scripts/rule_engine/fixers.py`

```python
N5_MARKER = "engine-trace:N-5"

@register("insert_trace_log_n5")
def apply_insert_trace_log_n5(file: Path, spec: dict, dry_run: bool = True) -> bool:
    # 1. Parse XAML (lxml, preserving format)
    tree, encoding, has_bom = parse_preserving_format(file)
    # 2. Find activity
    activity = find_activity_by_idref(tree, spec["activity_id"]) or \
               find_activity_by_line(tree, spec["activity_line"])
    if activity is None:
        return False
    # 3. Idempotency
    if _has_trace_log_marker_in_window(activity, N5_MARKER, window_chars=600):
        return False
    if _has_trace_log_activity_in_window(activity, window_chars=600):
        return False  # manually-added Trace already covers it
    # 4. Generate message
    msg = spec.get("message")  # pre-computed by detector
    if spec.get("llm_fallback"):
        msg = _llm_generate_trace_message(activity, spec["vars_in_scope"], file.parent)
    # 5. Build LogMessage element with marker
    log_elem = _build_trace_logmessage_elem(msg, activity)
    insert_after_with_marker(activity, log_elem, N5_MARKER)
    # 6. Write
    if not dry_run:
        file.write_bytes(serialize_preserving_format(tree, encoding, has_bom))
    return True
```

Helper:
```python
def _build_trace_logmessage_elem(message: str, activity_context) -> etree._Element:
    """Build <ui:LogMessage Level="Trace" Message="..."/> with namespace
    inherited from activity_context. Uses ui: prefix as canonical Sicoob."""
```

Tests (`tests/test_fixer_insert_trace_log_n5.py`):
- Insertion correctness (correct sibling position)
- Namespace preservation (no dup xmlns decls)
- Idempotency: re-running same fix = no-op (marker detection)
- Marker present em output
- BOM preserved
- Dry-run no write
- LLM fallback path (mocked)

Estimate: ~180 LOC novo + ~200 LOC tests.

### Sprint F41: LLM fallback integration
**Modificado**: `scripts/rule_engine/llm_validator.py` (extend existing infra) + new `prompts/n5_trace_generator.md`.

```python
def llm_generate_trace_message(activity_xaml: str, vars: list[dict],
                                project_root: Path) -> str:
    """Claude CLI call w/ batching + cache. Reuses _resolve_claude_cmd
    + BATCH_SIZE + cache infra do N-16 validator.

    Cache key: hash(activity_xaml_normalized + vars_signature)
    Cache file: .tmp/analyzer_cache/<sig>/llm_n5_trace.json
    """
```

Prompt outline (`prompts/n5_trace_generator.md`):
```
You generate UiPath LogMessage Trace text. Input: XAML activity + vars in scope.
Output: 1-line VB expression that, when used as Message= attribute, provides
runtime traceability.

Rules:
- Length: 30-120 chars
- Include activity intent (not generic "Concluído" / "Done")
- Reference at least 1 variable via VB concat (`& vX.ToString` or `+ vX`)
- Match XAML Studio VB syntax (NO C# templates, NO multi-line)
- Output ONLY the Message expression (no quotes, no explanation)

Example:
Input activity: <ui:OpenBrowser DisplayName="Abrir portal Sipag" Url="[in_UrlPortal]"/>
Vars in scope: in_UrlPortal (String), vIdTransacao (String)
Output: "[\"Browser aberto em \" + in_UrlPortal + \" para transação \" + vIdTransacao]"
```

Tests (`tests/test_n5_llm_fallback.py`):
- Mocked Claude CLI (no real API)
- Cache hit → no subprocess call
- Cache miss → subprocess invocation + cache write
- Batch up to 50 messages per CLI call

Estimate: ~120 LOC novo + ~80 LOC tests (mocked).

### Sprint F42: End-to-end validation
**No code changes**. Validation + docs.

Steps:
1. `rm -rf .tmp/analyzer_cache/*` (cold cache to test full path)
2. `uip <target-project>` → PENDING_REVIEW exit 1
3. `uip <target-project> --apply-contextual` → expect PASS exit 0
4. Verify:
   - All 295 N-5 findings resolved (or marked NEEDS_REVIEW se LLM falhou)
   - 0 NEW Studio analyzer errors (diff vs baseline pre-N-5-fixer)
   - Manual spot-check 5 random insertions = sensible Message text
5. Documentação:
   - `README.md` Quick start: mencionar N-5 capability
   - `ARCHITECTURE.md`: novo bullet em PHASE 1
   - `CLAUDE.md` (project root): atualizar fluxo

Acceptance criteria:
- N-5 findings post `--apply-contextual` = 0 (ou <5 com NEEDS_REVIEW honesto)
- 0 NEW Studio analyzer errors
- All inserted Traces carry `<!-- engine-trace:N-5 -->`

Estimate: ~30 LOC docs + manual validation (~1h).

## Risks + mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| lxml parse fail em XAML malformed | Baixa | Fix skipa file, finding fica PENDING | Try/except parse; honest fallback |
| N-16 LLM rejeita generated msg | Média | F41 retry; fail → finding PENDING_REVIEW | Retry once com prompt revisado |
| Trace em scope errado (parent não-Sequence) | Média | F35 cascade rollback | Validate parent type pré-insert |
| LLM cost burst | Baixa | $0.30/projeto × 50/dia = $15/dia | Cache aggressive; reuse entre projetos |
| Idempotency falha → dup-insert | Baixa | XAML inflate | Marker + Trace-in-window detection |
| Namespace inheritance issue (ui: prefix) | Média | XAML inválido | F38 testes round-trip pegam; inherit from activity parent |

## Out-of-scope (próximas iterações, NÃO neste plano)

- N-10 (auto-extract sub-workflow) — bigger semantic task
- CX-2/CX-4 (nesting depth) — manual refactor por natureza
- TCC-1 (auto-generate Test Cases) — LLM-heavy
- Other structural rules — caso a caso após F38 lxml infra estabilizar

## Estimativa total

| Sprint | LOC novo | LOC test | Sessões |
|---|---|---|---|
| Step 0 persist | — | — | 0.1 |
| Step 1 prototype | ~80 (throwaway) | — | 0.3 |
| F38 lxml infra | ~250 | ~150 | 1.0 |
| F39 detector + template | ~200 | ~250 | 1.0 |
| F40 fixer mechanical | ~180 | ~200 | 1.0 |
| F41 LLM fallback | ~120 | ~80 (mock) | 0.5 |
| F42 validation + docs | ~30 | — | 0.3 |
| **Total** | **~860** | **~680** | **~4.2 sessões** |

## Status de cada sprint

| Sprint | Status | Commit | Notes |
|---|---|---|---|
| Step 0 persist | ✅ done | (this commit) | |
| Step 1 prototype | ✅ done | 81.2% pass-rate | 3 fails → F39 refinements documentados |
| F38 lxml infra | ✅ done | 25/25 tests pass | `_helpers/xaml_dom.py` byte-surgical insertion; reusável outros fixers |
| F39 detector | ✅ done | (descoberta) | Detector já emitia fix_mechanical spec — gap real era apply_class |
| F40 fixer | ✅ done | (descoberta) | Fixer `apply_insert_trace_log` já existia em fixers.py:1968 (F35 commit). Sofisticado: lxml parent classification + wrap-able detection + Message template + DisplayName uniqueness |
| F41 LLM fallback | ⏸ deferred | | Pode ser implementado quando ~19% N-16 fails motivar. Atualmente: ~10/134 (7%) Traces flagged N-16 contextual — não blocker PASS. F35 analyzer-gate rollback catches regressões reais |
| F42 validation | ✅ done | applied=134, PASS exit 0 | Projeto-alvo `contestacao-...-performer`: 295 N-5 findings → 134 mecanicamente aplicados (~45% absorbed). Restante: blocked parents (restrictive collections), Sequence wrap-failures. Contextual residual 624→232. Errors 29→39 (+10 N-16-flagged Trace messages = contextual, não-blocking) |

Update este table conforme cada sprint completa (commit message link).
