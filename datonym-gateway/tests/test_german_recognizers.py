from __future__ import annotations

import pytest

from presidio_analyzer.predefined_recognizers import (
    CreditCardRecognizer,
    DateRecognizer,
    DeBsnrRecognizer,
    DeFuehrerscheinRecognizer,
    DeHandelsregisterRecognizer,
    DeHealthInsuranceRecognizer,
    DeIdCardRecognizer,
    DeKfzRecognizer,
    DeLanrRecognizer,
    DePassportRecognizer,
    DePlzRecognizer,
    DeSocialSecurityRecognizer,
    DeTaxIdRecognizer,
    DeTaxNumberRecognizer,
    DeVatIdRecognizer,
    EmailRecognizer,
    IbanRecognizer,
    IpRecognizer,
    PhoneRecognizer,
    UrlRecognizer,
)


@pytest.mark.parametrize(
    ("recognizer_cls", "entity", "sample"),
    [
        (DeTaxIdRecognizer, "DE_TAX_ID", "12345678903"),
        (DeTaxNumberRecognizer, "DE_TAX_NUMBER", "0981508150999"),
        (DePassportRecognizer, "DE_PASSPORT", "C01234565"),
        (DeIdCardRecognizer, "DE_ID_CARD", "L01X00T44"),
        (DeSocialSecurityRecognizer, "DE_SOCIAL_SECURITY", "15070649C103"),
        (DeHealthInsuranceRecognizer, "DE_HEALTH_INSURANCE", "A123456780"),
        (DeKfzRecognizer, "DE_KFZ", "B AB 1234"),
        (DeHandelsregisterRecognizer, "DE_HANDELSREGISTER", "HRB 123456"),
        (DePlzRecognizer, "DE_PLZ", "10115"),
        (DeLanrRecognizer, "DE_LANR", "123456601"),
        (DeBsnrRecognizer, "DE_BSNR", "021234568"),
        (DeVatIdRecognizer, "DE_VAT_ID", "DE136695976"),
        (DeFuehrerscheinRecognizer, "DE_FUEHRERSCHEIN", "BO12345678A"),
    ],
)
def test_german_recognizers_detect_representative_values(
    recognizer_cls, entity, sample
):
    recognizer = recognizer_cls()

    results = recognizer.analyze(sample, [entity])

    assert any(result.entity_type == entity for result in results)


@pytest.mark.parametrize(
    ("recognizer", "entity", "sample"),
    [
        (
            EmailRecognizer(supported_language="de", context=["email"]),
            "EMAIL_ADDRESS",
            "max@example.de",
        ),
        (IbanRecognizer(supported_language="de"), "IBAN_CODE", "DE89370400440532013000"),
        (
            PhoneRecognizer(
                supported_language="de",
                supported_regions=("DE", "AT", "CH", "LU"),
            ),
            "PHONE_NUMBER",
            "+49 30 123456",
        ),
        (
            CreditCardRecognizer(supported_language="de"),
            "CREDIT_CARD",
            "4111 1111 1111 1111",
        ),
        (IpRecognizer(supported_language="de"), "IP_ADDRESS", "192.168.0.1"),
        (UrlRecognizer(supported_language="de"), "URL", "https://example.de"),
        (DateRecognizer(supported_language="de"), "DATE_TIME", "01.01.2025"),
    ],
)
def test_global_prompt_entities_detect_representative_values(
    recognizer, entity, sample
):
    results = recognizer.analyze(sample, [entity])

    assert any(result.entity_type == entity for result in results)
