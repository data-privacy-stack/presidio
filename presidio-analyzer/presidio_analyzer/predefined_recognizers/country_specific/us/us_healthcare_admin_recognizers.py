"""Recognizers for US healthcare administrative identifiers."""

from typing import Dict, List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class _HealthcareAdminPatternRecognizer(PatternRecognizer):
    """Pattern recognizer using context enhancement and score thresholds."""

    COUNTRY_CODE = "us"
    DEFAULT_SCORE_THRESHOLD = 0.6

    def __init__(
        self,
        patterns: List[Pattern],
        context: List[str],
        supported_entity: str,
        supported_language: str = "en",
        name: Optional[str] = None,
        score_thresholds: Optional[Dict[str, float]] = None,
    ):
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )
        self.score_thresholds = (
            score_thresholds
            if score_thresholds is not None
            else {supported_entity: self.DEFAULT_SCORE_THRESHOLD}
        )


class UsPriorAuthorizationNumberRecognizer(_HealthcareAdminPatternRecognizer):
    """Recognize US healthcare prior authorization numbers with context."""

    PATTERNS = [
        Pattern(
            "Prior authorization number",
            r"\bPA-?\d{6,12}\b",
            0.35,
        ),
    ]

    CONTEXT = [
        "authorization",
        "auth",
        "preauthorization",
        "approval",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_PRIOR_AUTHORIZATION_NUMBER",
        name: Optional[str] = None,
        score_thresholds: Optional[Dict[str, float]] = None,
    ):
        super().__init__(
            patterns=patterns if patterns else self.PATTERNS,
            context=context if context else self.CONTEXT,
            supported_entity=supported_entity,
            supported_language=supported_language,
            name=name,
            score_thresholds=score_thresholds,
        )


class UsClaimNumberRecognizer(_HealthcareAdminPatternRecognizer):
    """Recognize US healthcare claim numbers with billing/claims context."""

    PATTERNS = [
        Pattern(
            "Claim number",
            r"\bCLM-?\d{6,12}\b",
            0.35,
        ),
    ]

    CONTEXT = [
        "claim",
        "billing",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_CLAIM_NUMBER",
        name: Optional[str] = None,
        score_thresholds: Optional[Dict[str, float]] = None,
    ):
        super().__init__(
            patterns=patterns if patterns else self.PATTERNS,
            context=context if context else self.CONTEXT,
            supported_entity=supported_entity,
            supported_language=supported_language,
            name=name,
            score_thresholds=score_thresholds,
        )


class UsPrescriptionNumberRecognizer(_HealthcareAdminPatternRecognizer):
    """Recognize US prescription numbers with pharmacy context."""

    PATTERNS = [
        Pattern(
            "Prescription number",
            r"\bRX-?\d{6,12}\b",
            0.35,
        ),
    ]

    CONTEXT = [
        "prescription",
        "pharmacy",
        "medication",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_PRESCRIPTION_NUMBER",
        name: Optional[str] = None,
        score_thresholds: Optional[Dict[str, float]] = None,
    ):
        super().__init__(
            patterns=patterns if patterns else self.PATTERNS,
            context=context if context else self.CONTEXT,
            supported_entity=supported_entity,
            supported_language=supported_language,
            name=name,
            score_thresholds=score_thresholds,
        )


class UsReferralNumberRecognizer(_HealthcareAdminPatternRecognizer):
    """Recognize US healthcare referral numbers with referral context."""

    PATTERNS = [
        Pattern(
            "Referral number",
            r"\b(?:REF|INF)-?\d{6,12}\b",
            0.35,
        ),
    ]

    CONTEXT = [
        "referral",
        "infusion",
        "specialty",
        "referring",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_REFERRAL_NUMBER",
        name: Optional[str] = None,
        score_thresholds: Optional[Dict[str, float]] = None,
    ):
        super().__init__(
            patterns=patterns if patterns else self.PATTERNS,
            context=context if context else self.CONTEXT,
            supported_entity=supported_entity,
            supported_language=supported_language,
            name=name,
            score_thresholds=score_thresholds,
        )


class UsProviderTaxIdRecognizer(_HealthcareAdminPatternRecognizer):
    """Recognize US provider TIN/EIN values with healthcare provider context."""

    PATTERNS = [
        Pattern(
            "Provider tax ID",
            r"\b\d{2}-\d{7}\b",
            0.35,
        ),
    ]

    CONTEXT = [
        "provider",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_PROVIDER_TAX_ID",
        name: Optional[str] = None,
        score_thresholds: Optional[Dict[str, float]] = None,
    ):
        super().__init__(
            patterns=patterns if patterns else self.PATTERNS,
            context=context if context else self.CONTEXT,
            supported_entity=supported_entity,
            supported_language=supported_language,
            name=name,
            score_thresholds=score_thresholds,
        )
