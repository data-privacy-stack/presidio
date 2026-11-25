# PRD: Extract presidio-base

## Overview

Create a new package, `presidio-base`, in the monorepo and move the recognizer base classes and result models into it. `presidio-analyzer` depends on it and keeps every existing import path working.

This is phase 1 of moving country-specific recognizers into a separate `presidio-recognizers` package ([discussion 2414](https://github.com/data-privacy-stack/presidio/discussions/2414)). A recognizers package cannot depend on `presidio-analyzer` while the analyzer depends on it, so the shared base classes need a home below both.

## Goals

- `presidio-base` exists, is tested in CI, and is published with every release.
- Recognizer base classes and result models live in `presidio-base`.
- No change in behavior, public API, or import paths for users of any Presidio package or image.
- `presidio-base` has `regex` as its only runtime dependency.

## Non-Goals

- Creating `presidio-recognizers` or moving any predefined recognizer.
- Moving `NlpArtifacts` or changing how the analyzer uses spaCy.
- Merging the analyzer and anonymizer `RecognizerResult` classes.
- Adding a `presidio-base` dependency to `presidio-anonymizer`.
- Moving `RemoteRecognizer`, `LMRecognizer`, the registry, loaders, or the YAML validation layer.
- Relocating or rewriting existing analyzer tests.
- Changing any recognizer pattern, score, or context word.

## What Moves

| Module (today under `presidio_analyzer/`) | New location |
| --- | --- |
| `analysis_explanation.py` | `presidio_base/analysis_explanation.py` |
| `recognizer_result.py` | `presidio_base/recognizer_result.py` |
| `pattern.py` | `presidio_base/pattern.py` |
| `score_thresholds.py` | `presidio_base/score_thresholds.py` |
| `entity_recognizer.py` | `presidio_base/entity_recognizer.py` |
| `local_recognizer.py` | `presidio_base/local_recognizer.py` |
| `pattern_recognizer.py` | `presidio_base/pattern_recognizer.py` |

## Design Constraints

These apply to every story.

- **Old module paths are aliases, not copies.** Each old module (for example `presidio_analyzer.pattern_recognizer`) resolves to the same module object as its `presidio_base` counterpart. Patching, `importlib.reload`, and module-level constants such as `REGEX_TIMEOUT_SECONDS` behave as before. A plain `from presidio_base.x import *` shim is not sufficient.
- **Class identity is preserved.** `presidio_analyzer.PatternRecognizer is presidio_base.PatternRecognizer`, and the same for every moved class.
- **Existing tests are the regression gate.** Existing test source files (`*.py`) under `presidio-analyzer/tests`, `presidio-cli/tests`, `presidio-structured/tests`, `presidio-image-redactor/tests`, and `e2e-tests` are not edited, skipped, or deleted. Test dependency and configuration files, such as `e2e-tests/requirements.txt`, may change where a story requires it.
- **`NlpArtifacts` stays in the analyzer.** Moved modules reference it only under `TYPE_CHECKING`, as they do today. `presidio_base` never imports `spacy` or `presidio_analyzer` at runtime.
- **Logger names are unchanged.** Moved modules keep `logging.getLogger("presidio-analyzer")`.
- **Versions are lockstep.** `presidio-base` carries the same version as `presidio-analyzer`.
- **Packaging matches the repo.** Python `>=3.11,<3.15`, `poetry-core` build backend, uv lockfile committed, Ruff clean.
- **Published metadata uses PyPI names.** The analyzer's wheel declares `presidio-base` as a normal versioned dependency. The local path source affects development and Docker builds only.

## Prerequisite

A maintainer registers the `presidio-base` project on PyPI and configures trusted publishing for the release workflow. This is a manual step outside the stories.

## User Stories

### US-001: Scaffold the presidio-base package

**Description:** As a maintainer, I want an empty, installable `presidio-base` package wired into CI so later stories only move code.

**Acceptance Criteria:**
- [ ] `presidio-base/` contains `pyproject.toml`, `uv.lock`, `README.md`, `presidio_base/__init__.py`, `presidio_base/py.typed`, and `tests/`.
- [ ] Package name is `presidio_base`; version equals the analyzer's current version; the only runtime dependency is `regex` with the same constraint the analyzer uses.
- [ ] `cd presidio-base && uv sync --locked --group dev && uv run pytest` passes with at least one test importing the package.
- [ ] `.github/workflows/ci.yml` test matrix has a `Base` component that runs on all supported Python versions.
- [ ] `.github/labeler.yml` and `.github/dependabot.yml` cover `presidio-base/`.
- [ ] `uv run ruff check .` passes in `presidio-base`.

### US-002: Build the analyzer images from the repo root

**Description:** As a maintainer, I want analyzer images built with the repository root as the Docker context so the build can read sibling packages.

**Acceptance Criteria:**
- [ ] All six analyzer Dockerfiles (`Dockerfile`, `.dev`, `.distroless`, `.stanza`, `.transformers`, `.windows`) build with the repo root as context.
- [ ] `docker-compose.yml` and `docker-compose.distroless.yml` use the root context for the analyzer service; `docker-compose up --build` from the repo root works unchanged.
- [ ] The analyzer build steps in `.github/workflows/ci.yml` and `.github/workflows/release.yml` use the root context.
- [ ] The two analyzer devcontainers (`.devcontainer/presidio-analyzer` and `.devcontainer/presidio-analyzer-transformers`) build `Dockerfile.dev` with the root context and still open with `presidio-analyzer` as the working folder.
- [ ] Paths inside the image are unchanged: `/app` layout, conf file locations, `entrypoint.sh`, user, port, and healthcheck.
- [ ] A root `.dockerignore` (or equivalent) keeps the analyzer image contents equivalent to today's; unrelated packages are not copied into the image.
- [ ] `docker build -f presidio-analyzer/Dockerfile .` succeeds and the container answers `/health`.
- [ ] No Python source file changes in this story.

### US-003: Move the result and pattern models

**Description:** As a maintainer, I want the leaf models in `presidio-base` and the analyzer consuming them, so the dependency between the two packages is established on the simplest classes first.

**Acceptance Criteria:**
- [ ] `analysis_explanation.py`, `recognizer_result.py`, `pattern.py`, and `score_thresholds.py` live in `presidio_base`; the four names `AnalysisExplanation`, `RecognizerResult`, `Pattern`, and the score-threshold helpers are importable from it.
- [ ] `presidio-analyzer/pyproject.toml` declares `presidio-base` as a dependency and a `[tool.uv.sources]` path entry pointing at `../presidio-base`; `presidio-analyzer/uv.lock` is regenerated.
- [ ] The four old `presidio_analyzer.*` module paths alias the new modules per the design constraints.
- [ ] Analyzer Dockerfiles install `presidio-base` from the repo source; `python -c "import presidio_base"` works in the built image.
- [ ] The CI test jobs for Image Redactor, CLI, and Structured install the in-repo `presidio-base` and the in-repo analyzer over the locked PyPI analyzer, and later steps do not re-sync the environment back to the locked versions.
- [ ] Both analyzer devcontainers mount `presidio-base` next to `presidio-analyzer` so the path source resolves, and their dependency setup installs the in-repo `presidio-base`.
- [ ] `e2e-tests/requirements.txt` installs the in-repo `presidio-base` alongside the in-repo analyzer, so both E2E jobs pass before `presidio-base` is published.
- [ ] The full `presidio-analyzer` test suite passes with no test file edited.
- [ ] A new analyzer test asserts class identity and old-module-path imports for each moved class.
- [ ] `presidio-base` tests cover the moved code at 90% or more and run in an environment without `spacy` and without `presidio_analyzer`.

### US-004: Move the recognizer base classes

**Description:** As a recognizer author, I want `EntityRecognizer`, `LocalRecognizer`, and `PatternRecognizer` in `presidio-base` so a recognizer package can subclass them without depending on the analyzer.

**Acceptance Criteria:**
- [ ] `entity_recognizer.py`, `local_recognizer.py`, and `pattern_recognizer.py` live in `presidio_base` and import only from `presidio_base`, the standard library, and `regex` at runtime.
- [ ] The three old `presidio_analyzer.*` module paths alias the new modules; `from presidio_analyzer.pattern_recognizer import REGEX_TIMEOUT_SECONDS` and reloading that module with the environment variable set behave as before.
- [ ] `presidio_analyzer.__init__` exports the same names in the same order as before.
- [ ] The full test suites of `presidio-analyzer`, `presidio-cli`, `presidio-structured`, and `presidio-image-redactor` pass with no test file edited, each running against the in-repo analyzer and `presidio-base`.
- [ ] The identity test from US-003 is extended to the three classes.
- [ ] `presidio-base` tests define a `PatternRecognizer` subclass and assert detection, exact score, and start/end positions with `nlp_artifacts=None`, in an environment without `spacy` and without `presidio_analyzer`. Moved code is covered at 90% or more.
- [ ] End-to-end tests pass against the default and distroless images.

### US-005: Publish presidio-base in the release workflow

**Description:** As a maintainer, I want `presidio-base` released together with the other packages so a published analyzer always finds its dependency on PyPI.

**Acceptance Criteria:**
- [ ] `.github/workflows/release.yml` builds and publishes `presidio-base` to PyPI.
- [ ] The analyzer publish job runs after the base publish job succeeds.
- [ ] The built analyzer wheel's metadata lists `presidio-base` with a version constraint and contains no local path.
- [ ] The version-bump process updates `presidio-base` together with the analyzer; a CI check fails when the two versions differ.
- [ ] `pip install` of the locally built analyzer and base wheels into a clean environment succeeds, and `from presidio_analyzer import AnalyzerEngine, PatternRecognizer` works.

### US-006: Update the install-from-source documentation

**Description:** As a user building Presidio from a clone, I want the docs to describe one supported way to build so I do not build a single package directory that depends on a sibling.

**Acceptance Criteria:**
- [ ] The "Install from source" section of `docs/installation.md` describes building from the repository root with Docker Compose as the supported path, including building a single service through Compose.
- [ ] The per-directory example (`docker build ./presidio-anonymizer`) is replaced with a root-context command, and the analyzer form `docker build -f presidio-analyzer/Dockerfile .` is shown.
- [ ] `docs/analyzer/languages.md` shows the root-context command next to the `Dockerfile.transformers` reference.
- [ ] `docs/development.md` lists `presidio-base` among the packages and states that the analyzer resolves it from the local checkout.
- [ ] `presidio-base/README.md` states the package's purpose and that applications should install `presidio-analyzer`, not `presidio-base` directly.
- [ ] `CHANGELOG.md` is not edited.

## Story Order

US-001 and US-002 are independent. US-003 requires both. US-004 requires US-003. US-005 and US-006 require US-004.

## Behavior Changes to Declare in Pull Requests

| Change | Affected users |
| --- | --- |
| Analyzer images build from the repo root; `docker build ./presidio-analyzer` no longer works | Users building analyzer images from a clone without Compose |
| Installing `presidio-analyzer` also installs `presidio-base` | All analyzer users; no action needed |
| `__module__` of moved classes is `presidio_base.*` | Visible in reprs and in newly created pickles; existing pickles still load |

No detection results, scores, explanations, or YAML configuration behavior change.

## Success Metrics

- Every existing test passes with zero edits to existing test files.
- `pip install presidio-base` installs only `presidio-base` and `regex`.
- A `PatternRecognizer` subclass can be defined and run with only `presidio-base` installed.
- Published images and `pip install presidio-analyzer` behave identically to the previous release.
