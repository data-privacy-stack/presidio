"""Digit scripts used by the Indian recognizer tests.

The Indian recognizers must recognise an identifier whichever script writes
its digits. The tables below hold the code point of the digit zero in each
script, so that a test can rewrite an ASCII sample into that script.
"""

#: Code point of the digit zero in each script used to write Indian text.
INDIC_DIGIT_BLOCKS = {
    "devanagari": 0x0966,
    "bengali": 0x09E6,
    "gurmukhi": 0x0A66,
    "gujarati": 0x0AE6,
    "oriya": 0x0B66,
    "tamil": 0x0BE6,
    "telugu": 0x0C66,
    "kannada": 0x0CE6,
    "malayalam": 0x0D66,
}

#: Code point of the digit zero in the decimal digit blocks that are used
#: outside India, and which therefore must keep matching nothing.
NON_INDIC_DIGIT_BLOCKS = {
    "thai": 0x0E50,
    "arabic-indic": 0x0660,
    "fullwidth": 0xFF10,
}


def to_script(text: str, zero: int) -> str:
    """Rewrite every ASCII digit in ``text`` using the script at ``zero``.

    :param text: text holding ASCII digits.
    :param zero: code point of the digit zero in the target script.
    :return: the text with its digits written in the target script.
    """
    return "".join(
        chr(zero + int(char)) if char in "0123456789" else char for char in text
    )
