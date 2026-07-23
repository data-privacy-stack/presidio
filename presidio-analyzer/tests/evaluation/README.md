# Analyzer evaluation harness

A CI harness that measures analyzer detection quality (per-entity
precision / recall / F2) and latency against a curated, hand-annotated golden
dataset, using the org's own
[`presidio-evaluator`](https://github.com/data-privacy-stack/presidio-research)
package as the scoring engine. It addresses
[#1639](https://github.com/data-privacy-stack/presidio/issues/1639) (evaluate
precision/recall/latency during CI) and
[#1810](https://github.com/data-privacy-stack/presidio/issues/1810) (curated
PII/PHI benchmark dataset), and lays the groundwork for the recipes comparison
in [#1809](https://github.com/data-privacy-stack/presidio/issues/1809).

## Installing

`presidio-evaluator` is in the `evaluation` dependency group (not installed by
the default test matrix). From the `presidio-analyzer` directory:

```sh
uv sync --group dev --group evaluation
uv run python -m spacy download en_core_web_sm   # tokenization
uv run python -m spacy download en_core_web_lg   # default NER
```

## Running it

```sh
python -m tests.evaluation.run_evaluation            # report to stdout
python -m tests.evaluation.run_evaluation --output report.md
python -m tests.evaluation.run_evaluation --iou 0.75 # stricter span overlap

# evaluate another analyzer configuration (e.g. transformers):
python -m tests.evaluation.run_evaluation \
    --analyzer-conf path/to/analyzer_conf.yaml \
    --write-baseline tests/evaluation/baselines/my_config.json

# enforce the baseline locally (CI does not do this yet):
python -m tests.evaluation.run_evaluation --fail-on-regression
```

The end-to-end smoke run also executes under `pytest tests/evaluation` when the
`evaluation` group is installed (it is skipped otherwise), and a CI job
publishes the report to the workflow step summary on every PR.

## Design decisions

**Scoring engine is `presidio-evaluator`.** Rather than a bespoke evaluator,
scoring uses `presidio-evaluator`'s span-based `SpanEvaluator` (character IoU)
wrapped around `PresidioAnalyzerWrapper`, with F-beta = 2 (recall-weighted),
matching Presidio's documented evaluation convention. `presidio-evaluator` is
the org's own sibling package (`data-privacy-stack/presidio-research`), already
referenced by `docs/evaluation/index.md`, so this reuses the standard data
model (`InputSample`/`Span`), metrics and error analysis instead of reinventing
them. This harness is the thin CI layer on top: dataset, baseline ratchet,
markdown report and gating flags.

**The `CanonicalMapper` step is skipped.** `presidio-evaluator`'s entity
hierarchy/mapper reconciles differing label spaces between a model and a
dataset. Our golden dataset is annotated with the analyzer's own entity names,
so predictions and annotations already share a label space — mapping is
unnecessary, and skipping it keeps the report keyed by raw Presidio entity
types and the run deterministic (no interactive resolution).

**Enforcement is built in but switched off.** The report compares every run
against the checked-in baseline (`baselines/spacy_en.json`) and shows
per-entity F2 deltas; `--fail-on-regression` exits non-zero when overall or
per-entity F2 drops more than `--f2-tolerance` (default 0.02) below the
baseline. CI runs report-only: switching enforcement on is a one-line CI
change, deliberately left as a maintainer decision once the numbers have proven
stable across real PRs (a new spaCy model release can shift NER results with no
code change).

**Updating the baseline** is part of the PR that changes behavior:
`python -m tests.evaluation.run_evaluation --write-baseline
tests/evaluation/baselines/spacy_en.json`, committed alongside the code, so
reviewers see the metric change explicitly in the diff.

**Curated golden set now, synthetic generation later.** A checked-in,
hand-annotated dataset is deterministic, reviewable in diffs, and cheap to run
per-PR. The template + Faker synthetic generation described in #1639 (available
in `presidio-evaluator` as `PresidioSentenceFaker`) is the right tool for
scaling coverage with every new recognizer, and is planned as a follow-up
phase — its output is `InputSample`s, the same type this harness already
consumes.

**Evaluated entities are a fixed allowlist.** Predictions for entity types not
declared in the dataset (`entities` in `golden_en.json`) are excluded via
`entities_to_keep`, so recognizers without golden coverage don't pollute the
report with unreviewable false positives. Adding coverage for a new entity =
adding annotated samples + the entity to the allowlist.

**Per-PR CI evaluates the default configuration only.** That covers spaCy NER
(`PERSON`, `LOCATION`, `DATE_TIME`) plus the predefined pattern/checksum
recognizers. HuggingFace, GLiNER and transformers recognizers are optional
extras with large model downloads — and their `transformers>=?` pins conflict
with `presidio-evaluator`'s, so they are declared mutually exclusive in
`[tool.uv] conflicts` and not run per-PR. The runner already supports them via
`--analyzer-conf <yaml>` with a separate baseline per configuration; wiring
them into a scheduled nightly job is roadmap step 4.

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

> Note: per-entity `support` in the report is computed by `presidio-evaluator`
> from its token/span reconstruction and may differ slightly from the raw gold
> span count.

### Extending the dataset

`generate_golden_en.py` is the source of truth — samples are defined as
interleaved text parts and `(value, entity_type)` tuples, so offsets are
computed rather than hand-counted. To add coverage (e.g. for a new recognizer):

1. Add samples to `SAMPLES` in `generate_golden_en.py` (and the entity type
   to `ENTITIES` if new).
2. Regenerate: `python -m tests.evaluation.generate_golden_en`
3. Regenerate the baseline: `... run_evaluation --write-baseline
   tests/evaluation/baselines/spacy_en.json`
4. Commit all three; a sync test fails if the JSON drifts from the generator,
   so the JSON can never be hand-edited.

### Other languages

The dataset format is language-agnostic: one file per language
(`golden_en.json` today, e.g. `golden_de.json` later), each declaring its
`language` and evaluated entity list. What is still English-only is the runner,
which builds a default `AnalyzerEngine`; another language means adding a
per-language engine configuration and installing its model in the CI job.
Planned alongside the nightly matrix (roadmap step 4).

## Roadmap

1. **(this PR)** `presidio-evaluator`-based harness + golden dataset +
   baselines and regression detection (enforcement off) + report-only CI job.
2. Switch `--fail-on-regression` on in CI once metrics have proven stable —
   a one-line CI change plus a baseline-update note in CONTRIBUTING.
3. Synthetic data generation via `PresidioSentenceFaker` (templates + Faker
   providers); contributing a recognizer requires contributing templates (#1639).
4. Nightly multi-configuration matrix (spaCy / transformers / GLiNER / LLM)
   with per-configuration baselines and non-English datasets, feeding the
   fast/balanced/accurate recipes comparison (#1809).
