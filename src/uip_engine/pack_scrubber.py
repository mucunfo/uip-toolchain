"""pack_scrubber — OPC .nupkg post-publish scrubber.

Stream E dossier §05 (`sicoob-studio-research/05-pack-format.md`) documenta
layout do `.nupkg` produzido pelo Studio (plain OPC / ZIP DEFLATE) e o
privacy leak: `<repository url="ssh://git@bit.sicoob.com.br:..." commit="..."/>`
gravado no `.nuspec` durante publish.

Operações expostas:

  1. inspect(path)           — dump structure + repository tag content
  2. scrub_repository(path)  — remove <repository> tag de .nuspec (privacy fix)
  3. sign(path, ...)         — optional, invoke nuget sign (cert disponível)
  4. verify(path)            — invoke nuget verify post-sign

Tudo via stdlib (zipfile + xml.etree). Sem deps externos.

OPC integrity notes:
  - [Content_Types].xml NÃO precisa atualizar quando só editamos o .nuspec
    inplace (mesma file name, mesma extension override).
  - _rels/.rels NÃO muda (relationship aponta pra .nuspec path, não bytes).
  - .psmdcp NÃO muda (Dublin-core não contém repository URL).
  - SHA-512 sidecar (`<file>.nupkg.sha512`) recompute se existir.

Order preservation: zipfile.ZipFile.namelist() retorna na order de criação.
Quando re-emitimos copiamos na mesma order pra minimizar diff binário e
manter compat com tools sensíveis a ordering (raro mas seguro).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# NuSpec XML namespace (Studio writes `xmlns=` no root <package>). Necessário
# pra ET locate dos children (repository/metadata/etc) — ET usa Clark notation
# `{ns}tag`. Manter consistente com schema 2013/05 (default desde NuGet 3.0).
NUSPEC_NS = "http://schemas.microsoft.com/packaging/2013/05/nuspec.xsd"
NUSPEC_NS_MAP = {"n": NUSPEC_NS}

# Default timestamper se sign() chamado sem override. DigiCert é o canonical
# RFC 3161 server público gratuito usado pela maioria das toolchains NuGet.
DEFAULT_TIMESTAMPER = "http://timestamp.digicert.com"


@dataclass
class NupkgInfo:
    """Snapshot estrutural + privacy de um .nupkg."""

    path: Path
    nuspec_name: str = ""
    package_id: str = ""
    version: str = ""
    repository_url: Optional[str] = None
    repository_commit: Optional[str] = None
    repository_branch: Optional[str] = None
    has_signature: bool = False
    content_types_size: int = 0
    content_files_count: int = 0
    lib_files_count: int = 0
    total_entries: int = 0
    sha512_sidecar: Optional[Path] = field(default=None, repr=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_root_nuspec(zf: zipfile.ZipFile) -> Optional[str]:
    """Retorna o nome (com path) do .nuspec em raiz do zip, ou None.

    O .nuspec canonical mora em raiz (não em content/ nem contentFiles/). OPC
    spec garante isso; aqui filtramos entries cujo path NÃO contém `/`.
    """
    for name in zf.namelist():
        # Em ZIP os separators são sempre '/'. Studio nunca escreve backslash.
        if name.endswith(".nuspec") and "/" not in name:
            return name
    return None


def _parse_nuspec_repository(nuspec_bytes: bytes) -> dict:
    """Extract id/version + repository attribs sem mutar o XML.

    Retorna dict com keys: id, version, repo_url, repo_commit, repo_branch
    (todos Optional[str]). Tolerante a XML malformado — retorna empty dict.
    """
    out: dict = {}
    try:
        root = ET.fromstring(nuspec_bytes)
    except ET.ParseError:
        return out

    # Metadata pode estar com ou sem namespace dependendo de quem gerou
    # (Studio sempre escreve com NS canonical, mas tolerar variants).
    meta = root.find(f"{{{NUSPEC_NS}}}metadata")
    if meta is None:
        meta = root.find("metadata")
    if meta is None:
        return out

    def _txt(tag: str) -> Optional[str]:
        el = meta.find(f"{{{NUSPEC_NS}}}{tag}")
        if el is None:
            el = meta.find(tag)
        return el.text if el is not None and el.text else None

    out["id"] = _txt("id")
    out["version"] = _txt("version")

    repo = meta.find(f"{{{NUSPEC_NS}}}repository")
    if repo is None:
        repo = meta.find("repository")
    if repo is not None:
        out["repo_url"] = repo.attrib.get("url")
        out["repo_commit"] = repo.attrib.get("commit")
        out["repo_branch"] = repo.attrib.get("branch")
    return out


def _strip_repository_from_nuspec(nuspec_bytes: bytes) -> tuple[bytes, bool]:
    """Remove <repository> tag de dentro de <metadata>.

    Retorna (new_bytes, removed: bool). Se não havia repository tag,
    retorna (nuspec_bytes, False) sem modificar.

    Preserva XML declaration + namespace + indentation o máximo possível.
    """
    # Register namespace pra ET emitir prefix vazio (default ns) em vez de ns0:
    # Sem isso, output fica `<ns0:package xmlns:ns0="...">` quebrando consumers
    # que esperam o canonical Studio output.
    ET.register_namespace("", NUSPEC_NS)

    try:
        root = ET.fromstring(nuspec_bytes)
    except ET.ParseError:
        return nuspec_bytes, False

    meta = root.find(f"{{{NUSPEC_NS}}}metadata")
    if meta is None:
        meta = root.find("metadata")
    if meta is None:
        return nuspec_bytes, False

    # Localizar repository element (com OU sem ns explícito).
    repo = meta.find(f"{{{NUSPEC_NS}}}repository")
    if repo is None:
        repo = meta.find("repository")
    if repo is None:
        return nuspec_bytes, False

    meta.remove(repo)

    # Serializar de volta. xml_declaration=True replica Studio header
    # (`<?xml version="1.0" encoding="utf-8"?>`).
    buf = io.BytesIO()
    tree = ET.ElementTree(root)
    tree.write(buf, encoding="utf-8", xml_declaration=True)
    return buf.getvalue(), True


def _recompute_sha512_sidecar(nupkg_path: Path) -> Optional[Path]:
    """Se existe `<nupkg>.sha512` sibling, recompute + write.

    NuGet client convention: sidecar holds base64(SHA-512(<nupkg bytes>)).
    Retorna o path do sidecar atualizado, ou None se não havia.
    """
    sidecar = nupkg_path.with_suffix(nupkg_path.suffix + ".sha512")
    if not sidecar.exists():
        return None
    digest = hashlib.sha512(nupkg_path.read_bytes()).digest()
    sidecar.write_text(base64.b64encode(digest).decode("ascii"), encoding="ascii")
    return sidecar


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def inspect(nupkg_path: Path) -> NupkgInfo:
    """Read-only structural + privacy snapshot do .nupkg.

    NÃO modifica o arquivo. Abre como zip, localiza .nuspec, parseia
    metadata, conta entries.
    """
    nupkg_path = Path(nupkg_path)
    info = NupkgInfo(path=nupkg_path)

    with zipfile.ZipFile(nupkg_path, "r") as zf:
        names = zf.namelist()
        info.total_entries = len(names)

        # Signature .p7s (NuGet 4.6+) — Studio nunca escreve mas detect anyway.
        info.has_signature = any(n.endswith(".signature.p7s") for n in names)

        # Content / lib counts (proxy estrutural pra preservation tests).
        info.content_files_count = sum(
            1 for n in names if n.startswith("content/") and not n.endswith("/")
        )
        info.lib_files_count = sum(
            1 for n in names if n.startswith("lib/") and not n.endswith("/")
        )

        # [Content_Types].xml size (preservation indicator).
        ctypes_name = "[Content_Types].xml"
        if ctypes_name in names:
            with zf.open(ctypes_name) as fh:
                info.content_types_size = len(fh.read())

        # Locate + parse nuspec.
        nuspec_name = _find_root_nuspec(zf)
        if nuspec_name is None:
            return info
        info.nuspec_name = nuspec_name
        with zf.open(nuspec_name) as fh:
            data = fh.read()
        meta = _parse_nuspec_repository(data)
        info.package_id = meta.get("id") or ""
        info.version = meta.get("version") or ""
        info.repository_url = meta.get("repo_url")
        info.repository_commit = meta.get("repo_commit")
        info.repository_branch = meta.get("repo_branch")

    # Detect SHA-512 sidecar (não read content, só existence).
    sidecar = nupkg_path.with_suffix(nupkg_path.suffix + ".sha512")
    if sidecar.exists():
        info.sha512_sidecar = sidecar

    return info


def scrub_repository(
    nupkg_path: Path,
    *,
    output_path: Optional[Path] = None,
    dry_run: bool = False,
) -> NupkgInfo:
    """Remove <repository> tag do .nuspec dentro do .nupkg.

    Args:
        nupkg_path: source .nupkg.
        output_path: se None, opera inplace via tmp + atomic replace.
            Se fornecido, escreve em output_path (source intacto).
        dry_run: se True, retorna inspect() do source sem modificar nada.

    Returns:
        NupkgInfo do output (post-scrub). repository_url == None se scrub
        applied; se nuspec já não tinha repo tag, idêntico ao input.
    """
    nupkg_path = Path(nupkg_path)
    if dry_run:
        return inspect(nupkg_path)

    # Decide destino: inplace via tmp + rename, ou output_path direto.
    inplace = output_path is None
    if inplace:
        # tmp same dir pra garantir os.replace atomic (cross-device falha).
        tmp_dir = nupkg_path.parent
        tmp = tempfile.NamedTemporaryFile(
            prefix=nupkg_path.stem + "_scrub_",
            suffix=".nupkg.tmp",
            dir=tmp_dir,
            delete=False,
        )
        tmp.close()
        write_target = Path(tmp.name)
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        write_target = output_path

    try:
        with zipfile.ZipFile(nupkg_path, "r") as src:
            # ZipInfo preserva timestamp + compression metadata original;
            # writestr(zinfo, data) replica fielmente exceto pelo CRC/size
            # que zipfile recompute (correto pq mudamos bytes do nuspec).
            with zipfile.ZipFile(
                write_target, "w", compression=zipfile.ZIP_DEFLATED
            ) as dst:
                nuspec_name = _find_root_nuspec(src)
                for zinfo in src.infolist():
                    data = src.read(zinfo.filename)
                    if nuspec_name is not None and zinfo.filename == nuspec_name:
                        new_data, _removed = _strip_repository_from_nuspec(data)
                        data = new_data
                    # Recreate ZipInfo p/ preservar date_time + flags mas deixa
                    # zipfile re-derive CRC32/compress_size automaticamente.
                    new_zinfo = zipfile.ZipInfo(
                        filename=zinfo.filename, date_time=zinfo.date_time
                    )
                    new_zinfo.compress_type = zinfo.compress_type
                    new_zinfo.external_attr = zinfo.external_attr
                    new_zinfo.create_system = zinfo.create_system
                    dst.writestr(new_zinfo, data)

        if inplace:
            os.replace(write_target, nupkg_path)
            final_path = nupkg_path
        else:
            final_path = write_target

        # Recompute SHA-512 sidecar se existia ao lado do FINAL path.
        _recompute_sha512_sidecar(final_path)

        return inspect(final_path)
    except Exception:
        # Cleanup tmp em caso de falha mid-write.
        if inplace and write_target.exists():
            try:
                write_target.unlink()
            except OSError:
                pass
        raise


def sign(
    nupkg_path: Path,
    *,
    cert_fingerprint: str,
    timestamper: str = DEFAULT_TIMESTAMPER,
    nuget_binary: Optional[str] = None,
) -> tuple[bool, str]:
    """Invoke `nuget sign` via subprocess.

    Args:
        nupkg_path: .nupkg a assinar.
        cert_fingerprint: SHA-1 ou SHA-256 thumbprint do cert no store.
        timestamper: RFC 3161 server URL.
        nuget_binary: override path; default tenta `nuget` no PATH.

    Returns:
        (ok, message). ok=False se nuget não encontrado ou sign falhou.
    """
    nuget = nuget_binary or shutil.which("nuget") or shutil.which("nuget.exe")
    if not nuget:
        return False, "nuget binary not found on PATH (post-pack signing skipped)"

    cmd = [
        nuget,
        "sign",
        str(nupkg_path),
        "-CertificateFingerprint",
        cert_fingerprint,
        "-Timestamper",
        timestamper,
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120, check=False
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return False, f"nuget sign invocation failed: {exc!r}"
    ok = proc.returncode == 0
    msg = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return ok, msg.strip()


def verify(
    nupkg_path: Path, *, nuget_binary: Optional[str] = None
) -> tuple[bool, str]:
    """Invoke `nuget verify -All` via subprocess.

    Retorna (ok, message). ok=False se nuget binary missing OR verify failed.
    """
    nuget = nuget_binary or shutil.which("nuget") or shutil.which("nuget.exe")
    if not nuget:
        return False, "nuget binary not found on PATH"
    cmd = [nuget, "verify", str(nupkg_path), "-All"]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, check=False
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return False, f"nuget verify invocation failed: {exc!r}"
    ok = proc.returncode == 0
    msg = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return ok, msg.strip()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _fmt_info(info: NupkgInfo) -> str:
    repo = info.repository_url or "(none)"
    sig = "yes" if info.has_signature else "no"
    return (
        f"path:           {info.path}\n"
        f"package_id:     {info.package_id}\n"
        f"version:        {info.version}\n"
        f"nuspec_name:    {info.nuspec_name}\n"
        f"repository_url: {repo}\n"
        f"repo_branch:    {info.repository_branch or '(none)'}\n"
        f"repo_commit:    {info.repository_commit or '(none)'}\n"
        f"has_signature:  {sig}\n"
        f"total_entries:  {info.total_entries}\n"
        f"content_files:  {info.content_files_count}\n"
        f"lib_files:      {info.lib_files_count}\n"
        f"ctypes_size:    {info.content_types_size}\n"
    )


def cli_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="pack-scrub",
        description="OPC .nupkg post-publish scrubber (Stream E §05)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    pi = sub.add_parser("inspect", help="Dump structure + repository leak status")
    pi.add_argument("nupkg", help="Path ao .nupkg")

    ps = sub.add_parser("scrub", help="Remove <repository> tag do .nuspec")
    ps.add_argument("nupkg", help="Path ao .nupkg")
    ps.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output path; default = inplace (atomic replace)",
    )
    ps.add_argument(
        "--dry-run",
        action="store_true",
        help="Só inspect, não modifica",
    )

    pg = sub.add_parser("sign", help="nuget sign <nupkg> -CertificateFingerprint <fp>")
    pg.add_argument("nupkg")
    pg.add_argument("--cert", required=True, help="Cert thumbprint (SHA-1 ou SHA-256)")
    pg.add_argument("--timestamper", default=DEFAULT_TIMESTAMPER)

    pv = sub.add_parser("verify", help="nuget verify -All")
    pv.add_argument("nupkg")

    args = p.parse_args(argv)
    target = Path(args.nupkg)
    if not target.exists():
        print(f"ERROR: {target} not found", file=sys.stderr)
        return 2

    if args.command == "inspect":
        info = inspect(target)
        print(_fmt_info(info))
        return 0

    if args.command == "scrub":
        info_before = inspect(target)
        out = Path(args.output) if args.output else None
        info_after = scrub_repository(target, output_path=out, dry_run=args.dry_run)
        had_leak = info_before.repository_url is not None
        still_leak = info_after.repository_url is not None
        status = (
            "DRY-RUN (no write)"
            if args.dry_run
            else ("SCRUBBED" if had_leak and not still_leak else "NO-CHANGE")
        )
        print(f"[{status}] {target}")
        print(f"  before.repository_url: {info_before.repository_url or '(none)'}")
        print(f"  after.repository_url : {info_after.repository_url or '(none)'}")
        return 0 if (args.dry_run or not still_leak) else 1

    if args.command == "sign":
        ok, msg = sign(target, cert_fingerprint=args.cert, timestamper=args.timestamper)
        print(msg)
        return 0 if ok else 1

    if args.command == "verify":
        ok, msg = verify(target)
        print(msg)
        return 0 if ok else 1

    return 2


if __name__ == "__main__":
    sys.exit(cli_main())
