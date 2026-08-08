from typing import List, Optional

from presidio_analyzer.predefined_recognizers.generic.phone_recognizer import (
    PhoneRecognizer,
)


class TwPhoneNumberRecognizer(PhoneRecognizer):
    """
    Recognize Taiwan phone numbers using python-phonenumbers with TW region hints.

    This recognizer intentionally delegates parsing and validation to the
    generic PhoneRecognizer with the supported region restricted to Taiwan.

    Public references for numbering background:
    https://law.moda.gov.tw/EngLawContent.aspx?id=53
    https://law.moda.gov.tw/EngLawContent.aspx?id=68

    :param context: Base context words for enhancing the assurance scores.
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: Optional recognizer name override
    """

    COUNTRY_CODE = "tw"

    CONTEXT = [
        "電話",
        "電話號碼",
        "手機",
        "手機號碼",
        "行動電話",
        "聯絡電話",
        "市話",
        "office phone",
        "phone",
        "phone number",
        "mobile",
        "cell",
        "call",
        "contact",
    ]

    def __init__(
        self,
        context: Optional[List[str]] = None,
        supported_language: str = "zh",
        supported_entity: str = "TW_PHONE_NUMBER",
        name: Optional[str] = None,
    ):
        super().__init__(
            context=context if context else self.CONTEXT,
            supported_language=supported_language,
            supported_entity=supported_entity,
            supported_regions=["TW"],
            name=name,
        )
