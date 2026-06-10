# UiPath CLI Migration Notes

Date reviewed: 2026-06-01.

Official docs reviewed:

- https://docs.uipath.com/uipath-cli/standalone/latest/user-guide/about-uipath-cli
- https://docs.uipath.com/uipath-cli/standalone/latest/user-guide/whats-new
- https://docs.uipath.com/uipath-cli/standalone/latest/user-guide/versioning
- https://docs.uipath.com/uipath-cli/standalone/latest/user-guide/installing-uipath-cli
- https://docs.uipath.com/uipath-cli/standalone/latest/user-guide/migration-command-map
- https://docs.uipath.com/uipath-cli/standalone/latest/user-guide/migration-flag-renames
- https://docs.uipath.com/uipath-cli/standalone/latest/user-guide/migration-breaking-changes
- https://docs.uipath.com/uipath-cli/standalone/latest/user-guide/output-formats
- https://docs.uipath.com/uipath-cli/standalone/latest/user-guide/uip-rpa
- https://docs.uipath.com/uipath-cli/standalone/latest/user-guide/coding-agents

## Decision

Reserve `uip` for the official UiPath CLI distributed as `@uipath/cli`.
This toolchain publishes two CCS console scripts:

- `ccs-uip`: local full-gate command; never uploads packages.
- `ccs-uip-publish`: authenticated DEV handoff command; scans/selects projects,
  reads `project.json::projectVersion`, bumps it, packs with Studio/Robot
  23.10 `UiRobot.exe pack` for DEV net6 compatibility, uploads to
  `RPA_Desenvolvimento` with official `uip`, then downloads the uploaded
  `.nupkg`.

The internal debug entrypoint remains:

```powershell
python -m uip_engine.cli <subcommand> ...
```

## Why This Is Not A Binary Swap

The official CLI is a new TypeScript/npm host invoked as `uip`, with Node.js
18+ as a host requirement. RPA operations are provided by `uip rpa` through the
`@uipath/rpa-tool` plugin, and those RPA commands still rely on Studio/.NET for
packaging, analyzer and workflow compiler operations.

Key contract changes:

- Output is structured JSON by default, with envelope fields such as `Result`,
  `Code`, `Data`, `Message`, `Instructions`, and optional `Context` or `Log`.
- Auth is session-oriented. Legacy user/password and refresh-token flags are
  removed; CI should use `uip login` with External App credentials.
- Environment variables such as `UIPATH_CLIENT_ID` are not read implicitly;
  pass them as `env.VARNAME` on login flags.
- Legacy `uipcli package analyze` maps to `uip rpa analyze`.
- Legacy `uipcli package pack` maps to `uip rpa pack`.
- Legacy `uipcli package restore` maps to `uip rpa restore`.
- Some legacy flows split into multiple commands, for example deploy and job
  execution.

## Version Compatibility

The installation docs show `1.0.0` as an example installed version, but the
versioning docs describe UiPath CLI as a semver 1.x contract and explicitly use
`@uipath/cli@1.1.0` as an upgrade/pinning example. Local validation on
2026-06-01 used:

- `@uipath/cli@1.1.0`
- `rpa-tool@1.1.0`

Toolchain policy:

- Supported official CLI host line: `1.x`.
- Pre-1 versions are blocked as preview/unstable.
- Future major versions are blocked until the command flags and JSON envelope
  shape are revalidated.
- Unknown version emits a warning diagnostic but does not stop the gate.

Compatibility diagnostics emitted by the CCS gate:

- `UIPATH:CLI_VERSION_UNSUPPORTED`: official `uip` host is outside validated
  1.x.
- `UIPATH:CLI_VERSION_UNKNOWN`: version could not be read with
  `uip --version`.
- `UIPATH:CLI_ASSEMBLY_MISSING`: official `uip rpa analyze/pack` could not
  load an assembly such as `NPOI` or `Microsoft.VisualStudio.Services.Common`.
  Treat as package restore/feed/graph mismatch, not a generic analyzer halt.
- `UIPATH:CLI_PACKAGE_DOWNGRADE`: official CLI detected a package downgrade.
- `UIPATH:CLI_PROJECT_FORMAT`: official RPA gate was pointed at a project that
  is not yet in the expected migrated Windows/project.uiproj shape.
- `UIPATH:CLI_DOTNET_SDK`: official RPA tool requires a compatible .NET SDK.
- `UIPATH:RESTORE_PACKAGE_MISSING`: `uip rpa restore` could not resolve a
  package id/version from available feeds.
- `UIPATH:RESTORE_DOWNGRADE`: `uip rpa restore` detected a dependency
  downgrade that must be pinned or fixed in the package graph.
- `UIPATH:RESTORE_FEED_UNAVAILABLE`: one or more NuGet sources were not
  reachable or usable by the official restore.
- `UIPATH:RESTORE_NUGET_ERROR`: another NuGet restore error was surfaced by
  the official CLI.
- `UIPATH:RESTORE_HALT`: restore invocation failed before producing a
  classifiable restore diagnostic.

## Current Toolchain Boundary

The CCS local gate command is `ccs-uip`. The authenticated DEV handoff command
is `ccs-uip-publish`. The official UiPath CLI owns `uip`.

The engine now uses official `uip` as the source of truth for modern gates:

- `uip rpa restore` for dependency resolution before analyzer/pack.
- `uip rpa analyze` for the Analyzer gate.
- `uip rpa build --skip-analyze` for the compile gate.
- `uip rpa pack --skip-analyze` for the pack/publish dry-run gate. Analyzer
  remains a separate gate, so pack only proves package generation.

`ccs-uip-publish` uses official `uip` directly for tenant operations, but the
final DEV package artifact is generated by the 23.10 Robot packer:

- `uip login status` / `uip login --interactive` / `uip login tenant list`.
- CCS package validation against the authenticated Orchestrator feed with
  `uip or packages versions <CCS_*> --tenant RPA_Desenvolvimento`. The local
  `.nupkgs` source used by offline `D-1q-CCS-AUTO` is suppressed in the
  publish review; publish has no local package fallback.
- `project.uiproj` sync from `project.json` when the installed modern RPA
  packer requires the descriptor.
- removal of controlled stale `AssemblyReference` lines that are not backed by
  dependencies and are not used by an `xmlns ... assembly=...`.
- `UiRobot.exe pack <project.json> -o <out> -v <version>` using a Studio/Robot
  23.10 packer discovered via `UIP_TOOLCHAIN_DEV_ROBOT_PACKER`, the local
  `Documents\UiPathStudio23x` path, standard `%LOCALAPPDATA%`/`%ProgramFiles%`
  installs, or `PATH`.
- post-pack validation that the `.nupkg` exposes a DEV-compatible net6 TFM
  before upload.
- `uip or packages upload` to DEV.
- `uip or packages download` from DEV for the handoff `.nupkg`.

Legacy `UiPath.Studio.CommandLine.exe` remains only for `migrate-windows`,
where the Activity Migrator is still the bridge for old Legacy/Windows-Legacy
projects. It is not a review/fix/publish fallback. `UiRobot.exe pack` 23.10 is
the explicit DEV handoff packer because the official `uip rpa pack` can emit
net8 packages that Robot 23.10/net6 cannot install.

The pack gate prepares a temporary project copy through `publish_readiness.py`,
so review gates do not mutate the source while analyzer, build and pack gates
run through the official CLI.

## Safe Migration Path

1. Keep `ccs-uip` as the CCS local gate command.
2. Add a separate official-CLI adapter for `uip`, with explicit discovery such
   as `UIPATH_UIP_CLI` or `shutil.which("uip")`.
3. Parse official CLI stdout as the JSON envelope, not as legacy `#json...#json`
   or pack/publish text.
4. Run `uip rpa restore` before analyzer/pack. If restore fails, report the
   restore cause and skip later official analyzer/pack for that review run.
5. Keep `uip rpa analyze` as the analyzer gate, without legacy fallback.
6. Keep `uip rpa build --skip-analyze` as the compile gate, without direct
   compiler fallback.
7. Keep `uip rpa pack --skip-analyze` as the local review pack gate, but use
   `UiRobot.exe pack` 23.10 for the authenticated DEV artifact.
8. Keep network/npm/tool auto-install visible in logs and docs. Do not hide it
   inside offline CCS phases. `ccs-uip-publish` must fail clearly if the
   Studio/Robot 23.10 packer is absent.
9. Keep tenant-mutating commands outside `ccs-uip`; use
   `ccs-uip-publish` for explicit DEV upload/download only.

Official adapter file: `src/uip_engine/official_uip.py`. It discovers the
official CLI, runs migrated `uip rpa` commands, and parses the JSON envelope.
DEV handoff file: `src/uip_engine/publish_dev.py`.
Shared official-pack readiness helpers: `src/uip_engine/publish_readiness.py`.

## Agent Skill Boundary

Official UiPath skills can be installed with `uip skills install --agent codex`,
which uses `.agents/skills/<skill>`. The CCS skills in this repo are separate:

- `ccs-creator`: authoring only.
- `ccs-auditor`: read-only review only.
- `ccs-quality`: full CCS gate through `ccs-uip`.

The CCS skills must not copy `rules.yaml` or activity schema data. They should
query the toolchain on demand so `rules.yaml` remains the single source of
truth.

## Skill Installation Policy

Official UiPath skills are installed through the official CLI and remain
separate from CCS skills:

```powershell
uip skills install --agent codex
uip skills install --agent claude
```

CCS skills are managed by the CCS toolchain:

```powershell
python -m uip_engine.cli install-skills
```

The public `ccs-uip <project>` command also runs this CCS skill sync before
the full gate. It is idempotent and installs/updates only:

- `ccs-creator`
- `ccs-auditor`
- `ccs-quality`

Global destinations:

- Codex: `%USERPROFILE%\.agents\skills\<skill>`
- Claude: `%USERPROFILE%\.claude\skills\<skill>`

The sync intentionally does not touch official `uipath-*` skills.
