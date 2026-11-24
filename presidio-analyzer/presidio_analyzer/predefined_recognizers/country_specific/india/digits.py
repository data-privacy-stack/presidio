r"""Digit scripts shared by the Indian recognizers.

Indian-language text routinely writes numbers in the digit block of its own
script, so a single identifier appears as ``312345678909`` in an English
invoice and in the Devanagari digits in a Hindi or Marathi sentence. The
recognizers in this package therefore match digits from ASCII and from the
nine Indic digit blocks.

The set is deliberately limited to the scripts used in India. ``\d`` and
``\p{Nd}`` would also match Thai, Arabic-Indic, fullwidth and other decimal
blocks, which are not used to write Indian identifiers, so matching them
would report Indian entities in unrelated text.
"""

#: A single digit, written in ASCII or in any of the nine Indic digit blocks.
#: The code points are kept as escape text so that the regex stays ASCII.
DIGIT_CLASS = (
    "[0-9"
    r"\u0966-\u096f"  # Devanagari
    r"\u09e6-\u09ef"  # Bengali
    r"\u0a66-\u0a6f"  # Gurmukhi
    r"\u0ae6-\u0aef"  # Gujarati
    r"\u0b66-\u0b6f"  # Oriya
    r"\u0be6-\u0bef"  # Tamil
    r"\u0c66-\u0c6f"  # Telugu
    r"\u0ce6-\u0cef"  # Kannada
    r"\u0d66-\u0d6f"  # Malayalam
    "]"
)
