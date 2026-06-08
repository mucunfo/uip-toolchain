"""Shared readiness helpers for official UiPath RPA package generation."""
from __future__ import annotations

import codecs
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .project_view import iter_project_xamls


PACK_INCOMPATIBLE_STALE_ASSEMBLY_REFERENCES = frozenset({
    "BalaReva.EasyExcel",
    "BalaReva.EasyExcel.Utilities",
    "BalaReva.Excel",
    "CCS_DataUtil",
    "CCS_EstruturaPastas",
    "CCS_SipagDirect",
    "CCS_SipagNet",
    "CCS_Sisbr_2_0",
    "CCS_TOPdesk",
    "Microsoft.Activities",
    "Microsoft.VisualStudio.Services.Common",
    "NPOI",
    "TimeSpan2",
    "UiPath.IntelligentOCR",
    "UiPath.Python",
    "UiPath.Python.Activities",
    "UiPath.Process.Activities",
    "UiPath.Word.Activities",
    "UiPath.Word.Activities.Design",
})


@dataclass(frozen=True)
class OfficialPackPreparation:
    descriptor: Path
    descriptor_changed: bool
    scrubbed_xamls: list[Path]


def _load_project_json(project_root: Path) -> dict[str, Any]:
    project_json = project_root / "project.json"
    if not project_json.is_file():
        raise ValueError(f"project.json not found at {project_json}")
    try:
        data = json.loads(project_json.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid project.json: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("project.json root must be an object")
    return data


def _project_name(project_root: Path) -> str:
    data = _load_project_json(project_root)
    name = data.get("name") or data.get("projectName")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("project.json must define a non-empty 'name'")
    return name.strip()


def _project_version(project_root: Path) -> str:
    data = _load_project_json(project_root)
    version = data.get("projectVersion")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("project.json must define a non-empty 'projectVersion'")
    return version.strip()


def is_packable_project(project_root: Path) -> bool:
    return (
        (project_root / "project.uiproj").is_file()
        or (project_root / "webAppManifest.json").is_file()
    )


def _project_output_type(project_root: Path) -> str | None:
    data = _load_project_json(project_root)
    design = data.get("designOptions")
    if not isinstance(design, dict):
        return None
    output_type = design.get("outputType")
    if not isinstance(output_type, str) or not output_type.strip():
        return None
    output_type = output_type.strip()
    if output_type in {"Process", "Library", "Tests", "Objects"}:
        return output_type
    return None


def _project_description(project_root: Path) -> str:
    data = _load_project_json(project_root)
    description = data.get("description")
    return description.strip() if isinstance(description, str) else ""


def _project_main_file(project_root: Path) -> str:
    data = _load_project_json(project_root)
    main = data.get("main")
    return main.strip() if isinstance(main, str) and main.strip() else "Main.xaml"


def _project_uiproj_data(project_root: Path) -> dict[str, str]:
    return {
        "Name": _project_name(project_root),
        "ProjectType": _project_output_type(project_root) or "Process",
        "Description": _project_description(project_root),
        "MainFile": _project_main_file(project_root),
    }


def sync_project_uiproj(project_root: Path) -> tuple[Path, bool]:
    """Create/update project.uiproj from project.json for modern official pack."""
    if (project_root / "webAppManifest.json").is_file():
        return project_root / "webAppManifest.json", False

    uiproj = project_root / "project.uiproj"
    desired = _project_uiproj_data(project_root)
    current: dict[str, Any] = {}
    if uiproj.is_file():
        try:
            loaded = json.loads(uiproj.read_text(encoding="utf-8-sig"))
            if isinstance(loaded, dict):
                current = loaded
        except json.JSONDecodeError:
            current = {}

    changed = False
    for key, value in desired.items():
        if current.get(key) != value:
            current[key] = value
            changed = True

    if changed or not uiproj.is_file():
        uiproj.write_text(
            json.dumps(current, indent=2) + "\n",
            encoding="utf-8",
        )
        return uiproj, True
    return uiproj, False


def project_uiproj_needs_sync(project_root: Path) -> tuple[bool, str]:
    if (project_root / "webAppManifest.json").is_file():
        return False, "webAppManifest.json present"

    uiproj = project_root / "project.uiproj"
    desired = _project_uiproj_data(project_root)
    if not uiproj.is_file():
        return True, "project.uiproj missing"
    try:
        loaded = json.loads(uiproj.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return True, f"project.uiproj invalid JSON: {exc}"
    if not isinstance(loaded, dict):
        return True, "project.uiproj root must be an object"

    mismatches = [
        f"{key}={loaded.get(key)!r} expected {value!r}"
        for key, value in desired.items()
        if loaded.get(key) != value
    ]
    if mismatches:
        return True, "; ".join(mismatches)
    return False, "project.uiproj synced"


def _project_dependency_names(project_root: Path) -> set[str]:
    data = _load_project_json(project_root)
    dependencies = data.get("dependencies")
    if not isinstance(dependencies, dict):
        return set()
    return {
        str(name).strip()
        for name in dependencies
        if str(name).strip()
    }


def _dependency_covers_assembly(dependency: str, assembly: str) -> bool:
    dependency_lower = dependency.lower()
    assembly_lower = assembly.lower()
    return (
        dependency_lower == assembly_lower
        or dependency_lower.startswith(f"{assembly_lower}.")
        or assembly_lower.startswith(f"{dependency_lower}.")
    )


def _has_dependency_for_assembly(dependencies: set[str], assembly: str) -> bool:
    if assembly.lower().endswith(".design"):
        return assembly.lower() in {dependency.lower() for dependency in dependencies}
    return any(_dependency_covers_assembly(dependency, assembly) for dependency in dependencies)


def _xaml_uses_assembly(text: str, assembly: str) -> bool:
    return re.search(
        rf"assembly\s*=\s*{re.escape(assembly)}(?=[\s\"';>])",
        text,
        flags=re.IGNORECASE,
    ) is not None


def stale_pack_incompatible_assembly_references_for_text(
    project_root: Path,
    text: str,
) -> list[str]:
    dependencies = _project_dependency_names(project_root)
    stale: list[str] = []
    for assembly in sorted(PACK_INCOMPATIBLE_STALE_ASSEMBLY_REFERENCES):
        if _has_dependency_for_assembly(dependencies, assembly):
            continue
        if _xaml_uses_assembly(text, assembly):
            continue
        if re.search(
            rf"<AssemblyReference>{re.escape(assembly)}</AssemblyReference>",
            text,
        ):
            stale.append(assembly)
    return stale


def stale_pack_incompatible_assembly_references_for_file(
    project_root: Path,
    xaml: Path,
) -> list[str]:
    try:
        text = xaml.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return []
    return stale_pack_incompatible_assembly_references_for_text(project_root, text)


def scrub_pack_incompatible_assembly_references(project_root: Path) -> list[Path]:
    """Remove stale AssemblyReference lines that make modern headless pack fail."""
    changed: list[Path] = []

    for xaml in iter_project_xamls(project_root):
        raw = xaml.read_bytes()
        has_bom = raw.startswith(codecs.BOM_UTF8)
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            continue

        updated = text
        for assembly in stale_pack_incompatible_assembly_references_for_text(
            project_root,
            updated,
        ):
            updated = re.sub(
                rf"\r?\n[ \t]*<AssemblyReference>{re.escape(assembly)}</AssemblyReference>",
                "",
                updated,
            )

        if updated != text:
            payload = updated.encode("utf-8")
            if has_bom:
                payload = codecs.BOM_UTF8 + payload
            xaml.write_bytes(payload)
            changed.append(xaml)

    return changed


def prepare_project_for_official_pack(project_root: Path) -> OfficialPackPreparation:
    descriptor, descriptor_changed = sync_project_uiproj(project_root)
    scrubbed = scrub_pack_incompatible_assembly_references(project_root)
    return OfficialPackPreparation(
        descriptor=descriptor,
        descriptor_changed=descriptor_changed,
        scrubbed_xamls=scrubbed,
    )
