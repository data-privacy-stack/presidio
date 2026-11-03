"""Tests for Turkish National ID (TCKN) recognizer."""

import pytest
from presidio_analyzer import AnalyzerEngine, EntityRecognizer, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import TrNationalIdRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    """Create a Turkish TCKN recognizer instance for testing."""
    return TrNationalIdRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the Turkish TCKN entity type for testing."""
    return ["TR_NATIONAL_ID"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # Valid TCKNs with correct checksum
        ("10000000146", 1, ((0, 11),), ((0.5, 1.0),),),
        ("76543210794", 1, ((0, 11),), ((0.5, 1.0),),),
        ("36493665440", 1, ((0, 11),), ((0.5, 1.0),),),
        ("53857632436", 1, ((0, 11),), ((0.5, 1.0),),),
        ("94357219628", 1, ((0, 11),), ((0.5, 1.0),),),
        ("79059236630", 1, ((0, 11),), ((0.5, 1.0),),),
        ("64625294480", 1, ((0, 11),), ((0.5, 1.0),),),
        # Valid TCKNs in sentences
        (
            "TC Kimlik No: 10000000146",
            1,
            ((14, 25),),
            ((0.5, 1.0),),
        ),
        (
            "Başvuru sahibinin TCKN numarası 10000000146 olarak tescil edilmiştir.",
            1,
            ((32, 43),),
            ((0.5, 1.0),),
        ),
        # Multiple valid TCKNs
        (
            "Birinci kişi: 10000000146, ikinci kişi: 76543210794",
            2,
            ((14, 25), (40, 51),),
            ((0.5, 1.0), (0.5, 1.0),),
        ),
        # Invalid TCKNs - first digit is 0
        ("00000000000", 0, (), (),),
        ("02531814694", 0, (), (),),  # first digit 0, rest mathematically plausible
        # Invalid TCKNs - wrong 10th digit checksum
        ("12345678900", 0, (), (),),
        ("76543210780", 0, (), (),),
        ("83219500748", 0, (), (),),  # 10th digit wrong, single-digit mismatch
        ("11798724308", 0, (), (),),  # random entry, both 10th and 11th wrong
        # Invalid TCKNs - correct 10th digit but wrong 11th digit
        ("10000000145", 0, (), (),),
        ("62286775983", 0, (), (),),  # 10th correct, 11th wrong
        ("97485249605", 0, (), (),),  # OCR/typo scenario, single digit off
        # Invalid TCKNs - wrong length
        ("1234567890", 0, (), (),),
        ("123456789012", 0, (), (),),
        # Invalid TCKNs - non-digits
        ("abcdefghijk", 0, (), (),),
        # Context enhancement
        (
            "Turkish ID 10000000146",
            1,
            ((11, 22),),
            ((0.5, 1.0),),
        ),
        (
            "Türk kimlik numarası 36493665440",
            1,
            ((21, 32),),
            ((0.5, 1.0),),
        ),
    ],
)
def test_when_tckn_in_text_then_all_tckns_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    """Test that Turkish TCKN recognizer correctly identifies TCKNs."""
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len

    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        if fn_score == "max":
            fn_score = max_score
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )


def test_validate_result_with_valid_tckn(recognizer):
    """Test validate_result method with valid TCKNs."""
    assert recognizer.validate_result("10000000146") is True
    assert recognizer.validate_result("76543210794") is True
    assert recognizer.validate_result("36493665440") is True
    assert recognizer.validate_result("53857632436") is True
    assert recognizer.validate_result("94357219628") is True
    assert recognizer.validate_result("79059236630") is True
    assert recognizer.validate_result("64625294480") is True


def test_validate_result_with_invalid_first_digit(recognizer):
    """Test validate_result method with TCKNs starting with 0."""
    assert recognizer.validate_result("00000000000") is False
    assert recognizer.validate_result("02531814694") is False


def test_validate_result_with_wrong_checksum(recognizer):
    """Test validate_result method with wrong checksum."""
    # 10th digit wrong
    assert recognizer.validate_result("12345678900") is False
    assert recognizer.validate_result("76543210780") is False
    assert recognizer.validate_result("83219500748") is False
    assert recognizer.validate_result("11798724308") is False
    # 10th digit correct but 11th digit wrong
    assert recognizer.validate_result("10000000145") is False
    assert recognizer.validate_result("62286775983") is False
    assert recognizer.validate_result("97485249605") is False


def test_validate_result_with_wrong_length(recognizer):
    """Test validate_result method with wrong length."""
    assert recognizer.validate_result("1234567890") is False
    assert recognizer.validate_result("123456789012") is False


def test_validate_result_with_non_digits(recognizer):
    """Test validate_result method with non-digit characters."""
    assert recognizer.validate_result("abcdefghijk") is False


def test_context_words(recognizer):
    """Test that context words are properly set."""
    expected_context = [
        "tc kimlik",
        "kimlik no",
        "kimlik numarası",
        "tckn",
        "tc no",
        "nüfus cüzdanı",
        "national id",
        "turkish id",
        "türk kimlik",
    ]
    assert recognizer.context == expected_context


def test_supported_entity(recognizer):
    """Test that supported entity is correctly set."""
    assert recognizer.supported_entities == ["TR_NATIONAL_ID"]


def test_supported_language(recognizer):
    """Test that supported language is correctly set."""
    assert recognizer.supported_language == "tr"


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_scores",
    [
        # Space-separated formats (3-3-3-2, 3-2-2-2-2, 4-4-3)
        ("100 000 001 46", 1, ((0, 14),), (EntityRecognizer.MAX_SCORE,)),
        ("765 432 107 94", 1, ((0, 14),), (EntityRecognizer.MAX_SCORE,)),
        ("100 00 00 01 46", 1, ((0, 15),), (EntityRecognizer.MAX_SCORE,)),
        ("1000 0000 146", 1, ((0, 13),), (EntityRecognizer.MAX_SCORE,)),
        # Hyphen-separated formats
        ("100-000-001-46", 1, ((0, 14),), (EntityRecognizer.MAX_SCORE,)),
        ("765-432-107-94", 1, ((0, 14),), (EntityRecognizer.MAX_SCORE,)),
        ("100-00-00-01-46", 1, ((0, 15),), (EntityRecognizer.MAX_SCORE,)),
        ("1000-0000-146", 1, ((0, 13),), (EntityRecognizer.MAX_SCORE,)),
        # ASR comma-separated formats (pause commas between spoken digit groups)
        ("100, 000, 001, 46", 1, ((0, 17),), (EntityRecognizer.MAX_SCORE,)),
        ("765, 432, 107, 94", 1, ((0, 17),), (EntityRecognizer.MAX_SCORE,)),
        ("100,000,001,46", 1, ((0, 14),), (EntityRecognizer.MAX_SCORE,)),
        ("100 000, 001, 46", 1, ((0, 16),), (EntityRecognizer.MAX_SCORE,)),
        ("100, 00, 00, 01, 46", 1, ((0, 19),), (EntityRecognizer.MAX_SCORE,)),
        ("1000, 0000, 146", 1, ((0, 15),), (EntityRecognizer.MAX_SCORE,)),
        # Embedded in Turkish sentences with exact boundaries
        (
            "Müşteri TCKN kaydı: 100, 000, 001, 46 olarak alındı.",
            1,
            ((20, 37),),
            (EntityRecognizer.MAX_SCORE,),
        ),
        (
            "Kimlik no 100-000-001-46 doğrulandı.",
            1,
            ((10, 24),),
            (EntityRecognizer.MAX_SCORE,),
        ),
        # Lookalike negatives: mismatched delimiters
        ("100-000 001-46", 0, (), ()),
        ("100-000, 001-46", 0, (), ()),
        ("100,000 001 46", 0, (), ()),
        # Lookalike negatives: English thousands separator for 10 billion (2-3-3-3)
        ("10,000,000,146", 0, (), ()),
        # Lookalike negatives: 10-digit number followed by ", 6"
        ("1000000014, 6", 0, (), ()),
        # Lookalike negatives: longer delimited sequence containing a valid TCKN
        ("99-100-000-001-46", 0, (), ()),
        ("100-000-001-46-99", 0, (), ()),
        ("99 100 000 001 46", 0, (), ()),
        ("100 000 001 46 99", 0, (), ()),
        ("99, 100, 000, 001, 46", 0, (), ()),
        ("100, 000, 001, 46, 99", 0, (), ()),
        ("99,100,000,001,46", 0, (), ()),
        ("100,000,001,46,99", 0, (), ()),
        # Dummy repeated-digit sequences that mathematically satisfy NVI modulo
        ("11111111110", 0, (), ()),
        ("22222222220", 0, (), ()),
        ("33333333330", 0, (), ()),
        ("99999999990", 0, (), ()),
        ("111-111-111-10", 0, (), ()),
        ("111, 111, 111, 10", 0, (), ()),
    ],
)
def test_delimited_and_invalidated_tckn_exact_scores(
    text,
    expected_len,
    expected_positions,
    expected_scores,
    recognizer,
    entities,
):
    """Test delimited TCKNs, ASR comma-separated TCKNs, and lookalike negatives."""
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len

    for res, (st_pos, fn_pos), expected_score in zip(
        results, expected_positions, expected_scores
    ):
        assert res.entity_type == "TR_NATIONAL_ID"
        assert res.start == st_pos
        assert res.end == fn_pos
        assert res.score == pytest.approx(expected_score)


def test_invalidate_result_rejects_dummy_and_mismatched_delimiters(recognizer):
    """Test that invalidate_result rejects dummy repeated digits and mixed delimiters."""
    assert recognizer.invalidate_result("11111111110") is True
    assert recognizer.invalidate_result("22222222220") is True
    assert recognizer.invalidate_result("99999999990") is True
    assert recognizer.invalidate_result("100-000 001-46") is True
    assert recognizer.invalidate_result("100-000, 001-46") is True
    assert recognizer.invalidate_result("100,000 001 46") is True

    assert recognizer.invalidate_result("10000000146") is False
    assert recognizer.invalidate_result("100-000-001-46") is False
    assert recognizer.invalidate_result("100, 000, 001, 46") is False

    assert recognizer.validate_result("11111111110") is False
    assert recognizer.validate_result("100-000 001-46") is False
    assert recognizer.validate_result("100-000-001-46") is True
    assert recognizer.validate_result("100, 000, 001, 46") is True


def test_custom_replacement_pairs():
    """Test that custom replacement_pairs are respected during validation."""
    strict_recognizer = TrNationalIdRecognizer(replacement_pairs=[])
    assert strict_recognizer.validate_result("10000000146") is True
    assert strict_recognizer.validate_result("100-000-001-46") is False
    assert strict_recognizer.analyze("100-000-001-46", ["TR_NATIONAL_ID"]) == []
    assert len(strict_recognizer.analyze("10000000146", ["TR_NATIONAL_ID"])) == 1


def test_recognizer_loads_and_detects_when_enabled_in_yaml(tmp_path):
    """Detection must work through the path users actually configure."""
    conf = tmp_path / "recognizers.yaml"
    conf.write_text(
        """
supported_languages:
  - tr
recognizers:
  - name: TrNationalIdRecognizer
    supported_languages:
      - tr
    type: predefined
    enabled: true
    country_code: tr
""",
        encoding="utf-8",
    )
    nlp_engine = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "no_op",
            "models": [{"lang_code": "tr", "model_name": "no_op"}],
        }
    ).create_engine()
    registry = RecognizerRegistryProvider(
        conf_file=conf, nlp_engine=nlp_engine
    ).create_recognizer_registry()
    analyzer = AnalyzerEngine(
        registry=registry, nlp_engine=nlp_engine, supported_languages=["tr"]
    )

    direct = TrNationalIdRecognizer()
    manual_registry = RecognizerRegistry(supported_languages=["tr"])
    manual_registry.add_recognizer(TrNationalIdRecognizer())
    assert len(registry.recognizers) == 1
    loaded_recognizer = registry.recognizers[0]
    assert loaded_recognizer.name == direct.name
    assert loaded_recognizer.supported_entities == direct.supported_entities
    assert loaded_recognizer.supported_language == direct.supported_language
    assert loaded_recognizer.context == direct.context
    assert loaded_recognizer.COUNTRY_CODE == "tr"

    results = analyzer.analyze(
        "TC Kimlik No: 100, 000, 001, 46", language="tr"
    )

    assert [result.entity_type for result in results] == ["TR_NATIONAL_ID"]
    assert results[0].start == 14
    assert results[0].end == 31
    assert results[0].score == pytest.approx(EntityRecognizer.MAX_SCORE)

