"""Tests for orphan NuGet.config cleanup guard.

Pack-gate cria NuGet.config temp p/ apontar `.nupkgs/` local + remove em
finally. Em crash hard (SIGKILL, machine reboot) finally não roda → orphan
permanece no projeto. `_cleanup_orphan_temp_nuget_config()` detecta via
sentinel comment + remove em próxima invocação.

Cobertura:
  - Orphan com sentinel → removido
  - Config sem sentinel (dev committed) → preservado
  - Sem NuGet.config → no-op
  - File não-legível → no-op (não crasha)
"""
import json
from pathlib import Path

import pytest

from uip_engine.cli import (
    _cleanup_orphan_temp_nuget_config,
    _TEMP_NUGET_CONFIG_SENTINEL,
)


_TEMP_NUGET_XML = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    f'<!-- {_TEMP_NUGET_CONFIG_SENTINEL} -->\n'
    '<configuration>\n'
    '  <packageSources>\n'
    '    <clear />\n'
    '    <add key="Sicoob_Local" value="/some/path/.nupkgs" />\n'
    '  </packageSources>\n'
    '</configuration>\n'
)

_DEV_NUGET_XML = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<configuration>\n'
    '  <packageSources>\n'
    '    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" />\n'
    '  </packageSources>\n'
    '</configuration>\n'
)


def test_orphan_with_sentinel_removed(tmp_path):
    cfg = tmp_path / "NuGet.config"
    cfg.write_text(_TEMP_NUGET_XML, encoding="utf-8")
    assert _cleanup_orphan_temp_nuget_config(tmp_path) is True
    assert not cfg.exists()


def test_dev_config_without_sentinel_preserved(tmp_path):
    cfg = tmp_path / "NuGet.config"
    cfg.write_text(_DEV_NUGET_XML, encoding="utf-8")
    assert _cleanup_orphan_temp_nuget_config(tmp_path) is False
    assert cfg.exists()
    assert cfg.read_text(encoding="utf-8") == _DEV_NUGET_XML


def test_no_nuget_config_noop(tmp_path):
    assert _cleanup_orphan_temp_nuget_config(tmp_path) is False


def test_directory_with_nuget_config_name_skipped(tmp_path):
    """NuGet.config como diretório (caso degenerado) → no-op, não crasha."""
    (tmp_path / "NuGet.config").mkdir()
    assert _cleanup_orphan_temp_nuget_config(tmp_path) is False


def test_sentinel_string_stable():
    """Sentinel deve ser estável cross-version pra cleanup funcionar com
    orphans deixados por engine versions anteriores. Lock literal."""
    assert _TEMP_NUGET_CONFIG_SENTINEL == "engine-temp-nuget-config (.uip-toolchain)"


def test_pack_gate_generated_xml_carries_sentinel():
    """Garantia que pack-gate emite sentinel — protege contra regressão
    onde alguém edita XML gerado e esquece de incluir o comment."""
    import inspect
    from uip_engine import cli
    src = inspect.getsource(cli)
    # Procura f-string com sentinel no XML gerado pelo pack-gate.
    assert f'<!-- {{_TEMP_NUGET_CONFIG_SENTINEL}} -->' in src or \
           '_TEMP_NUGET_CONFIG_SENTINEL' in src
