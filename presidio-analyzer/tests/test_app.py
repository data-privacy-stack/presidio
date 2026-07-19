# ruff: noqa: D103

from types import SimpleNamespace
from unittest.mock import Mock, patch

from app import Server, _get_supported_languages


def test_get_supported_languages_from_environment(monkeypatch):
    monkeypatch.setenv("SUPPORTED_LANGUAGES", " en, es ,it ")

    assert _get_supported_languages() == ["en", "es", "it"]


def test_get_supported_languages_is_unset(monkeypatch):
    monkeypatch.delenv("SUPPORTED_LANGUAGES", raising=False)

    assert _get_supported_languages() is None


def test_server_passes_supported_languages_to_provider(monkeypatch):
    monkeypatch.setenv("SUPPORTED_LANGUAGES", "en,es,it")
    provider = Mock()
    provider.return_value.create_engine.return_value = SimpleNamespace()

    with (
        patch("app.AnalyzerEngineProvider", provider),
        patch("app.BatchAnalyzerEngine"),
    ):
        Server()

    assert provider.call_args.kwargs["supported_languages"] == ["en", "es", "it"]


def test_supported_entities_uses_configured_language(monkeypatch):
    monkeypatch.setenv("SUPPORTED_LANGUAGES", "en,es")
    engine = Mock()
    engine.get_supported_entities.return_value = ["ES_NIF"]
    provider = Mock()
    provider.return_value.create_engine.return_value = engine

    with (
        patch("app.AnalyzerEngineProvider", provider),
        patch("app.BatchAnalyzerEngine"),
    ):
        client = Server().app.test_client()
        response = client.get("/supportedentities?language=es")

    assert response.status_code == 200
    assert response.get_json() == ["ES_NIF"]
    engine.get_supported_entities.assert_called_once_with("es")
