"""Try directly constructing XamlMigrationProjectEndpoint with minimal deps.

Tests:
  T1: Construct with None/null deps -> see what fails (which deps are critical)
  T2: Try resolve via reflection on a freshly-built Autofac container
  T3: If accessible, call ApplyMigration on a real XAML

Outputs a verdict: which integration path is realistic.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_DEFAULT_STUDIO = r"C:\Users\lisan\AppData\Local\Programs\UiPathPlatform\Studio\26.0.193-cloud.23060"
STUDIO_DIR = Path(os.environ.get("UIPATH_STUDIO_DIR", _DEFAULT_STUDIO))
RUNTIME_CONFIG = STUDIO_DIR / "UiPath.Studio.runtimeconfig.json"


def boot_clr():
    os.environ["DOTNET_ROOT"] = str(STUDIO_DIR)
    sys.path.insert(0, str(STUDIO_DIR))
    from pythonnet import load
    load("coreclr", runtime_config=str(RUNTIME_CONFIG))
    import clr  # noqa: F401


def t1_construct_null():
    """T1: Try ctor with null deps."""
    print("=== T1: Construct XamlMigrationProjectEndpoint with null deps ===")
    from System.Reflection import Assembly
    asm = Assembly.LoadFrom(str(STUDIO_DIR / "UiPath.Studio.Plugin.Workflow.dll"))
    try:
        types = asm.GetTypes()
    except Exception as e:
        types = [t for t in e.Types if t is not None]
    by_name = {t.FullName: t for t in types if t is not None and t.FullName}
    endpoint_t = by_name["UiPath.Studio.Plugin.Workflow.Services.XamlMigrationProjectEndpoint"]
    from System import Activator
    try:
        ctor = endpoint_t.GetConstructors()[0]
        inst = ctor.Invoke([None, None])
        print(f"  OK ctor with null deps: {inst}")
        return inst
    except Exception as e:
        print(f"  FAIL ctor: {type(e).__name__}: {e}")
        return None


def t2_autofac_resolve():
    """T2: Try resolving via Autofac container built from ServiceLocatorAutofac()."""
    print("\n=== T2: Resolve via ServiceLocatorAutofac (empty container) ===")
    from System.Reflection import Assembly
    asm_app = Assembly.LoadFrom(str(STUDIO_DIR / "UiPath.Studio.App.dll"))
    try:
        types = asm_app.GetTypes()
    except Exception as e:
        types = [t for t in e.Types if t is not None]
    by_name = {t.FullName: t for t in types if t is not None and t.FullName}
    sl_type = by_name.get("UiPath.Studio.App.ServiceLocator.ServiceLocatorAutofac")
    if sl_type is None:
        print("  FAIL: ServiceLocatorAutofac not found")
        return None
    try:
        sl = sl_type.GetConstructors()[0].Invoke([])  # parameterless ctor
        print(f"  OK SL instantiated: {sl}")
    except Exception as e:
        print(f"  FAIL SL ctor: {type(e).__name__}: {e}")
        return None

    # Try ResolveType<IXamlMigrationShellService>()
    asm_wf = Assembly.LoadFrom(str(STUDIO_DIR / "UiPath.Studio.Plugin.Workflow.Shared.dll"))
    try:
        wf_types = asm_wf.GetTypes()
    except Exception as e:
        wf_types = [t for t in e.Types if t is not None]
    wf_by = {t.FullName: t for t in wf_types if t is not None and t.FullName}
    shell_iface = wf_by.get(
        "UiPath.Studio.Plugin.Workflow.Services.Interfaces.IXamlMigrationShellService"
    )
    if shell_iface is None:
        print("  FAIL: IXamlMigrationShellService iface missing in Shared")
        return None
    print(f"  IFACE found: {shell_iface}")

    # ResolveType is generic — call non-generic Object ResolveType(Type)
    try:
        resolve = sl_type.GetMethod("ResolveType", [type(shell_iface)])
        result = resolve.Invoke(sl, [shell_iface])
        print(f"  OK ResolveType returned: {result}")
        return result
    except Exception as e:
        print(f"  FAIL ResolveType: {type(e).__name__}: {e}")
        return None


def t3_inspect_cli_bootstrap():
    """T3: Inspect what CliApplication's parameterless ctor does."""
    print("\n=== T3: Inspect CliApplication parameterless ctor ===")
    from System.Reflection import Assembly
    asm = Assembly.LoadFrom(str(STUDIO_DIR / "UiPath.Studio.CommandLine.dll"))
    try:
        types = asm.GetTypes()
    except Exception as e:
        types = [t for t in e.Types if t is not None]
    by_name = {t.FullName: t for t in types if t is not None and t.FullName}
    cli_app = by_name.get("UiPath.Studio.CommandLine.Application.CliApplication")
    if cli_app is None:
        print("  FAIL: CliApplication missing")
        return None
    try:
        ctor = next(c for c in cli_app.GetConstructors() if c.GetParameters().Length == 0)
        print(f"  parameterless ctor: {ctor}")
        # Don't invoke — likely heavy. Just confirm structure.
        return ctor
    except Exception as e:
        print(f"  FAIL parameterless ctor: {type(e).__name__}: {e}")
        return None


def main():
    boot_clr()
    print(f"Studio: {STUDIO_DIR}")
    t1_construct_null()
    t2_autofac_resolve()
    t3_inspect_cli_bootstrap()


if __name__ == "__main__":
    main()
