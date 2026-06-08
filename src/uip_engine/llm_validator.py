"""Compatibility wrapper for the renamed traceability validator.

The old module name is kept for third-party imports only. Runtime code should
import `uip_engine.traceability_validator` directly.
"""
from __future__ import annotations

from .traceability_validator import is_traceable, validate_messages

__all__ = ["is_traceable", "validate_messages"]
