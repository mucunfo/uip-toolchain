# Toolchain Architecture Dimensions Review

Date: 2026-06-07

Scope: rule engine, contextual rule handoff, deterministic fix loop, external
gates, publish readiness, documentation, and test guardrails.

## Executive Result

The rule architecture is now stronger in the dimensions that directly affect
enterprise execution:

- Rules are model-provider agnostic.
- Every effective rule has explicit `fix.prose`.
- CLI rule loading enforces schema plus enterprise quality checks.
- N-16 traceability is named and implemented as an offline heuristic, not a
  hidden LLM path.
- Canonical pins are documented as a second source artifact synthesized into
  effective rules.

Validation after changes:

- `python -m uip_engine.cli validate`: 303 valid rules.
- Focused tests: `17 passed`.
- Full suite: `1325 passed, 16 skipped`.

## Dimensions Reviewed

| Dimension | Status | Action taken / finding |
|---|---|---|
| Rule source of truth | Hardened | `rules.yaml` remains source for explicit rules; `assets/canonical_pins.yaml` is documented as the source for synthesized D-1*/J-1 rules. |
| Schema validation | Hardened | Existing schema validation remains in `loader.py`. |
| Rule quality validation | Fixed | `validate_rule_quality()` is enforced at `_load_rules_or_die`, so `review`, `fix`, `list`, `docs`, `all`, and `validate` reject bad rule text. |
| Contextual instructions | Fixed | 303/303 effective rules now have `fix.prose`; 171/171 contextual rules have explicit instructions. |
| Model/runtime coupling | Fixed | Rule quality blocks local/agent runtime terms such as `ollama`, `llama.cpp`, and `claude -p` inside rule text. |
| N-16 traceability | Fixed | Runtime code imports `traceability_validator`; `llm_validator.py` is compatibility-only. No subprocess/network/model call remains. |
| Apply-class taxonomy | Acceptable | `deterministic`, `contextual`, and `structural` remain clear. Per-finding downgrades still live in CLI and should be centralized if this grows. |
| Detection layer | Acceptable | Declarative detectors remain shallow but useful; Python heuristics are escape hatches. Loader dynamic-mechanical detection is conservative but source-inspection based. |
| Fixer layer | Watch | `fixers.py` is very large. The safety gate mitigates risk, but long-term locality would improve by splitting fixers by domain. |
| Safety/rollback | Acceptable | `apply_with_gate` remains the main protection for XML/VB/cascade regressions. It is deep enough to keep behind one interface. |
| External gates | Acceptable | Official `uip` restore/analyze/pack plus activity compile remain the publish-safety surface. Env opt-outs must stay test/debug only. |
| Project view / skip dirs | Acceptable | `project_view.py` is the right seam for project traversal. Legacy skip lists still exist in older helpers and should converge over time. |
| Publish readiness | Acceptable | J-9/W-40/A-19d readiness remains the right layer for pack/publish blockers. |
| Contextual LLM handoff | Hardened | The expected model class is frontier models (Claude Opus, Codex or equivalent), but rules stay provider-agnostic and the model only proposes diffs. |
| Security/compliance | Hardened | No hidden LLM subprocess path; cloud selector leak rules remain explicit. |
| Observability | Acceptable | Telemetry/stats exist, but architecture decisions should continue to be captured in docs/tests when hardening rules. |
| Test coverage | Hardened | Added tests for mandatory prose, provider/runtime neutrality, and CLI-wide quality enforcement. |

## Logic Failures Found And Corrected

1. Quality gate ran only on `validate`.

Impact: `review`, `fix`, `docs`, or `list` could load an enterprise-invalid
rules file if called directly.

Correction: moved `validate_rule_quality()` into `_load_rules_or_die`.

2. N-16 naming implied hidden LLM use.

Impact: future agents could infer that `ccs-uip` should call `claude -p` or
another model during review.

Correction: introduced `traceability_validator.py`, updated runtime import, and
kept `llm_validator.py` as compatibility shim only.

3. Documentation overstated `rules.yaml` as the only source artifact.

Impact: D-1*/J-1 pins are synthesized from `assets/canonical_pins.yaml`; agents
could edit the wrong file.

Correction: `ARCHITECTURE.md` now documents canonical pins as the source for
synthesized pin rules.

4. Rule text carried stale LLM-validator language.

Impact: rule prose and descriptions contradicted the offline implementation.

Correction: replaced N-16/N-5 references with traceability heuristic language.

## Remaining Architecture Opportunities

These are not blockers for enterprise rule execution, but they are the next
places to deepen the design:

1. Centralize effective apply-class policy.

`classify.py` owns rule-level apply-class, while CLI owns per-finding downgrades
for safety-guarded deterministic findings and external analyzer findings. If
more per-finding policies appear, move them behind a small classifier module so
review/fix/all cannot drift.

2. Split `fixers.py` by domain.

The module is over 5k lines. The current registry is a useful interface, but
locality would improve if implementations were grouped by XML syntax, project
JSON, logging, dependencies, invocation contracts, and UI/package-specific
fixers.

3. Converge project traversal skip rules.

`project_view.py` is the canonical seam, but some older helpers still carry
local skip lists. Future changes should move traversal decisions toward
`ProjectView` instead of copying directory heuristics.

4. Replace source-inspection detection of dynamic mechanical findings.

`loader.py` currently detects Python heuristics that emit `fix_mechanical` via
source inspection. This is pragmatic, but a declared detector capability would
be less brittle.

5. Make contextual patch loop explicit.

The rules are ready for frontier-model handoff, but there is still no first
class adapter that turns one contextual finding into one constrained diff and
then runs gates. That adapter should be model-provider agnostic and should never
write directly without toolchain validation.
