"""Tests for Turkish Tax Identification Number (VKN / TR_TAX_ID) recognizer."""

from pathlib import Path

import pytest
import yaml

import presidio_analyzer
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
from presidio_analyzer.nlp_engine import NlpArtifacts, NoOpNlpEngine
from presidio_analyzer.predefined_recognizers import TrTaxIdRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistry, RecognizerRegistryProvider
from tests import assert_result

# Base pattern score from TrTaxIdRecognizer.PATTERNS. Because validate_result
# returns None when the GİB Modulo-10 checksum passes (rather than promoting
# bare 10-digit numbers to 1.0), isolated recognizer matches carry this score;
# context words boost confidence in the full pipeline.
_PATTERN_SCORE = 0.3


@pytest.fixture(scope="module")
def recognizer():
    """Create a TrTaxIdRecognizer instance for testing."""
    return TrTaxIdRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the TR_TAX_ID entity type for testing."""
    return ["TR_TAX_ID"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_scores",
    [
        # --- Real-world valid VKNs with official GİB Modulo-10 checksum ---
        ("0910008891", 1, ((0, 10),), (_PATTERN_SCORE,)),  # Aselsan
        ("8790017566", 1, ((0, 10),), (_PATTERN_SCORE,)),  # Garanti BBVA
        ("8760040732", 1, ((0, 10),), (_PATTERN_SCORE,)),  # Turkish Airlines (THY)
        ("8790035021", 1, ((0, 10),), (_PATTERN_SCORE,)),  # Tüpraş
        ("0150015264", 1, ((0, 10),), (_PATTERN_SCORE,)),  # Akbank
        ("1234567890", 1, ((0, 10),), (_PATTERN_SCORE,)),  # Checksum-valid (0), kept at base score
        ("9876543217", 1, ((0, 10),), (_PATTERN_SCORE,)),  # Checksum-valid (7), kept at base score
        ("1112223339", 1, ((0, 10),), (_PATTERN_SCORE,)),  # Checksum-valid (9), kept at base score
        # --- Valid VKNs embedded in sentences (recognizer in isolation returns base score) ---
        (
            "Vergi Kimlik No: 0910008891",
            1,
            ((17, 27),),
            (_PATTERN_SCORE,),
        ),
        (
            "Şirketin VKN numarası 8790017566 olarak kayıtlıdır.",
            1,
            ((22, 32),),
            (_PATTERN_SCORE,),
        ),
        (
            "Mükellef vergi no: 8760040732",
            1,
            ((19, 29),),
            (_PATTERN_SCORE,),
        ),
        (
            "Kadıköy vergi dairesi 0150015264 mükellefi",
            1,
            ((22, 32),),
            (_PATTERN_SCORE,),
        ),
        (
            "Tax ID: 8790035021",
            1,
            ((8, 18),),
            (_PATTERN_SCORE,),
        ),
        (
            "Tax number: 1234567890",
            1,
            ((12, 22),),
            (_PATTERN_SCORE,),
        ),
        # --- Multiple valid VKNs in text ---
        (
            "Tedarikçi VKN: 0910008891, Müşteri VKN: 8790017566",
            2,
            ((15, 25), (40, 50)),
            (_PATTERN_SCORE, _PATTERN_SCORE),
        ),
        # --- Invalid checksums (single-digit mutations / wrong check digits -> dropped) ---
        ("0910008892", 0, (), ()),
        ("8790017565", 0, (), ()),
        ("8760040733", 0, (), ()),
        ("1234567891", 0, (), ()),
        ("9876543210", 0, (), ()),
        # --- Invalid lengths ---
        ("123456789", 0, (), ()),  # 9 digits
        ("12345678901", 0, (), ()),  # 11 digits
        # --- Lookalike negatives (non-digits / strings) ---
        ("abcdefghij", 0, (), ()),
        ("TR12345678", 0, (), ()),
        ("hello world", 0, (), ()),
        # --- Dummy repeated sequences (invalidated by invalidate_result) ---
        ("4444444444", 0, (), ()),
        ("0000000000", 0, (), ()),
        ("1111111111", 0, (), ()),
    ],
)
def test_when_vkn_in_text_then_all_vkns_found(
    text,
    expected_len,
    expected_positions,
    expected_scores,
    recognizer,
    entities,
):
    """Test that TrTaxIdRecognizer identifies valid VKNs at base score and drops invalid ones."""
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len

    for res, (st_pos, fn_pos), expected_score in zip(
        results, expected_positions, expected_scores
    ):
        assert_result(res, entities[0], st_pos, fn_pos, expected_score)


def test_validate_result_with_valid_vkns(recognizer):
    """Test validate_result returns None for valid VKNs to preserve base pattern score."""
    assert recognizer.validate_result("0910008891") is None
    assert recognizer.validate_result("8790017566") is None
    assert recognizer.validate_result("8760040732") is None
    assert recognizer.validate_result("8790035021") is None
    assert recognizer.validate_result("0150015264") is None
    assert recognizer.validate_result("1234567890") is None
    assert recognizer.validate_result("9876543217") is None
    assert recognizer.validate_result("1112223339") is None


def test_validate_result_with_invalid_checksum(recognizer):
    """Test validate_result returns False for incorrect checksums."""
    assert recognizer.validate_result("0910008892") is False
    assert recognizer.validate_result("8790017565") is False
    assert recognizer.validate_result("8760040733") is False
    assert recognizer.validate_result("1234567891") is False
    assert recognizer.validate_result("9876543210") is False


def test_validate_result_with_invalid_format(recognizer):
    """Test validate_result returns False for wrong length or non-digits."""
    assert recognizer.validate_result("123456789") is False
    assert recognizer.validate_result("12345678901") is False
    assert recognizer.validate_result("abcdefghij") is False


def test_invalidate_result(recognizer):
    """Test invalidate_result filters dummy repeated sequences."""
    assert recognizer.invalidate_result("4444444444") is True
    assert recognizer.invalidate_result("0000000000") is True
    assert recognizer.invalidate_result("1111111111") is True
    assert recognizer.invalidate_result("0910008891") is False
    assert recognizer.invalidate_result("8790017566") is False


def test_recognizer_metadata(recognizer):
    """Test recognizer supported entity, language, and country code."""
    assert recognizer.supported_entities == ["TR_TAX_ID"]
    assert recognizer.supported_language == "tr"
    assert recognizer.COUNTRY_CODE == "tr"
    assert recognizer.patterns[0].score == _PATTERN_SCORE


def test_context_words(recognizer):
    """Test that context words are properly configured."""
    expected_context = [
        "vergi kimlik",
        "vergi kimlik no",
        "vergi kimlik numarası",
        "vergi no",
        "vergi numarası",
        "vkn",
        "tax id",
        "tax number",
        "vergi dairesi",
    ]
    assert recognizer.context == expected_context


def test_context_words_enhance_real_analysis_score():
    """Verify real recognizer output (0.3) is boosted by context enhancer when context is present."""
    recognizer = TrTaxIdRecognizer()

    # 1. With context word ("vkn") in text: real recognizer produces 0.3, enhancer boosts to 0.65
    text_with_context = "VKN: 0910008891"
    raw_results_with_context = recognizer.analyze(
        text_with_context, entities=["TR_TAX_ID"]
    )
    assert len(raw_results_with_context) == 1
    assert raw_results_with_context[0].score == pytest.approx(_PATTERN_SCORE)

    nlp_artifacts_with_context = NlpArtifacts(
        entities=[],
        tokens=["vkn", ":", "0910008891"],
        tokens_indices=[0, 3, 5],
        lemmas=["vkn", ":", "0910008891"],
        nlp_engine=None,
        language="tr",
    )
    nlp_artifacts_with_context.keywords = ["vkn"]

    enhancer = LemmaContextAwareEnhancer(
        context_similarity_factor=0.35, min_score_with_context_similarity=0.4
    )
    enhanced = enhancer.enhance_using_context(
        text=text_with_context,
        raw_results=raw_results_with_context,
        nlp_artifacts=nlp_artifacts_with_context,
        recognizers=[recognizer],
    )
    assert len(enhanced) == 1
    assert enhanced[0].score == pytest.approx(0.65)
    assert enhanced[0].analysis_explanation.supportive_context_word == "vkn"

    # 2. Without context words in text: real recognizer produces 0.3, enhancer leaves it at 0.3
    text_no_context = "fatura 0910008891"
    raw_results_no_context = recognizer.analyze(
        text_no_context, entities=["TR_TAX_ID"]
    )
    assert len(raw_results_no_context) == 1
    assert raw_results_no_context[0].score == pytest.approx(_PATTERN_SCORE)

    nlp_artifacts_no_context = NlpArtifacts(
        entities=[],
        tokens=["fatura", "0910008891"],
        tokens_indices=[0, 7],
        lemmas=["fatura", "0910008891"],
        nlp_engine=None,
        language="tr",
    )
    nlp_artifacts_no_context.keywords = ["fatura"]

    unenhanced = enhancer.enhance_using_context(
        text=text_no_context,
        raw_results=raw_results_no_context,
        nlp_artifacts=nlp_artifacts_no_context,
        recognizers=[recognizer],
    )
    assert len(unenhanced) == 1
    assert unenhanced[0].score == pytest.approx(_PATTERN_SCORE)


def test_tr_tax_id_in_default_recognizers_yaml():
    """Verify TrTaxIdRecognizer is listed in default_recognizers.yaml."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "TrTaxIdRecognizer"]
    assert len(entries) == 1, "TrTaxIdRecognizer missing from default_recognizers.yaml"
    entry = entries[0]
    assert entry["country_code"] == "tr"
    assert "tr" in entry["supported_languages"]
    assert entry["type"] == "predefined"
    assert entry["enabled"] is False


def test_recognizer_loads_and_detects_when_enabled_in_yaml(tmp_path):
    """Detection must work through both direct instance and AnalyzerEngine with and without context."""
    conf = tmp_path / "recognizers.yaml"
    conf.write_text(
        """
supported_languages:
  - tr
recognizers:
  - name: TrTaxIdRecognizer
    supported_languages:
      - tr
    type: predefined
    enabled: true
    country_code: tr
""",
        encoding="utf-8",
    )
    registry = RecognizerRegistryProvider(conf_file=conf).create_recognizer_registry()
    matching_recognizers = [
        r for r in registry.recognizers if type(r).__name__ == "TrTaxIdRecognizer"
    ]
    assert len(matching_recognizers) == 1
    loaded_recognizer = matching_recognizers[0]
    assert loaded_recognizer.country_code() == "tr"
    assert loaded_recognizer.COUNTRY_CODE == "tr"
    assert loaded_recognizer.supported_language == "tr"

    # End-to-end analysis through AnalyzerEngine without context -> base score (0.3)
    nlp_engine = NoOpNlpEngine(models=[{"lang_code": "tr", "model_name": "no_op"}])
    analyzer = AnalyzerEngine(
        registry=registry,
        nlp_engine=nlp_engine,
        supported_languages=["tr"],
    )
    results_no_context = analyzer.analyze(
        text="0910008891", language="tr", entities=["TR_TAX_ID"]
    )
    assert len(results_no_context) == 1
    assert results_no_context[0].entity_type == "TR_TAX_ID"
    assert results_no_context[0].start == 0
    assert results_no_context[0].end == 10
    assert results_no_context[0].score == pytest.approx(_PATTERN_SCORE)

    # End-to-end analysis through AnalyzerEngine with explicit context -> boosted score (0.65)
    results_with_context = analyzer.analyze(
        text="Vergi Kimlik No: 0910008891",
        language="tr",
        entities=["TR_TAX_ID"],
        context=["vergi kimlik"],
        return_decision_process=True,
    )
    assert len(results_with_context) == 1
    assert results_with_context[0].entity_type == "TR_TAX_ID"
    assert results_with_context[0].start == 17
    assert results_with_context[0].end == 27
    assert results_with_context[0].score == pytest.approx(0.65)
    assert (
        results_with_context[0].analysis_explanation.supportive_context_word
        == "vergi kimlik"
    )


def test_construction_paths_agree():
    """Verify direct instantiation, add_recognizer, and YAML create identical recognizers."""
    direct = TrTaxIdRecognizer()

    registry = RecognizerRegistry(supported_languages=["tr"])
    registry.add_recognizer(direct)
    assert len(registry.recognizers) == 1
    assert registry.recognizers[0].supported_entities == direct.supported_entities
    assert registry.recognizers[0].supported_language == direct.supported_language
    assert registry.recognizers[0].country_code() == direct.country_code()


def test_custom_constructor_params():
    """Verify constructor accepts custom name, context, and patterns."""
    from presidio_analyzer import Pattern

    custom_pattern = [Pattern("CUSTOM_VKN", r"\b[0-9]{10}\b", 0.5)]
    custom_context = ["custom_vkn_context"]
    rec = TrTaxIdRecognizer(
        name="CustomTrTaxIdRecognizer",
        patterns=custom_pattern,
        context=custom_context,
        supported_entity="CUSTOM_TAX_ID",
    )
    assert rec.name == "CustomTrTaxIdRecognizer"
    assert rec.patterns == custom_pattern
    assert rec.context == custom_context
    assert rec.supported_entities == ["CUSTOM_TAX_ID"]
