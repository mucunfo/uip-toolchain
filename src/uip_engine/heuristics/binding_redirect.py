"""CFG-BINDING-REDIRECT-IGNORED — .config files com `<bindingRedirect>`.

`<bindingRedirect>` em `App.config`, `*.exe.config`, `*.dll.config` é
**silenciosamente ignorado em .NET 6+**. UiPath Windows target roda em
.NET 6+ runtime; configs com redirects pré-existentes (.NET Framework era)
deixam dev acreditando que binding está garantido quando na verdade NuGet
resolveu lowest-applicable transitive.

Detector scaneia `.config` no projeto, emite finding por arquivo com
`<bindingRedirect>` encontrado.

Sem fix mecânico (decisão arquitetural: remover redirect E/OU pinar versão
em project.json para forçar NuGet escolher a versão correta).
"""
from __future__ import annotations

import re
from pathlib import Path

from uip_engine._types import Finding


_BINDING_REDIRECT_RE = re.compile(
    r"<bindingRedirect\b[^>]*\bnewVersion\s*=\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)

_CONFIG_GLOB_PATTERNS = ("*.config", "*.dll.config", "*.exe.config", "App.config")


def detect_binding_redirect(rule, fc, pc) -> list[Finding]:
    """Walk project root, scan `.config` files. Emit per arquivo achado."""
    if pc is None:
        return []
    findings: list[Finding] = []
    seen: set[Path] = set()
    for pat in _CONFIG_GLOB_PATTERNS:
        for cfg in pc.root.rglob(pat):
            if cfg in seen or not cfg.is_file():
                continue
            seen.add(cfg)
            # Skip .local/.tmp caches
            rel = cfg.relative_to(pc.root)
            if rel.parts and rel.parts[0] in {".local", ".tmp"}:
                continue
            try:
                text = cfg.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            redirects = _BINDING_REDIRECT_RE.findall(text)
            if not redirects:
                continue
            findings.append(Finding(
                rule_id=rule.id,
                severity=rule.severity,
                category=rule.category,
                file=str(cfg),
                line=1,
                message=(
                    f"{rule.title}: {rel.as_posix()} tem {len(redirects)} "
                    f"bindingRedirect — silenciosamente ignorado em .NET 6+"
                ),
                fix_mechanical=None,
                fix_prose=(rule.fix or {}).get("prose"),
            ))
    return findings
