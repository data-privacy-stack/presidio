# Presidio Development Instructions

Presidio is a Python-based data protection and de-identification SDK with multiple components for detecting and anonymizing PII (Personally Identifiable Information) in text and images.

## Core Philosophy

**Data Privacy is Paramount** - This is a PII detection and anonymization system used in sensitive contexts. Security and correctness are non-negotiable.

**Key Principles:**
- **Accuracy First**: False negatives (missed PII) and false positives (incorrect detections) both damage trust
- **Security by Default**: Never log PII values, use non-reversible anonymization, validate all inputs
- **Cross-Component Awareness**: Presidio is a multi-component system - changes ripple across boundaries
- **Stateless Design**: Presidio is designed for scalability - avoid adding unnecessary state
- **Documentation Integrity**: Code and docs must stay synchronized - outdated docs are dangerous

---

## Part 1: Implementation Guidelines

Use these guidelines when **generating or writing code** for Presidio.

### Presidio Architecture Patterns



**Data Flow (Unidirectional):**
```
Analyzer (detect PII) → Anonymizer (transform PII) → Output
    ↓
nlp_engine → recognizers → context
```

**Design Patterns:**
- **Registry Pattern**: `RecognizerRegistry` for dynamic recognizer management
- **Provider Pattern**: `NlpEngineProvider`, `RecognizerRegistryProvider` for configuration

### Implementing New Recognizers

**1. Choose the Right Base Class:**
```python
from presidio_analyzer import PatternRecognizer, LocalRecognizer, RemoteRecognizer

# For regex-based detection
class MyPatternRecognizer(PatternRecognizer):
    pass

# For custom logic (NLP, ML)
class MyCustomRecognizer(LocalRecognizer):
    def load(self): ...
    def analyze(self, text, entities, nlp_artifacts): ...

# For calling remote services
class MyRemoteRecognizer(RemoteRecognizer):
    def analyze(self, text, entities, nlp_artifacts): ...
```

**2. Predefined Recognizers Location Matters:**
- Country-specific: `presidio-analyzer/presidio_analyzer/predefined_recognizers/country_specific/{country}/`
- Generic patterns: `.../predefined_recognizers/generic/`
- NLP/ML-based: `.../predefined_recognizers/nlp_engine_recognizers/` or `.../ner/`
- Third-party: `.../predefined_recognizers/third_party/`

**3. Pattern Design Best Practices:**
```python
# ❌ BAD: Too broad - matches month names as persons
pattern = r"\b[A-Z][a-z]+\b"

# ✅ GOOD: Specific pattern with context
PATTERNS = [
    Pattern(
        "SSN", 
        r"\b\d{3}-\d{2}-\d{4}\b",
        0.3  # Low base score, context will boost
    )
]

CONTEXT = ["ssn", "social security", "tax id"]
```

**4. Document Pattern Sources:**
```python
"""
Recognizes US Social Security Numbers.

Pattern based on SSA Publication No. 05-10633:
https://www.ssa.gov/history/ssn/geocard.html

Validation uses SSN format rules: AAA-GG-SSSS
- AAA: Area number (001-899, excluding 666)
- GG: Group number (01-99)
- SSSS: Serial number (0001-9999)
"""
```

**5. Required Configuration Updates:**
```python
# Update all of these:
# 1. presidio_analyzer/predefined_recognizers/__init__.py
from .country_specific.us.my_recognizer import MyRecognizer
__all__ = [..., "MyRecognizer"]

# 2. presidio_analyzer/predefined_recognizers/country_specific/us/__init__.py  
from .my_recognizer import MyRecognizer
__all__ = [..., "MyRecognizer"]

# 3. presidio_analyzer/conf/default_recognizers.yaml
recognizers:
  - name: MyRecognizer
    supported_languages: ["en"]
    type: predefined
    enabled: false  # Country-specific defaults to false

# 4. docs/supported_entities.md (add row to appropriate table)
# 5. CHANGELOG.md (under "Unreleased" section)
```

**6. Comprehensive Test Coverage:**
```python
@pytest.mark.parametrize("text, expected_len, expected_positions", [
    # True positives - valid formats
    ("SSN: 123-45-6789", 1, ((5, 16),)),
    ("My SSN is 123-45-6789", 1, ((10, 21),)),
    
    # True negatives - invalid formats  
    ("SSN: 000-00-0000", 0, ()),  # Invalid area
    ("SSN: 666-12-3456", 0, ()),  # Excluded area
    
    # Boundary testing - embedded in text
    ("Contact: 123-45-6789 for info", 1, ((9, 20),)),
    
    # False positive prevention
    ("ISBN: 123-45-6789", 0, ()),  # Different context
])
def test_ssn_detection(text, expected_len, expected_positions, recognizer):
    results = recognizer.analyze(text, ["US_SSN"])
    assert len(results) == expected_len
    for result, (start, end) in zip(results, expected_positions):
        assert result.start == start
        assert result.end == end
```

### Implementing New Anonymizers (Operators)

**1. Implement the Operator Interface:**
```python
from presidio_anonymizer.operators import Operator, OperatorType

class MyOperator(Operator):
    """Custom anonymization operator."""
    
    def operate(self, text: str, params: dict = None) -> str:
        """Transform the detected PII."""
        # Ensure non-reversible transformation
        import uuid
        return f"<{params.get('entity_type', 'REDACTED')}_{uuid.uuid4().hex[:8]}>"
    
    def validate(self, params: dict = None) -> None:
        """Validate operator parameters before use."""
        if params and 'entity_type' not in params:
            raise ValueError("entity_type is required")
    
    def operator_name(self) -> str:
        return "my_operator"
    
    def operator_type(self) -> OperatorType:
        return OperatorType.Anonymize
```

**2. Security Checklist:**
- ✅ **Non-reversible**: Cannot recover original PII from anonymized output
- ✅ **Entropy**: Uses random/unpredictable values (not deterministic hashing)
- ✅ **No PII leakage**: Doesn't preserve PII characteristics (length, format)

```python
# ❌ BAD: Reversible via rainbow tables
def operate(self, text, params):
    return hashlib.md5(text.encode()).hexdigest()

# ✅ GOOD: Non-reversible with entropy  
def operate(self, text, params):
    return f"<{params['entity_type']}_{uuid.uuid4().hex[:8]}>"
```

**3. Test Anonymization Quality:**
```python
def test_operator_is_non_reversible():
    """Verify same input produces different output."""
    operator = MyOperator()
    result1 = operator.operate("John Doe", {"entity_type": "PERSON"})
    result2 = operator.operate("John Doe", {"entity_type": "PERSON"})
    assert result1 != result2  # Different each time

def test_operator_preserves_structure():
    """Verify anonymized text maintains sentence structure."""
    text = "Email: john@example.com, Phone: 555-1234"
    # After anonymization
    expected = "Email: <EMAIL_xxx>, Phone: <PHONE_yyy>"
    # Structure preserved, PII replaced
```

### API Development

**1. Maintain Backward Compatibility:**
```python
# ❌ BAD: Breaking change
def analyze(text: str, language: str, entities: List[str]):
    ...

# ✅ GOOD: Optional parameter with default
def analyze(
    text: str, 
    language: str, 
    entities: Optional[List[str]] = None
) -> List[RecognizerResult]:
    ...
```

**2. Required Updates for API Changes:**
```bash
# 1. Update OpenAPI schema
docs/api-docs/api-docs.yml

# 2. Add E2E tests  
e2e-tests/tests/test_new_endpoint.py

# 3. Add usage example
docs/samples/python/new_feature_example.ipynb

# 4. Update CHANGELOG.md
```

### Cross-Component Changes

**When modifying shared interfaces:**

1. **Identify all consumers:**
```python
# RecognizerResult is consumed by:
# - presidio-anonymizer (takes analyzer results)
# - presidio-cli (displays results)
# - presidio-structured (processes tabular data)
# - docs/samples/* (user examples)
```

2. **Update all components in same changeset:**
```python
# If adding field to RecognizerResult:
# 1. presidio-analyzer: Add field and populate
# 2. presidio-anonymizer: Handle new field (or ignore safely)
# 3. presidio-cli: Display new field (optional)
# 4. Tests: Update expectations
# 5. Docs: Document new field
# 6. e2e-tests: Add integration test for new field
```

3. **Respect component boundaries:**
```python
# ❌ BAD: Anonymizer importing analyzer internals
from presidio_analyzer.predefined_recognizers import UsSsnRecognizer

# ✅ GOOD: Use public interfaces only
from presidio_analyzer import RecognizerResult
```

### Performance Optimization

**1. Cache Compiled Regexes:**
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def _compile_pattern(pattern_str: str) -> re.Pattern:
    return re.compile(pattern_str, re.IGNORECASE)
```

**2. Avoid Catastrophic Backtracking:**
```python
# ❌ BAD: O(2^n) on "aaaa...ab"
pattern = r"(a+)+"

# ✅ GOOD: Atomic grouping
pattern = r"(?>a+)"
```

**3. Batch NLP Processing:**
```python
# ❌ BAD: Process one at a time
for text in texts:
    doc = nlp(text)
    ...

# ✅ GOOD: Use spaCy pipe for batching
for doc in nlp.pipe(texts, batch_size=50):
    ...
```

### Testing Requirements

**Test Naming Convention:**
```python
# ✅ GOOD: Descriptive, intention-revealing
def test_when_valid_ssn_then_detect_with_correct_boundaries()
def test_when_invalid_checksum_then_no_match()
def test_when_context_missing_then_low_confidence()

# ❌ BAD: Non-descriptive
def test_ssn_1()
def test_case2()
```

### Documentation Requirements

**1. Required Documentation Updates:**
```markdown
When adding a feature, update ALL of:

✅ CHANGELOG.md - Under "Unreleased" section
✅ docs/supported_entities.md - For new entity types  
✅ docs/api-docs/api-docs.yml - For API changes
✅ README.md - For major features
✅ Docstrings - All public classes/methods
✅ docs/samples/ - Usage examples for complex features
✅ Update docstrings based on the reST docstring format (:param:, :return:, :raises:, :example:)
```

**2. Pattern Source Documentation:**
```python
# In recognizer docstring or comments
"""
Pattern based on Royal Mail PAF specification:
https://www.royalmail.com/find-a-postcode

UK postcodes follow 6 formats:
- A9 9AA   (e.g., M1 1AA)
- A99 9AA  (e.g., M60 1NW)  
- AA9 9AA  (e.g., CR2 6XH)
- AA99 9AA (e.g., DN55 1PT)
- A9A 9AA  (e.g., W1A 1HQ)
- AA9A 9AA (e.g., EC1A 1BB)

Plus special case: GIR 0AA
"""
```

---

## Part 2: Code Review Guidelines

Use these guidelines when **reviewing pull requests** for Presidio.

### Review Philosophy

* Only comment when you have HIGH CONFIDENCE (>80%) that an issue exists
* Be concise: one sentence per comment when possible
* Focus on actionable feedback, not observations
* Data privacy is paramount - this is a PII detection/anonymization system
* All modules in Presidio which process records are stateless - avoid suggesting stateful solutions
* Presidio is a multi-component system - consider cross-component impacts of changes
* Don't reinvent the wheel - check for existing patterns, functions and best practices in the codebase before suggesting new approaches

### Review Priorities

Focus on issues in this order of importance:

### 🔴 CRITICAL (Always Flag)

#### 1. Security & Privacy Vulnerabilities

**PII-Specific Risks:**
- **PII leakage in logs, error messages, or debug output** - Never log detected PII values, only entity types and positions
- **Regex injection vulnerabilities** - User-provided patterns must be validated before compilation
- **Inadequate anonymization** - Reversible transformations, weak masking, deterministic fake data without proper context
- **Side-channel leaks** - Timing attacks revealing PII presence, cache-based information disclosure

**General Security:**
- Hardcoded secrets, API keys, credentials (especially for NLP model endpoints, cloud services)
- Command injection (especially in CLI component)
- Unsafe deserialization (pickle files, untrusted NLP models)
- Missing input validation on API endpoints (analyzer, anonymizer, image-redactor)
- Path traversal in file operations
- Insecure random number generation for fake data

#### 2. Correctness & Logic Errors

**PII Detection Accuracy:**
- **False positives** - Overly broad regex patterns matching non-PII or other entity types with med/high confidence
- **False negatives** - Missing valid cases for a given entity type, especially edge cases or common variations
- **Incorrect entity boundaries** - Off-by-one errors in start/end positions causing malformed anonymization
- **Confidence score miscalculation** - Scores outside [0.0, 1.0], incorrect aggregation of multiple detection methods

**General Logic:**
- Race conditions in multi-threaded analysis
- Resource leaks (NLP models not released, file handles, network connections)
- Null/None handling in entity detection chains
- Incorrect error handling that silently fails to detect PII
- Adding state where unnecessary (Presidio is designed to be stateless for scalability)

#### 3. Performance Issues

**PII Detection Specific:**
- **Inefficient regex patterns** - Catastrophic backtracking (e.g., `(a+)+b` on "aaaa...a")
- **Redundant passes** - Running the same logic multiple times on same text
- **Unbounded batch processing** - Loading entire datasets into memory
- **Missing regex compilation caching** - Recompiling patterns on every call
- **Unnecessary model loads** - Loading the same model multiple times instead of reusing instances

**General Performance:**
- O(n²) or worse algorithms when O(n) exists
- Blocking I/O on critical API paths
- Missing database indexes for entity result storage
- Inefficient image processing (loading full image when bounding box would suffice)

### 🟡 IMPORTANT (Flag if Significant)

#### 4. Cross-Component Alignment & Integration

**Respect the Natural Data Flow:**
- Presidio follows a unidirectional flow: Analyzer → Anonymizer → Output
- Downstream components (CLI, structured, image-redactor) consume analyzer/anonymizer, never the reverse
- Breaking this flow creates circular dependencies and tight coupling
- Changes should propagate forward through the data pipeline, not backward

**Module Reuse Guidelines:**
- Reuse code by importing from shared modules, not by copying code across components
- Shared data models (RecognizerResult, OperatorConfig) should be treated as contracts - changes require coordinated updates across all consumers
- When adding functionality, check if it belongs in an existing shared module rather than duplicating logic
- If multiple components need the same feature, extract it to a common location rather than implementing it multiple times
- Backward compatibility is critical when modifying shared modules - ensure existing consumers continue to work without changes

**Avoid Cross-Component Side Effects:**
- Changes to internal implementation should not affect other components' behavior
- Modifying shared configuration files requires understanding impact on all components that consume them
- Registry and provider patterns exist to decouple components - bypassing them creates hidden dependencies
- Component boundaries must be respected: anonymizer should never import from analyzer internals, only public interfaces
- Providing a solution specific to one component in a shared module instead of providing a general solution that can be used by multiple components creates tight coupling and maintenance challenges

**When Making Changes Across Components:**
- Identify all components that consume the interface you're modifying
- Update dependent components in the same changeset to maintain system consistency
- Ensure configuration files, API schemas, and documentation stay synchronized
- Test the complete integration path, not just individual components in isolation in unit tests, integration tests, and the e2e test suite
- Communicate changes clearly in the PR description, especially if they affect multiple components or require coordinated

#### 5. Architecture & Design

**Presidio Patterns:**
- **Recognizer design violations** - Not inheriting from `EntityRecognizer`, missing `load()` or `analyze()`
- **Operator design violations** - Not implementing `OperatorType` interface correctly
- **Registry pattern misuse** - Bypassing `RecognizerRegistry`, hardcoding recognizer lists
- **Provider pattern violations** - Not following `NlpEngineProvider` or `RecognizerRegistryProvider` patterns
- **Tight coupling** - Recognizers depending on specific NLP engine implementation details

**General Design:**
- Circular dependencies between modules
- Missing abstraction for third-party service integrations
- Breaking existing public APIs without deprecation warnings
- Inconsistent error handling strategies (mixing exceptions and error codes)

#### 6. Data Integrity & Validation

**Input Validation:**
- Missing validation of user-provided entity types
- Accepting arbitrary regex patterns without safety checks
- No length limits on input text (DoS via memory exhaustion)
- Missing validation of parameters
- Unchecked file uploads

**Output Validation:**
- Confidence scores outside valid range
- Overlapping entity spans not handled correctly
- Missing entity type in anonymization results

#### 7. Testing Requirements

**Presidio-Specific Testing:**
- **Missing tests for new recognizers** - Must include: true positives, true negatives, edge cases, false positive scenarios, entity within larger context
- **No validation of entity boundaries** - Tests only check entity type, not exact start/end positions
- **Missing multilingual tests** - Recognizers claiming multi-language support without language-specific tests
- **Anonymization reversibility not tested** - No verification that anonymized data can't be de-anonymized
- **Missing E2E analyzer→anonymizer tests** - Testing components in isolation without integration validation

**General Testing:**
- Missing tests for critical business logic (PII detection, anonymization)
- Flaky tests due to non-deterministic NLP/ML models (use fixed random seeds)
- Tests that don't validate behavior (checking implementation details instead)
- Missing regex pattern edge cases (empty strings, special characters, unicode)

#### 8. Documentation Requirements

**Code-Documentation Consistency:**
- Code changes must be reflected in documentation - outdated docs are misleading and dangerous
- Implementation must not contradict existing documentation - if conflict exists, either update docs or reconsider implementation
- API documentation is auto-generated from docstrings - formatting errors break the build

**Docstring Quality:**
- All public classes, methods, and functions must have docstrings
- Docstrings must follow consistent format (Args, Returns, Raises, Examples)
- No formatting issues that break API doc generation (malformed RST/Markdown, incorrect indentation)
- Include type information in docstrings when not obvious from type hints

**Documentation for New Features:**
- New recognizers must document pattern sources - link to official standards, government specifications, or authoritative references
- Complex additions require usage examples in `docs/samples/` - show common use cases, not just API reference
- New entity types must be added to `docs/supported_entities.md` with description and example
- API changes require updates to `docs/api-docs/api-docs.yml` (OpenAPI schema)

**Pattern Recognizer Documentation:**
- Explain the logic source: "Based on ISO standard X", "Follows format defined by Y government agency"
- Document regex pattern rationale - why specific character classes, lookaheads, or groups are needed
- Include references to validation algorithms (e.g., "Luhn checksum validation per ISO/IEC 7812")
- Note any limitations or known edge cases in the pattern

### 💡 OPTIONAL (Low Priority)

#### 9. Code Quality (only if impacts maintainability)

- Overly complex recognizer logic (>50 lines in `analyze()` method, >3 nesting levels)
- Misleading variable names (e.g., `pattern` for compiled regex, should be `compiled_pattern`)
- Missing docstrings on public recognizer/operator classes
- Incomplete type hints on public APIs (especially `analyze()`, `anonymize()` signatures)

### What NOT to Flag

**DO NOT comment on these (handled by automated tools):**

- ❌ Code formatting, line length, indentation (handled by `ruff format`)
- ❌ Import ordering (handled by `ruff check --select I`)
- ❌ Trailing commas, whitespace (handled by `ruff`)
- ❌ Type hint style preferences (`List[str]` vs `list[str]` - both valid for Python 3.9-3.12 support)

**DO NOT comment on style preferences that don't affect correctness:**

- Personal preferences for syntax variations
- Subjective naming when current name is clear in PII context
- Minor refactoring suggestions that don't fix bugs or improve accuracy
- Unnecessary abstractions "for future flexibility" in recognizers

### Review Examples

**Be specific and actionable:**
```
✅ GOOD: "🔴 CRITICAL: Line 45 logs detected PII value. Change logger.info(f'Found: {entity.text}') 
to logger.info(f'Found entity type: {entity.entity_type}')"

❌ BAD: "Don't log PII"
```

**Provide context:**
```
✅ GOOD: "🟡 Important: This regex has catastrophic backtracking on input 'aaaaaa...b' (O(2^n) time). 
Use atomic grouping: (?>a+)b or possessive quantifier a++b"

❌ BAD: "This regex is slow"
```

**Differentiate severity:**
- **🔴 CRITICAL** - Security, data leakage, correctness bugs affecting PII detection accuracy
- **🟡 Important** - Performance issues, cross-component breaks, missing tests for new recognizers  
- **💡 Suggestion** - Code quality improvements, better error messages, optimization opportunities

**Acknowledge good practices:**
- Well-tested recognizers with comprehensive edge case coverage
- Proper use of context validation (NLP + regex)
- Good error handling with informative messages
- Performance optimizations (regex caching, batch processing)

---

## Part 3: Repository-Specific Context

### Technology Stack
- **Python** - Must support all versions
- **uv** - Dependency management and installation (not pip or Poetry). Each package commits a `uv.lock`; `poetry-core` is retained only as the build backend for now.
- **Ruff** - Linting and formatting (replaces flake8, black, isort)
- **spaCy** - Default NLP engine (en_core_web_lg for production), although one can use other NLP engines via provider pattern
- **Docker** - Deployment via GitHub Container Registry (`ghcr.io/data-privacy-stack`)


### Critical Files for Cross-Component Changes
- `RecognizerResult` - Shared analyzer output format
- `OperatorConfig` - Anonymizer operator configuration
- `conf/default_recognizers.yaml` - System-wide recognizer registry
- `docs/supported_entities.md` - Public entity type documentation
- API schemas in `docs/api-docs/`

## Quick Reference Commands

### Local Development
```bash
# Setup (uv reads the committed uv.lock; --locked fails if it is stale)
cd presidio-analyzer  # or presidio-anonymizer, presidio-cli, etc.
uv sync --locked --all-extras --group dev
uv run python -m spacy download en_core_web_lg  # For analyzer/CLI only

# Run tests
uv run pytest -xvv  # Stop on first failure with verbose output
uv run pytest tests/test_us_ssn_recognizer.py -k "test_valid"  # Specific test

# Lint
uv run ruff check .
uv run ruff format .
```

> **Dependency changes:** whenever you edit a package's `pyproject.toml`
> dependencies (add/remove/bump `[project]` deps, extras, or
> `[dependency-groups]`), you MUST regenerate and commit that package's
> `uv.lock` in the same change (`cd <package> && uv lock`). CI installs with
> `uv sync --locked` and fails if `pyproject.toml` and `uv.lock` are out of
> sync, so an updated `pyproject.toml` without its matching `uv.lock` will
> break the build.

### Docker Testing
```bash
# Quick test with pre-built images
docker pull ghcr.io/data-privacy-stack/presidio-analyzer:latest
docker run -d -p 5002:3000 --name analyzer ghcr.io/data-privacy-stack/presidio-analyzer:latest
curl http://localhost:5002/health

# Full build from source (takes 15+ minutes)
docker compose up --build -d
```

### E2E Testing
```bash
docker-compose up -d  # Start all services
cd e2e-tests
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pytest -v  # Run all E2E tests
```

## Common Issues to Watch For

### Build/Test Issues
- **Stale `uv.lock`** - If `uv sync --locked` fails with "lockfile needs to be updated", run `uv lock` in that package and commit the result.
- **Missing spaCy models** - Download en_core_web_lg before running tests
- **AHDS test skips** - Expected when AHDS_ENDPOINT not set
- **Transformers test failures** - Expected without HuggingFace access in restricted environments

### Code Issues
- **Logging PII values** - Never log `entity.text`, only `entity.entity_type`
- **Hardcoded language assumptions** - Use `context.language` parameter
- **Missing None checks** - NLP engines return None for empty/invalid text
- **Unbounded regex backtracking** - Test patterns with long strings
- **Confidence score > 1.0** - Validate score normalization logic

## Documentation Requirements Checklist

**See section 8 in Review Priorities above for comprehensive documentation guidelines.**

When adding features, update:
- **CHANGELOG.md** - Under "Unreleased" section
- **docs/supported_entities.md** - For new entity types
- **docs/api-docs/api-docs.yml** - For API changes
- **README.md** - For major features
- **Docstrings** - All public classes and methods (ensure proper formatting for API doc generation)
- **docs/samples/** - Add usage examples for complex new features

## Reference Documentation

**Consult these for detailed guidance:**
- **CONTRIBUTING.md** - PR process, CLA, code of conduct
- **docs/development.md** - Build process, testing, CI/CD
- **docs/analyzer/developing_recognizers.md** - Recognizer best practices
- **docs/analyzer/adding_recognizers.md** - Step-by-step recognizer guide
- **docs/anonymizer/adding_operators.md** - Operator development guide

---

**Summary for Code Review**: Prioritize security (PII leakage), correctness (detection accuracy), and performance (regex efficiency). Ensure comprehensive testing for all recognizers. Let automated tools handle formatting. Focus on actionable, specific feedback with concrete fixes.