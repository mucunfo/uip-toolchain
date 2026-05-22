"""Spike: invoke Studio's XamlMigrationProjectEndpoint.ApplyMigration on a XAML.

Approach:
  1. Construct XamlMigrationProjectEndpoint(null, null) -- T1 confirmed PASS.
  2. Make a working copy of pre-fix XAML.
  3. Call ApplyMigration(working_copy_path) -- async Task.
  4. Wait for completion.
  5. Diff vs canonical (engine-fixed) form.

Goal: empirical evidence whether Studio API can be called outside Studio UI
to produce canonical XAML matching the "Import References" auto-fix output.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

REPO = Path(r"C:\Users\lisan\OneDrive - Sicoob\Projects\.uipath-rules")
_DEFAULT_STUDIO = r"C:\Users\lisan\AppData\Local\Programs\UiPathPlatform\Studio\26.0.193-cloud.23060"
STUDIO_DIR = Path(os.environ.get("UIPATH_STUDIO_DIR", _DEFAULT_STUDIO))
RUNTIME_CONFIG = STUDIO_DIR / "UiPath.Studio.runtimeconfig.json"

PRE_FIX = REPO / ".tmp" / "RetryCurrentTransaction.pre-studio.xaml"
CANONICAL = REPO / ".tmp" / "RetryCurrentTransaction.canonical.xaml"
WORK_COPY = REPO / ".tmp" / "RetryCurrentTransaction.spike-attempt.xaml"


def boot_clr():
    os.environ["DOTNET_ROOT"] = str(STUDIO_DIR)
    sys.path.insert(0, str(STUDIO_DIR))
    from pythonnet import load
    load("coreclr", runtime_config=str(RUNTIME_CONFIG))
    import clr  # noqa: F401


def get_type(asm_filename: str, type_fullname: str):
    from System.Reflection import Assembly
    asm = Assembly.LoadFrom(str(STUDIO_DIR / asm_filename))
    try:
        types = asm.GetTypes()
    except Exception as e:
        types = [t for t in e.Types if t is not None]
    for t in types:
        if t is not None and t.FullName == type_fullname:
            return t
    raise RuntimeError(f"Type {type_fullname} not in {asm_filename}")


def main():
    if not PRE_FIX.is_file():
        print(f"ABORT: pre-fix snapshot missing at {PRE_FIX}", file=sys.stderr)
        return 2
    if not CANONICAL.is_file():
        print(f"ABORT: canonical snapshot missing at {CANONICAL}", file=sys.stderr)
        return 2

    shutil.copy2(PRE_FIX, WORK_COPY)
    print(f"[spike] working copy: {WORK_COPY}")
    print(f"[spike] size pre:  {WORK_COPY.stat().st_size} bytes")

    boot_clr()

    EndpointT = get_type(
        "UiPath.Studio.Plugin.Workflow.dll",
        "UiPath.Studio.Plugin.Workflow.Services.XamlMigrationProjectEndpoint",
    )

    print(f"[spike] type: {EndpointT.FullName}")
    ctor = EndpointT.GetConstructors()[0]
    param_count = ctor.GetParameters().Length
    print(f"[spike] ctor params: {param_count}")
    null_args = [None] * param_count

    try:
        endpoint = ctor.Invoke(null_args)
        print(f"[spike] OK constructed with {param_count}x null deps")
    except Exception as e:
        print(f"[spike] FAIL ctor: {type(e).__name__}: {e}")
        return 3

    # Get the ApplyMigration(String) overload.
    apply_method = None
    for m in EndpointT.GetMethods():
        if m.Name != "ApplyMigration":
            continue
        ps = m.GetParameters()
        if ps.Length == 1 and ps[0].ParameterType.FullName == "System.String":
            apply_method = m
            break
    if apply_method is None:
        print("[spike] FAIL: ApplyMigration(String) not found", file=sys.stderr)
        return 4

    print(f"[spike] calling ApplyMigration('{WORK_COPY.name}')")
    try:
        task = apply_method.Invoke(endpoint, [str(WORK_COPY)])
        print(f"[spike] returned: {task}")
    except Exception as e:
        print(f"[spike] FAIL Invoke: {type(e).__name__}: {e}")
        # Print inner exceptions
        inner = getattr(e, "InnerException", None)
        depth = 0
        while inner is not None and depth < 5:
            print(f"   inner[{depth}]: {type(inner).__name__}: {inner}")
            inner = getattr(inner, "InnerException", None)
            depth += 1
        return 5

    # task is Task<bool> per signature; wait synchronously.
    try:
        from System.Threading.Tasks import Task
        task.Wait(30000)  # 30s timeout
        print(f"[spike] task completed: IsCompleted={task.IsCompleted}, "
              f"IsFaulted={task.IsFaulted}")
        if task.IsFaulted:
            ex = task.Exception
            print(f"[spike] task fault: {ex}")
            return 6
        result = task.Result  # bool
        print(f"[spike] result: {result}")
    except Exception as e:
        print(f"[spike] FAIL Wait/Result: {type(e).__name__}: {e}")
        return 7

    print(f"[spike] size post: {WORK_COPY.stat().st_size} bytes")
    pre_text = PRE_FIX.read_text(encoding="utf-8")
    post_text = WORK_COPY.read_text(encoding="utf-8")
    canon_text = CANONICAL.read_text(encoding="utf-8")

    if post_text == pre_text:
        print("[spike] DIFF: no change between pre and post (Studio left file alone)")
    elif post_text == canon_text:
        print("[spike] DIFF: post == canonical (PERFECT MATCH)")
    else:
        print("[spike] DIFF: post differs from BOTH pre and canonical (partial fix)")
        # Quick line-by-line head comparison
        for i, (a, b) in enumerate(zip(post_text.splitlines(), canon_text.splitlines())):
            if a != b:
                print(f"   first divergence at line {i+1}:")
                print(f"     spike : {a[:160]}")
                print(f"     canon : {b[:160]}")
                break

    return 0


if __name__ == "__main__":
    sys.exit(main())
