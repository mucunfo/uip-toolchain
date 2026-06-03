---
name: ccs-quality
description: Use for full UiPath project quality gates, publish readiness, final approval, batch validation, or the CCS ccs-uip workflow.
---

# CCS Quality

## Contract

- Owns the full CCS gate.
- Run `ccs-uip <project>` for project-level quality and publish readiness.
- Use `ccs-uip <project> --apply-contextual` only with explicit user approval.
- Never spawn hidden LLM subprocesses.
- Never run `git add`, `git commit`, or `git push` in UiPath project repos.
- Do not author a new solution from scratch; hand scoped creation back to
  `ccs-creator`.

## Full Gate

```powershell
ccs-uip <project>
```

Expected status:

- `PASS`: deploy-safe.
- `PASS-WITH-NOTES`: deploy-safe with contextual or structural notes.
- `FAIL`: blocker remains in migration, deterministic fix, analyzer, NuGet,
  pack, or pipeline integrity.

## Triage

Use read-only review for details before manual repairs:

```powershell
python -m uip_engine.cli review <project> --format json
```

For batch validation, use:

```powershell
python tools/batch_uip.py <input-file> --workers 3 --t1 900 --t2 2400
```
