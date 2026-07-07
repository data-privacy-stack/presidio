"""DatOnym anonymization and LLM forwarding services."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Protocol

import httpx
from presidio_anonymizer import AnonymizerEngine, OperatorConfig

from datonym_gateway.config import Settings
from datonym_gateway.models import EntityFinding, JsonDict
from datonym_gateway.operators import DatonymTokenAnonymizer
from datonym_gateway.presidio import build_analyzer, build_anonymizer
from datonym_gateway.tokens import DatonymMapping

DEFAULT_ENTITIES = [
    "PERSON",
    "LOCATION",
    "ORGANIZATION",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "IBAN_CODE",
    "CREDIT_CARD",
    "IP_ADDRESS",
    "URL",
    "DATE_TIME",
    "DE_TAX_ID",
    "DE_TAX_NUMBER",
    "DE_PASSPORT",
    "DE_ID_CARD",
    "DE_SOCIAL_SECURITY",
    "DE_HEALTH_INSURANCE",
    "DE_KFZ",
    "DE_HANDELSREGISTER",
    "DE_PLZ",
    "DE_LANR",
    "DE_BSNR",
    "DE_VAT_ID",
    "DE_FUEHRERSCHEIN",
]


class AnalyzerProtocol(Protocol):
    """Protocol for Presidio analyzer-compatible objects."""

    def analyze(
        self,
        text: str,
        language: str,
        entities: list[str] | None = None,
        score_threshold: float | None = None,
    ) -> list[Any]:
        ...


@dataclass
class AnonymizedText:
    """Anonymized text plus public entity metadata."""

    text: str
    entities: list[EntityFinding]
    mapping: DatonymMapping


class DatonymService:
    """Runs Presidio analysis and DatOnym token anonymization."""

    def __init__(
        self,
        settings: Settings,
        analyzer: AnalyzerProtocol | None = None,
        anonymizer: AnonymizerEngine | None = None,
        entities: list[str] | None = None,
    ) -> None:
        self.settings = settings
        self._analyzer = analyzer
        self._anonymizer = anonymizer
        self.entities = entities or DEFAULT_ENTITIES

    @property
    def analyzer(self) -> AnalyzerProtocol:
        if self._analyzer is None:
            self._analyzer = build_analyzer(self.settings.analyzer_config)
        return self._analyzer

    @property
    def anonymizer(self) -> AnonymizerEngine:
        if self._anonymizer is None:
            self._anonymizer = build_anonymizer()
        return self._anonymizer

    def anonymize_text(
        self,
        text: str,
        *,
        language: str | None = None,
        mapping: DatonymMapping | None = None,
    ) -> AnonymizedText:
        """Analyze and replace PII with reversible DatOnym tokens."""

        mapping = mapping or DatonymMapping()
        mapping.assert_no_token_collision(text)
        analyzer_results = self.analyzer.analyze(
            text=text,
            language=language or self.settings.language,
            entities=self.entities,
            score_threshold=self.settings.score_threshold,
        )
        result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=analyzer_results,
            operators={
                "DEFAULT": OperatorConfig(
                    DatonymTokenAnonymizer.NAME,
                    {"mapping": mapping},
                )
            },
        )
        return AnonymizedText(
            text=result.text,
            entities=[
                EntityFinding(
                    entity_type=item.entity_type,
                    token=item.text,
                    start=item.start,
                    end=item.end,
                    score=_score_for_item(item, analyzer_results, text, mapping),
                )
                for item in result.items
            ],
            mapping=mapping,
        )

    def restore_text(self, text: str, mapping: DatonymMapping) -> str:
        """Restore known DatOnym tokens in text."""

        return mapping.restore_text(text)


def _score_for_item(
    item: Any,
    analyzer_results: list[Any],
    original_text: str,
    mapping: DatonymMapping,
) -> float | None:
    entry_by_token = {entry.token: entry for entry in mapping.entries()}
    entry = entry_by_token.get(item.text)
    if entry is None:
        return None

    for result in analyzer_results:
        if (
            result.entity_type == item.entity_type
            and original_text[result.start : result.end] == entry.original
        ):
            return result.score
    return None


class LLMClient:
    """Small OpenAI-compatible chat completion client."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def chat_completions(self, payload: JsonDict) -> JsonDict:
        """Forward an anonymized chat completion request."""

        url = self.settings.llm_base_url.rstrip("/") + "/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.settings.llm_api_key:
            headers["Authorization"] = f"Bearer {self.settings.llm_api_key}"

        async with httpx.AsyncClient(
            timeout=self.settings.request_timeout_seconds
        ) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()


class ChatGateway:
    """Coordinates request-local anonymization, LLM call, and restoration."""

    def __init__(self, service: DatonymService, llm_client: LLMClient) -> None:
        self.service = service
        self.llm_client = llm_client

    async def chat_completions(self, payload: JsonDict) -> JsonDict:
        """Anonymize chat messages, call the LLM, and restore response tokens."""

        mapping = DatonymMapping()
        outbound = copy.deepcopy(payload)
        model = outbound.get("model") or self.service.settings.llm_model_default
        if not model:
            raise ValueError("A model is required via request.model or LLM_MODEL_DEFAULT.")
        outbound["model"] = model

        for message in outbound.get("messages", []):
            content = message.get("content")
            if not isinstance(content, str):
                raise TypeError("DatOnym MVP supports string message content only.")
            message["content"] = self.service.anonymize_text(
                content,
                mapping=mapping,
            ).text

        response = await self.llm_client.chat_completions(outbound)
        return restore_chat_response(response, mapping)


def restore_chat_response(response: JsonDict, mapping: DatonymMapping) -> JsonDict:
    """Restore known DatOnym tokens in common chat response text fields."""

    restored = copy.deepcopy(response)
    for choice in restored.get("choices", []):
        message = choice.get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            message["content"] = mapping.restore_text(message["content"])

        delta = choice.get("delta")
        if isinstance(delta, dict) and isinstance(delta.get("content"), str):
            delta["content"] = mapping.restore_text(delta["content"])

        if isinstance(choice.get("text"), str):
            choice["text"] = mapping.restore_text(choice["text"])

    return restored
