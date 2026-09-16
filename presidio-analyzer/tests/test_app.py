# ruff: noqa: D103,E501
"""Tests for the analyzer REST API server."""

from unittest.mock import MagicMock, patch

import pytest
from app import create_app


@pytest.fixture(scope="module")
def client():
    with (
        patch("app.AnalyzerEngineProvider") as provider,
        patch("app.BatchAnalyzerEngine") as batch_engine_cls,
    ):
        engine = MagicMock()
        engine.get_supported_entities.return_value = ["PERSON", "IBAN_CODE"]
        provider.return_value.create_engine.return_value = engine

        batch_engine_cls.return_value.analyze_iterator.return_value = iter([[]])

        app = create_app()
        app.testing = True
        yield app.test_client(), engine, batch_engine_cls


def test_given_supported_entities_then_return_200(client):
    test_client, _, _ = client
    response = test_client.post(
        "/analyze",
        json={
            "text": "John Smith",
            "language": "en",
            "entities": ["PERSON"],
        },
    )

    assert response.status_code == 200


def test_given_unsupported_entity_then_return_400(client):
    test_client, engine, batch_engine_cls = client

    def raise_unsupported_error(*args, **kwargs):
        raise ValueError(
            "No matching recognizers were found to serve the request. "
            "The following entities are not supported in language 'en': "
            "['UNSUPPORTED_ENTITY']."
        )

    engine.get_supported_entities.return_value = ["PERSON", "IBAN_CODE"]
    batch_engine_cls.return_value.analyze_iterator.side_effect = raise_unsupported_error

    response = test_client.post(
        "/analyze",
        json={
            "text": "John Smith",
            "language": "en",
            "entities": ["PERSON", "UNSUPPORTED_ENTITY"],
        },
    )

    assert response.status_code == 400
    assert "UNSUPPORTED_ENTITY" in response.get_data(as_text=True)
