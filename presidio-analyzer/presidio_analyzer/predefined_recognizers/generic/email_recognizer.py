from typing import List, Optional

import tldextract

from presidio_analyzer import Pattern, PatternRecognizer


class EmailRecognizer(PatternRecognizer):
    """
    Recognize email addresses using regex.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    # The domain part allows internal hyphen groups inside each label, including
    # consecutive hyphens, so RFC 3490 punycode labels (e.g. "xn--80ak6aa92e")
    # and raw IDN labels (matched via the Unicode-aware "\w") are detected.
    # Each label still starts and ends with an alphanumeric, and at least one
    # dot is required, so no arbitrary non-email text is matched.
    PATTERNS = [
        Pattern(
            "Email (Medium)",
            r"\b((([!#$%&'*+\-/=?^_`{|}~\w])|([!#$%&'*+\-/=?^_`{|}~\w][!#$%&'*+\-/=?^_`{|}~\.\w]{0,}[!#$%&'*+\-/=?^_`{|}~\w]))[@]\w+(?:-+\w+)*(?:\.\w+(?:-+\w+)*)+)\b",
            0.5,
        ),
    ]

    CONTEXT = ["email"]

    # Not public suffixes, so tldextract finds no registrable domain, yet
    # mailboxes on them are real: ".local" (RFC 6762) and the private-network
    # TLDs listed in RFC 6762 Appendix G.
    PRIVATE_NETWORK_TLDS = frozenset(
        ("local", "intranet", "internal", "private", "corp", "home", "lan")
    )

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "EMAIL_ADDRESS",
        name: Optional[str] = None,
    ):
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str):  # noqa: D102
        result = tldextract.extract(pattern_text)
        if result.fqdn != "":
            return True
        if pattern_text.rsplit(".", 1)[-1].lower() in self.PRIVATE_NETWORK_TLDS:
            # Cannot be checked against the public suffix list: keep the score.
            return None
        return False
