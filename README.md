# .uip-toolchain

Setup de desenvolvimento UiPath pra Sicoob. Autoridade primária = **engine YAML-driven (`src/uip_engine`)**. Fonte única = **`rules.yaml`**.

## Instalacao facil em computador novo

Para uso operacional, sem precisar conhecer Python/pip:

1. Baixe ou clone esta pasta da toolchain no computador.
2. Dê duplo clique em `instalar-ccs-uip.cmd`.
3. Escolha `1. Instalacao recomendada`.
4. Ao final, abra um novo PowerShell.
5. Valide:

```powershell
ccs-uip-publish --help
```

O instalador roda em modo usuario, sem permissao de administrador. Ele:

- instala/atualiza esta toolchain com `pip install --user -e`;
- adiciona o Scripts do Python ao PATH do usuario;
- valida os comandos `ccs-uip` e `ccs-uip-publish`;
- verifica a CLI oficial UiPath `uip`;
- se Node/npm existir, oferece instalar `@uipath/cli@1` no escopo do usuario;
- verifica .NET SDK 8+ para gates oficiais do `ccs-uip` e oferece o instalador portable de `tools/install-dotnet-sdk-portable.cmd` quando necessario;
- grava log em `.tmp/install-ccs-uip-*.log`.

O instalador nao faz login no Orchestrator e nao publica pacote. Login e publish
continuam acontecendo somente quando `ccs-uip-publish` for executado.

## Quick start — gate local `ccs-uip`

**Pipeline completo (god command)**:

```powershell
# 1ª run — migration + deterministic fix + gates + contextual report.
# Deploy-safe: FAIL só quando sobram blockers mecânicos/pipeline/HALT.
ccs-uip <project_path>

# 2ª run — modo assistido por IA para polish/governança contextual.
ccs-uip <project_path> --apply-contextual
```

Interface pública do gate local = `ccs-uip <path> [--apply-contextual]`
**e nada mais**.
Tudo o resto (rules-file, max-iters, watch loop, skip-migration, no-swap)
é intrínseco — defaults internos sobreescritos só via env vars (debug):

| Env var | Default | Efeito |
|---|---|---|
| `UIP_TOOLCHAIN_RULES_FILE` | `<repo>/rules.yaml` | override rules.yaml |
| `UIP_TOOLCHAIN_SKIP_MIGRATION` | `0` | pula PHASE 0 (Activity Migrator) |
| `UIP_TOOLCHAIN_NO_SWAP` | `0` | não swap source ↔ _Migrated após Migrator |
| `UIP_TOOLCHAIN_WATCH` | `0` | loop interativo aguardando mtime change |
| `UIP_TOOLCHAIN_WATCH_INTERVAL` | `2.0` | poll cadence watch (s) |
| `UIP_TOOLCHAIN_MAX_ITERS` | `0` (ilimitado) | limite iters loop |
| `UIP_TOOLCHAIN_KEEP_BACKUP` | `0` | mantém `_BeforeMigration_*` backups pós-PASS (default = auto-clean) |
| `UIP_TOOLCHAIN_DEV_ROBOT_PACKER` | auto-discovery 23.10 | override explícito do `UiRobot.exe` 23.10 usado por `ccs-uip-publish` |

Status final do `ccs-uip <path>`:

| Status | Exit | Significado |
|---|---:|---|
| `PASS` | `0` | sem ERROR/HALT e sem pendências contextuais relevantes |
| `PASS-WITH-NOTES` | `0` | sem ERROR/HALT; há WARN/INFO contextuais/estruturais/governança para IA/humano |
| `FAIL` | `2` | sobrou ERROR, HALT ou falha de integridade do pipeline |

`--apply-contextual` não é pré-requisito para deploy. Ele existe para aplicar
correções que exigem interpretação semântica (mensagem, refactor, camada correta,
decisão arquitetural) com IA/humano no loop. O fluxo contextual assume modelos
frontier (Claude Opus, Codex ou equivalente), nunca runtime local obrigatório;
mesmo assim a LLM só propõe diff e a toolchain valida.

Console scripts públicos:

| Comando | Uso |
|---|---|
| `ccs-uip <project>` | gate local completo: migrate/fix/review/report |
| `ccs-uip <project> --apply-contextual` | aplica fixes contextuais aprovados |
| `ccs-uip-publish <major|minor|patch> [path]` | operação autenticada: seleciona projetos, lê `projectVersion`, empacota próxima versão, faz upload em DEV e baixa `.nupkg` de handoff |

O namespace `uip` fica reservado para a CLI oficial da UiPath (`@uipath/cli`).
Underlying do gate local: `python -m uip_engine.cli all <project>`.
Subcomandos atômicos (`review`, `fix`, `migrate-windows`, `pack-scrub`,
`doctor-uipath-cli`, etc.) seguem existindo **somente** para debug interno via
`python -m uip_engine.cli ...`; não são aceitos pelo comando público `ccs-uip`.

## Arquivos ativos

| Arquivo | Papel |
|---|---|
| `README.md` | este — setup, hooks, scripts, fluxo |
| `rules.yaml` | **fonte única** de regras. Contagem efetiva atual: `python -m uip_engine.cli validate` / `list --by-class` |
| `ARCHITECTURE.md` | manual operacional (schema, decision tree, file map) |
| `models.conf.example` | template versionado para lista local de projetos modelo |
| `models.conf` | arquivo local/gitignored com paths de projetos modelo (lookup de exemplos via `xaml_example.py`) |

## Como Claude opera

1. **Qualquer edição em `.xaml`** → hook `PostToolUse` roda `uip_engine.cli review`. Violações voltam — corrigir antes de continuar.
2. **Edit em `project.json`** → hook chama `uip_engine.cli review` (J-/D-* validam pinning).
3. **Ler XAML grande (>500 linhas)** → hook `PreToolUse` sugere `xaml_summary.py`/`xaml_find.py` em vez de Read bruto.
4. **Precisa de exemplo de activity** → `xaml_example.py --activity NOME` extrai do projeto modelo.
5. **Adicionar/editar regra** → tocar SÓ `rules.yaml` (ver `ARCHITECTURE.md` decision tree).
6. **Decisões arquiteturais** (regras `agent_only`) → consultar `rules.yaml` filtrando por categoria.

## Layout (`src/`, `tools/`, `hooks/`)

| Script | Automação | Uso |
|---|---|---|
| `uip_engine` (pacote, `src/uip_engine/`) | auto via hooks PostToolUse | review/validate/list/fix/all/gates |
| `xaml_summary.py` | auto via hook PreToolUse Read `.xaml >500` | resumo estrutural compacto |
| `xaml_find.py` | manual | lookup por DisplayName/arg/var/invokes/linha |
| `xaml_example.py` | manual | exemplo real de activity (fonte local: `models.conf`) |
| `config_xlsx_manager.py` | manual | inspecionar/alterar Config.xlsx |
| `resolve_nuget.py --add/--all` | manual | adicionar pacote nova dependência |
| `tools/batch_uip.py` | manual | valida muitos projetos com retry adaptativo e relatório em `.tmp/` |
| `inspect-ui-tree.ps1` | manual | inspecionar UI Automation (app em runtime) |

## CLI interna `uip_engine`

Esta seção é para manutenção/debug da toolchain. Para execução em projetos,
use só `ccs-uip <project_path>` ou `ccs-uip <project_path> --apply-contextual`.

```bash
# Validar schema rules.yaml
python -m uip_engine.cli validate

# Review (read-only, mostra TODOS findings — todas classes)
python -m uip_engine.cli review <project_path> --format text
python -m uip_engine.cli review <project_path> --format json

# Fix dry-run (default, só deterministic class)
python -m uip_engine.cli fix <project_path>

# Fix --apply (escreve, default só deterministic)
python -m uip_engine.cli fix --apply <project_path>

# Fix --apply opt-in classes
python -m uip_engine.cli fix --apply --include-class=deterministic,contextual <project_path>
python -m uip_engine.cli fix --apply --include-class=all <project_path>

# Listar regras
python -m uip_engine.cli list                  # com [apply_class] em cada linha
python -m uip_engine.cli list --by-class       # agrupado por classe
python -m uip_engine.cli list --by-category

# Catálogo derivado (markdown — auto-gerado, NÃO editar à mão)
python -m uip_engine.cli docs --llm-only --out .tmp/llm-rules.md
python -m uip_engine.cli docs --out .tmp/all-rules.md

# Workspace multi-projeto
python -m uip_engine.cli review <workspace> --multi-project

# Batch de validação/fix multi-projeto com retry para TIMEOUT/FAIL transitório
# `uip rpa analyze`/restore oficial é serializado para evitar falso FAIL por concorrência.
python tools/batch_uip.py C:\Users\lisan\Desktop\temp\_uip_relacao.txt --workers 1 --t1 900 --t2 2400

# Diagnóstico da CLI oficial UiPath usada pelos gates externos
python -m uip_engine.cli doctor-uipath-cli
```

Exit codes: 0 (OK), 1 (WARN), 2 (ERROR), 3 (HALT), ≥10 (INTERNAL).

## Publicação DEV / handoff

`ccs-uip-publish` é separado do gate local por design: ele empacota com
`UiRobot.exe pack` 23.10 para gerar `.nupkg` compatível com DEV net6, e usa a
CLI oficial `uip` só para login/upload/download no tenant.

```powershell
ccs-uip-publish minor "C:\Users\lisandro.souza\OneDrive - Sicoob\Projects\3. done"

# opcional: depois de cada publish OK, commita e faz push de todas as alterações do repo do projeto
ccs-uip-publish minor "C:\Users\lisandro.souza\OneDrive - Sicoob\Projects\3. done" `
  --commit-branch "release/nc-179" `
  --commit-message "chore: publish DEV packages"
```

Fluxo:
1. varre a pasta informada e permite selecionar os projetos;
2. exige bump explícito `major`, `minor` ou `patch`;
3. lê a versão atual de `project.json::projectVersion`;
4. autentica no `uip` e valida acesso ao tenant `RPA_Desenvolvimento`;
5. no pre-publish, substitui a validação local de `D-1q-CCS-AUTO` por consulta ao Orchestrator (`uip or packages versions <CCS_*> --tenant RPA_Desenvolvimento`); não há fallback para `.nupkgs` local no publish;
6. se `--commit-message` e `--commit-branch` forem informados, valida a branch atual de todos os repositórios selecionados antes de qualquer pack/upload;
7. com commit habilitado, faz `git fetch origin <branch>` e bloqueia se a branch local estiver atrás/divergente do remoto;
8. grava a próxima versão no `project.json` antes do pack;
9. prepara o projeto para o pack (`project.uiproj` derivado de `project.json`);
10. exige packer `UiRobot.exe` 23.10; a descoberta tenta `UIP_TOOLCHAIN_DEV_ROBOT_PACKER`, `Documents\UiPathStudio23x`, instalações padrão em `%LOCALAPPDATA%`, `%ProgramFiles%` e `PATH`;
11. remove referências legadas conhecidamente incompatíveis com pack headless e roda `UiRobot.exe pack <project.json> -o <out> -v <version>`;
12. faz upload do pacote em `RPA_Desenvolvimento`;
13. valida que o `.nupkg` gerado contém TFM compatível com DEV net6 (`net6.0-windows*`) antes de qualquer upload;
14. baixa os `.nupkg` finais soltos em `<path>\.publish-dev-handoff\`;
15. se commit estiver habilitado, commita todas as alterações existentes no repositório Git do projeto e faz `git push -u origin HEAD:<branch>`.

O batch para no primeiro erro por padrão. Use `--keep-going` apenas quando quiser
continuar processando os demais projetos mesmo após falhas.

Se pack/upload/download falhar em um projeto, a alteração de `projectVersion`
desse projeto é revertida para evitar versão local sem pacote publicado.

O gate local (`ccs-uip review`/`ccs-uip`) usa as mesmas regras de readiness:
`J-9` bloqueia `project.uiproj` ausente/desatualizado, `W-40` bloqueia
`AssemblyReference` obsoleta que quebra `uip rpa pack`, e `A-19d` bloqueia
`InvokeWorkflowFile` produtivo que passa `x:Key` não declarado no callee.

## Apply-class taxonomy

Cada rule classifica seu fix em uma de 3 classes (`fix.apply_class`):

| Classe | Critério | `fix --apply` default |
|---|---|---|
| **deterministic** | Mecânico, output único correto, sem judgment | ✅ aplica |
| **contextual** | Exige interpretação semântica (qual mensagem, qual valor) | ❌ nota em `PASS-WITH-NOTES` só se WARN/INFO; ERROR bloqueia |
| **structural** | Reorganiza estrutura (split/extract/move) | ❌ nota em `PASS-WITH-NOTES` só se WARN/INFO; ERROR bloqueia |

Default derivation (sem `apply_class` declarado):
- `fix.auto_apply: false` (legado) → `contextual`
- `fix.mechanical:` declarado em YAML → `deterministic`
- prose-only → `contextual`

Heuristic-emitted mechanical (sem `fix.mechanical` em YAML mas detector retorna `fix_mechanical=`) precisa declarar `apply_class: deterministic` explícito.

Qualidade enterprise de rules: toda regra efetiva precisa ter `fix.prose`.
`python -m uip_engine.cli validate` falha se qualquer regra ficar sem instrução
explícita ou se o texto acoplar a execução a runtime/agente específico.

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
| `PostToolUse` | `Edit/Write/MultiEdit` em `.xaml` | roda `uip_engine.cli review`; violações voltam pro Claude |
| `PostToolUse` | `Edit/Write/MultiEdit` em `project.json` | roda `uip_engine.cli review`; J-/D-* validam pinning |

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

`.uip-toolchain/` é repo git próprio (`mucunfo/uip-toolchain`, branch `main`).
Essa política vale para projetos UiPath processados pela toolchain, não para o
desenvolvimento da toolchain em si.

## Configurar novo projeto modelo

Copiar `models.conf.example` para `models.conf` e adicionar paths absolutos de
projetos modelo (1 linha por projeto). Ordem = prioridade. `models.conf` é
gitignored por conter paths locais; `xaml_example.py` busca na ordem declarada.

## Referência de IDs

IDs em `rules.yaml`: `A-3`, `S-5`, `W-12`, `J-1`, `EXC-1`, etc. Engine usa nas mensagens de finding. Lookup: `python -m uip_engine.cli list --by-category`.
