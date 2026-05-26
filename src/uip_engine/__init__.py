"""UiPath rules engine — single source of truth."""
import sys as _sys

# Disable .pyc bytecode caching pra TODO import do pacote rule_engine.
# Stale .pyc causou false positive J-6 (cache leu versão velha do detector
# após edits). Aplicado aqui — não só no cli.py — pra cobrir tests
# (pytest), hooks (post_xaml_edit), e qualquer entry point alternativo.
_sys.dont_write_bytecode = True

__version__ = "0.1.0"
