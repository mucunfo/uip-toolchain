"""Guarded legacy Activity Migrator runner - pre-flight + halt detection.

`migrate-windows` still invokes the Studio CommandLine Activity Migrator for
old Windows-Legacy/Legacy projects. Plain subprocess timeout is not enough
for two production failure modes:

1. uipcli can stall on license, cloud heartbeat, NuGet feed, or file-lock I/O
   without consuming CPU. A hard timeout then burns the full budget with poor
   diagnostics.

2. Without environment preflight, Studio install or cloud reachability errors
   happen inside the heavy migrator process and produce noisy failures.

This module keeps that legacy bridge isolated from modern review/fix gates:

- `preflight()` performs fast checks before a heavy invocation.
- `run_uipcli_guarded()` uses Popen plus CPU-delta watchdog and kill-tree,
  returning structured `halt_reason` data.

API stable; migrate.py consumes `UipcliResult`.
"""
from __future__ import annotations

import os
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

try:
    import psutil  # type: ignore
    _PSUTIL_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PSUTIL_AVAILABLE = False


# Halt-detect defaults. Empirical choice:
#   - Migrator normal: CPU is active for long blocks during rewrite and restore.
#     Idle > 60s is a reliable stall signature for license, cloud heartbeat,
#     or file-lock waits.
#   - cpu_floor=0.5s: if total increment is < 0.5s in the window, treat it
#     as stalled with margin for timer skew and measurement noise.
DEFAULT_HALT_WINDOW_SEC = 60
DEFAULT_HALT_CPU_FLOOR_SEC = 0.5
DEFAULT_POLL_INTERVAL_SEC = 5
# uipcli --version cold start: 15-25s típico em Sicoob (Studio service init +
# license check). Casos observados em prod: 60-90s sob carga / disco frio.
# 90s = teto seguro; > 90s = instalação travada de fato.
PREFLIGHT_VERSION_TIMEOUT_SEC = 90
PREFLIGHT_SOCKET_TIMEOUT_SEC = 3

# Cache module-level: preflight only needs one cold start per process.


def _console_spawn_attrs() -> tuple[int, "subprocess.STARTUPINFO | None"]:
    """Windows-only console handling para Popen de uipcli.

    uipcli Studio v26 cloud requer console handle alocado pra iniciar.
    Sem console (CREATE_NO_WINDOW ou stdout=PIPE puro) trava em AllocConsole.
    Trade-off histórico: CREATE_NEW_CONSOLE resolveu hang mas abre console
    visível a cada gate — atrapalha workflow do dev.

    Solução: CREATE_NEW_CONSOLE + STARTUPINFO(STARTF_USESHOWWINDOW, SW_HIDE).
    Console alocada (uipcli happy), janela invisível.

    Env var `UIP_TOOLCHAIN_SHOW_CLI_CONSOLE=1` força console visível — escape
    hatch se SW_HIDE regredir hang em ambiente específico, ou pra debug
    quando precisar ver stdout cru do uipcli.

    No-op em não-Windows: returna (0, None).
    """
    creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
    if not creationflags or not hasattr(subprocess, "STARTUPINFO"):
        return 0, None
    if os.environ.get("UIP_TOOLCHAIN_SHOW_CLI_CONSOLE") == "1":
        return creationflags, None
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE
    return creationflags, si


@dataclass
class PreflightResult:
    """Status de pré-checks rápidos antes de invocar uipcli pesado."""
    ok: bool
    uipcli_responsive: bool = False
    uipcli_version: str = ""
    cloud_reachable: bool = False
    cloud_host: str = ""
    diagnose: str = ""  # Razão da falha, vazia se ok=True

    def as_message(self) -> str:
        """Formata pra log / Finding.message."""
        if self.ok:
            return (f"preflight OK: uipcli={self.uipcli_version} "
                    f"cloud={self.cloud_host} reachable")
        return f"preflight FAIL: {self.diagnose}"


@dataclass
class UipcliResult:
    """Resultado normalizado de uma invocação uipcli guarded."""
    completed: bool                      # True se o processo terminou natural
    returncode: int                      # -1 se foi morto pelo guard
    stdout: str = ""
    stderr: str = ""
    duration_sec: float = 0.0
    halt_reason: str | None = None       # None|timeout|halt_no_cpu|preflight_fail|spawn_fail
    halt_detail: str = ""                # Mensagem detalhada do halt
    preflight: PreflightResult | None = None

    @property
    def succeeded(self) -> bool:
        """True só se completed + exit zero. Halt/timeout/preflight_fail = False."""
        return self.completed and self.returncode == 0

    def as_diagnostic(self) -> str:
        """Formata pra mensagem usuário-visível."""
        if self.halt_reason == "preflight_fail":
            return self.preflight.as_message() if self.preflight else "preflight FAIL"
        if self.halt_reason == "halt_no_cpu":
            return (f"uipcli STALLED após {self.duration_sec:.0f}s sem CPU "
                    f"({self.halt_detail}). Kill-tree disparado.")
        if self.halt_reason == "timeout":
            return f"uipcli TIMEOUT em {self.duration_sec:.0f}s (limite duro)."
        if self.halt_reason == "spawn_fail":
            return f"uipcli SPAWN FAIL: {self.halt_detail}"
        if self.succeeded:
            return f"uipcli OK ({self.duration_sec:.1f}s, exit 0)"
        return (f"uipcli exit {self.returncode} ({self.duration_sec:.1f}s). "
                f"stderr tail: {(self.stderr or '')[-200:]!r}")


def preflight(
    uipcli_path: Path,
    cloud_host: str = "cloud.uipath.com",
    cloud_port: int = 443,
) -> PreflightResult:
    """Health checks before invoking the Activity Migrator.

    Typical call is <8s on the happy path and <10s on failure.

    Checks:
      1. `uipcli --version` returns quickly.
      2. TCP socket to cloud.uipath.com:443 connects quickly.

    Caching: OK result is memoized by (uipcli_path, cloud_host:port).
    Failures are not cached so the next migration attempt can retry.
    """
    cache_key = f"{uipcli_path}|{cloud_host}:{cloud_port}"
    cached = _PREFLIGHT_CACHE.get(cache_key)
    if cached is not None and cached.ok:
        return cached

    res = PreflightResult(ok=False, cloud_host=cloud_host)

    # Check 1: uipcli responsive.
    # subprocess.run(timeout=) é UNRELIABLE no Windows: quando child spawna
    # grandchildren ou abre named pipes, communicate() pode pendurar
    # MUITO além do timeout aguardando reader thread join. Observado em
    # produção: subprocess.run(timeout=30) pendurando 5+min.
    # Workaround: Popen + watchdog manual + kill-tree via psutil.
    #
    # CRITICAL: pipe MUST drain durante poll loop. uipcli --version em
    # Studio v26 cospe ~10 linhas help/commands list (~2-4KB). Pipe
    # buffer Windows = 4-64KB; child block em write quando cheio sem
    # reader. Poll loop nunca vê exit → timeout 90s false-positive.
    # Background threads drenam stdout/stderr continuamente.
    import threading
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []

    def _drain(pipe, chunks):
        try:
            for line in iter(pipe.readline, ""):
                chunks.append(line)
        except (OSError, ValueError):
            pass
        finally:
            try:
                pipe.close()
            except OSError:
                pass

    # Windows-only: Studio v26 cloud uipcli requer console handle alocado
    # para iniciar. Sem console (CREATE_NO_WINDOW implícito) trava em
    # AllocConsole. CREATE_NEW_CONSOLE + SW_HIDE: aloca console mas
    # janela invisível. uipcli completa cold start em ~9s vs 90s+ hang.
    # Env UIP_TOOLCHAIN_SHOW_CLI_CONSOLE=1 reverte pra console visível
    # (escape hatch debug / regressão). No-op em não-Windows.
    _creationflags, _startupinfo = _console_spawn_attrs()
    try:
        popen = subprocess.Popen(
            [str(uipcli_path), "--version"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace",
            creationflags=_creationflags,
            startupinfo=_startupinfo,
        )
    except OSError as e:
        res.diagnose = f"uipcli spawn fail: {e}"
        return res

    t_out = threading.Thread(target=_drain, args=(popen.stdout, stdout_chunks),
                             daemon=True)
    t_err = threading.Thread(target=_drain, args=(popen.stderr, stderr_chunks),
                             daemon=True)
    t_out.start()
    t_err.start()

    started = time.monotonic()
    while True:
        rc = popen.poll()
        if rc is not None:
            break
        if time.monotonic() - started >= PREFLIGHT_VERSION_TIMEOUT_SEC:
            _kill_tree(popen.pid)
            try:
                popen.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            res.diagnose = (f"uipcli --version não respondeu em "
                            f"{PREFLIGHT_VERSION_TIMEOUT_SEC}s — instalação "
                            f"corrompida ou Studio service travado.")
            return res
        time.sleep(0.5)

    # Reader threads convergem pós-exit (pipes EOF). Join curto.
    t_out.join(timeout=2)
    t_err.join(timeout=2)
    stdout = "".join(stdout_chunks)
    stderr = "".join(stderr_chunks)

    # Responsive = binary spawnou + completou dentro timeout. Exit code
    # irrelevante: uipcli sem subcomando legítimo retorna 127 ("command not
    # found" interno) mas isso prova que binário RODA (cospe help). Para
    # preflight não estamos validando comportamento — só liveness.
    res.uipcli_responsive = True
    first_line = (stdout or stderr or "").strip().splitlines()
    res.uipcli_version = first_line[0] if first_line else f"(rc={popen.returncode})"

    # Check 2: cloud reachable (uipcli faz heartbeat síncrono em analyze/publish)
    try:
        with socket.create_connection((cloud_host, cloud_port),
                                       timeout=PREFLIGHT_SOCKET_TIMEOUT_SEC):
            res.cloud_reachable = True
    except (socket.timeout, OSError) as e:
        res.diagnose = (f"{cloud_host}:{cloud_port} inacessível ({e}). uipcli "
                        f"trava em heartbeat. Verifique VPN/proxy/firewall.")
        return res

    res.ok = True
    _PREFLIGHT_CACHE[cache_key] = res
    return res


def _total_cpu_seconds(proc) -> float:
    """Soma user+system CPU time do processo + filhos recursivamente.

    psutil — único path suportado. Sem psutil, retorna 0.0 (halt-detect inativo).
    """
    if not _PSUTIL_AVAILABLE:
        return 0.0
    total = 0.0
    try:
        for p in [proc] + proc.children(recursive=True):
            try:
                t = p.cpu_times()
                total += (t.user or 0.0) + (t.system or 0.0)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return total


def _kill_tree(pid: int) -> None:
    """Kill processo + descendentes. Best-effort, no-raise."""
    if not _PSUTIL_AVAILABLE:
        # Fallback Windows: taskkill /T
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True, timeout=10, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
        return
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            try:
                child.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        parent.kill()
        # gone in 5s ou os.kill via taskkill como fallback
        gone, alive = psutil.wait_procs([parent], timeout=5)
        for p in alive:
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(p.pid), "/T", "/F"],
                    capture_output=True, timeout=5, check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                pass
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass


def run_uipcli_guarded(
    args: list[str],
    timeout_sec: int,
    halt_window_sec: int = DEFAULT_HALT_WINDOW_SEC,
    halt_cpu_floor_sec: float = DEFAULT_HALT_CPU_FLOOR_SEC,
    poll_interval_sec: float = DEFAULT_POLL_INTERVAL_SEC,
    preflight_result: PreflightResult | None = None,
) -> UipcliResult:
    """Spawn uipcli + watchdog CPU-delta. Kill se estalar.

    Args:
        args: comando completo (incluindo path uipcli em args[0]).
        timeout_sec: limite duro de execução (kill irrevogável).
        halt_window_sec: se CPU delta em últimos N segundos < `halt_cpu_floor_sec`,
            consideramos halt e mata. Default 60s.
        halt_cpu_floor_sec: incremento mínimo de CPU na janela pra processo ser
            considerado "vivo". Default 0.5s.
        poll_interval_sec: ciclo de poll. Default 5s.
        preflight_result: se já chamou preflight, passa o resultado pra
            inclusão no result. Caller pode ter aborted before spawn.

    Returns:
        UipcliResult com stdout/stderr/returncode normalizados + halt_reason
        estruturado pra diagnose downstream.
    """
    result = UipcliResult(completed=False, returncode=-1, preflight=preflight_result)
    started = time.monotonic()

    # Spawn process — CREATE_NEW_CONSOLE + SW_HIDE em Windows: Studio v26
    # cloud uipcli precisa console handle alocado pra start. SW_HIDE deixa
    # a janela invisível. Env UIP_TOOLCHAIN_SHOW_CLI_CONSOLE=1 reverte.
    # Mesma justificativa que preflight().
    _creationflags, _startupinfo = _console_spawn_attrs()
    try:
        popen = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=_creationflags,
            startupinfo=_startupinfo,
        )
    except OSError as e:
        result.halt_reason = "spawn_fail"
        result.halt_detail = str(e)
        result.duration_sec = time.monotonic() - started
        return result

    # CRITICAL: drain pipes in background threads. Activity Migrator can emit
    # 10KB+ output. Windows pipe buffer is around 4-64KB; without a reader the
    # child can block when the buffer fills and the poll loop never sees exit.
    import threading
    _stdout_chunks: list[str] = []
    _stderr_chunks: list[str] = []

    def _drain_pipe(pipe, chunks):
        try:
            for line in iter(pipe.readline, ""):
                chunks.append(line)
        except (OSError, ValueError):
            pass
        finally:
            try:
                pipe.close()
            except OSError:
                pass

    _t_out = threading.Thread(target=_drain_pipe,
                              args=(popen.stdout, _stdout_chunks),
                              daemon=True)
    _t_err = threading.Thread(target=_drain_pipe,
                              args=(popen.stderr, _stderr_chunks),
                              daemon=True)
    _t_out.start()
    _t_err.start()

    # CPU-delta tracking history: list[(monotonic_sec, total_cpu_sec)]
    cpu_history: list[tuple[float, float]] = []
    if _PSUTIL_AVAILABLE:
        try:
            ps_proc = psutil.Process(popen.pid)
            cpu_history.append((time.monotonic(), _total_cpu_seconds(ps_proc)))
        except psutil.NoSuchProcess:
            ps_proc = None
    else:
        ps_proc = None

    # Watchdog loop
    halt_reason: str | None = None
    halt_detail = ""
    while True:
        # Process terminou natural?
        ret = popen.poll()
        if ret is not None:
            result.completed = True
            result.returncode = ret
            break

        elapsed = time.monotonic() - started

        # Hard timeout
        if elapsed >= timeout_sec:
            halt_reason = "timeout"
            halt_detail = f"hard limit {timeout_sec}s exceeded"
            break

        # CPU-delta halt detection.
        # Estratégia: comparar CPU acumulada do oldest snapshot (ANTES da
        # janela atual) vs. atual. Se delta < floor E pelo menos
        # halt_window_sec passaram, processo está estagnado.
        # Manter SEMPRE primeira entrada do começo da janela atual (não
        # descartar pelo filtro de tempo) — caso contrário, len(history)<2
        # silencia o check.
        if ps_proc is not None and elapsed >= halt_window_sec:
            try:
                cur_cpu = _total_cpu_seconds(ps_proc)
                now = time.monotonic()
                cpu_history.append((now, cur_cpu))
                # Encontra entrada mais antiga ainda dentro da janela (mas
                # mantém pelo menos uma se todas saíram).
                window_start = now - halt_window_sec
                in_window = [(t, c) for t, c in cpu_history if t >= window_start]
                if not in_window:
                    # Todas antigas — pega a mais recente fora pra anchor.
                    in_window = [cpu_history[-2]] if len(cpu_history) >= 2 else cpu_history[:]
                cpu_history = in_window + ([cpu_history[-1]] if cpu_history[-1] not in in_window else [])
                # Avalia delta entre oldest in-window e atual.
                if len(cpu_history) >= 2:
                    oldest_t, oldest_c = cpu_history[0]
                    span = now - oldest_t
                    delta = cur_cpu - oldest_c
                    # Só dispara se realmente passou halt_window_sec de observação
                    # (evita false-positive em primeiros segundos)
                    if span >= halt_window_sec and delta < halt_cpu_floor_sec:
                        halt_reason = "halt_no_cpu"
                        halt_detail = (f"CPU delta {delta:.2f}s < "
                                       f"{halt_cpu_floor_sec}s em janela de "
                                       f"{span:.0f}s")
                        break
            except psutil.NoSuchProcess:
                pass  # processo morreu durante poll — próxima iteração detecta

        time.sleep(poll_interval_sec)

    # Captura stdout/stderr dos drain threads (chunks acumulados continuamente).
    # Pós-exit (natural ou kill), threads convergem em EOF — join curto.
    if halt_reason in ("timeout", "halt_no_cpu"):
        _kill_tree(popen.pid)
        result.halt_reason = halt_reason
        result.halt_detail = halt_detail
        result.completed = False
        result.returncode = -1
    _t_out.join(timeout=5)
    _t_err.join(timeout=5)
    result.stdout = "".join(_stdout_chunks)
    result.stderr = "".join(_stderr_chunks)

    result.duration_sec = time.monotonic() - started
    return result
