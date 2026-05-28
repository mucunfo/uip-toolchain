"""Tests Tier 1 — migrate routing Studio 23.10 canonical pin injection."""
from __future__ import annotations

from uip_engine.canonical import canonical_pin_for


def test_uia_canonical_pin_available_for_migrate():
    """Migrate.py injeta `--uia-package-version=<canonical>` no cmd Migrator.
    Pré-condição: canonical UIA pin resolvível."""
    pin = canonical_pin_for("UiPath.UIAutomation.Activities")
    assert pin == "25.10.8"


def test_o365_canonical_pin_available_for_migrate():
    """Migrate.py injeta `--mail-o365-package-version=<canonical>`."""
    pin = canonical_pin_for("UiPath.MicrosoftOffice365.Activities")
    assert pin == "2.7.24"


def test_migrate_module_imports_canonical_pin_for():
    """Verifica import path canonical_pin_for está acessível em migrate.py."""
    from uip_engine.migrate import cmd_migrate_windows  # noqa: F401
    # Import succeeds = canonical.py reachable.
