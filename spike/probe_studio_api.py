"""Reflection probe: enumerate Studio types/methods matching 'Import' + 'Reference'.

Goal: find canonical entry point for Studio "Import References" workflow operation.

Usage:
    python spike/probe_studio_api.py [filter_keyword]

Output: lines `<assembly> :: <type> :: <method>(<sig>)`. Stdout only.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

_DEFAULT_STUDIO = r"C:\Users\lisan\AppData\Local\Programs\UiPathPlatform\Studio\26.0.193-cloud.23060"
STUDIO_DIR = Path(os.environ.get("UIPATH_STUDIO_DIR", _DEFAULT_STUDIO))
RUNTIME_CONFIG = STUDIO_DIR / "UiPath.Studio.runtimeconfig.json"

CANDIDATE_DLLS = [
    "UiPath.Studio.Plugin.Workflow.dll",
    "UiPath.Studio.Plugin.Workflow.Configuration.dll",
    "UiPath.Studio.Plugin.Workflow.Shared.dll",
    "UiPath.Studio.Plugin.Workflow.Shell.dll",
    "UiPath.Studio.ProjectMigration.dll",
    "UiPath.Studio.ProjectPreprocessor.dll",
    "UiPath.Studio.Workflow.ActivitiesMetadata.dll",
    "UiPath.Studio.Workflow.CodeAnalysis.dll",
    "UiPath.Studio.Workflow.Shared.dll",
    "UiPath.Studio.Workflow.ProjectActivities.dll",
    "UiPath.Studio.WorkflowCompiler.Shared.dll",
    "UiPath.Studio.ActivitiesInformation.dll",
    "UiPath.Studio.ActivitiesMetadata.dll",
    "UiPath.Studio.Activities.Api.dll",
    "UiPath.Studio.NugetPackageRestorer.dll",
    "UiPath.Studio.Project.dll",
    "UiPath.Studio.Project.Desktop.dll",
    "UiPath.Studio.Project.Client.dll",
    "UiPath.Studio.Core.dll",
]


def boot_clr():
    os.environ["DOTNET_ROOT"] = str(STUDIO_DIR)
    sys.path.insert(0, str(STUDIO_DIR))
    from pythonnet import load
    load("coreclr", runtime_config=str(RUNTIME_CONFIG))
    import clr  # noqa: F401  (side effect: prime CLR)
    return clr


def main(keyword: str = "import"):
    clr = boot_clr()
    from System.Reflection import Assembly

    keyword_re = re.compile(keyword, re.IGNORECASE)
    refs_re = re.compile(r"reference", re.IGNORECASE)

    for dll_name in CANDIDATE_DLLS:
        dll_path = STUDIO_DIR / dll_name
        if not dll_path.is_file():
            print(f"# SKIP missing: {dll_name}", file=sys.stderr)
            continue
        try:
            asm = Assembly.LoadFrom(str(dll_path))
        except Exception as e:
            print(f"# FAIL load {dll_name}: {type(e).__name__}: {e}", file=sys.stderr)
            continue

        try:
            types = asm.GetTypes()
        except Exception as e:
            inner = getattr(e, "LoaderExceptions", None)
            print(f"# PARTIAL GetTypes {dll_name}: {type(e).__name__}", file=sys.stderr)
            try:
                # ReflectionTypeLoadException -> use Types prop (some nulls).
                types = [t for t in e.Types if t is not None]  # type: ignore[attr-defined]
            except Exception:
                continue

        for t in types:
            if t is None:
                continue
            full_name = t.FullName or ""
            type_hit = keyword_re.search(full_name) and refs_re.search(full_name)
            try:
                methods = t.GetMethods()
            except Exception:
                methods = []
            for m in methods:
                method_name = m.Name or ""
                method_hit = (keyword_re.search(method_name) and
                              refs_re.search(method_name))
                if type_hit or method_hit:
                    try:
                        params = ", ".join(
                            f"{p.ParameterType.Name} {p.Name}"
                            for p in m.GetParameters()
                        )
                    except Exception:
                        params = "?"
                    print(f"{dll_name} :: {full_name} :: {method_name}({params})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "import")
