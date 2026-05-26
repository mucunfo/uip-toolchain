# Snapshot Regression Suite

Engine output stability gate. Pega regressões silenciosas (rule mudou, detector quebrou, fixer over-reach mascarando findings que antes apareciam).

## Workflow

### 1. Capture baseline (uma vez por projeto canonical)

```bash
cd C:/Users/lisan/OneDrive - Sicoob/Projects/.uip-toolchain
python -m tools.snapshot_regression --capture
```

Grava `tests/snapshots/<project_slug>.json` com normalized findings count + per-rule breakdown.

### 2. Validar (após qualquer mudança engine)

```bash
python -m tools.snapshot_regression
```

- Exit `0` = match baseline (no drift)
- Exit `1` = drift (review diff + decidir)
- Exit `2` = erro infra (canonical ausente, engine fail)

Diff mostra `+ findings` (cobertura nova OR detector quebrou) e `- findings` (intentional mascaramento OR fixer auto-aplicou).

### 3. Update baseline (após mudança engine intentional)

Após drift legítimo (ex: nova rule add findings esperados):

```bash
python -m tools.snapshot_regression --capture --force
```

Commit novo baseline JSON.

## Canonical catalog

Projetos canonical = estáveis, Windows-target migrados, conhecidamente PASS engine. Lista em `tools/snapshot_regression.py::CANONICAL`.

Critério inclusão:
- targetFramework: Windows
- Pipeline `uip` retorna PASS ou PENDING_REVIEW estável (3 runs consecutivos zero diff)
- Cobre patterns Sicoob típicos (NApplicationCard, REFramework, CCS_* libs)

Atual:
- `importar-cadastro-avais-fiancas-honrados-performer` (REF Windows-target Sicoob canonical)

Expandir conforme projetos estabilizam pós-migração.

## CI integration (futuro)

GitHub Actions workflow em `.github/workflows/snapshot.yml`:

```yaml
name: Snapshot Regression
on: [pull_request]
jobs:
  snapshot:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: python -m tools.snapshot_regression
```

Bloqueia merge em drift inesperado.

## Layout

```
tests/snapshots/                # baseline (versioned, commit estável)
  <project_slug>.json
.tmp/snapshot_runs/             # run atual (gitignored, descartável)
  <project_slug>.json
```

## Normalização aplicada

- Path absoluto → relativo do project root
- Strip campos voláteis (timestamps, run_id, message body)
- Sort findings por (file, line, rule_id) — determinismo
- Counts agregados por rule_id
