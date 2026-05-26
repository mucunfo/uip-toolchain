"""Probe specific Studio types: dump methods/properties/ctors.

Pass type-fullname args, or use defaults.
Usage:
    python spike/probe_specific_types.py [type_fullname [type_fullname ...]]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_DEFAULT_STUDIO = r"C:\Users\lisan\AppData\Local\Programs\UiPathPlatform\Studio\26.0.193-cloud.23060"
STUDIO_DIR = Path(os.environ.get("UIPATH_STUDIO_DIR", _DEFAULT_STUDIO))
RUNTIME_CONFIG = STUDIO_DIR / "UiPath.Studio.runtimeconfig.json"

DEFAULT_TARGETS = [
    "UiPath.Studio.Plugin.Workflow.Services.Interfaces.IXamlMigrationShellService",
    "UiPath.Studio.Plugin.Workflow.Services.XamlMigrationShellEndpoint",
    "UiPath.Studio.ProjectPreprocessor.IProjectPreprocessorService",
    "UiPath.Studio.ProjectPreprocessor.Services.ProjectPreprocessorService",
    "UiPath.Studio.Plugin.Workflow.Services.Interfaces.IXamlMigrationService",
    "UiPath.Studio.Plugin.Workflow.Services.XamlMigrationProjectEndpoint",
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


def dump_type(t):
    print(f"\n=== {t.FullName} ===")
    print(f"  IsInterface: {t.IsInterface}  IsAbstract: {t.IsAbstract}")
    if t.BaseType:
        print(f"  Base: {t.BaseType.FullName}")
    try:
        interfaces = [i.FullName for i in t.GetInterfaces()]
        if interfaces:
            print(f"  Implements: {', '.join(interfaces)}")
    except Exception:
        pass

    print("  -- Constructors --")
    try:
        for c in t.GetConstructors():
            params = ", ".join(f"{p.ParameterType.Name} {p.Name}" for p in c.GetParameters())
            print(f"    .ctor({params})")
    except Exception:
        pass

    print("  -- Methods --")
    try:
        for m in t.GetMethods():
            if m.DeclaringType.FullName == "System.Object":
                continue
            if not m.IsPublic:
                continue
            params = ", ".join(f"{p.ParameterType.Name} {p.Name}" for p in m.GetParameters())
            ret = m.ReturnType.Name if m.ReturnType else "void"
            print(f"    {ret} {m.Name}({params})")
    except Exception:
        pass

    print("  -- Properties --")
    try:
        for p in t.GetProperties():
            print(f"    {p.PropertyType.Name} {p.Name}  R={p.CanRead} W={p.CanWrite}")
    except Exception:
        pass


def main():
    boot_clr()
    from System.Reflection import Assembly

    targets = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_TARGETS
    target_set = set(targets)

    found: dict[str, "Type"] = {}
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
            if t.FullName in target_set and t.FullName not in found:
                found[t.FullName] = t

    for tgt in targets:
        t = found.get(tgt)
        if t is None:
            print(f"\n# MISS: {tgt}", file=sys.stderr)
            continue
        dump_type(t)


if __name__ == "__main__":
    main()
