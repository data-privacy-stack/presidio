# Presidio — Agent Guidelines

Presidio is a Python SDK for detecting (presidio-analyzer) and anonymizing
(presidio-anonymizer) PII in text and images, plus CLI, structured-data, and
image-redaction components. It is a widely used **library**: users depend on
current detection behavior, and configuration files written years ago must keep
working. Correctness and backward compatibility outrank cleverness.

The review-side versions of these rules — which the Copilot PR review agent
also enforces — live in `.github/copilot-instructions.md` and
`.github/instructions/*.instructions.md`. Follow them at authoring time so the
review finds nothing.

## Working in this repo

```bash
cd presidio-analyzer            # or presidio-anonymizer, presidio-cli, ...
uv sync --locked --all-extras --group dev
uv run python -m spacy download en_core_web_lg   # analyzer/CLI only
uv run pytest -xvv
uv run ruff check . && uv run ruff format .
```

- Python `>=3.10,<3.15`; code must run on every version in range.
- Dependencies are managed with **uv**, not pip/Poetry. If you touch a
  package's `pyproject.toml` dependencies, run `uv lock` in that package and
  commit the updated `uv.lock` in the same change — CI fails on drift.
- Do not edit `CHANGELOG.md`; release entries are generated from merged PRs.
- Never log PII values (`entity.text`) — only entity types and positions.
- Modules that process records are stateless; do not add state.
- Terminology: "threshold", not "cutoff"; ISO 639-1 language codes everywhere.

## Adding a PII recognizer

Work in this order — the last step is the one most often missed, and it is the
one that matters most.

1. **Place and name it.** Country-specific recognizers go in
   `presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/{country}/`
   using the full lowercase country name (`south_africa`, `philippines`) — do
   not imitate the pre-existing short forms (`us`, `uk`, `thai`). Generic
   patterns go in `generic/`, NLP/ML-based in `nlp_engine_recognizers/` or
   `ner/`, third-party in `third_party/`.
2. **Get language codes right.** `supported_language` takes ISO 639-1 language
   codes (`ko` for Korean), never country codes (`kr`) — a mismatch loads
   nothing, silently.
3. **Make the constructor loader-compatible.** The YAML loader passes config
   keys (`name`, `supported_entity`, `context`, ...) as constructor kwargs.
   Accept them and forward to the base class, or the recognizer crashes the
   whole registry the moment a user enables it:
   `TypeError: __init__() got an unexpected keyword argument 'name'`.
4. **Calibrate scores to the pattern alone**: 0.05–0.1 bare digit runs,
   0.1–0.3 some structure, 0.3–0.5 distinctive format without validation,
   0.5+ strong. Compare with existing recognizers (`UsPassportRecognizer` uses
   0.05 for nine bare digits). Low-scoring coincidental matches are fine —
   thresholds filter them. Suppress with `score_thresholds`, not by requiring
   context (presidio-structured has no surrounding text).
5. **Choose context words that survive substring matching.** Context matches
   substrings by default (`member` fires on `remember`), and only *before* the
   match (prefix-only). Use unambiguous phrases: `member id`, `subscriber`.
6. **Use validation hooks conservatively.** `validate_result` returning `True`
   replaces the score with 1.0 — only do it when the check is genuinely
   mandatory for that value (a mod-11 check that ~9% of random tokens pass is
   not that). Return `None`, never `False`, when the check doesn't apply. No
   checksum at all is a valid design (~40% of recognizers have none). Put
   well-known sample values and reserved ranges in `invalidate_result`.
7. **Document the pattern source** in the docstring: the standard or government
   specification the format comes from, and the validation algorithm if any.
8. **Register it everywhere**: export in
   `predefined_recognizers/__init__.py` *and* the country/category
   `__init__.py`; entry in `presidio_analyzer/conf/default_recognizers.yaml`
   (`enabled: false` unless justified — the bar for shipping enabled is that no
   coincidental match can reach a score the user cannot filter); row in
   `docs/supported_entities.md`.
9. **Write the configuration-path test.** This is the load-bearing step. Most
   recognizers ship `enabled: false`, so only a test that enables yours in a
   YAML config and loads it through `RecognizerRegistryProvider` exercises the
   path users actually take:

   ```python
   def test_recognizer_loads_and_detects_when_enabled_in_yaml(tmp_path):
       conf = tmp_path / "recognizers.yaml"
       conf.write_text(
           """
   supported_languages:
     - en
   recognizers:
     - name: MyRecognizer
       supported_languages:
         - en
       type: predefined
       enabled: true
       country_code: us
   """
       )
       registry = RecognizerRegistryProvider(
           conf_file=conf
       ).create_recognizer_registry()
       analyzer = AnalyzerEngine(registry=registry, nlp_engine=nlp_engine)
       results = analyzer.analyze("Member ID ABC123456", language="en")
       assert [r.entity_type for r in results] == ["MY_ENTITY"]
   ```

   For non-English recognizers, set the top-level `supported_languages` in the
   test config — it defaults to `["en"]` and silently filters everything else.

Test-quality bar: assert **exact** scores
(`result.score == pytest.approx(EntityRecognizer.MAX_SCORE)`), never ranges;
include a lookalike negative (a plausible non-PII token of the same shape,
asserted not flagged); test the score with and without a context word; assert
exact start/end boundaries; and use example values the recognizer actually
accepts (well-known samples like `123-45-6789` are denylisted by
`UsSsnRecognizer`).

When **modifying** an existing recognizer: changed patterns, scores, or context
change detection results for existing users — state that in the PR description,
and never change an existing recognizer as a side effect of adding a new one.

## Changing the YAML configuration layer

The pydantic models in `presidio_analyzer/input_validation/` translate user
YAML into instances. Rules of the layer:

- **Every YAML-settable field needs a schema field.** Predefined-recognizer
  configs ignore unknown keys, so a constructor kwarg without a matching
  pydantic field is silently dropped. Recognizers with model-specific kwargs
  need a dedicated config model registered in `CONFIG_MODEL_MAP` (follow
  `HuggingFaceRecognizerConfig` / `GLiNERRecognizerConfig`).
- **Pick `extra` deliberately**: `forbid` for closed configs (typos fail fast),
  `allow` for pass-through kwargs models. Don't leave pydantic's silent
  `ignore` default unexamined.
- **Pass-through models dump with `exclude_none=True`** so omitted YAML fields
  keep constructor defaults instead of overriding them with `None`. Any new
  kwargs model must override `model_dump` the same way.
- **Validate at parse time with actionable messages** that name the offending
  field and show the fix — not distant `TypeError`s. Follow the existing
  validators' style (class existence, mutually exclusive fields, mode-dependent
  parameters). Prefer warnings over exceptions when the user can't fix the
  condition.
- **Never break existing YAML.** Legacy singular forms
  (`supported_language`, `supported_entity`) stay supported alongside the
  plural forms; bare-string recognizer entries and inferred `type` stay valid;
  new fields are optional; tightened validators and changed defaults are
  breaking changes that must be declared in the PR.
- **Test through `RecognizerRegistryProvider`**, not just the pydantic model:
  prove new fields reach the constructed object, and assert error *messages*
  for invalid YAML. Keep `conf/default_recognizers.yaml` validating against
  the models.

## General engineering rules

- **Declare behavior changes.** Any edit outside a brand-new file needs the PR
  description to say what existing behavior changes. Defaults on shared base
  classes, properties on abstract interfaces, and anything altering returned
  entities or scores all count, even with no signature change.
- **Explainability**: anything that changes how a score is derived must be
  reflected in `AnalysisExplanation`.
- **Component boundaries**: data flows Analyzer → Anonymizer → Output; import
  public interfaces, never another component's internals; shared models
  (`RecognizerResult`, `OperatorConfig`) are contracts — update all consumers
  in the same changeset.
- **Anonymizer operators** must be non-reversible (no deterministic hashing —
  rainbow tables), use unpredictable replacement values, and not preserve PII
  characteristics.
- **Performance**: no catastrophic regex backtracking (test long adversarial
  inputs); cache compiled regexes; batch NLP with `nlp.pipe`.
- **Docs move with code**: `docs/supported_entities.md` for entities,
  `docs/api-docs/api-docs.yml` for API changes, reST docstrings on public
  APIs, samples for complex features.
