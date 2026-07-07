from __future__ import annotations

def test_healthz(client_factory):
    client, _llm = client_factory([])

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "DatOnym"}


def test_chat_completion_masks_upstream_and_restores_response(client_factory):
    client, llm = client_factory([("Max Mustermann", "PERSON")])

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "test-model",
            "messages": [
                {
                    "role": "user",
                    "content": "Schreibe eine Begruessung fuer Max Mustermann.",
                }
            ],
        },
    )

    assert response.status_code == 200
    assert "Max Mustermann" not in llm.payload["messages"][0]["content"]
    assert "#DATONYM_PERSON_0001#" in llm.payload["messages"][0]["content"]
    assert response.json()["choices"][0]["message"]["content"] == (
        "Hallo Max Mustermann!"
    )


def test_chat_completion_rejects_streaming(client_factory):
    client, _llm = client_factory([])

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "test-model",
            "stream": True,
            "messages": [{"role": "user", "content": "Hallo"}],
        },
    )

    assert response.status_code == 400
    assert "streaming" in response.json()["detail"].lower()


def test_anonymize_endpoint_does_not_return_original_values(client_factory):
    client, _llm = client_factory(
        [("Max Mustermann", "PERSON"), ("max@example.de", "EMAIL_ADDRESS")]
    )

    response = client.post(
        "/v1/anonymize",
        json={"text": "Max Mustermann schreibt an max@example.de."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "Max Mustermann" not in str(payload)
    assert "max@example.de" not in str(payload)
    assert payload["token_count"] == 2


def test_chat_completion_requires_model_when_no_default(client_factory):
    client, _llm = client_factory([], default_model=None)

    response = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "Hallo"}]},
    )

    assert response.status_code == 400
    assert "model" in response.json()["detail"].lower()
