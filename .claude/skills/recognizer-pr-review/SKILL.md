---
name: recognizer-pr-review
description: >-
  Reviews Presidio pull requests for recognizer correctness, test coverage, and
  backward compatibility. Use this whenever reviewing, or being asked to review,
  a PR or diff in this repo — especially any change that adds or modifies a
  PII recognizer (files under predefined_recognizers/, edits to
  default_recognizers.yaml, new Pattern/CONTEXT/validate_result code, or a new
  recognizer test). Also use it for any change to a shared analyzer/anonymizer
  base class, since those ripple across the library. Trigger even when the user
  just says "review this PR", "look over my changes", or "does this recognizer
  look right" without naming recognizers explicitly.
---

# Reviewing Presidio recognizer & core PRs

Presidio is a library. A recognizer that works when built in Python can still be
unreachable, or crash, when a user enables it in YAML — and a one-line change to a
shared base class silently alters detection results for every downstream user who
wrote no new code. This skill exists so those two failure modes get caught in
review instead of in production.

Use it to review a diff. Work in two passes: first decide **what kind of change
this is**, then apply the matching checklist below.

## Pass 1 — Classify the change

Look at the changed files and answer these before commenting:

- **Does it add or change a recognizer?** Signals: new/edited files under
  `predefined_recognizers/`, new `Pattern(...)` / `PATTERNS` / `CONTEXT`, a
  `validate_result` / `invalidate_result` override, a new entry (or an
  `enabled:` / `supported_languages:` edit) in
  `presidio_analyzer/conf/default_recognizers.yaml`, or a new
  `test_*_recognizer.py`. → Apply **Recognizer checklist**.
- **Does it touch a shared class?** Anything in the analyzer/anonymizer base
  classes, `RecognizerRegistry`, providers, enhancers, or `EntityRecognizer` /
  `PatternRecognizer` themselves. → Apply **Backward-compatibility checklist**.

A single PR is often both. When in doubt, run both passes.

Keep feedback specific and actionable — cite the file and line, and give the
concrete fix, not just the concern. Let CI handle formatting; don't spend review
budget on style Ruff already enforces.

## Recognizer checklist

The single highest-value thing to verify is the **configuration-path test**,
because it is the gap that Python-only tests structurally cannot cover.

### 1. Require a configuration-path test (the load-bearing rule)

Most predefined recognizers ship `enabled: false`, so the default test run never
constructs them from configuration. Users, however, reach them exactly one way:
flipping `enabled: true` in a registry YAML. If the PR's only tests build the
recognizer directly in Python, that user path is untested.

**Require at least one test that loads the recognizer through
`RecognizerRegistryProvider` and asserts detection.** It should write a small
YAML config with the recognizer `enabled: true`, build the registry, run
`AnalyzerEngine.analyze`, and assert the entity is returned. See
`references/config-path-testing.md` for a template and the full list of defects
this catches (constructor-signature mismatches, missing `__init__.py` exports,
`country_code` / language-filter mismatches, class defaults dropped on load).

Real bugs this rule surfaces, reproduced through the registry:

```
TypeError: UsMbiRecognizer.__init__() got an unexpected keyword argument 'name'
```

The loader passes the YAML `name` key to the constructor; a recognizer whose
`__init__` doesn't accept `name` takes down construction of the whole registry
the moment it's enabled. Python-only tests never see it.

### 2. Construction paths must agree

Building the recognizer directly, adding it via `registry.add_recognizer()`, and
loading it from configuration must all yield the same recognizer. Flag any
defaulting or validation logic that runs on one path but not the others — that
divergence is a latent bug, and it's the thing config-path tests exist to expose.

### 3. Language codes vs. country codes

`supported_language` / the YAML `supported_languages` key take **ISO 639-1
language codes** (`ko` for Korean), not country codes (`kr`). A mismatch produces
a recognizer that loads nothing — silently, with no error. Also check the
top-level `supported_languages` in any test config: it defaults to `["en"]` and
acts as a global filter, so a `de`-only recognizer won't load unless the test
sets it. Non-English recognizers should state the required top-level languages in
the PR description.

### 4. Score calibration and pattern specificity

The base score should reflect how much the pattern *alone* narrows the space,
independent of any downstream threshold. A generic pattern scored high is the
core false-positive risk.

| Score | Use when | Name |
| --- | --- | --- |
| 0.05–0.1 | Bare digit/alphanumeric runs, no structure | `(very weak)` |
| 0.1–0.3 | Some structure: delimiters, prefix, length constraint | `(weak)` |
| 0.3–0.5 | Distinctive format, no validation | `(medium)` |
| 0.5+ | Distinctive format | `(strong)` |

Compare against existing recognizers before accepting a score (`UsPassport` uses
0.05 for nine bare digits). A 0.3 on a pattern that also matches `covid19` or
`sha256` is overstated.

### 5. Validation / invalidation hooks

`validate_result` returning `True` **replaces the score with 1.0** — it is a jump
to full confidence, not a nudge. Before accepting a `return True`, ask what
fraction of arbitrary same-shape tokens would pass the check; a mod-11 check on a
17-char token passes ~9% of the time, sending ~9% of coincidental matches to 1.0
where no threshold can filter them.

- Return `None`, never `False`, when the check doesn't apply. `False` means
  "definitely not the entity" and discards the result.
- Only promote with `True` where the check is genuinely mandatory for that value.
- No checksum is fine — ~40% of predefined recognizers don't override
  `validate_result`. Don't flag a missing validator; the base score plus a
  threshold is a valid design. Do flag an *invented* one that promotes weak
  matches.
- Well-known sample values and reserved ranges belong in `invalidate_result`,
  not buried in the regex.

### 6. Enabled-by-default decision

The question is **not** which country the entity belongs to — it's whether the
recognizer can produce *high-confidence* false positives. Default to
`enabled: false`; anything else needs justification in the PR description. The
disqualifier for shipping enabled is a coincidental match arriving at a score the
user cannot filter (i.e. something promoted it to a high score).

### 7. Context words

Context is matched as **substrings** by default (`context_matching_mode=
"substring"` in `LemmaContextAwareEnhancer`), so short words fire on unrelated
tokens: `member` matches `remember`, `auth` matches `author`. Prefer context
words long enough to be unambiguous (`member id`, `subscriber`). Context is also
prefix-only by default, so a context word *after* the match doesn't boost — tests
should cover both placements.

Don't design a recognizer that can't fire without context: `presidio-structured`
has no surrounding text. Suppress low-confidence matches with thresholds, not by
requiring context.

### 8. Test quality

- **Assert exact scores, not ranges.** `assert 0.5 <= score <= 1.0` still passes
  when checksum promotion or context enhancement breaks entirely. Pin it:
  `assert result.score == pytest.approx(EntityRecognizer.MAX_SCORE)`.
- **Include a lookalike negative.** The false-positive surface is the point of the
  test, not the happy path. Add a plausible non-PII token of the same shape (a
  17-char order ID for a VIN, a legal citation for a bank number) and assert it is
  *not* flagged.
- **Exercise context enhancement.** A recognizer defining `CONTEXT` needs a test
  showing the score differs between text with and without a context word.
- **Use example values the recognizer actually accepts.** Well-known samples like
  `123-45-6789` are denylisted by `UsSsnRecognizer`; using one as a true positive
  fails, and using it as a false-positive case passes for the wrong reason.

### 9. Required companion updates

A new recognizer needs all of: the export in `predefined_recognizers/__init__.py`
and the country `__init__.py`, an entry in `default_recognizers.yaml`, and a row
in `docs/supported_entities.md`. A missing export is exactly what the
config-path test catches.

Directory naming: prefer the full lowercase country name
(`south_africa`, `philippines`). Some pre-existing dirs use short forms
(`us`, `uk`, `thai`) — don't imitate them for new directories.

## Backward-compatibility checklist

Because Presidio is a library, changes to shared classes alter results for users
who wrote no new code. Require the PR description to state what existing behavior
changes for anything edited outside a brand-new file. These count as behavior
changes even with no signature change:

- Default values on shared base classes (`None` → `[]` flips truthiness for every
  subclass).
- Properties on abstract interfaces — custom implementations inherit the new
  default and may break.
- Scores, context lists, or patterns on *existing* recognizers. Flag any such
  edit made as a side effect of adding a new recognizer; users depend on current
  detection behavior.
- Anything altering which entities are returned for text that already worked.

Two more to watch for:

- **Surface new scoring inputs in explainability.** Anything changing how a score
  is derived (context, negative context, thresholds) must show up in
  `AnalysisExplanation`, or users can't tell why a result scored as it did.
- **Prefer warnings over exceptions when the caller can't fix the condition.**
  Raising on a config the user didn't write turns a degraded result into a hard
  failure. Prefer a property on a base class over a maintained list of class
  names — lists drift, and PyPI users can't extend them.

## Review-priority ordering

When summarizing, lead with the highest-impact gaps in this order:

1. No configuration-path test for a new recognizer.
2. Construction paths that disagree.
3. Undeclared backward-incompatible change to a shared class or existing recognizer.
4. `validate_result` promoting weak matches to 1.0 / range-based score assertions.
5. Missing lookalike negative or context-enhancement test.
6. Language/country-code mismatch, missing exports or doc rows.

Terminology: say "threshold", not "cutoff"; use ISO 639-1 codes in examples.
