"""Runner orchestrates: project discovery + rule x file iteration."""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

import pathspec

from ._types import Finding, Rule, Severity, ValidationResult, Target
from .context import FileContext, ProjectContext
from .suppressions import parse_suppressions, is_suppressed_at


# Detector signature: (rule, file_ctx, project_ctx) -> list[Finding]
DetectorFn = Callable[[Rule, FileContext, ProjectContext], list[Finding]]


def _default_worker_cap() -> int:
    """nproc/2, max 8. Override via env `RULE_ENGINE_WORKERS=N`."""
    override = os.environ.get("RULE_ENGINE_WORKERS")
    if override:
        try:
            n = int(override)
            if n >= 1:
                return n
        except ValueError:
            pass
    nproc = os.cpu_count() or 4
    return max(1, min(nproc // 2, 8))


def _parallel_enabled() -> bool:
    """Opt-out via `RULE_ENGINE_NO_PARALLEL=1` (debug/repro)."""
    return os.environ.get("RULE_ENGINE_NO_PARALLEL", "").strip() not in (
        "1", "true", "yes",
    )


class Runner:
    def __init__(
        self,
        rules: list[Rule],
        detectors: dict[str, DetectorFn],
        fixers: dict[str, Callable],
    ) -> None:
        self.rules = rules
        self.detectors = detectors
        self.fixers = fixers

    def run(self, project_path: Path | str) -> ValidationResult:
        project_path = Path(project_path)
        result = ValidationResult()

        # Resolve project context
        if (project_path / "project.json").exists():
            try:
                pc = ProjectContext.find_root(project_path / "project.json")
            except Exception:
                pc = None
        else:
            pc = ProjectContext.find_root(project_path)

        if pc is None:
            result.add_internal_error(f"no project.json found at {project_path}")
            return result

        # Filter rules by target
        active_rules = [r for r in self.rules if self._target_matches(r, pc)]

        # Iterate XAMLs + project.json
        files = list(pc.root.rglob("*.xaml"))
        if (pc.root / "project.json").exists():
            files.append(pc.root / "project.json")

        # P2 (2026-05): per-XAML detection paralelo via ThreadPoolExecutor.
        # Detectors são mix de I/O (file read) + CPU (lxml parse, regex).
        # lxml libera GIL durante parse → threading dá CPU parallelism real
        # mesmo sem multiprocessing. ValidationResult.add() é list.append,
        # GIL-atomic em CPython.
        # Cap: nproc/2 max 8 (override via RULE_ENGINE_WORKERS=N).
        # Opt-out determinístico: RULE_ENGINE_NO_PARALLEL=1.
        if _parallel_enabled() and len(files) > 1:
            workers = min(_default_worker_cap(), len(files))
            with ThreadPoolExecutor(max_workers=workers) as ex:
                futures = [
                    ex.submit(self._run_file, fp, active_rules, pc, result)
                    for fp in files
                ]
                for fut in as_completed(futures):
                    # Re-raise se _run_file levantou (não deve — captura interna)
                    fut.result()
        else:
            for file_path in files:
                self._run_file(file_path, active_rules, pc, result)

        return result

    def _target_matches(self, rule: Rule, pc: ProjectContext) -> bool:
        if rule.target == Target.ALL:
            return True
        if rule.target == Target.WINDOWS:
            return pc.target_framework == "Windows"
        if rule.target == Target.LEGACY:
            return pc.target_framework == "Legacy"
        return False

    def _run_file(
        self,
        file_path: Path,
        rules: list[Rule],
        pc: ProjectContext,
        result: ValidationResult,
    ) -> None:
        # Lazy load file context (only if any rule applies)
        try:
            fc: FileContext | None = None
            suppressions = []

            for rule in rules:
                if not self._applies_to(rule, file_path, pc):
                    continue

                detector_name = rule.detect.get("type")
                detector = self.detectors.get(detector_name)
                if detector is None:
                    result.add_internal_error(
                        f"detector '{detector_name}' not registered (rule {rule.id})"
                    )
                    continue

                # Lazy init FileContext
                if fc is None:
                    try:
                        fc = FileContext(file_path)
                    except Exception as e:
                        result.add_internal_error(
                            f"cannot read {file_path}: {type(e).__name__}: {e}"
                        )
                        return
                    suppressions = parse_suppressions(fc.content)

                try:
                    findings = detector(rule, fc, pc)
                except Exception as e:
                    result.findings.append(Finding(
                        rule_id=rule.id, severity=Severity.WARN,
                        category=rule.category, file=str(file_path), line=0,
                        message=f"[INTERNAL] detector {detector_name} crashed: "
                                f"{type(e).__name__}: {e}",
                    ))
                    continue

                # Apply suppressions — ERROR/HALT NUNCA podem ser silenciados
                # (proibição arquitetural; ver CLAUDE.md project root).
                for f in findings:
                    if f.severity in (Severity.WARN, Severity.INFO):
                        if is_suppressed_at(suppressions, f.rule_id, f.line):
                            f.suppressed = True
                    result.add(f)
        except Exception as e:
            result.add_internal_error(
                f"runner crashed on {file_path}: {type(e).__name__}: {e}"
            )

    def _applies_to(self, rule: Rule, file_path: Path, pc: ProjectContext) -> bool:
        applies = rule.applies_to or {}
        rel = file_path.relative_to(pc.root).as_posix()

        include = applies.get("include")
        if include:
            spec = pathspec.PathSpec.from_lines("gitwildmatch", include)
            if not spec.match_file(rel):
                return False

        exclude = applies.get("exclude")
        if exclude:
            spec = pathspec.PathSpec.from_lines("gitwildmatch", exclude)
            if spec.match_file(rel):
                return False

        # project_type filter
        project_type = applies.get("project_type")
        if project_type and pc.project_type not in project_type:
            return False

        return True
