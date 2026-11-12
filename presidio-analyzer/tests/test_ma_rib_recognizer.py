import pytest
from presidio_analyzer.predefined_recognizers import MaRibRecognizer

from tests.morocco_analyzer import analyzer_for

ONE_RUN_SCORE = 0.3
GROUPED_SCORE = 0.2
CONTEXT_BOOST = 0.35


def _rib(first_22_digits: str) -> str:
    """Append the key that makes the 24 digits divisible by 97."""
    key = 97 - (int(first_22_digits) * 100) % 97
    return f"{first_22_digits}{key:02d}"


def _grouped(rib: str, separator: str, *sizes: int) -> str:
    """Write the digits in groups of the given sizes."""
    groups, position = [], 0
    for size in sizes:
        groups.append(rib[position : position + size])
        position += size
    return separator.join(groups)


# Published by Bank Al-Maghrib for the special fund no. 126 (2023 earthquake).
FUND_126_RIB = "001810007800020110620318"
FUND_126_RIB_AS_PRINTED = "001 810 00 780 002 011 062 03 18"

GENERATED_RIB = _rib("0077800001234567890123")
WITH_DOTS = _grouped(GENERATED_RIB, ".", 3, 3, 16, 2)
WITH_HYPHENS = _grouped(GENERATED_RIB, "-", 3, 3, 16, 2)
ACCOUNT_AND_KEY_TOGETHER = _grouped(GENERATED_RIB, " ", 3, 3, 18)
DOTS_THEN_SPACE_BEFORE_KEY = f"{_grouped(GENERATED_RIB[:22], '.', 3, 3, 16)} 96"
THREE_OTHER_NUMBERS = _grouped(GENERATED_RIB, " ", 9, 10, 5)
IN_ARABIC_DIGITS = GENERATED_RIB.translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))

WRONG_KEY = FUND_126_RIB[:22] + "19"
ZERO_ACCOUNT_WITH_VALID_KEY = "0" * 22 + "97"


@pytest.fixture(scope="module")
def recognizer():
    return MaRibRecognizer()


@pytest.mark.parametrize(
    "text, value, score",
    [
        (FUND_126_RIB, FUND_126_RIB, ONE_RUN_SCORE),
        (f"le {FUND_126_RIB}.", FUND_126_RIB, ONE_RUN_SCORE),
        (f"ligne 12 {GENERATED_RIB} 2026", GENERATED_RIB, ONE_RUN_SCORE),
        (
            f"ref {FUND_126_RIB_AS_PRINTED} merci",
            FUND_126_RIB_AS_PRINTED,
            GROUPED_SCORE,
        ),
        (f"sur le {WITH_DOTS} merci", WITH_DOTS, GROUPED_SCORE),
        (WITH_HYPHENS, WITH_HYPHENS, GROUPED_SCORE),
        (ACCOUNT_AND_KEY_TOGETHER, ACCOUNT_AND_KEY_TOGETHER, GROUPED_SCORE),
    ],
)
def test_when_rib_key_is_valid_then_found_with_pattern_score(
    text, value, score, recognizer
):
    results = recognizer.analyze(text, ["MA_RIB"])

    start = text.index(value)
    assert len(results) == 1
    assert results[0].entity_type == "MA_RIB"
    assert (results[0].start, results[0].end) == (start, start + len(value))
    assert results[0].score == pytest.approx(score)


@pytest.mark.parametrize(
    "text",
    [
        f"numéro de suivi du colis {WRONG_KEY}",
        FUND_126_RIB[:23],
        FUND_126_RIB + "7",
        f"SKU{FUND_126_RIB}X",
        f"{FUND_126_RIB_AS_PRINTED} 44",
        f"44 {FUND_126_RIB_AS_PRINTED}",
        f"{FUND_126_RIB_AS_PRINTED} ٤٤",
        f"٤٤ {FUND_126_RIB_AS_PRINTED}",
        THREE_OTHER_NUMBERS,
        DOTS_THEN_SPACE_BEFORE_KEY,
        ZERO_ACCOUNT_WITH_VALID_KEY,
        IN_ARABIC_DIGITS,
        "1" * 10_000,
        "1 " * 10_000,
    ],
)
def test_when_not_a_rib_then_nothing_found(text, recognizer):
    assert recognizer.analyze(text, ["MA_RIB"]) == []


@pytest.mark.parametrize(
    "text, language, value, score",
    [
        (f"ref {FUND_126_RIB}", "fr", FUND_126_RIB, ONE_RUN_SCORE),
        (
            f"virement sur le {FUND_126_RIB}",
            "fr",
            FUND_126_RIB,
            ONE_RUN_SCORE + CONTEXT_BOOST,
        ),
        (
            f"relevé d'identité bancaire : {FUND_126_RIB}",
            "fr",
            FUND_126_RIB,
            ONE_RUN_SCORE + CONTEXT_BOOST,
        ),
        (
            f"الحساب البنكي {FUND_126_RIB}",
            "ar",
            FUND_126_RIB,
            ONE_RUN_SCORE + CONTEXT_BOOST,
        ),
        (
            f"virement bancaire {FUND_126_RIB_AS_PRINTED}",
            "fr",
            FUND_126_RIB_AS_PRINTED,
            GROUPED_SCORE + CONTEXT_BOOST,
        ),
        (f"{FUND_126_RIB} virement", "fr", FUND_126_RIB, ONE_RUN_SCORE),
        (f"Tribunal {FUND_126_RIB}", "fr", FUND_126_RIB, ONE_RUN_SCORE),
        (f"Contribution {FUND_126_RIB}", "fr", FUND_126_RIB, ONE_RUN_SCORE),
        (f"حساب الضريبة {FUND_126_RIB}", "ar", FUND_126_RIB, ONE_RUN_SCORE),
    ],
)
def test_when_enabled_in_yaml_then_only_bank_context_raises_score(
    text, language, value, score
):
    results = analyzer_for("MaRibRecognizer").analyze(text, language=language)

    start = text.index(value)
    assert [(r.entity_type, r.start, r.end) for r in results] == [
        ("MA_RIB", start, start + len(value))
    ]
    assert results[0].score == pytest.approx(score)
