# DatOnym Gateway

DatOnym is a German prompt anonymization gateway for LLM calls. It detects
PII with Presidio, replaces values with request-local tokens such as
`#DATONYM_PERSON_0001#`, forwards the anonymized prompt to an OpenAI-compatible
LLM endpoint, and restores known tokens in the answer before returning it.

## Scope

The MVP supports text-only chat completion requests:

- `POST /v1/chat/completions`
- `POST /v1/anonymize`
- `GET /healthz`

Streaming, tool calls, images, files, structured data, and persistent mapping
storage are intentionally out of scope for the first version.

## Local Setup

From the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\python -m pip install -e .\presidio-analyzer -e .\presidio-anonymizer -e .\datonym-gateway[dev]
.\.venv\Scripts\python -m spacy download de_core_news_md
```

Then start the gateway:

```powershell
$env:LLM_BASE_URL = "https://api.openai.com"
$env:LLM_API_KEY = "..."
$env:LLM_MODEL_DEFAULT = "gpt-4.1-mini"
.\.venv\Scripts\python -m uvicorn datonym_gateway.app:app --app-dir .\datonym-gateway --host 127.0.0.1 --port 8080
```

## Privacy Defaults

Original values are kept only in memory for the duration of a request. The
gateway does not persist mappings and does not include original values in logs
or error responses.
