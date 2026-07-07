from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
for rel_path in ("presidio-analyzer", "presidio-anonymizer", "datonym-gateway"):
    path = str(REPO_ROOT / rel_path)
    if path not in sys.path:
        sys.path.insert(0, path)

from datonym_gateway.app import create_app  # noqa: E402
from datonym_gateway.service import DatonymService  # noqa: E402
from test_service import FakeAnalyzer, make_settings  # noqa: E402


class FakeLLMClient:
    def __init__(self) -> None:
        self.payload = None

    async def chat_completions(self, payload):
        self.payload = payload
        return {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hallo #DATONYM_PERSON_0001#!",
                    },
                    "finish_reason": "stop",
                }
            ],
        }


@pytest.fixture
def client_factory():
    def make_client(findings, default_model="test-model"):
        settings = make_settings()
        settings = settings.__class__(
            llm_base_url=settings.llm_base_url,
            llm_api_key=settings.llm_api_key,
            llm_model_default=default_model,
            analyzer_config=settings.analyzer_config,
            language=settings.language,
            score_threshold=settings.score_threshold,
            request_timeout_seconds=settings.request_timeout_seconds,
        )
        service = DatonymService(settings, analyzer=FakeAnalyzer(findings))
        llm = FakeLLMClient()
        app = create_app(service=service, llm_client=llm, settings=settings)
        return TestClient(app), llm

    return make_client
