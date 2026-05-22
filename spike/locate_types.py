"""Find which DLL contains a given type by suffix match."""
from __future__ import annotations

import os
import re
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


def main():
    boot_clr()
    from System.Reflection import Assembly

    needles = sys.argv[1:] or [
        "IXamlFileMigration", "ITextExpressionClassMethods",
        "IAssemblyContainer", "XamlFileMigration", "TextExpressionClassMethods",
    ]
    pats = [re.compile(re.escape(n) + r"$") for n in needles]

    for fn in sorted(os.listdir(STUDIO_DIR)):
        if not (fn.startswith("UiPath") and fn.endswith(".dll") and "resources" not in fn.lower()):
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
            if t is None or "<" in (t.FullName or "") or "+" in (t.FullName or ""):
                continue
            full = t.FullName or ""
            for needle, pat in zip(needles, pats):
                # Match either FullName ends with .needle OR name == needle
                short = full.split(".")[-1]
                if short == needle or pat.search(full):
                    kind = "I" if t.IsInterface else ("A" if t.IsAbstract else "C")
                    print(f"{kind} {fn} :: {full}")
                    break


if __name__ == "__main__":
    main()
