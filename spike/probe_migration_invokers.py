"""Find callers + DI registrations of IXamlMigrationService across Studio assemblies.

Goal: identify the *higher-level* command/menu that triggers "Import References"
auto-fix, so we can call it without manually constructing the DI graph.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

_DEFAULT_STUDIO = r"C:\Users\lisan\AppData\Local\Programs\UiPathPlatform\Studio\26.0.193-cloud.23060"
STUDIO_DIR = Path(os.environ.get("UIPATH_STUDIO_DIR", _DEFAULT_STUDIO))
RUNTIME_CONFIG = STUDIO_DIR / "UiPath.Studio.runtimeconfig.json"

# Search all Studio DLLs root-level.
TARGET_KEYWORDS = [
    "XamlMigration",
    "ImportRefs",
    "MigrationCommand",
    "FixReferences",
    "ProjectPreprocessor",
    "WorkflowMigration",
    "MigrateXaml",
]


def boot_clr():
    os.environ["DOTNET_ROOT"] = str(STUDIO_DIR)
    sys.path.insert(0, str(STUDIO_DIR))
    from pythonnet import load
    load("coreclr", runtime_config=str(RUNTIME_CONFIG))
    import clr  # noqa: F401
    return clr


def all_dlls():
    for f in sorted(os.listdir(STUDIO_DIR)):
        if f.startswith("UiPath.Studio") and f.endswith(".dll") and "resources" not in f.lower():
            yield STUDIO_DIR / f


def main():
    boot_clr()
    from System.Reflection import Assembly

    keyword_re = re.compile("|".join(TARGET_KEYWORDS), re.IGNORECASE)

    seen_types: set[str] = set()
    for dll_path in all_dlls():
        try:
            asm = Assembly.LoadFrom(str(dll_path))
        except Exception:
            continue
        try:
            types = asm.GetTypes()
        except Exception as e:
            try:
                types = [t for t in e.Types if t is not None]  # type: ignore
            except Exception:
                continue
        for t in types:
            if t is None:
                continue
            full = t.FullName or ""
            if full in seen_types:
                continue
            if keyword_re.search(full):
                seen_types.add(full)
                kind = ("interface" if t.IsInterface else
                        ("abstract" if t.IsAbstract else "class"))
                print(f"{dll_path.name} :: {full}  [{kind}]")


if __name__ == "__main__":
    main()
