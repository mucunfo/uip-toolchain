"""Canonical project file view used by rules, gates, cache and publish."""
from __future__ import annotations

import hashlib
import os
from collections.abc import Iterable, Iterator
from pathlib import Path


PROJECT_SKIP_DIRS = frozenset({
    ".git",
    ".hg",
    ".svn",
    ".local",
    ".nuget",
    ".settings",
    ".tmp",
    ".uipath",
    "__pycache__",
    "bin",
    "node_modules",
    "obj",
})

PUBLISH_SKIP_DIRS = PROJECT_SKIP_DIRS | frozenset({
    ".publish-dev-handoff",
})

PROJECT_METADATA_FILES = (
    "project.json",
    "project.uiproj",
    "webAppManifest.json",
    "NuGet.config",
    "nuget.config",
)


def skip_dirs(*, extra_skip_dirs: Iterable[str] = ()) -> frozenset[str]:
    return PROJECT_SKIP_DIRS | frozenset(extra_skip_dirs)


def filter_walk_dirs(dirs: list[str], *, extra_skip_dirs: Iterable[str] = ()) -> None:
    """Mutate ``dirs`` in-place for deterministic ``os.walk`` traversal."""
    excluded = skip_dirs(extra_skip_dirs=extra_skip_dirs)
    dirs[:] = sorted(d for d in dirs if d not in excluded)


def iter_project_xamls(
    project_root: Path | str,
    *,
    extra_skip_dirs: Iterable[str] = (),
) -> Iterator[Path]:
    """Yield productive XAML files under a UiPath project root.

    Technical/cache/build folders are excluded centrally so runner, fixers,
    scrubbers and cache signatures reason over the same project surface.
    """
    root = Path(project_root)
    for current_text, dirs, files in os.walk(root):
        filter_walk_dirs(dirs, extra_skip_dirs=extra_skip_dirs)
        current = Path(current_text)
        for name in sorted(files):
            if name.lower().endswith(".xaml"):
                yield current / name


def iter_project_json_files(
    root: Path | str,
    *,
    extra_skip_dirs: Iterable[str] = (),
) -> Iterator[Path]:
    """Yield ``project.json`` files under ``root`` using canonical skips."""
    base = Path(root)
    for current_text, dirs, files in os.walk(base):
        filter_walk_dirs(dirs, extra_skip_dirs=extra_skip_dirs)
        if "project.json" in files:
            yield Path(current_text) / "project.json"


def iter_project_material_files(
    project_root: Path | str,
    *,
    extra_skip_dirs: Iterable[str] = (),
) -> Iterator[Path]:
    """Yield project files that influence local/official gate results."""
    root = Path(project_root)
    seen: set[Path] = set()
    for name in PROJECT_METADATA_FILES:
        path = root / name
        if path.is_file():
            resolved = path.resolve()
            seen.add(resolved)
            yield path
    for xaml in iter_project_xamls(root, extra_skip_dirs=extra_skip_dirs):
        resolved = xaml.resolve()
        if resolved not in seen:
            seen.add(resolved)
            yield xaml


def default_engine_contract_files() -> tuple[Path, ...]:
    """Files whose changes invalidate cached external-gate results."""
    package_dir = Path(__file__).resolve().parent
    repo_root = package_dir.parents[1]
    candidates = (
        repo_root / "rules.yaml",
        package_dir / "analyzer.py",
        package_dir / "official_uip.py",
        package_dir / "project_view.py",
        package_dir / "publish_readiness.py",
    )
    return tuple(path for path in candidates if path.is_file())


def _hash_file(
    hasher: "hashlib._Hash",
    *,
    base: Path,
    path: Path,
    namespace: str,
) -> None:
    try:
        rel = path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        rel = str(path.resolve())
    hasher.update(namespace.encode("utf-8"))
    hasher.update(b"\0")
    hasher.update(rel.encode("utf-8", errors="surrogatepass"))
    hasher.update(b"\0")
    hasher.update(path.read_bytes())
    hasher.update(b"\0")


def project_content_signature(
    project_root: Path | str,
    *,
    extra_files: Iterable[Path | str] = (),
    extra_skip_dirs: Iterable[str] = (),
    salt: str = "project-content-v1",
) -> str:
    """Hash project content and engine contract files for cache invalidation."""
    root = Path(project_root)
    hasher = hashlib.sha256()
    hasher.update(salt.encode("utf-8", errors="surrogatepass"))
    hasher.update(b"\0")
    hasher.update(",".join(sorted(skip_dirs(extra_skip_dirs=extra_skip_dirs))).encode("utf-8"))
    hasher.update(b"\0")

    for path in iter_project_material_files(root, extra_skip_dirs=extra_skip_dirs):
        try:
            _hash_file(hasher, base=root, path=path, namespace="project")
        except OSError:
            continue

    for item in sorted((Path(p) for p in extra_files), key=lambda p: str(p).lower()):
        if not item.is_file():
            continue
        try:
            _hash_file(hasher, base=item.parent, path=item, namespace="engine")
        except OSError:
            continue

    return hasher.hexdigest()[:32]
