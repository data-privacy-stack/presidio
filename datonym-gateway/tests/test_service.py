from __future__ import annotations

from dataclasses import dataclass

import pytest

from datonym_gateway.config import Settings
from datonym_gateway.service import DatonymService, restore_chat_response
from datonym_gateway.tokens import DatonymMapping, TokenCollisionError


@dataclass
class FakeRecognizerResult:
    entity_type: str
    start: int
    end: int
    score: float = 0.9

    def __gt__(self, other: "FakeRecognizerResult") -> bool:
        if self.start == other.start:
            return self.end > other.end
        return self.start > other.start


class FakeAnalyzer:
    def __init__(self, findings: list[tuple[str, str]]) -> None:
        self.findings = findings

    def analyze(self, text, language, entities=None, score_threshold=None):
        results = []
        for value, entity_type in self.findings:
            start = text.find(value)
            while start != -1:
                results.append(
                    FakeRecognizerResult(entity_type, start, start + len(value))
                )
                start = text.find(value, start + len(value))
        return results


def make_settings() -> Settings:
    return Settings(
        llm_base_url="https://example.test",
        llm_api_key=None,
        llm_model_default="test-model",
        analyzer_config="unused",
        language="de",
        score_threshold=0.35,
        request_timeout_seconds=5,
    )


def test_anonymize_text_reuses_tokens_and_restores_text():
    service = DatonymService(
        make_settings(),
        analyzer=FakeAnalyzer([("Max Mustermann", "PERSON")]),
    )
    mapping = DatonymMapping()

    result = service.anonymize_text(
        "Max Mustermann ruft Max Mustermann an.",
        mapping=mapping,
    )

    assert (
        result.text
        == "#DATONYM_PERSON_0001# ruft #DATONYM_PERSON_0001# an."
    )
    assert len(list(mapping.entries())) == 1
    assert (
        service.restore_text(result.text, mapping)
        == "Max Mustermann ruft Max Mustermann an."
    )


def test_anonymize_text_rejects_user_supplied_datonym_tokens():
    service = DatonymService(make_settings(), analyzer=FakeAnalyzer([]))

    with pytest.raises(TokenCollisionError):
        service.anonymize_text("Hallo #DATONYM_PERSON_0001#")


def test_restore_chat_response_restores_common_text_fields_only():
    mapping = DatonymMapping()
    token = mapping.get_or_create("PERSON", "Max Mustermann")

    restored = restore_chat_response(
        {
            "id": "chatcmpl-test",
            "choices": [
                {"message": {"role": "assistant", "content": f"Hallo {token}"}},
                {"delta": {"content": f"Tschuess {token}"}},
                {"text": f"Plain {token}"},
            ],
        },
        mapping,
    )

    assert restored["choices"][0]["message"]["content"] == "Hallo Max Mustermann"
    assert restored["choices"][1]["delta"]["content"] == "Tschuess Max Mustermann"
    assert restored["choices"][2]["text"] == "Plain Max Mustermann"
