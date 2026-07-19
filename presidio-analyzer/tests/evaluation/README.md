# Analyzer evaluation harness

A span-level evaluation harness for measuring analyzer detection quality
(per-entity precision / recall / F1) and latency against a curated,
hand-annotated golden dataset. It addresses
[#1639](https://github.com/data-privacy-stack/presidio/issues/1639) (evaluate
precision/recall/latency during CI) and
[#1810](https://github.com/data-privacy-stack/presidio/issues/1810) (curated
PII/PHI benchmark dataset), and lays the groundwork for the recipes comparison
in [#1809](https://github.com/data-privacy-stack/presidio/issues/1809).

## Running it

From the `presidio-analyzer` directory (requires `en_core_web_lg`):

```sh
python -m tests.evaluation.run_evaluation            # report to stdout
python -m tests.evaluation.run_evaluation --output report.md
python -m tests.evaluation.run_evaluation --iou 1.0  # exact-span matching

# evaluate another analyzer configuration (e.g. transformers):
python -m tests.evaluation.run_evaluation \
    --analyzer-conf path/to/analyzer_conf.yaml \
    --write-baseline tests/evaluation/baselines/my_config.json

# enforce the baseline locally (CI does not do this yet):
python -m tests.evaluation.run_evaluation --fail-on-regression
```

The same evaluation also runs as part of the regular test suite
(`pytest tests/evaluation`), and a CI job publishes the report to the
workflow step summary on every PR.

## Design decisions

**Enforcement is built in but switched off.** The report compares every run
against the checked-in baseline (`baselines/spacy_en.json`) and shows
per-entity F1 deltas; `--fail-on-regression` exits non-zero when overall or
per-entity F1 drops more than `--f1-tolerance` (default 0.02) below the
baseline. CI runs report-only: switching enforcement on is a one-line CI
change, deliberately left as a maintainer decision to take once the numbers
have been observed to be stable across real PRs. Gating on day one would
risk blocking contributor PRs on flaky or contested thresholds — e.g. a new
`en_core_web_lg` release can shift NER results with no code change.

**Updating the baseline** is part of the PR that changes behavior:
`python -m tests.evaluation.run_evaluation --write-baseline
tests/evaluation/baselines/spacy_en.json`, committed alongside the code, so
reviewers see the metric change explicitly in the diff.

**Curated golden set now, synthetic generation later.** A checked-in,
hand-annotated dataset is deterministic, reviewable in diffs, and cheap to
run per-PR. The template + Faker synthetic generation described in #1639 is
the right tool for scaling coverage with every new recognizer, and is planned
as a follow-up phase — the evaluator here consumes plain annotated samples,
so generated data plugs into the same pipeline.

**Small internal evaluator instead of depending on presidio-evaluator.** The
matching logic needed for CI (span IoU matching, per-entity counts, a
markdown report) is a few hundred lines. Vendoring it avoids coupling CI to
an external research repo and keeps install time minimal. If it grows, it can
graduate to a standalone package.

**Raw analyzer output is evaluated.** The analyzer intentionally returns
overlapping candidates of different types (e.g. `PHONE_NUMBER` over an SSN)
and leaves conflict resolution to the anonymizer. The report therefore counts
such overlaps as false positives — that is useful signal about analyzer
precision, but it means per-entity precision here is a lower bound on
end-to-end precision after anonymizer conflict resolution.

**Evaluated entities are a fixed allowlist.** Predictions for entity types
not declared in the dataset (`entities` in `golden_en.json`) are ignored, so
recognizers without golden coverage don't pollute the report with
unreviewable false positives. Adding coverage for a new entity = adding
annotated samples + the entity to the allowlist.

**Per-PR CI evaluates the default configuration only.** That covers spaCy
NER (`PERSON`, `LOCATION`, `DATE_TIME`) plus the predefined pattern/checksum
recognizers. HuggingFace, GLiNER and other NER recognizers are optional
extras with large model downloads, so they are not run per-PR; the runner
already supports them via `--analyzer-conf <yaml>` with a separate baseline
per configuration (`--write-baseline`). Wiring those configurations into a
scheduled nightly job — where model download cost is paid once a day, not
per PR — is roadmap step 4.

## Dataset

`datasets/golden_en.json` — 46 English samples, 93 annotated spans across 12
entity types (`PERSON`, `LOCATION`, `DATE_TIME`, `EMAIL_ADDRESS`,
`PHONE_NUMBER`, `CREDIT_CARD`, `US_SSN`, `IP_ADDRESS`, `URL`, `IBAN_CODE`,
`CRYPTO`, `UK_NHS`), organized in categories per #1810:

- `simple` — single-entity one-liners
- `medium` — multi-entity texts (support tickets, clinical notes, logs)
- `long` — full documents (discharge summary, incident report, KYC)
- `edge` — lowercase/inverted names, hyphenated names, adjacent entities,
  entities at text boundaries, inline IDs
- `negative` — no PII, but tempting lookalikes (version numbers, room
  numbers, quantities)

Entity values are checksum-valid where recognizers validate (Luhn for cards,
mod-97 for IBANs, NHS check digit, SSN excluded ranges), reusing values from
the unit tests where possible. Span offsets are validated by
`test_golden_dataset.py::TestDatasetIntegrity`, so every annotation is
guaranteed to match its text slice.

### Extending the dataset

`generate_golden_en.py` is the source of truth — samples are defined as
interleaved text parts and `(value, entity_type)` tuples, so offsets are
computed rather than hand-counted. To add coverage (e.g. for a new
recognizer):

1. Add samples to `SAMPLES` in `generate_golden_en.py` (and the entity type
   to `ENTITIES` if new).
2. Regenerate: `python -m tests.evaluation.generate_golden_en`
3. Commit both files; a sync test fails if the JSON drifts from the
   generator, so the JSON can never be hand-edited.

### Other languages

The dataset format and evaluator are language-agnostic: one file per
language (`golden_en.json` today, e.g. `golden_de.json` later), each
declaring its `language` and evaluated entity list. What is still
English-only is the runner, which builds a default `AnalyzerEngine`;
supporting another language means adding a per-language engine
configuration (NLP model + registry languages) to `run_evaluation.py` and
installing that language's model in the CI job. Planned alongside the
nightly multi-configuration matrix (roadmap step 4).

## Roadmap

1. **(this PR)** Evaluator + golden dataset + baselines and regression
   detection (enforcement off) + report-only CI job.
2. Switch `--fail-on-regression` on in CI once metrics have proven stable —
   a one-line CI change plus a baseline-update workflow note in
   CONTRIBUTING.
3. Synthetic data generation from templates + Faker providers; contributing
   a recognizer requires contributing templates (see #1639).
4. Nightly multi-configuration matrix (spaCy / transformers / GLiNER / LLM)
   with per-configuration baselines and non-English datasets, feeding the
   fast/balanced/accurate recipes comparison (#1809).
