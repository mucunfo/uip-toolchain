# Toolchain Contract

The CCS public full-gate command is:

```powershell
ccs-uip <project>
ccs-uip <project> --apply-contextual
```

The official UiPath CLI owns the `uip` command.

Internal debug commands remain available through:

```powershell
python -m uip_engine.cli <subcommand> ...
```

Do not run hidden LLM subprocesses. The toolchain must stay script/offline for
the CCS engine path unless an explicit external UiPath/Studio/npm gate is being
run and reported.
