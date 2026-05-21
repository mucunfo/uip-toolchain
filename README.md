# .uipath-rules

Setup de desenvolvimento UiPath pra Sicoob. Autoridade primária = **engine YAML-driven (`scripts/rule_engine`)**. Fonte única = **`rules.yaml`**.

## Quick start — comando único `uip`

**Pipeline completo (god command)**:

```powershell
# 1ª run — migration + deterministic fix + gates + contextual dry-run.
# Exit imediato em FAIL (modo CI/agentic).
uip <project_path>

# 2ª run — aprova contextual remanescente da 1ª.
uip <project_path> --apply-contextual
```

Interface pública = `uip <path> [--apply-contextual]` **e nada mais**.
Tudo o resto (rules-file, max-iters, watch loop, skip-migration, no-swap)
é intrínseco — defaults internos sobreescritos só via env vars (debug):

| Env var | Default | Efeito |
|---|---|---|
| `UIPATH_RULES_FILE` | `<repo>/rules.yaml` | override rules.yaml |
| `UIPATH_RULES_SKIP_MIGRATION` | `0` | pula PHASE 0 (Activity Migrator) |
| `UIPATH_RULES_NO_SWAP` | `0` | não swap source ↔ _Migrated após Migrator |
| `UIPATH_RULES_WATCH` | `0` | loop interativo aguardando mtime change |
| `UIPATH_RULES_WATCH_INTERVAL` | `2.0` | poll cadence watch (s) |
| `UIPATH_RULES_MAX_ITERS` | `0` (ilimitado) | limite iters loop |

Exit codes: `0` PASS, `1` PENDING_REVIEW (contextual aguarda `--apply-contextual`),
`2` FAIL, `3` HALT, `10` INTERNAL.

Alias PS em `$HOME\Documents\WindowsPowerShell\profile.ps1`. Underlying:
`python -m scripts.rule_engine.cli all <project>`. Subcomandos atômicos
(`review`, `fix`, `migrate-windows`) seguem existindo para debug interno.

## Arquivos ativos

| Arquivo | Papel |
|---|---|
| `README.md` | este — setup, hooks, scripts, fluxo |
| `rules.yaml` | **fonte única** de regras (233 hoje: A/S/P/I/T/W/D/J/X + per-package; 58 deterministic + 170 contextual + 5 structural) |
| `ARCHITECTURE.md` | manual operacional (schema, decision tree, file map) |
| `models.conf` | paths de projetos modelo (lookup de exemplos via `xaml_example.py`) |

## Como Claude opera

1. **Qualquer edição em `.xaml`** → hook `PostToolUse` roda `rule_engine.cli review`. Violações voltam — corrigir antes de continuar.
2. **Edit em `project.json`** → hook chama `rule_engine.cli review` (J-/D-* validam pinning).
3. **Ler XAML grande (>500 linhas)** → hook `PreToolUse` sugere `xaml_summary.py`/`xaml_find.py` em vez de Read bruto.
4. **Precisa de exemplo de activity** → `xaml_example.py --activity NOME` extrai do projeto modelo.
5. **Adicionar/editar regra** → tocar SÓ `rules.yaml` (ver `ARCHITECTURE.md` decision tree).
6. **Decisões arquiteturais** (regras `agent_only`) → consultar `rules.yaml` filtrando por categoria.

## Scripts (`scripts/`)

| Script | Automação | Uso |
|---|---|---|
| `rule_engine` (pacote) | auto via hooks PostToolUse | review/validate/list/fix |
| `xaml_summary.py` | auto via hook PreToolUse Read `.xaml >500` | resumo estrutural compacto |
| `xaml_find.py` | manual | lookup por DisplayName/arg/var/invokes/linha |
| `xaml_example.py` | manual | exemplo real de activity (fonte: `models.conf`) |
| `config_xlsx_manager.py` | manual | inspecionar/alterar Config.xlsx |
| `resolve_nuget.py --add/--all` | manual | adicionar pacote nova dependência |
| `inspect-ui-tree.ps1` | manual | inspecionar UI Automation (app em runtime) |

## CLI rule_engine

```bash
# Validar schema rules.yaml
python -m scripts.rule_engine.cli validate

# Review (read-only, mostra TODOS findings — todas classes)
python -m scripts.rule_engine.cli review <project_path> --format text
python -m scripts.rule_engine.cli review <project_path> --format json

# Fix dry-run (default, só deterministic class)
python -m scripts.rule_engine.cli fix <project_path>

# Fix --apply (escreve, default só deterministic)
python -m scripts.rule_engine.cli fix --apply <project_path>

# Fix --apply opt-in classes
python -m scripts.rule_engine.cli fix --apply --include-class=deterministic,contextual <project_path>
python -m scripts.rule_engine.cli fix --apply --include-class=all <project_path>

# Listar regras
python -m scripts.rule_engine.cli list                  # com [apply_class] em cada linha
python -m scripts.rule_engine.cli list --by-class       # agrupado por classe
python -m scripts.rule_engine.cli list --by-category

# Catálogo derivado (markdown — auto-gerado, NÃO editar à mão)
python -m scripts.rule_engine.cli docs --llm-only --out .tmp/llm-rules.md
python -m scripts.rule_engine.cli docs --out .tmp/all-rules.md

# Workspace multi-projeto
python -m scripts.rule_engine.cli review <workspace> --multi-project
```

Exit codes: 0 (OK), 1 (WARN), 2 (ERROR), 3 (HALT), ≥10 (INTERNAL).

## Apply-class taxonomy

Cada rule classifica seu fix em uma de 3 classes (`fix.apply_class`):

| Classe | Critério | `fix --apply` default |
|---|---|---|
| **deterministic** | Mecânico, output único correto, sem judgment | ✅ aplica |
| **contextual** | Exige interpretação semântica (qual mensagem, qual valor) | ❌ alerta only (review) |
| **structural** | Reorganiza estrutura (split/extract/move) | ❌ alerta only (review) |

Default derivation (sem `apply_class` declarado):
- `fix.auto_apply: false` (legado) → `contextual`
- `fix.mechanical:` declarado em YAML → `deterministic`
- prose-only → `contextual`

Heuristic-emitted mechanical (sem `fix.mechanical` em YAML mas detector retorna `fix_mechanical=`) precisa declarar `apply_class: deterministic` explícito.

Pipeline de defesa (`fix --apply`):
1. **Pre-fix snapshot** do primary file
2. **Apply fixer** (com fixpoint loop — re-detecta até convergir, max 20 iter)
3. **XML well-formedness gate** (rollback se quebrou parse)
4. **VB ref↔declaration gate** (rollback se introduziu orphan ref)
5. **Cascade detection** (mtime delta — log only)
6. **Idempotência**: 2ª aplicação produz `applied=0`

## Hooks (globais via `~/.claude/settings.json`)

| Evento | Match | Ação |
|---|---|---|
| `PreToolUse` | `Read` em `.xaml >500 linhas` | roda `xaml_summary.py` e retorna resumo inline |
| `PostToolUse` | `Edit/Write/MultiEdit` em `.xaml` | roda `rule_engine.cli review`; violações voltam pro Claude |
| `PostToolUse` | `Edit/Write/MultiEdit` em `project.json` | roda `rule_engine.cli review`; J-/D-* validam pinning |

Hooks silenciam quando nada a reportar — zero ruído em tarefas normais.

## Convenções resumidas (detalhes em `rules.yaml`)

**Nomenclatura:**
- PT-BR em workflows, variáveis, argumentos (S-9, prefixo de tipo `St`, `Int`, `Dt`, `Bl`, `DTab`, etc.)
- Argumentos: `in_`/`out_`/`io_` + tipo + PascalCase
- Acrônimos UPPERCASE (S-4): XML, RPA, DB2, API, URL, JSON, SQL, UI, CPF, CNPJ
- `x:Class` = filename sem `.xaml` (S-6)

**Estrutura:**
- REFramework Dispatcher/Performer
- Pastas por sistema externo na raiz (A-16), sem numeração
- Config em `assets/configs/Config_<Role>.xlsx` (A-8)
- Mensagens de exceção no Config, nunca hardcoded (A-13)

**Logs:**
- Sem bookends `[INICIO]/[FIM]` (A-7)
- Workflows na cadeia Process recebem `in_StPrefixoLog`

**Código:**
- Sem annotations em XAML (S-5)
- InvokeCode omite `Language` (S-7) — VB.NET default
- Credenciais: `in_StCredentialAssetName` só (A-3)
- Progress counter `"Nr - Desc"` em Main.xaml (A-14)
- Sem UI activities em workflows de dados (A-18)

**Windows target:**
- studioVersion `23.10.13` (J-1) + packages pinados (D-1*)
- W-1..W-17: armadilhas Legacy → Windows
- Cabeçalho XAML usa `assembly=System.Private.CoreLib` (W-4)

## Suppressões

```xml
<!-- rule-disable: A-7 -->
<!-- rule-disable: A-7, S-8 -->
<!-- rule-disable-file: A-3 -->
```

`rtk-disable` é alias legado. Só silencia WARN/INFO. ERROR/HALT não silenciáveis.

## Política de versionamento

Engine, hooks, agentes e CLI **NUNCA** rodam `git add/commit/push` em projetos UiPath. Toda alteração fica como modificação local pendente; usuário commita manualmente. Volume alto de modificações é normal em batch fixes.

`.uipath-rules/` em si não é repo git.

## Configurar novo projeto modelo

Editar `models.conf` e adicionar path absoluto do projeto (1 linha). Ordem = prioridade. `xaml_example.py` busca na ordem declarada.

## Referência de IDs

IDs em `rules.yaml`: `A-3`, `S-5`, `W-12`, `J-1`, `EXC-1`, etc. Engine usa nas mensagens de finding. Lookup: `python -m scripts.rule_engine.cli list --by-category`.
