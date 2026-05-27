"""migrate_resolver — offline clone de MigratedPackageVersionResolver.GetRecommendedVersion.

Reproduz algoritmo Studio ProjectMigration §6 (Stream E dossier 04) em pure Python.
Permite pre-check pin drift ANTES de invocar Activity Migrator GA Studio.

Algoritmo decompilado de `UiPath.Studio.ProjectMigration.dll::
MigratedPackageVersionResolver.GetRecommendedVersion()`:

    if any p in packages has p.Version == oldVersion:
        return (oldVersion, Same)        # KEEP pin — only if exact version exists for new TFM

    oldVer = NuGetVersion.Parse(oldVersion)
    candidates = packages
                 .Select(p => NuGetVersion.Parse(p.Version))
                 .Where(v => v > oldVer)
                 .OrderBy(v => v)

    if candidates is empty:
        return (oldVersion, Unresolved)

    smallestPatch = candidates.First()
    chosen = candidates
        .TakeWhile(v => v.Major == smallestPatch.Major AND v.Minor == smallestPatch.Minor)
        .OrderByDescending(v => v)
        .First()
    return (chosen.ToString(), Updated)

Fluxo:
  1. Parse project.json::dependencies + targetFramework.
  2. Para cada dep, query NuGet API por versoes compativeis com new TFM (Windows = net6.0-windows7.0).
  3. Aplicar algoritmo GetRecommendedVersion (KeepSame se pin exists, senao upgrade-within-minor).
  4. Retornar lista (pkg_id, current, recommended, action). Action = Same | Updated | Unresolved.

Pin drift = Same em todos = safe migrate. Updated em qualquer = drift target.

Limitations (MVP):
  - TFM filtering nao eh aplicado em fetch_versions (NuGet v3 flat-container nao expoe
    deps por versao sem querying catalog entry per-version). Phase 2.1 deepen TODO.
  - Pre-release SEMPRE excluido (alinhado com Studio `IsPrereleaseIncluded = false`).
  - NuGetVersion semver-like; ambiguidade revision (e.g. "1.2.3.4") tratada com fallback.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable, Optional


# ---------------------------------------------------------------------------
# ResolutionAction
# ---------------------------------------------------------------------------


class ResolutionAction(Enum):
    """Outcome do algoritmo GetRecommendedVersion para um package."""

    SAME = "Same"
    UPDATED = "Updated"
    UNRESOLVED = "Unresolved"


# ---------------------------------------------------------------------------
# NuGetVersion — semver-like ordering compatible com regras NuGet v3.
# ---------------------------------------------------------------------------


_VERSION_RE = re.compile(
    r"""
    ^
    (?P<major>\d+)
    (?:\.(?P<minor>\d+))?
    (?:\.(?P<patch>\d+))?
    (?:\.(?P<revision>\d+))?
    (?:-(?P<prerelease>[0-9A-Za-z.\-]+))?
    (?:\+(?P<build>[0-9A-Za-z.\-]+))?
    $
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class NuGetVersion:
    """Versao NuGet com ordering semver-like.

    Pre-release < release (mesma major.minor.patch).
    Revision (4o segmento) tratada como tie-breaker apos patch.
    Build metadata (+xxx) ignorado em comparisons (alinhado com semver).
    """

    major: int
    minor: int
    patch: int
    revision: Optional[int]
    prerelease: Optional[str]
    original: str

    # -- parsing -----------------------------------------------------------

    @classmethod
    def parse(cls, s: str) -> "NuGetVersion":
        """Parse "25.10.8" / "25.10.8.0" / "25.10.8-preview.1" etc.

        Strip surrounding NuGet range brackets "[1.0.0]" first (caller-friendly).
        Raises ValueError em input invalido.
        """
        if s is None:
            raise ValueError("NuGetVersion.parse: input is None")
        raw = s.strip()
        # UiPath project.json pin shorthand: "[1.0.0]" => exact 1.0.0
        if raw.startswith("[") and raw.endswith("]"):
            raw = raw[1:-1].strip()
        # Range mais complexos ("[1.0.0, 2.0.0)") nao suportados — pega lower-bound.
        if "," in raw:
            raw = raw.split(",", 1)[0].strip().lstrip("[(")
        match = _VERSION_RE.match(raw)
        if not match:
            raise ValueError(f"NuGetVersion.parse: cannot parse {s!r}")
        major = int(match.group("major"))
        minor = int(match.group("minor") or 0)
        patch = int(match.group("patch") or 0)
        revision_raw = match.group("revision")
        revision = int(revision_raw) if revision_raw is not None else None
        prerelease = match.group("prerelease")
        return cls(
            major=major,
            minor=minor,
            patch=patch,
            revision=revision,
            prerelease=prerelease,
            original=s,
        )

    # -- ordering ----------------------------------------------------------

    def _sort_key(self) -> tuple:
        # Pre-release < release: representar release com pre_marker=(1,)
        # e prerelease com pre_marker=(0, prerelease_tuple).
        if self.prerelease is None:
            pre_marker: tuple = (1,)
        else:
            # split por dots para comparison sensata "1 < 2 < 10" se numeric
            tokens = []
            for tok in self.prerelease.split("."):
                if tok.isdigit():
                    tokens.append((0, int(tok)))
                else:
                    tokens.append((1, tok))
            pre_marker = (0, tuple(tokens))
        return (
            self.major,
            self.minor,
            self.patch,
            self.revision if self.revision is not None else 0,
            pre_marker,
        )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, NuGetVersion):
            return NotImplemented
        return self._sort_key() < other._sort_key()

    def __le__(self, other: object) -> bool:
        if not isinstance(other, NuGetVersion):
            return NotImplemented
        return self._sort_key() <= other._sort_key()

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, NuGetVersion):
            return NotImplemented
        return self._sort_key() > other._sort_key()

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, NuGetVersion):
            return NotImplemented
        return self._sort_key() >= other._sort_key()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NuGetVersion):
            return NotImplemented
        return self._sort_key() == other._sort_key()

    def __hash__(self) -> int:
        return hash(self._sort_key())

    def __str__(self) -> str:
        return self.original

    # -- helpers -----------------------------------------------------------

    def is_prerelease(self) -> bool:
        return self.prerelease is not None


# ---------------------------------------------------------------------------
# ResolutionResult
# ---------------------------------------------------------------------------


@dataclass
class ResolutionResult:
    """Outcome per-package do algoritmo GetRecommendedVersion."""

    package_id: str
    current_version: str
    recommended_version: str
    action: ResolutionAction
    candidates_count: int
    reason: str

    def to_dict(self) -> dict:
        return {
            "package_id": self.package_id,
            "current_version": self.current_version,
            "recommended_version": self.recommended_version,
            "action": self.action.value,
            "candidates_count": self.candidates_count,
            "reason": self.reason,
        }


# ---------------------------------------------------------------------------
# NuGet v3 fetch — pure-stdlib, urllib only.
# ---------------------------------------------------------------------------


_NUGET_FLATCONTAINER = "https://api.nuget.org/v3-flatcontainer"


def _http_get_json(url: str, timeout: int = 30) -> dict:
    """GET + JSON parse. Raises urllib.error.URLError ou json.JSONDecodeError."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 — controlled URL
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def fetch_versions(
    package_id: str,
    *,
    target_framework: str = "net6.0-windows7.0",
    include_prerelease: bool = False,
    cache_dir: Optional[Path] = None,
    http_timeout: int = 30,
) -> list[str]:
    """Query NuGet v3 flat-container index para todas versoes de um package.

    URL: https://api.nuget.org/v3-flatcontainer/<lowercased-id>/index.json
    Retorna list de version strings (raw, unparsed).

    Filters:
      - Pre-release excluido unless include_prerelease=True (alinhado Studio).
      - TFM filtering NAO aplicado (MVP). Phase 2.1: query per-version catalog entry
        para checar `dependencies[].targetFramework`.

    Cache: se cache_dir set, persiste `{package_id_lower}_versions.json` com TTL 24h.

    Resilience: 3 retries com backoff exponencial (1s/2s/4s) on transient HTTP errors.
    Em falha terminal: stderr log + raises urllib.error.URLError (caller handles).

    Args:
        package_id: NuGet package id (e.g. "UiPath.System.Activities").
        target_framework: TFM target (info-only, ainda nao filtra).
        include_prerelease: Se True, mantem versoes com `-suffix`.
        cache_dir: Diretorio pra cache JSON. None disable cache.
        http_timeout: Timeout em segundos.

    Returns:
        List of version strings, raw como API retorna (lowercased package_id em URL).
    """
    pkg_lower = package_id.lower()

    # Cache check ----------------------------------------------------------
    cache_path: Optional[Path] = None
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / f"{pkg_lower}_versions.json"
        if cache_path.exists():
            age = time.time() - cache_path.stat().st_mtime
            if age < 24 * 3600:
                try:
                    cached = json.loads(cache_path.read_text(encoding="utf-8"))
                    versions = cached.get("versions", [])
                    return _filter_prerelease(versions, include_prerelease)
                except (json.JSONDecodeError, OSError):
                    pass  # fallthrough refetch

    # HTTP fetch with retries ---------------------------------------------
    url = f"{_NUGET_FLATCONTAINER}/{pkg_lower}/index.json"
    last_err: Optional[Exception] = None
    versions: list[str] = []
    for attempt in range(3):
        try:
            data = _http_get_json(url, timeout=http_timeout)
            versions = list(data.get("versions", []))
            break
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
            last_err = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
            continue
    else:
        # all retries exhausted
        print(
            f"[migrate_resolver] fetch_versions failed for {package_id}: {last_err}",
            file=sys.stderr,
        )
        raise urllib.error.URLError(f"NuGet unreachable for {package_id}: {last_err}")

    # Persist cache --------------------------------------------------------
    if cache_path is not None:
        try:
            cache_path.write_text(
                json.dumps({"package_id": package_id, "versions": versions, "fetched_at": time.time()}),
                encoding="utf-8",
            )
        except OSError:
            pass

    return _filter_prerelease(versions, include_prerelease)


def _filter_prerelease(versions: Iterable[str], include_prerelease: bool) -> list[str]:
    if include_prerelease:
        return list(versions)
    return [v for v in versions if "-" not in v]


# ---------------------------------------------------------------------------
# Phase 2.1 (2026-05): local .nupkgs/ folder source.
# Decisao do usuario: NAO hookar private feed (auth+vpn). Em vez disso, scan
# pasta local com .nupkg files baixados (CCS_*) e extrai id+version do .nuspec
# embedded. Offline, zero network. Suplementa fetch_versions quando NuGet
# public nao conhece o pacote (caso CCS_* proprietarios Sicoob).
# ---------------------------------------------------------------------------


_NUSPEC_NS = "http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd"


def _extract_nuspec_meta(nupkg_path: Path) -> Optional[tuple[str, str]]:
    """Open .nupkg (zip), localize .nuspec na raiz, extract (id, version).

    Returns None se .nuspec faltando, XML malformado, ou metadata incompleto.
    Tolerante: nunca raise, sempre log to stderr em caso de skip.
    """
    try:
        with zipfile.ZipFile(nupkg_path) as zf:
            nuspec_name: Optional[str] = None
            for name in zf.namelist():
                # .nuspec na raiz do nupkg (nao em content/, lib/, etc).
                if name.lower().endswith(".nuspec") and "/" not in name and "\\" not in name:
                    nuspec_name = name
                    break
            if nuspec_name is None:
                print(
                    f"[migrate_resolver] local source: no .nuspec in {nupkg_path.name}",
                    file=sys.stderr,
                )
                return None
            raw = zf.read(nuspec_name).decode("utf-8-sig")
        root = ET.fromstring(raw)
    except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError, UnicodeDecodeError) as exc:
        print(
            f"[migrate_resolver] local source: skip {nupkg_path.name}: {exc}",
            file=sys.stderr,
        )
        return None

    # XML namespace handling — .nuspec usa http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd
    ns = {"n": _NUSPEC_NS}
    # Try namespaced first, then bare (legacy .nuspec sem ns).
    meta = root.find("n:metadata", ns)
    if meta is None:
        meta = root.find("metadata")
    if meta is None:
        print(
            f"[migrate_resolver] local source: <metadata> missing in {nupkg_path.name}",
            file=sys.stderr,
        )
        return None

    def _find_text(tag: str) -> Optional[str]:
        el = meta.find(f"n:{tag}", ns)
        if el is None:
            el = meta.find(tag)
        if el is None or el.text is None:
            return None
        return el.text.strip()

    pkg_id = _find_text("id")
    version = _find_text("version")
    if not pkg_id or not version:
        print(
            f"[migrate_resolver] local source: missing id/version in {nupkg_path.name}",
            file=sys.stderr,
        )
        return None
    return pkg_id, version


def local_nupkgs_source(folder: Path) -> dict[str, list[str]]:
    """Scan local .nupkgs/ folder + parse .nuspec inside each .nupkg.

    Each .nupkg = zipfile. Locate .nuspec at archive root (not content/, lib/).
    Parse XML, extract <id> + <version> from <metadata>. Build dict.

    Tolerates malformed / non-nupkg files (skip silently w/ stderr log).
    Empty / nonexistent folder -> empty dict (no raise).

    Returns:
        dict mapping package_id -> sorted list of unique versions found.
        Keys are EXACT package_id casing from .nuspec.
    """
    folder = Path(folder)
    if not folder.exists() or not folder.is_dir():
        return {}

    found: dict[str, set[str]] = {}
    for nupkg in sorted(folder.glob("*.nupkg")):
        meta = _extract_nuspec_meta(nupkg)
        if meta is None:
            continue
        pkg_id, version = meta
        found.setdefault(pkg_id, set()).add(version)
    return {pkg_id: sorted(versions) for pkg_id, versions in found.items()}


def fetch_versions_with_fallback(
    package_id: str,
    *,
    target_framework: str = "net6.0-windows7.0",
    include_prerelease: bool = False,
    cache_dir: Optional[Path] = None,
    http_timeout: int = 30,
    local_nupkgs_folder: Optional[Path] = None,
    local_index: Optional[dict[str, list[str]]] = None,
    _remote_fetcher: Optional[Callable[..., list[str]]] = None,
) -> list[str]:
    """Fetch versions with local fallback chain.

    Priority:
      1. Local .nupkgs/ index (se local_index OR local_nupkgs_folder set):
         se package_id presente no index local, esse e o source-of-truth e
         retorna direto (NAO chama remote). Decisao alinhada com "CCS local
         nupkgs source-of-truth" memory rule.
      2. Remote NuGet public API (fetch_versions). Normal path para pacotes
         publicos (UiPath.*, etc).

    Merge semantics: local SUPLEMENTA remote (1 wins se ID local). Para IDs
    nao locais, remote eh chamado. Se ambos falham => empty list (caller
    flags UNRESOLVED via get_recommended_version).

    Args:
        package_id: NuGet id (e.g. "CCS_SipagDirect" ou "UiPath.System.Activities").
        target_framework: TFM (passthrough to remote).
        include_prerelease: passthrough remote + filtra local.
        cache_dir: NuGet cache dir (passthrough remote).
        http_timeout: HTTP timeout (passthrough remote).
        local_nupkgs_folder: Path para pasta local .nupkgs/. None disable local source.
        local_index: Pre-computed local index (dict pkg_id -> versions). Se set,
            evita re-scan de folder em loops; tem prioridade sobre folder.
        _remote_fetcher: Injection point para tests (default fetch_versions).

    Returns:
        list[str] of versions (raw). Empty se ambos sources retornam nada.
    """
    remote_fetcher = _remote_fetcher if _remote_fetcher is not None else fetch_versions

    # Build / accept local index ------------------------------------------
    index: dict[str, list[str]] = {}
    if local_index is not None:
        index = local_index
    elif local_nupkgs_folder is not None:
        index = local_nupkgs_source(local_nupkgs_folder)

    # Local hit -> return local-only (source-of-truth para IDs proprietarios).
    if package_id in index:
        local_versions = list(index[package_id])
        return _filter_prerelease(local_versions, include_prerelease)

    # Fallback: remote NuGet.
    try:
        remote = remote_fetcher(
            package_id,
            target_framework=target_framework,
            include_prerelease=include_prerelease,
            cache_dir=cache_dir,
            http_timeout=http_timeout,
        )
    except urllib.error.URLError:
        # Remote down + no local hit => empty (caller flags UNRESOLVED).
        return []
    return list(remote)


# ---------------------------------------------------------------------------
# get_recommended_version — algoritmo §6 EXATO.
# ---------------------------------------------------------------------------


def get_recommended_version(
    package_id: str,
    current_version: str,
    available_versions: list[str],
) -> ResolutionResult:
    """Implementa algoritmo MigratedPackageVersionResolver.GetRecommendedVersion §6.

    Steps:
      1. SAME se algum p em packages tem p.Version == oldVersion (compare como NuGetVersion).
      2. UNRESOLVED se nenhuma version > oldVer.
      3. Else: pega smallestPatch (= min de candidates > oldVer), TakeWhile mesma
         major.minor, pick highest patch.
    """
    if not available_versions:
        return ResolutionResult(
            package_id=package_id,
            current_version=current_version,
            recommended_version=current_version,
            action=ResolutionAction.UNRESOLVED,
            candidates_count=0,
            reason="no versions available from NuGet (offline/unknown package?)",
        )

    try:
        old_ver = NuGetVersion.parse(current_version)
    except ValueError as exc:
        return ResolutionResult(
            package_id=package_id,
            current_version=current_version,
            recommended_version=current_version,
            action=ResolutionAction.UNRESOLVED,
            candidates_count=len(available_versions),
            reason=f"invalid current_version: {exc}",
        )

    parsed: list[NuGetVersion] = []
    for v_str in available_versions:
        try:
            parsed.append(NuGetVersion.parse(v_str))
        except ValueError:
            continue  # skip malformed entries

    # Step 1: KEEP if exact match exists.
    if any(p == old_ver for p in parsed):
        return ResolutionResult(
            package_id=package_id,
            current_version=current_version,
            recommended_version=current_version,
            action=ResolutionAction.SAME,
            candidates_count=len(parsed),
            reason="exact pin exists in NuGet feed (TFM-compatible assumed)",
        )

    # Step 2: candidates > oldVer, ordered asc.
    candidates = sorted([p for p in parsed if p > old_ver])
    if not candidates:
        return ResolutionResult(
            package_id=package_id,
            current_version=current_version,
            recommended_version=current_version,
            action=ResolutionAction.UNRESOLVED,
            candidates_count=len(parsed),
            reason="no versions > current_version found",
        )

    # Step 3: smallestPatch + TakeWhile same major.minor + highest patch.
    smallest_patch = candidates[0]
    same_minor = [
        c for c in candidates if c.major == smallest_patch.major and c.minor == smallest_patch.minor
    ]
    # Algoritmo §6: OrderByDescending(v).First() => highest within same major.minor.
    chosen = max(same_minor)
    return ResolutionResult(
        package_id=package_id,
        current_version=current_version,
        recommended_version=str(chosen),
        action=ResolutionAction.UPDATED,
        candidates_count=len(parsed),
        reason=(
            f"upgraded within major.minor={chosen.major}.{chosen.minor} "
            f"(smallest patch > current: {smallest_patch}, highest in band: {chosen})"
        ),
    )


# ---------------------------------------------------------------------------
# check_project — orchestrator pra project.json inteiro.
# ---------------------------------------------------------------------------


def _strip_range_brackets(version_constraint: str) -> str:
    """UiPath project.json pin shorthand: '[25.4.4]' -> '25.4.4'.

    Para ranges complexos ('[25.4.4, 26.0)'), pega lower-bound como pin (aproximacao).
    """
    s = version_constraint.strip()
    if s.startswith("[") and s.endswith("]") and "," not in s:
        return s[1:-1].strip()
    # Range: extract lower-bound
    if s and s[0] in "[(":
        body = s[1:]
        if "," in body:
            body = body.split(",", 1)[0]
        return body.strip()
    return s


def check_project(
    project_json_path: Path,
    *,
    target_framework: str = "net6.0-windows7.0",
    cache_dir: Optional[Path] = None,
    include_prerelease: bool = False,
    http_timeout: int = 30,
    local_nupkgs_folder: Optional[Path] = None,
    _fetch_versions=None,  # injection-point pra tests
) -> list[ResolutionResult]:
    """Parse project.json + run get_recommended_version per dependency.

    UiPath project.json dependency format:
        "dependencies": { "<pkg_id>": "<version_constraint>", ... }
    Onde version_constraint eh tipicamente "[X.Y.Z]" (exact pin).

    Args:
        project_json_path: Path ao project.json.
        target_framework: TFM target post-migrate.
        cache_dir: NuGet cache dir.
        include_prerelease: Se True, mantem versoes com `-suffix`.
        http_timeout: HTTP timeout.
        local_nupkgs_folder: Phase 2.1 — pasta local com .nupkg files
            (proprietarios Sicoob CCS_*). Se set, scaneada UMA vez e usado
            como source-of-truth para pacotes presentes localmente. Fallback
            para NuGet public restante. None = backward-compat (remote only).
        _fetch_versions: Override pra tests (signature igual a fetch_versions).
            Quando set + local_nupkgs_folder also set, injection vai como
            _remote_fetcher dentro de fetch_versions_with_fallback.

    Returns:
        List de ResolutionResult, um por dependency.
    """
    project_json = json.loads(Path(project_json_path).read_text(encoding="utf-8"))
    deps = project_json.get("dependencies", {})
    if not isinstance(deps, dict):
        return []

    # Build local index once (avoid re-scanning per-dep) -------------------
    local_index: Optional[dict[str, list[str]]] = None
    if local_nupkgs_folder is not None:
        local_index = local_nupkgs_source(Path(local_nupkgs_folder))

    # Compose fetcher. Two modes:
    #   - local_nupkgs_folder set: use fetch_versions_with_fallback, treating
    #     _fetch_versions (if any) as remote-injection.
    #   - local_nupkgs_folder None: backward-compat — direct fetch_versions
    #     or _fetch_versions override.
    if local_nupkgs_folder is not None:
        def fetcher(pkg_id, **kw):
            return fetch_versions_with_fallback(
                pkg_id,
                local_index=local_index,
                _remote_fetcher=_fetch_versions if _fetch_versions is not None else fetch_versions,
                **kw,
            )
    else:
        fetcher = _fetch_versions if _fetch_versions is not None else fetch_versions

    results: list[ResolutionResult] = []
    for pkg_id, constraint in deps.items():
        current = _strip_range_brackets(str(constraint))
        try:
            available = fetcher(
                pkg_id,
                target_framework=target_framework,
                include_prerelease=include_prerelease,
                cache_dir=cache_dir,
                http_timeout=http_timeout,
            )
        except urllib.error.URLError as exc:
            results.append(
                ResolutionResult(
                    package_id=pkg_id,
                    current_version=current,
                    recommended_version=current,
                    action=ResolutionAction.UNRESOLVED,
                    candidates_count=0,
                    reason=f"NuGet fetch failed: {exc}",
                )
            )
            continue
        except Exception as exc:  # noqa: BLE001 — broad catch by design (offline / unknown pkg)
            results.append(
                ResolutionResult(
                    package_id=pkg_id,
                    current_version=current,
                    recommended_version=current,
                    action=ResolutionAction.UNRESOLVED,
                    candidates_count=0,
                    reason=f"unexpected fetch error: {exc}",
                )
            )
            continue

        results.append(get_recommended_version(pkg_id, current, available))
    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "NuGetVersion",
    "ResolutionAction",
    "ResolutionResult",
    "check_project",
    "fetch_versions",
    "fetch_versions_with_fallback",
    "get_recommended_version",
    "local_nupkgs_source",
]
