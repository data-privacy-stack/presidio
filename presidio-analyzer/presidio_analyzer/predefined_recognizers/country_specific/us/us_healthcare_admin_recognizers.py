"""Recognizers for US healthcare administrative identifiers."""

from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult


class _ContextRequiredPatternRecognizer(PatternRecognizer):
    """Pattern recognizer which keeps only matches with required context."""

    COUNTRY_CODE = "us"

    NEGATIVE_CONTEXT: List[str] = []

    def __init__(
        self,
        patterns: List[Pattern],
        context: List[str],
        supported_entity: str,
        supported_language: str = "en",
        name: Optional[str] = None,
        context_window: int = 45,
    ):
        self.context_window = context_window
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def analyze(
        self,
        text: str,
        entities: List[str],
        nlp_artifacts=None,
        regex_flags: Optional[int] = None,
    ) -> List[RecognizerResult]:
        """Analyze text and keep only matches with nearby positive context."""
        results = super().analyze(text, entities, nlp_artifacts, regex_flags)
        return [
            result for result in results if self.__has_required_context(text, result)
        ]

    def __has_required_context(self, text: str, result: RecognizerResult) -> bool:
        window_text = self.__get_context_window(text, result).lower()
        if any(context in window_text for context in self.NEGATIVE_CONTEXT):
            return False
        return any(context in window_text for context in self.context)

    def __get_context_window(self, text: str, result: RecognizerResult) -> str:
        start = max(0, result.start - self.context_window)
        end = min(len(text), result.end + self.context_window)
        return text[start:end]


class UsPriorAuthorizationNumberRecognizer(_ContextRequiredPatternRecognizer):
    """Recognize US healthcare prior authorization numbers with context."""

    PATTERNS = [
        Pattern(
            "Prior authorization number",
            r"\bPA-?\d{6,12}\b",
            0.35,
        ),
    ]

    CONTEXT = [
        "prior authorization",
        "prior auth",
        "preauthorization",
        "pre-auth",
        "authorization number",
        "auth number",
        "approval request",
        "treatment authorization",
        "drug authorization",
    ]

    NEGATIVE_CONTEXT = [
        "order number",
        "tracking number",
        "case number",
        "claim number",
        "claim id",
        "invoice number",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_PRIOR_AUTHORIZATION_NUMBER",
        name: Optional[str] = None,
        context_window: int = 45,
    ):
        super().__init__(
            patterns=patterns if patterns else self.PATTERNS,
            context=context if context else self.CONTEXT,
            supported_entity=supported_entity,
            supported_language=supported_language,
            name=name,
            context_window=context_window,
        )


class UsClaimNumberRecognizer(_ContextRequiredPatternRecognizer):
    """Recognize US healthcare claim numbers with billing/claims context."""

    PATTERNS = [
        Pattern(
            "Claim number",
            r"\bCLM-?\d{6,12}\b",
            0.35,
        ),
    ]

    CONTEXT = [
        "claim number",
        "claim id",
        "claim",
        "healthcare claim",
        "medical claim",
        "billing",
        "billing claim",
        "claims processing",
        "processed claim",
    ]

    NEGATIVE_CONTEXT = [
        "order number",
        "tracking number",
        "case number",
        "referral number",
        "authorization number",
        "invoice number",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_CLAIM_NUMBER",
        name: Optional[str] = None,
        context_window: int = 45,
    ):
        super().__init__(
            patterns=patterns if patterns else self.PATTERNS,
            context=context if context else self.CONTEXT,
            supported_entity=supported_entity,
            supported_language=supported_language,
            name=name,
            context_window=context_window,
        )


class UsPrescriptionNumberRecognizer(_ContextRequiredPatternRecognizer):
    """Recognize US prescription numbers with pharmacy context."""

    PATTERNS = [
        Pattern(
            "Prescription number",
            r"\bRX-?\d{6,12}\b",
            0.35,
        ),
    ]

    CONTEXT = [
        "prescription number",
        "prescription id",
        "rx number",
        "rx no",
        "pharmacy",
        "prescription",
        "medication order",
        "drug order",
    ]

    NEGATIVE_CONTEXT = [
        "order number",
        "tracking number",
        "case number",
        "claim number",
        "claim id",
        "invoice number",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_PRESCRIPTION_NUMBER",
        name: Optional[str] = None,
        context_window: int = 45,
    ):
        super().__init__(
            patterns=patterns if patterns else self.PATTERNS,
            context=context if context else self.CONTEXT,
            supported_entity=supported_entity,
            supported_language=supported_language,
            name=name,
            context_window=context_window,
        )


class UsReferralNumberRecognizer(_ContextRequiredPatternRecognizer):
    """Recognize US healthcare referral numbers with referral context."""

    PATTERNS = [
        Pattern(
            "Referral number",
            r"\b(?:REF|INF)-?\d{6,12}\b",
            0.35,
        ),
    ]

    CONTEXT = [
        "referral number",
        "referral id",
        "referral",
        "infusion referral",
        "infusion therapy",
        "specialty referral",
        "specialty care",
        "referring provider",
    ]

    NEGATIVE_CONTEXT = [
        "order number",
        "tracking number",
        "case number",
        "claim number",
        "claim id",
        "invoice number",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_REFERRAL_NUMBER",
        name: Optional[str] = None,
        context_window: int = 45,
    ):
        super().__init__(
            patterns=patterns if patterns else self.PATTERNS,
            context=context if context else self.CONTEXT,
            supported_entity=supported_entity,
            supported_language=supported_language,
            name=name,
            context_window=context_window,
        )


class UsProviderTaxIdRecognizer(_ContextRequiredPatternRecognizer):
    """Recognize US provider TIN/EIN values with healthcare provider context."""

    PATTERNS = [
        Pattern(
            "Provider tax ID",
            r"\b\d{2}-\d{7}\b",
            0.35,
        ),
    ]

    CONTEXT = [
        "provider tax id",
        "provider tin",
        "provider ein",
        "tax id",
        "tin",
        "ein",
        "healthcare organization",
        "provider organization",
        "billing provider",
        "rendering provider",
    ]

    NEGATIVE_CONTEXT = [
        "employee tax id",
        "vendor tax id",
        "company tax id",
        "order number",
        "tracking number",
        "case number",
        "claim number",
        "invoice number",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_PROVIDER_TAX_ID",
        name: Optional[str] = None,
        context_window: int = 45,
    ):
        super().__init__(
            patterns=patterns if patterns else self.PATTERNS,
            context=context if context else self.CONTEXT,
            supported_entity=supported_entity,
            supported_language=supported_language,
            name=name,
            context_window=context_window,
        )
