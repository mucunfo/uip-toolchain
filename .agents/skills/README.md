# CCS UiPath Skills

These skills are CCS skills for the UiPath toolchain.

- `ccs-creator`: authoring and stabilization within the requested creation
  scope.
- `ccs-auditor`: read-only review and reporting.
- `ccs-quality`: full project quality gate, equivalent to the public
  `ccs-uip` workflow.

They are intentionally separate from official UiPath CLI skills installed by
`uip skills install --agent codex` or `uip skills install --agent claude`.

The CCS toolchain installs these skills globally for Codex and Claude through:

```powershell
python -m uip_engine.cli install-skills
```

The public `ccs-uip <project>` command also runs that sync automatically before
the full gate.
