---
name: ccs-auditor
description: Use when reviewing, auditing, inspecting, or validating a UiPath project without changing files under the CCS UiPath toolchain.
---

# CCS Auditor

## Contract

- Read-only.
- Never edit, write, fix, migrate, or run batch mutation.
- Never run `ccs-uip <project>` because the full gate can apply deterministic
  fixes.
- Report by severity, rule id, file, line, and operational impact.

## Primary Commands

```powershell
python -m uip_engine.cli review <project> --format json
python -m uip_engine.cli review <project> --format text
```

Use targeted static reads when review cannot run:

```powershell
python tools/xaml_summary.py <file.xaml>
python tools/xaml_find.py <file.xaml> --line <line> --context 20
rg -n "<rule-id>|id: <rule-id>" rules.yaml
```

If falling back to static inspection, label the result partial and state which
gate could not run.
