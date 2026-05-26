"""Find DI container access patterns in Studio."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

_DEFAULT_STUDIO = r"C:\Users\lisan\AppData\Local\Programs\UiPathPlatform\Studio\26.0.193-cloud.23060"
STUDIO_DIR = Path(os.environ.get("UIPATH_STUDIO_DIR", _DEFAULT_STUDIO))
RUNTIME_CONFIG = STUDIO_DIR / "UiPath.Studio.runtimeconfig.json"


def main():
    os.environ["DOTNET_ROOT"] = str(STUDIO_DIR)
    sys.path.insert(0, str(STUDIO_DIR))
    from pythonnet import load
    load("coreclr", runtime_config=str(RUNTIME_CONFIG))
    import clr  # noqa: F401
    from System.Reflection import Assembly

    seen: set[str] = set()
    pattern = re.compile(
        r"(ServiceLocator|ServiceRegistry|\bIContainer\b|"
        r"IServiceProvider|Bootstrap\b|AutofacRegister|"
        r"\bResolve\b|ContainerBuilder)",
        re.IGNORECASE,
    )
    for fn in sorted(os.listdir(STUDIO_DIR)):
        if not (fn.startswith("UiPath.Studio") and fn.endswith(".dll")
                and "resources" not in fn.lower()):
            continue
        try:
            asm = Assembly.LoadFrom(str(STUDIO_DIR / fn))
        except Exception:
            continue
        try:
            types = asm.GetTypes()
        except Exception as e:
            try:
                types = [t for t in e.Types if t is not None]
            except Exception:
                continue
        for t in types:
            if t is None:
                continue
            n = t.FullName or ""
            if n in seen:
                continue
            if "<" in n or "+" in n:
                continue
            if pattern.search(n):
                seen.add(n)
                kind = "I" if t.IsInterface else ("A" if t.IsAbstract else "C")
                print(f"{kind} {fn} :: {n}")


if __name__ == "__main__":
    main()
