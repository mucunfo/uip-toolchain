"""Apply-class taxonomy for rule fixes.

Cada rule tem `fix.apply_class` declarando como o motor deve tratar o fix:

  - `deterministic` (DEFAULT quando há fix.mechanical):
      Fix mecânico produz único output correto. Sem judgment humano.
      `--apply` aplica automaticamente.
      Ex: `Level="Trace"`, `JsonSample="{x:Null}"`, rename canonical
      Hungarian, fix de declaração ausente.

  - `contextual`:
      Fix exige interpretação semântica — qual valor, qual mensagem.
      `--apply` NÃO aplica por default. Surfaceado via `review`.
      Ex: inserir `<ui:LogMessage Message="???">` (qual mensagem?),
      escolher qual de N candidatos pra rename ambíguo.

  - `structural`:
      Fix reorganiza estrutura (split/extract/move). Risco alto, escopo
      grande. `--apply` NÃO aplica. Sempre human review.
      Ex: refatorar workflow com >7 args em Dictionary, extrair
      sub-workflow.

Default derivation (quando `apply_class` ausente):
  - `fix.auto_apply: false` (legado) → contextual
  - `fix.mechanical` declarado em YAML → deterministic
  - else → contextual

Default conservador. Rules cujo detector heuristic-emite `fix_mechanical`
(sem YAML `fix.mechanical` block) DEVEM declarar `apply_class: deterministic`
explicitamente — senão ficam bloqueadas como contextual.
"""
from __future__ import annotations


VALID_CLASSES = ("deterministic", "contextual", "structural")


def get_apply_class(rule) -> str:
    """Resolve apply_class de uma rule. Lê `fix.apply_class` se declarado;
    senão deriva: auto_apply:false → contextual; YAML mechanical → deterministic;
    prose-only → contextual."""
    fix = rule.fix or {}
    declared = fix.get("apply_class")
    if declared in VALID_CLASSES:
        return declared
    if fix.get("auto_apply") is False:
        return "contextual"
    if fix.get("mechanical"):
        return "deterministic"
    return "contextual"


def should_auto_apply(rule, included_classes: frozenset[str]) -> bool:
    """True se rule deve ser aplicada dado o set de classes incluídas no run."""
    return get_apply_class(rule) in included_classes
