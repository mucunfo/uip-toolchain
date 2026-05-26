"""Pytest harness setup.

Default behavior: opt OUT dos external gates (analyzer/nuget/pack) durante
testes — esses gates invocam subprocess `uipcli`/`nuget` que:
  - Lentos (>60s cada quando rodam de verdade).
  - Não-determinísticos entre máquinas (binary presence, versions).
  - Em projetos sintéticos minimos, naturalmente falham (não é o que estamos
    testando aqui).

Test-specific opt-IN: tests que validam o comportamento dos próprios gates
(`test_review_gates.py`) precisam controlar diretamente — chamam as funções
gate via stub/patch sem depender do flag global. Esse arquivo só seta o
guard env var.
"""
from __future__ import annotations

import os


def pytest_configure(config):
    """Seta env var antes da coleta de testes. Process-wide → propaga p/
    subprocess via os.environ default. Tests podem override per-test via
    `monkeypatch.delenv` se quiserem testar o real pipeline.
    """
    os.environ.setdefault("UIP_TOOLCHAIN_DISABLE_EXTERNAL_GATES", "1")
