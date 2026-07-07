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


def test_demo_page_is_served(client_factory):
    client, _llm = client_factory([])

    response = client.get("/demo")

    assert response.status_code == 200
    assert "DatOnym" in response.text
    assert "/demo/assets/app.js" in response.text


def test_demo_anonymize_endpoint_returns_visible_mapping(client_factory):
    client, _llm = client_factory(
        [("Max Mustermann", "PERSON"), ("max@example.de", "EMAIL_ADDRESS")]
    )

    response = client.post(
        "/demo/anonymize",
        json={"text": "Max Mustermann schreibt an max@example.de."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["text"] == (
        "#DATONYM_PERSON_0001# schreibt an #DATONYM_EMAIL_ADDRESS_0001#."
    )
    assert payload["restored_text"] == "Max Mustermann schreibt an max@example.de."
    assert payload["mapping"] == [
        {
            "entity_type": "PERSON",
            "token": "#DATONYM_PERSON_0001#",
            "original": "Max Mustermann",
        },
        {
            "entity_type": "EMAIL_ADDRESS",
            "token": "#DATONYM_EMAIL_ADDRESS_0001#",
            "original": "max@example.de",
        },
    ]


def test_chat_completion_requires_model_when_no_default(client_factory):
    client, _llm = client_factory([], default_model=None)

    response = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "Hallo"}]},
    )

    assert response.status_code == 400
    assert "model" in response.json()["detail"].lower()
