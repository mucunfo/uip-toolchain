---
name: ccs-creator
description: Use when creating or editing UiPath workflows, project metadata, dependencies, Config.xlsx, or XAML under the CCS UiPath toolchain while keeping scope limited to authoring work.
---

# CCS Creator

## Contract

- Authoring only.
- Stay inside the requested creation or stabilization scope.
- Do not run the global mutating gate: no `ccs-uip <project>`, no `all`, no
  `fix --apply`, no `migrate-windows`, no batch runner.
- Do not copy rules or schemas into the prompt. Query them on demand.
- Never spawn hidden LLM subprocesses.

## Allowed Toolchain Commands

Read-only validation after edits:

```powershell
python -m uip_engine.cli review <project> --format json
```

Targeted lookup:

```powershell
python tools/activities_meta/lookup.py --activity <Name> --json
python tools/xaml_example.py --activity <Name>
python tools/xaml_summary.py <file.xaml>
python tools/xaml_find.py <file.xaml> --activity "<Name>"
python tools/config_xlsx_manager.py list <project>
python tools/resolve_nuget.py --validate <project>\project.json
```

Package authoring may use `resolve_nuget.py --add` only when the user request
requires adding dependencies. Keep versions pinned by the toolchain policy.

## Handoff

If the project needs final publish readiness, stop and hand off to
`ccs-quality`. Do not convert creation work into global standardization.
