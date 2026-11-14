from .assertions import assert_result, assert_result_within_score_range, assert_result_with_textual_explanation  # noqa: E501

ARABIC_INDIC_DIGITS = str.maketrans(
    "0123456789", "".join(chr(0x660 + d) for d in range(10))
)
PERSIAN_DIGITS = str.maketrans(
    "0123456789", "".join(chr(0x6F0 + d) for d in range(10))
)
DEVANAGARI_DIGITS = str.maketrans(
    "0123456789", "".join(chr(0x966 + d) for d in range(10))
)
BENGALI_DIGITS = str.maketrans(
    "0123456789", "".join(chr(0x9E6 + d) for d in range(10))
)
ODIA_DIGITS = str.maketrans(
    "0123456789", "".join(chr(0xB66 + d) for d in range(10))
)
