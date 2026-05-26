"""Tests for S-5b — Activity Migrator [PostMigration Action Required] markers.

Cobertura:
- Detect: regex pattern hits PostMigration annotations.
- Fix: strip_annotation_text com `text_prefix` remove SOMENTE o marker,
  preserva annotations comuns.
- Backward compat: strip_annotation_text sem params (S-5 legado) continua
  removendo TODOS annotations.
"""
from pathlib import Path

import pytest

from uip_engine.fixers import apply_strip_annotation_text
from uip_engine.loader import load_rules


# ---- Fixtures ----

XAML_MAIN_WITH_POSTMIGRATION = """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Main" xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
          xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <TryCatch DisplayName="Try to process transaction"
            sap2010:Annotation.AnnotationText="[PostMigration Action Required]: WARNING: As seguintes exceções clássicas foram encontradas: BusinessRuleException.">
    <TryCatch.Try>
      <Sequence />
    </TryCatch.Try>
  </TryCatch>
</Activity>
"""

XAML_PROCESS_MIXED_ANNOTATIONS = """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Process" xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation">
  <Sequence DisplayName="Outer"
            sap2010:Annotation.AnnotationText="Anotação legítima do dev">
    <TryCatch DisplayName="Try Catch - Processo"
              sap2010:Annotation.AnnotationText="[PostMigration Action Required]: WARNING: classic exception">
      <TryCatch.Try><Sequence /></TryCatch.Try>
    </TryCatch>
    <TryCatch DisplayName="Outro try"
              sap2010:Annotation.AnnotationText="[PostMigration Action Required]: WARNING: outro">
      <TryCatch.Try><Sequence /></TryCatch.Try>
    </TryCatch>
  </Sequence>
</Activity>
"""

XAML_ONLY_COMMON_ANNOTATION = """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Helper" xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
          xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation">
  <Sequence DisplayName="Body"
            sap2010:Annotation.AnnotationText="Comentário comum do dev">
  </Sequence>
</Activity>
"""


# ---- Rule registration ----

def test_s5b_rule_registered():
    rules = load_rules(Path(__file__).resolve().parents[1] / "rules.yaml")
    ids = {r.id for r in rules}
    assert "S-5b" in ids, "S-5b deve estar registrada em rules.yaml"


def test_s5b_rule_metadata():
    from uip_engine._types import Severity
    rules = load_rules(Path(__file__).resolve().parents[1] / "rules.yaml")
    s5b = next(r for r in rules if r.id == "S-5b")
    assert s5b.severity == Severity.ERROR
    assert s5b.category == "breaking"
    assert s5b.target == "windows"
    # fix.mechanical.params.text_prefix presente
    fix = s5b.fix
    assert fix is not None
    mech = fix.get("mechanical")
    assert mech is not None
    assert mech.get("type") == "strip_annotation_text"
    params = mech.get("params") or {}
    assert params.get("text_prefix") == "[PostMigration Action Required]"


# ---- Detector via regex ----

def test_s5b_detects_postmigration_marker_in_main(tmp_path):
    """Regex da S-5b deve hit annotation [PostMigration Action Required]."""
    import re
    pattern = r'sap2010:Annotation\.AnnotationText="\[PostMigration Action Required\]'
    hits = re.findall(pattern, XAML_MAIN_WITH_POSTMIGRATION)
    assert len(hits) == 1


def test_s5b_no_finding_on_common_annotation():
    """Annotation comum não-PostMigration NÃO deve ser detectada pela S-5b."""
    import re
    pattern = r'sap2010:Annotation\.AnnotationText="\[PostMigration Action Required\]'
    hits = re.findall(pattern, XAML_ONLY_COMMON_ANNOTATION)
    assert hits == []


def test_s5b_detects_multiple_postmigration_markers():
    """Múltiplos PostMigration no mesmo arquivo → múltiplos hits."""
    import re
    pattern = r'sap2010:Annotation\.AnnotationText="\[PostMigration Action Required\]'
    hits = re.findall(pattern, XAML_PROCESS_MIXED_ANNOTATIONS)
    assert len(hits) == 2


# ---- Fixer: strip_annotation_text com text_prefix (S-5b) ----

def test_fixer_strips_only_postmigration_when_text_prefix_set(tmp_path):
    """Com text_prefix, fixer remove SOMENTE markers PostMigration; mantém
    annotations comuns."""
    f = tmp_path / "Process.xaml"
    f.write_text(XAML_PROCESS_MIXED_ANNOTATIONS, encoding="utf-8")

    spec = {
        "type": "strip_annotation_text",
        "params": {"text_prefix": "[PostMigration Action Required]"},
    }
    changed = apply_strip_annotation_text(f, spec, dry_run=False)
    assert changed is True

    out = f.read_text(encoding="utf-8")
    assert "[PostMigration Action Required]" not in out
    # Annotation legítima permanece
    assert 'sap2010:Annotation.AnnotationText="Anotação legítima do dev"' in out
    # Activities preservadas
    assert 'DisplayName="Try Catch - Processo"' in out
    assert 'DisplayName="Outer"' in out


def test_fixer_strips_postmigration_in_main(tmp_path):
    """Caso típico: Main.xaml único TryCatch com marker."""
    f = tmp_path / "Main.xaml"
    f.write_text(XAML_MAIN_WITH_POSTMIGRATION, encoding="utf-8")

    spec = {
        "type": "strip_annotation_text",
        "params": {"text_prefix": "[PostMigration Action Required]"},
    }
    changed = apply_strip_annotation_text(f, spec, dry_run=False)
    assert changed is True

    out = f.read_text(encoding="utf-8")
    assert "PostMigration" not in out
    # TryCatch preservado
    assert 'DisplayName="Try to process transaction"' in out
    assert "<TryCatch" in out


def test_fixer_no_change_when_no_postmigration_marker(tmp_path):
    """Sem marker PostMigration + text_prefix definido → no-op."""
    f = tmp_path / "Helper.xaml"
    original = XAML_ONLY_COMMON_ANNOTATION
    f.write_text(original, encoding="utf-8")

    spec = {
        "type": "strip_annotation_text",
        "params": {"text_prefix": "[PostMigration Action Required]"},
    }
    changed = apply_strip_annotation_text(f, spec, dry_run=False)
    assert changed is False
    assert f.read_text(encoding="utf-8") == original


def test_fixer_dry_run_does_not_modify_file(tmp_path):
    f = tmp_path / "Main.xaml"
    original = XAML_MAIN_WITH_POSTMIGRATION
    f.write_text(original, encoding="utf-8")

    spec = {
        "type": "strip_annotation_text",
        "params": {"text_prefix": "[PostMigration Action Required]"},
    }
    changed = apply_strip_annotation_text(f, spec, dry_run=True)
    assert changed is True
    # Conteudo intacto em dry-run
    assert f.read_text(encoding="utf-8") == original


# ---- Backward compat: S-5 (sem text_prefix) ----

def test_fixer_without_text_prefix_strips_all_annotations(tmp_path):
    """Comportamento legado S-5: sem text_prefix, remove TODOS annotations."""
    f = tmp_path / "Process.xaml"
    f.write_text(XAML_PROCESS_MIXED_ANNOTATIONS, encoding="utf-8")

    spec = {"type": "strip_annotation_text", "params": {}}
    changed = apply_strip_annotation_text(f, spec, dry_run=False)
    assert changed is True

    out = f.read_text(encoding="utf-8")
    assert "sap2010:Annotation.AnnotationText" not in out


def test_fixer_without_params_block_strips_all(tmp_path):
    """Spec sem bloco params (forma legada YAML): remove TODOS annotations."""
    f = tmp_path / "Helper.xaml"
    f.write_text(XAML_ONLY_COMMON_ANNOTATION, encoding="utf-8")

    spec = {"type": "strip_annotation_text"}
    changed = apply_strip_annotation_text(f, spec, dry_run=False)
    assert changed is True
    out = f.read_text(encoding="utf-8")
    assert "sap2010:Annotation.AnnotationText" not in out
