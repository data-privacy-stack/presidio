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
    :param name: Name of the recognizer
    :param offline: If True, uses tldextract in offline mode with bundled PSL
        snapshot data only (no external network calls to publicsuffix.org).
        Defaults to False.
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

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "EMAIL_ADDRESS",
        name: Optional[str] = None,
        offline: bool = False,
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
        self.offline = offline
        if offline:
            self._extract = tldextract.TLDExtract(suffix_list_urls=())
        else:
            self._extract = tldextract.extract

    def validate_result(self, pattern_text: str):  # noqa: D102
        result = self._extract(pattern_text)
        return result.fqdn != ""
