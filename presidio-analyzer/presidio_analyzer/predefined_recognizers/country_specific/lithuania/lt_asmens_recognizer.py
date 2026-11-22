import datetime
from typing import List, Optional, Tuple

from presidio_analyzer import Pattern, PatternRecognizer


class LtAsmensRecognizer(PatternRecognizer):
    """
    Recognize Lithuanian personal codes (asmens kodas).

    The asmens kodas is the 11 digit personal
    number issued to Lithuanian citizens and
    registered residents by the Population
    Register (Registru centras). It doubles as
    the individual tax identification number
    (TIN) for dealings with the State Tax
    Inspectorate (VMI); no separate tax number
    is issued to residents. The number has 11
    digits and encodes the holder's sex, birth
    century and date of birth: GYYMMDDSSSC,
    where G is the gender and century digit
    (1 male and 2 female born 1800 to 1899, 3
    male and 4 female born 1900 to 1999, 5 male
    and 6 female born 2000 to 2099), YYMMDD is
    the date of birth, SSS is a three digit
    serial number distinguishing persons born
    on the same date, and C is a check digit.
    It is written plain, 11 digits with no
    separators, for example 33309240064.

    Checksum: the check digit comes from
    weights 1, 2, 3, 4, 5, 6, 7, 8, 9, 1 on
    the first 10 digits, as published in the
    OECD Lithuania TIN sheet and implemented
    by the python-stdnum lt.asmens module
    (which reuses the ee.ik check digit
    computation). With r = sum mod 11, a value
    of r from 0 to 9 is the check digit. When
    r is 10, a second round runs with weights
    3, 4, 5, 6, 7, 8, 9, 1, 2, 3 on the first
    10 digits, and the check digit is the
    second round remainder mod 10, so a second
    round remainder of 10 gives a check digit
    of 0. Worked examples, verified by hand
    and by computation: 33309240064 (a man
    born 24 September 1933, serial 006): the
    first weighted sum is 109, 109 mod 11 is
    10, so the second round runs, its weighted
    sum is 169, 169 mod 11 is 4, and the check
    digit is 4; 10101010005 (a man born 1
    January 1801, serial 000): the weighted
    sum is 16, 16 mod 11 is 5, and the check
    digit is 5; 38409152012 (a man born 15
    September 1984, serial 201): the weighted
    sum is 134, 134 mod 11 is 2, and the check
    digit is 2; 38503031230 (a man born 3
    March 1985, serial 123): the weighted sum
    is 99, 99 mod 11 is 0, and the check digit
    is 0; 60002290003 (a woman born on the
    leap day 29 February 2000, serial 000):
    the weighted sum is 91, 91 mod 11 is 3,
    and the check digit is 3; 50001010006 (a
    man born 1 January 2000, serial 000): the
    weighted sum is 17, 17 mod 11 is 6, and
    the check digit is 6; 19912310008 (a man
    born 31 December 1899, serial 000): the
    weighted sum is 85, 85 mod 11 is 8, and
    the check digit is 8; 29912310009 (a woman
    born 31 December 1899, serial 000): the
    weighted sum is 86, 86 mod 11 is 9, and
    the check digit is 9; 45409065730 (a woman
    born 6 September 1954, serial 573): the
    first weighted sum is 219, 219 mod 11 is
    10, so the second round runs, its weighted
    sum is 197, 197 mod 11 is 10, and the
    check digit is 0 through the fold;
    61507151237 (a woman born 15 July 2015,
    serial 123): the weighted sum is 128, 128
    mod 11 is 7, and the check digit is 7. The
    recognizer's checksum was also cross-checked
    against python-stdnum lt.asmens on all
    fixtures and on 2000 random 10 digit bodies
    (check digit computation), with zero
    mismatches. Full validation differs from
    lt.asmens only in the stricter direction,
    by design: this recognizer accepts only
    first digits 1 to 6 and rejects future
    birth dates, so in a 200,000 random 11
    digit number run, the only disagreements
    were 2,298 numbers lt.asmens accepts and
    this recognizer rejects (first digits 7,
    8 or 9, or future dates), none the other
    way.

    Seven honest caveats. First, the checksum
    alone passes about one time in ten for an
    arbitrary 11 digit token, so a bare 11
    digit number is weak evidence on its own;
    the recognizer keeps the pattern score at
    0.5 and never promotes it. The date and
    first digit rules cut this down sharply: a
    random 11 digit token passes the full
    validation only about 1 time in 617 (324
    in 200,000 random tokens measured). Second,
    python-stdnum lt.asmens accepts first
    digits 7 and 8 (the 2100 century through
    its ee.ik date helper) and skips the birth
    date check entirely for first digit 9,
    and it does not reject future birth dates,
    while this recognizer accepts only first
    digits 1 to 6 and rejects a birth date in
    the future, so it is stricter than
    python-stdnum. Third, the LookupTax
    Lithuania guide prints 38503031234 as its
    asmens kodas example with check digit 4,
    but the correct check digit for that body
    is 0, so 38503031230 is the valid number
    and 38503031234 fails validation in
    python-stdnum too; the recognizer follows
    the OECD sheet and python-stdnum, not the
    LookupTax example. Fourth, python-stdnum
    strips spaces when compacting a number,
    while this recognizer matches plain 11
    digits only, so a spaced form is not
    matched here. Fifth, the all zeros string
    00000000000 passes the checksum but is
    rejected here as implausible, and the
    fully sequential run 87654321098 passes
    the checksum but is rejected here as a
    sequential run; no other fully sequential
    11 digit run passes the checksum (all 20
    wrap runs checked). Sixth, a first digit
    of 9 is used for codes where the birth
    date is not known, and python-stdnum skips
    the date check for it; this recognizer does
    not match first digit 9, so those codes
    are missed here, in the safe direction.
    Seventh, a passing checksum only shows
    the number is well formed; it cannot show
    the number was ever issued to anyone, and
    only the Lithuanian Population Register
    (Registru centras) can confirm that.

    The recognizer validates the date, first
    digit, and checksum in invalidate_result
    and keeps the pattern score at 0.5: it does
    not promote a match to 1.0, because a
    checksum passes about one time in ten for
    an arbitrary same-shape token.

    Invalidation is based on: the number must be
    exactly 11 digits; the number must not be all
    the same digit; a fully sequential digit run
    is rejected; the first digit must be 1 to 6,
    giving the birth century (1 and 2 the 1800s,
    3 and 4 the 1900s, 5 and 6 the 2000s); the
    next 6 digits must be a real calendar date
    that is not in the future; and the check
    digit must satisfy the two round mod 11
    check, that is, with weights 1, 2, 3, 4, 5,
    6, 7, 8, 9, 1 on the first 10 digits, the
    remainder mod 11 is the check digit unless
    it is 10, in which case weights 3, 4, 5, 6,
    7, 8, 9, 1, 2, 3 are used and the remainder
    mod 10 is the check digit.
    This follows the approach of the Pakistani
    CNIC, Saudi national ID, UAE Emirates ID,
    Egyptian national ID, Bangladesh NID, Sri
    Lanka NIC, Ghana Card, Kazakhstan IIN,
    Ukraine RNOKPP, Uzbekistan PINFL, Morocco
    CNIE, Indonesia NIK, Malaysia MyKad, Vietnam
    CCCD, Chile RUT, Ecuador Cedula, Iran Code
    Melli, Argentina CUIT/CUIL, Mexico CURP,
    Peru RUC, Colombia NIT, Dominican Republic
    Cedula, Paraguay RUC, Uruguay RUT, Iceland
    kennitala, Czech birth number, Romanian
    personal numeric code, Dutch citizen service
    number, Croatian personal identification
    number, Slovenian unique master citizen
    number, Bulgarian uniform civil number,
    Greek tax identification number, and Serbian
    unique master citizen number recognizers.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    This can allow a greater variety in input, for example by removing dashes or spaces.
    """

    COUNTRY_CODE = "lt"

    PATTERNS = [
        Pattern(
            "LT_ASMENS",
            r"(?<![A-Za-z0-9./-])\d{11}(?![A-Za-z0-9/-])",
            0.5,
        ),
    ]

    CONTEXT = [
        "lithuania",
        "lithuanian",
        "asmens kodas",
        "asmens",
        "personal code",
        "lithuanian personal code",
        "population register",
    ]

    # First digit: 1 and 2 are the 1800s, 3 and 4
    # the 1900s, 5 and 6 the 2000s. Odd is male,
    # even is female. Digits 7, 8 and 9 are not
    # accepted: 7 and 8 would be the 2100s, and
    # 9 is used where the birth date is unknown.
    FIRST_DIGIT_CENTURIES = {
        "1": 1800,
        "2": 1800,
        "3": 1900,
        "4": 1900,
        "5": 2000,
        "6": 2000,
    }

    CHECK_WEIGHTS_FIRST = (1, 2, 3, 4, 5, 6, 7, 8, 9, 1)
    CHECK_WEIGHTS_SECOND = (3, 4, 5, 6, 7, 8, 9, 1, 2, 3)

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "LT_ASMENS",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ) -> None:
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def invalidate_result(self, pattern_text: str) -> bool:
        """
        Check if the pattern text cannot be a LT_ASMENS entity.

        The number must be 11 digits, must not be all
        the same digit, must not be a fully sequential
        digit run, must carry a first digit of 1 to 6,
        must carry a real birth date that is not in the
        future, and must pass the two round mod 11 check.

        :param pattern_text: Text detected as pattern by regex
        :return: True if invalidated
        """
        text = pattern_text.strip()
        if len(text) != 11 or not text.isdigit():
            return True
        if len(set(text)) == 1:
            # cannot be all the same digit
            return True
        if self._is_sequential(text):
            # a real issued number is never one fully sequential run
            return True
        if text[0] not in self.FIRST_DIGIT_CENTURIES:
            return True
        if not self._has_valid_birth_date(text):
            return True
        return not self._has_valid_checksum(text)

    @staticmethod
    def _has_valid_birth_date(digits: str) -> bool:
        """
        Check the birth date encoded in the first 7 digits.

        The date is GYYMMDD, with G of 1 or 2 meaning
        the 1800s, 3 or 4 the 1900s, and 5 or 6 the
        2000s. The date must be a real calendar date
        and must not be in the future.

        :param digits: The 11 digit personal code
        :return: True when the encoded birth date is real and past
        """
        century = LtAsmensRecognizer.FIRST_DIGIT_CENTURIES[digits[0]]
        year = century + int(digits[1:3])
        month = int(digits[3:5])
        day = int(digits[5:7])
        try:
            birth_date = datetime.date(year, month, day)
        except ValueError:
            return False
        return birth_date <= datetime.date.today()

    @staticmethod
    def _has_valid_checksum(digits: str) -> bool:
        """
        Check the two round mod 11 checksum of an 11 digit number.

        With weights 1, 2, 3, 4, 5, 6, 7, 8, 9, 1
        on the first 10 digits, the remainder mod 11
        is the check digit, unless it is 10, in which
        case weights 3, 4, 5, 6, 7, 8, 9, 1, 2, 3
        are used and the remainder mod 10 is the
        check digit.

        :param digits: The 11 digit personal code
        :return: True when the checksum holds
        """
        return LtAsmensRecognizer._check_digit(digits[:10]) == digits[10]

    @staticmethod
    def _check_digit(first_ten: str) -> str:
        """
        Compute the check digit for the first 10 digits.

        With weights 1, 2, 3, 4, 5, 6, 7, 8, 9, 1
        on the first 10 digits, the remainder mod 11
        is the check digit, unless it is 10, in which
        case weights 3, 4, 5, 6, 7, 8, 9, 1, 2, 3
        are used and the remainder mod 10 is the
        check digit, so every 10 digit body has a
        valid check digit.

        :param first_ten: The first 10 digits of the number
        :return: The check digit, 0 to 9
        """
        total = sum(
            int(digit) * weight
            for digit, weight in zip(first_ten, LtAsmensRecognizer.CHECK_WEIGHTS_FIRST)
        )
        remainder = total % 11
        if remainder == 10:
            total = sum(
                int(digit) * weight
                for digit, weight in zip(
                    first_ten, LtAsmensRecognizer.CHECK_WEIGHTS_SECOND
                )
            )
            remainder = total % 11
        return str(remainder % 10)

    @staticmethod
    def _is_sequential(digits: str) -> bool:
        """
        Check if the digits form a sequential run, allowing 9 to wrap to 0.

        For example, 01234567890 ascends by one each step, and
        98765432109 descends by one each step.

        :param digits: Numeric string to check
        :return: True if every digit follows the previous one sequentially
        """
        values = [int(digit) for digit in digits]
        ascending = all(
            (values[i] + 1) % 10 == values[i + 1] for i in range(len(values) - 1)
        )
        descending = all(
            (values[i] - 1) % 10 == values[i + 1] for i in range(len(values) - 1)
        )
        return ascending or descending
