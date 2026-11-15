import re
from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class CardTrackDataRecognizer(PatternRecognizer):
    """
    Recognize payment card magnetic stripe track data (track 1 and track 2).

    Track data is the full contents of a card's magnetic stripe, as output by a
    card reader or written into logs, support tickets and transcripts. PCI DSS
    v4.0.1 requirement 3.3.1.1 classes it as sensitive authentication data that
    must not be kept after authorization, even when encrypted. The card number
    inside track 1 is not found by ``CreditCardRecognizer``: the format code
    ``B`` sits directly before the first digit, so there is no word boundary.

    Layouts follow ISO/IEC 7813 for financial cards:

    - Track 1 (format code B): ``%B`` PAN (up to 19 digits) ``^`` name (2 to 26
      characters) ``^`` expiry YYMM, service code (3 digits), discretionary
      data, then the end sentinel ``?``.
    - Track 2: ``;`` PAN (up to 19 digits) ``=`` expiry YYMM, service code
      (3 digits), discretionary data, then the end sentinel ``?``.

    Start and end sentinels are optional in the patterns, because readers and
    log formatters often strip them.

    Validation: the PAN must pass the Luhn check (ISO/IEC 7812-1), the expiry
    month must be 01 to 12, and the first service code digit must be one ISO/IEC
    7813 assigns (1, 2, 5, 6, 7 or 9). A match that fails any check is dropped;
    one that passes all three is promoted to the maximum score. On random
    ``digits=digits`` strings of track 2 shape, about 0.7 percent pass all three
    (Luhn 1 in 10, month 12 in 100, service code 6 in 10), against 10 percent
    for a Luhn check alone on a bare digit run.

    Out of scope: EMV tag 57 (track 2 equivalent data, ``D`` separator), which
    appears in chip transaction logs and would need its own pattern.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words. None by default: every match is
    either promoted or dropped by validation, so context would not change a score
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: Name of this recognizer
    """

    PATTERNS = [
        Pattern(
            "Card track 1 (strong)",
            # With both sentinels, discretionary data may hold any track 1
            # character (ISO/IEC 7813 allows letters, digits, spaces and
            # punctuation) and runs to the end sentinel. Without them, it runs
            # over letters and digits and stops at the first space or other
            # character, so trailing words and numbers stay out.
            r"(?:%B\d{12,19}\^[^\^?\r\n]{2,26}\^\d{7}[^\^?%;\r\n]{0,60}\?"
            r"|(?:%|\b)B\d{12,19}\^[^\^?\r\n]{2,26}\^\d{7}[0-9A-Z]{0,60})",
            0.5,
        ),
        Pattern(
            "Card track 2 (strong)",
            r";?\b\d{12,19}=\d{7}\d{0,30}\??",
            0.5,
        ),
    ]

    # ISO/IEC 7813 service code, first digit (interchange and technology).
    _SERVICE_CODE_FIRST_DIGITS = frozenset("125679")

    _TRACK1_FIELDS = re.compile(
        r"B(\d{12,19})\^[^\^]*\^\d{2}(\d{2})(\d)", re.IGNORECASE
    )
    _TRACK2_FIELDS = re.compile(r"(\d{12,19})=\d{2}(\d{2})(\d)")

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "CARD_TRACK_DATA",
        name: Optional[str] = None,
    ):
        patterns = patterns if patterns else self.PATTERNS
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> Optional[bool]:
        """
        Check the PAN (Luhn), expiry month and service code in the matched track.

        :param pattern_text: the text matched by one of the patterns
        :return: True if all three checks pass, False if any fails,
        None if the fields cannot be read
        """
        fields = self._TRACK1_FIELDS.search(pattern_text) or (
            self._TRACK2_FIELDS.search(pattern_text)
        )
        if not fields:
            return None
        pan, month, service = fields.group(1), int(fields.group(2)), fields.group(3)
        if not 1 <= month <= 12:
            return False
        if service not in self._SERVICE_CODE_FIRST_DIGITS:
            return False
        return self._luhn_valid(pan)

    @staticmethod
    def _luhn_valid(number: str) -> bool:
        total = 0
        for index, char in enumerate(reversed(number)):
            digit = int(char)
            if index % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        return total % 10 == 0
