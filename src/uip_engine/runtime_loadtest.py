"""runtime_loadtest wrapper — invoca .NET runtime_loadtest.exe subprocess.

Coleta paths XAML do projeto, envia via stdin batch mode pra evitar 8KB args
limit Windows, parse JSON output, retorna lista de Finding pra engine
aggregator (`_run_runtime_loadtest_gate` em cli.py).

PHASE 2 gate paralelo a analyze/pack/nuget. Catches:
  - VB compile errors em Variable.Default (smart-quote bugs etc.)
  - Type resolution failures (missing assembly ref)
  - Malformed Activity tree (XAML parser errors)
  - Validation pass rejections (required arg sem binding, type mismatch)

Findings emitidos como `RT-LOAD-<STATUS>` severity ERROR category BREAKING.

Phase 9E (2026-05-26): findings `RT-LOAD-INVALID_WORKFLOW` cujo erro é do tipo
`'<arg>' is not declared` (BC30451) recebem inferência inline 3-layer (canonical
table → invocation xref → Hungarian convention). Se ≥1 layer resolve type, o
finding é enriquecido com `fix_mechanical={"type": "inject_missing_args", ...}`
pra dispatch pro fixer determinístico. Se TODAS as 3 layers falham, gate emite
finding adicional `RT-LOAD-AMBIGUOUS-ARG` severity HALT (block pipeline,
exige decisão manual).

Exit codes (do subprocess):
  0 = todos XAMLs load OK
  1 = ≥1 XAML failed load
  2 = invalid args (não deve acontecer via wrapper)

Graceful degradation:
  - Binary not built → finding RT-LOAD-INFRA diagnóstico (engine continua,
    gate skipa). Build via `dotnet build -c Release` em runtime_loadtest/.
  - Subprocess timeout → finding RT-LOAD-TIMEOUT.
  - Invalid JSON stdout → finding RT-LOAD-INFRA com snippet.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from ._types import Finding, Severity, Category


# Phase 9E: regex pra extrair identifier name de erro BC30451-class do VB.
# Examples:
#   "'in_Config' is not declared. It may be inaccessible due to its protection level."
#   "BC30451: 'in_StFoo' is not declared."
_NOT_DECLARED_RE = re.compile(r"'(?P<name>[A-Za-z_][\w]*)' is not declared")


# Binary name segue convention `dotnet build -c Release` em net6.0-windows.
# Se target mudar pra net8.0-windows, atualizar _binary_path() ramo.
_BINARY_NAME = "runtime_loadtest.exe"
_BINARY_TFM = "net6.0-windows"


def _binary_path() -> Path | None:
    """Resolve runtime_loadtest binary path.

    Lookup order:
      1. env UIPATH_RUNTIME_LOADTEST_BIN (explicit override)
      2. <.uip-toolchain>/experiments/runtime_loadtest/bin/Release/net6.0-windows/runtime_loadtest.exe
      3. None (caller emite RT-LOAD-INFRA finding)
    """
    explicit = os.environ.get("UIPATH_RUNTIME_LOADTEST_BIN", "").strip()
    if explicit and Path(explicit).is_file():
        return Path(explicit)

    # __file__ = .../.uip-toolchain/src/uip_engine/runtime_loadtest.py
    # parents[2] = .uip-toolchain/
    engine_root = Path(__file__).resolve().parents[2]
    candidate = (engine_root / "experiments" / "runtime_loadtest"
                 / "bin" / "Release" / _BINARY_TFM / _BINARY_NAME)
    return candidate if candidate.is_file() else None


def run_loadtest(project_root: Path, timeout: int = 180) -> tuple[int, list[Finding]]:
    """Run runtime_loadtest em todos XAMLs do projeto.

    Args:
        project_root: Path para raiz do projeto UiPath (contém project.json).
        timeout: Timeout total subprocess em segundos (default 180s = 3min).

    Returns:
        (exit_code, findings_list). exit_code segue subprocess returncode:
        0 = pass, 1 = XAML load fail, 2 = infra issue (binary/timeout/JSON).
    """
    project_root = Path(project_root).resolve()
    binary = _binary_path()
    if binary is None:
        return 2, [_infra_finding(
            project_root,
            "runtime_loadtest binary not found. Run 'dotnet build -c Release' "
            f"em .uip-toolchain/experiments/runtime_loadtest/ (expected: bin/Release/"
            f"{_BINARY_TFM}/{_BINARY_NAME}). Override via env "
            "UIPATH_RUNTIME_LOADTEST_BIN se binary em outro path."
        )]

    # Skipa `_BeforeMigration_*` siblings (Activity Migrator backups que
    # estão em outro folder mas rglob inclui se nested) + skipa Mocks/Tests
    # padrão Sicoob (false-positives intencionais).
    xamls: list[str] = []
    for p in project_root.rglob("*.xaml"):
        s = str(p)
        if "_BeforeMigration_" in s:
            continue
        # Skip nupkg extract folders (uipcli pack output em .tmp/)
        if ".tmp" in p.parts:
            continue
        xamls.append(s)
    xamls.sort()

    if not xamls:
        return 0, []

    stdin_data = "\n".join(xamls)
    try:
        proc = subprocess.run(
            [str(binary), "--stdin"],
            input=stdin_data,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            cwd=str(project_root),
        )
    except subprocess.TimeoutExpired:
        return 2, [Finding(
            rule_id="RT-LOAD-TIMEOUT",
            severity=Severity.ERROR,
            category=Category.BREAKING,
            file=str(project_root / "project.json"),
            line=0,
            message=f"runtime_loadtest timeout >{timeout}s em {len(xamls)} XAMLs. "
                    "Considere aumentar --runtime-loadtest-timeout ou investigar "
                    "XAMLs gigantes que travam metadata walk.",
        )]
    except OSError as e:
        return 2, [_infra_finding(
            project_root,
            f"runtime_loadtest subprocess OSError: {type(e).__name__}: {e}. "
            "Binary corrupto ou permissão negada?"
        )]

    findings = _parse_output(proc.stdout, project_root, proc.stderr)
    return proc.returncode, findings


def _infra_finding(project_root: Path, message: str) -> Finding:
    """Helper pra finding diagnóstico de infra (binary/timeout/JSON)."""
    return Finding(
        rule_id="RT-LOAD-INFRA",
        severity=Severity.WARN,
        category=Category.METADATA,
        file=str(project_root / "project.json"),
        line=0,
        message=message,
        fix_prose=(
            "Gate runtime_loadtest skipa silenciosamente se binary não built. "
            "Build host .NET via: cd .uip-toolchain/experiments/runtime_loadtest && "
            "dotnet build -c Release. Requer dotnet SDK 6+."
        ),
    )


def _infer_missing_arg_type(arg_name: str, xaml_file: Path,
                              project_root: Path) -> tuple[str | None, str]:
    """Phase 9E: 3-layer resolution chain pra missing-arg type inference.

    Returns (inferred_type, source). Source ∈ {"canonical", "invocation_xref",
    "hungarian", ""}. Empty source = all 3 layers miss → HALT case.

    L1: canonical Sicoob/REFramework table (1254 args mined from corpus).
    L2: invocation cross-reference — find callers of this XAML em project,
        majority-vote arg type from `<ui:InvokeWorkflowFile.Arguments>`.
    L3: Sicoob Hungarian convention prefix match (St=String, Int=Int32, etc.).
    """
    # Lazy import — these modules are heavy + only needed when finding triggers
    # the missing-arg path. Avoids penalising the common-case gate run.
    try:
        from . import _canonical_args as canonical
    except ImportError:
        canonical = None
    try:
        from . import invocation_xref as xref
    except ImportError:
        xref = None
    try:
        from . import hungarian_inference as hungarian
    except ImportError:
        hungarian = None

    # L1 — canonical table
    if canonical is not None:
        inferred = canonical.lookup(arg_name, min_confidence=0.85)
        if inferred:
            return inferred, "canonical"

    # L2 — invocation cross-reference
    if xref is not None:
        try:
            callers = xref.find_callers(xaml_file, project_root)
            inferred = xref.infer_arg_type_from_callers(arg_name, callers)
            if inferred:
                return inferred, "invocation_xref"
        except (OSError, ValueError):
            pass

    # L3 — Hungarian convention
    if hungarian is not None:
        inferred = hungarian.infer(arg_name)
        if inferred:
            return inferred, "hungarian"

    return None, ""


def _parse_output(stdout: str, project_root: Path, stderr: str = "") -> list[Finding]:
    """Parse JSON stdout em lista de Finding. Mapea Status → rule_id.

    Aceita ambos PascalCase (default System.Text.Json) e camelCase pra
    robustez (caso .NET host mude JsonSerializerOptions futuro).

    Phase 9E: missing-arg detection. Pra cada finding com `'<id>' is not
    declared` em Error, roda 3-layer inference. Se resolve, enriquece com
    fix_mechanical pra dispatch fixer. Se não resolve, emite finding extra
    `RT-LOAD-AMBIGUOUS-ARG` severity HALT.
    """
    findings: list[Finding] = []
    stdout = (stdout or "").strip()
    if not stdout:
        return [_infra_finding(
            project_root,
            f"runtime_loadtest produced empty stdout. Stderr: "
            f"{(stderr or '')[:300]}"
        )]
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as e:
        return [_infra_finding(
            project_root,
            f"runtime_loadtest produced invalid JSON: {e}. Stdout head: "
            f"{stdout[:300]}"
        )]

    for result in data.get("results", []):
        status = result.get("Status") or result.get("status") or "UNKNOWN"
        if status == "OK":
            continue
        file_path = result.get("File") or result.get("file") or "?"
        category_raw = result.get("Category") or result.get("category") or "load"
        error = result.get("Error") or result.get("error") or ""
        line = result.get("Line") or result.get("line") or 0
        rule_id = f"RT-LOAD-{status}"
        # Truncate error message — pra evitar dump gigante de stack trace
        # poluindo JSON output da engine. 400 chars cobre ~3 linhas de
        # mensagem VB compile.
        error_short = (error or "").strip()
        if len(error_short) > 400:
            error_short = error_short[:397] + "..."

        # Phase 9E: missing-arg inference inline.
        # Look pra padrão "'<name>' is not declared" no error string completo
        # (não truncado) pra capturar mesmo se a mensagem for longa.
        fix_mechanical: dict | None = None
        extra_findings: list[Finding] = []
        if status == "INVALID_WORKFLOW":
            for m in _NOT_DECLARED_RE.finditer(error or ""):
                arg_name = m.group("name")
                xaml_file = Path(file_path) if file_path and file_path != "?" else None
                if xaml_file is None:
                    continue
                inferred_type, source = _infer_missing_arg_type(
                    arg_name, xaml_file, project_root,
                )
                if inferred_type:
                    # First-hit wins — fixer consumes one arg per finding. Re-run
                    # do gate vai capturar próximo missing arg se houver chain.
                    fix_mechanical = {
                        "type": "inject_missing_args",
                        "arg_name": arg_name,
                        "inferred_type": inferred_type,
                        "source": source,
                    }
                    break
                # L4 HALT — emite finding paralelo bloqueando pipeline.
                extra_findings.append(Finding(
                    rule_id="RT-LOAD-AMBIGUOUS-ARG",
                    severity=Severity.HALT,
                    category=Category.BREAKING,
                    file=file_path,
                    line=int(line) if line else 0,
                    message=(
                        f"Cannot infer type pra arg ausente '{arg_name}': "
                        f"não está em canonical Sicoob table, nenhum caller "
                        f"declara, e Hungarian prefix convention não bate. "
                        f"Requer decisão manual."
                    ),
                    fix_prose=(
                        f"Adicionar manualmente <x:Property Name=\"{arg_name}\" "
                        f"Type=\"InArgument(<Type>)\"/> em <x:Members> do XAML. "
                        f"Type deve match com: (a) caller "
                        f"InvokeWorkflowFile.Arguments declaration, (b) "
                        f"REFramework standard, ou (c) Sicoob Hungarian "
                        f"convention (St=String, Int=Int32, Bol=Boolean, "
                        f"Dt=DateTime, Dtb=DataTable, etc.). Após fix manual, "
                        f"re-run `uip <project>` pra confirmar gate verde."
                    ),
                ))
                # Only process first not-declared identifier per finding pra
                # evitar duplicate HALT spam quando XAML tem cadeia de refs
                # órfãs — após fix do primeiro, gate re-emits restantes.
                break

        findings.append(Finding(
            rule_id=rule_id,
            severity=Severity.ERROR,
            category=Category.BREAKING,
            file=file_path,
            line=int(line) if line else 0,
            message=f"Runtime load fail [{category_raw}]: {error_short}",
            fix_mechanical=fix_mechanical,
            fix_prose=(
                "Workflow falha em load runtime UiPath (ActivityXamlServices."
                "Load + CacheMetadata). Causas típicas: VB expression compile "
                "error em Variable.Default (smart-quote, parens unbalanced), "
                "type unresolved (assembly ref missing em project.json deps), "
                "malformed Activity tree, required arg sem binding. Abra XAML "
                "em Studio e procure underline vermelho na linha indicada."
            ),
        ))
        findings.extend(extra_findings)
    return findings
