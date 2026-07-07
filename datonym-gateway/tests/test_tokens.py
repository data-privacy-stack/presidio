import pytest

from datonym_gateway.tokens import (
    DatonymMapping,
    TokenCollisionError,
    UnknownTokenError,
    normalize_entity_type,
)


def test_mapping_reuses_token_for_same_entity_value():
    mapping = DatonymMapping()

    first = mapping.get_or_create("PERSON", "Max Mustermann")
    second = mapping.get_or_create("PERSON", "Max Mustermann")
    other = mapping.get_or_create("EMAIL_ADDRESS", "max@example.de")

    assert first == "#DATONYM_PERSON_0001#"
    assert second == first
    assert other == "#DATONYM_EMAIL_ADDRESS_0001#"


def test_mapping_restores_known_tokens_and_leaves_unknown_tokens_by_default():
    mapping = DatonymMapping()
    token = mapping.get_or_create("PERSON", "Max Mustermann")

    restored = mapping.restore_text(
        f"Hallo {token}, unbekannt #DATONYM_PERSON_9999#."
    )

    assert restored == "Hallo Max Mustermann, unbekannt #DATONYM_PERSON_9999#."


def test_mapping_strict_restore_rejects_unknown_tokens():
    mapping = DatonymMapping()

    with pytest.raises(UnknownTokenError):
        mapping.restore_text("#DATONYM_PERSON_9999#", strict=True)


def test_collision_detection_rejects_token_like_user_input():
    mapping = DatonymMapping()

    with pytest.raises(TokenCollisionError):
        mapping.assert_no_token_collision("Bitte #DATONYM_PERSON_0001# pruefen")


def test_entity_type_normalization():
    assert normalize_entity_type("de-tax id") == "DE_TAX_ID"
