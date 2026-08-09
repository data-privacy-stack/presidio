"""Tests for the FastAPI anonymizer server."""

import asyncio
import json
from importlib import util
from pathlib import Path
from typing import Any

import pytest


def _load_fastapi_app():
    module_path = Path(__file__).parents[1] / "fastapi_app.py"
    spec = util.spec_from_file_location("presidio_anonymizer_fastapi_app", module_path)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.create_app()


class _Response:
    def __init__(self, status_code: int, body: bytes) -> None:
        self.status_code = status_code
        self.text = body.decode()

    def json(self) -> Any:
        return json.loads(self.text)


def _request(app, method: str, path: str, **request_kwargs) -> _Response:
    body = b""
    headers = []
    if "json" in request_kwargs:
        body = json.dumps(request_kwargs["json"]).encode()
        headers.append((b"content-type", b"application/json"))
    elif "content" in request_kwargs:
        body = request_kwargs["content"].encode()

    messages = []
    request_sent = False

    async def receive():
        nonlocal request_sent
        if request_sent:
            return {"type": "http.disconnect"}
        request_sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    asyncio.run(app(scope, receive, send))
    start = next(
        message for message in messages if message["type"] == "http.response.start"
    )
    response_body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    return _Response(start["status"], response_body)


def test_health_endpoint_returns_service_status():
    """Health endpoint mirrors the existing service status response."""
    app = _load_fastapi_app()

    response = _request(app, "GET", "/health")

    assert response.status_code == 200
    assert response.text == "Presidio Anonymizer service is up"


def test_anonymize_endpoint_returns_engine_response():
    """Anonymize endpoint returns the anonymizer engine JSON response."""
    app = _load_fastapi_app()

    response = _request(
        app,
        "POST",
        "/anonymize",
        json={
            "text": "My name is Jane",
            "analyzer_results": [
                {
                    "start": 11,
                    "end": 15,
                    "score": 0.8,
                    "entity_type": "PERSON",
                }
            ],
            "anonymizers": {
                "DEFAULT": {"type": "replace", "new_value": "<ANONYMIZED>"}
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["text"] == "My name is <ANONYMIZED>"


def test_empty_json_body_returns_flask_compatible_error_shape():
    """Empty JSON requests keep the existing error response shape."""
    app = _load_fastapi_app()

    response = _request(app, "POST", "/anonymize", json={})

    assert response.status_code == 400
    assert response.json() == {"error": "Invalid request json"}


@pytest.mark.parametrize("request_kwargs", [{}, {"content": "not json"}])
def test_invalid_json_body_returns_flask_compatible_error_shape(request_kwargs):
    """Missing and invalid JSON requests keep the existing error response shape."""
    app = _load_fastapi_app()

    response = _request(app, "POST", "/anonymize", **request_kwargs)

    assert response.status_code == 400
    assert response.json() == {"error": "Invalid request json"}


def test_anonymizers_endpoint_returns_supported_operators():
    """Anonymizers endpoint exposes built-in anonymizer operators."""
    app = _load_fastapi_app()

    response = _request(app, "GET", "/anonymizers")

    assert response.status_code == 200
    assert "replace" in response.json()


def test_deanonymize_endpoint_returns_engine_response():
    """Deanonymize endpoint returns the deanonymizer engine JSON response."""
    app = _load_fastapi_app()

    response = _request(
        app,
        "POST",
        "/deanonymize",
        json={
            "text": "My name is Jane",
            "anonymizer_results": [
                {
                    "start": 11,
                    "end": 15,
                    "entity_type": "PERSON",
                    "text": "Jane",
                    "operator": "keep",
                }
            ],
            "deanonymizers": {"DEFAULT": {"type": "deanonymize_keep"}},
        },
    )

    assert response.status_code == 200
    assert response.json()["text"] == "My name is Jane"


def test_deanonymizers_endpoint_returns_supported_operators():
    """Deanonymizers endpoint exposes built-in deanonymizer operators."""
    app = _load_fastapi_app()

    response = _request(app, "GET", "/deanonymizers")

    assert response.status_code == 200
    assert "deanonymize_keep" in response.json()
