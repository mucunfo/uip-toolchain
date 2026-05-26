"""Force UTF-8 stdout/stderr regardless of host terminal encoding.

Background: Windows terminals default to CP1252 which crashes on validator
output containing characters like '→', '✓'. `sys.stdout.reconfigure()` only
works on TextIOWrapper; under Claude Code hook subprocess, stdout may be a raw
buffer. We try reconfigure first, fall back to wrapping the underlying buffer.
errors='replace' is belt-and-suspenders so we never crash even if a glyph slips
past both layers.

Import this once at the top of every hook script:

    from _safe_encoding import enforce_utf8
    enforce_utf8()
"""
from __future__ import annotations

import io
import os
import sys


def enforce_utf8() -> None:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
                continue
        except Exception:
            pass
        try:
            buf = getattr(stream, "buffer", stream)
            wrapped = io.TextIOWrapper(buf, encoding="utf-8", errors="replace")
            setattr(sys, stream_name, wrapped)
        except Exception:
            # Last resort: leave stream as-is. Hook will swallow UnicodeError
            # in main() try/except, but at least we won't double-fail.
            pass
