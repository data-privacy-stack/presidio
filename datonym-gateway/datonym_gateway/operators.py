"""Custom Presidio anonymization operators for DatOnym tokens."""

from __future__ import annotations

from typing import Any

from presidio_anonymizer.operators import Operator, OperatorType

from datonym_gateway.tokens import DatonymMapping


class DatonymTokenAnonymizer(Operator):
    """Replace each detected value with a request-local DatOnym token."""

    NAME = "datonym_token"

    def operate(self, text: str, params: dict[str, Any] | None = None) -> str:
        params = params or {}
        mapping: DatonymMapping = params["mapping"]
        entity_type: str = params["entity_type"]
        return mapping.get_or_create(entity_type, text)

    def validate(self, params: dict[str, Any] | None = None) -> None:
        params = params or {}
        if not isinstance(params.get("mapping"), DatonymMapping):
            raise ValueError("A DatonymMapping parameter named 'mapping' is required.")
        if not params.get("entity_type"):
            raise ValueError("An entity_type parameter is required.")

    def operator_name(self) -> str:
        return self.NAME

    def operator_type(self) -> OperatorType:
        return OperatorType.Anonymize


class DatonymTokenDeanonymizer(Operator):
    """Restore a DatOnym token from a request-local mapping."""

    NAME = "datonym_token_deanonymizer"

    def operate(self, text: str, params: dict[str, Any] | None = None) -> str:
        params = params or {}
        mapping: DatonymMapping = params["mapping"]
        return mapping.restore_text(text, strict=True)

    def validate(self, params: dict[str, Any] | None = None) -> None:
        params = params or {}
        if not isinstance(params.get("mapping"), DatonymMapping):
            raise ValueError("A DatonymMapping parameter named 'mapping' is required.")

    def operator_name(self) -> str:
        return self.NAME

    def operator_type(self) -> OperatorType:
        return OperatorType.Deanonymize
