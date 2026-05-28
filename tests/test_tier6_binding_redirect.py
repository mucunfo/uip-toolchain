"""Tests Tier 6 — CFG-BINDING-REDIRECT-IGNORED scanner."""
from __future__ import annotations

import json
from pathlib import Path

from uip_engine._types import Rule, Severity
from uip_engine.context import FileContext, ProjectContext
from uip_engine.heuristics.binding_redirect import detect_binding_redirect


def _mk_rule() -> Rule:
    return Rule(
        id="CFG-BINDING-REDIRECT-IGNORED",
        severity=Severity.WARN,
        category="architectural",
        target="windows",
        title="bindingRedirect ignorado em .NET 6+",
        description="",
        detect={"type": "python"},
        fix={"apply_class": "structural", "prose": "manual"},
    )


def _mk_pc(tmp_path: Path) -> ProjectContext:
    proj = tmp_path / "P"
    proj.mkdir()
    (proj / "project.json").write_text(json.dumps({"targetFramework": "Windows"}))
    return ProjectContext(root=proj, project_json={"targetFramework": "Windows"})


def test_no_config_files_returns_empty(tmp_path):
    pc = _mk_pc(tmp_path)
    findings = detect_binding_redirect(_mk_rule(), FileContext(pc.root / "project.json"), pc)
    assert findings == []


def test_app_config_with_binding_redirect_flagged(tmp_path):
    pc = _mk_pc(tmp_path)
    (pc.root / "App.config").write_text("""<?xml version="1.0"?>
<configuration>
  <runtime>
    <assemblyBinding xmlns="urn:schemas-microsoft-com:asm.v1">
      <dependentAssembly>
        <assemblyIdentity name="Newtonsoft.Json" publicKeyToken="30ad4fe6b2a6aeed" />
        <bindingRedirect oldVersion="0.0.0.0-13.0.0.0" newVersion="13.0.0.0"/>
      </dependentAssembly>
    </assemblyBinding>
  </runtime>
</configuration>""")
    findings = detect_binding_redirect(_mk_rule(), FileContext(pc.root / "project.json"), pc)
    assert len(findings) == 1
    assert "App.config" in findings[0].message


def test_dll_config_also_scanned(tmp_path):
    pc = _mk_pc(tmp_path)
    (pc.root / "Foo.dll.config").write_text(
        '<configuration><runtime><assemblyBinding><dependentAssembly>'
        '<bindingRedirect newVersion="1.0.0"/></dependentAssembly></assemblyBinding>'
        '</runtime></configuration>'
    )
    findings = detect_binding_redirect(_mk_rule(), FileContext(pc.root / "project.json"), pc)
    assert len(findings) == 1
    assert "Foo.dll.config" in findings[0].message


def test_skip_local_tmp_caches(tmp_path):
    pc = _mk_pc(tmp_path)
    (pc.root / ".local").mkdir()
    (pc.root / ".local" / "cached.config").write_text(
        '<bindingRedirect newVersion="1.0.0"/>'
    )
    findings = detect_binding_redirect(_mk_rule(), FileContext(pc.root / "project.json"), pc)
    assert findings == []


def test_clean_config_no_finding(tmp_path):
    pc = _mk_pc(tmp_path)
    (pc.root / "App.config").write_text("""<?xml version="1.0"?>
<configuration>
  <appSettings>
    <add key="Foo" value="Bar"/>
  </appSettings>
</configuration>""")
    findings = detect_binding_redirect(_mk_rule(), FileContext(pc.root / "project.json"), pc)
    assert findings == []
