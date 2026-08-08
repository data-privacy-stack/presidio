---
applyTo: >-
  presidio-analyzer/presidio_analyzer/predefined_recognizers/**,
  presidio-analyzer/presidio_analyzer/conf/default_recognizers.yaml,
  presidio-analyzer/tests/**/test_*recognizer*.py
---

# Copilot code review — recognizer & core changes

These instructions apply only to code review of recognizer and shared-analyzer
changes. Give specific, actionable feedback: cite the file and line and propose
the concrete fix. Do not comment on formatting — Ruff and CI own that.

## Highest-priority checks (lead the review with these)

1. **Configuration-path test is required.** Most predefined recognizers ship
   `enabled: false`, so Python-only tests never construct them the way users do —
   by flipping `enabled: true` in a registry YAML. If a PR adds or changes a
   recognizer but only builds it directly in Python, request a test that loads it
   through `RecognizerRegistryProvider` (write a small YAML config with the
   recognizer `enabled: true`, build the registry, run `AnalyzerEngine.analyze`,
   assert the entity is returned). This is the check that catches
   `TypeError: __init__() got an unexpected keyword argument 'name'` — the loader
   passes the YAML `name` key to the constructor, and a recognizer that doesn't
   accept it crashes the whole registry when enabled.
2. **Construction paths must agree.** Direct construction, `add_recognizer()`, and
   config loading must yield the same recognizer. Flag defaulting or validation
   applied on one path but not the others.
3. **Undeclared backward-incompatible changes.** Presidio is a library; changes to
   shared base classes alter results for users who wrote no new code. If the PR
   edits anything outside a brand-new file (base-class defaults, interface
   properties, or scores/patterns/context on an *existing* recognizer), require the
   PR description to state what existing behavior changes. Flag edits to an existing
   recognizer's patterns/scores/context made as a side effect of adding a new one.

## Recognizer-specific checks

- **Language vs. country codes.** `supported_language` and the YAML
  `supported_languages` key take ISO 639-1 language codes (`ko`), not country codes
  (`kr`); a mismatch loads nothing, silently. The top-level `supported_languages`
  in a config defaults to `["en"]` and filters everything else out — non-English
  recognizers must set it in tests and note it in the PR.
- **Score calibration.** The base score should reflect how much the pattern alone
  narrows the space: ~0.05–0.1 for bare digit/alphanumeric runs, 0.1–0.3 for some
  structure, 0.3–0.5 for a distinctive format, 0.5+ for strong. Flag a high score
  on a generic pattern (a 0.3 that also matches `covid19`/`sha256` is overstated).
- **`validate_result` promotion.** Returning `True` replaces the score with 1.0 —
  full confidence, not a nudge. Flag `return True` on a check that arbitrary
  same-shape tokens pass at a meaningful rate (a mod-11 check on a 17-char token
  passes ~9% of the time). Require `None` (not `False`) when the check doesn't
  apply; `False` discards the result. A missing checksum is fine (~40% of
  recognizers have none) — don't ask for an invented one.
- **Context words.** Context is matched as substrings by default
  (`context_matching_mode="substring"` in `LemmaContextAwareEnhancer`), so short
  words fire on unrelated tokens (`member`→`remember`, `auth`→`author`). Prefer
  unambiguous multi-word context. Context is prefix-only by default; a word after
  the match doesn't boost. Don't require context to fire — `presidio-structured`
  has no surrounding text; suppress with thresholds instead.
- **Enabled-by-default.** Default to `enabled: false`. The test for shipping
  enabled is whether the recognizer can produce *high-confidence* false positives
  (a coincidental match at a score the user can't filter), not which country it
  belongs to.
- **Companion updates.** A new recognizer needs its exports in the
  `predefined_recognizers/__init__.py` and country `__init__.py`, an entry in
  `default_recognizers.yaml`, and a row in `docs/supported_entities.md`. New
  directories use the full lowercase country name (`south_africa`); pre-existing
  short forms (`us`, `uk`, `thai`) should not be imitated.

## Test-quality checks

- **Assert exact scores, not ranges.** `assert 0.5 <= score <= 1.0` still passes
  when checksum promotion or context enhancement breaks. Require
  `== pytest.approx(...)`.
- **Require a lookalike negative** — a plausible non-PII token of the same shape
  (a 17-char order ID for a VIN, a legal citation for a bank number) asserted as
  *not* flagged. This is the actual false-positive surface.
- **Require a context-enhancement test** for any recognizer defining `CONTEXT`:
  the score must differ between text with and without a context word.
- **Reject denylisted example values** used as true positives (e.g. `123-45-6789`
  is denylisted by `UsSsnRecognizer`).

## Terminology

Say "threshold", not "cutoff". Use ISO 639-1 language codes in examples.
