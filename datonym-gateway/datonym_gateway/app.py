"""FastAPI app for DatOnym."""

from __future__ import annotations

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from datonym_gateway.config import Settings
from datonym_gateway.models import (
    AnonymizeRequest,
    AnonymizeResponse,
    ChatCompletionRequest,
    DemoAnonymizeRequest,
    DemoAnonymizeResponse,
    DemoMappingEntry,
    HealthResponse,
)
from datonym_gateway.service import ChatGateway, DatonymService, LLMClient
from datonym_gateway.tokens import TokenCollisionError

STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app(
    service: DatonymService | None = None,
    llm_client: LLMClient | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """Create a DatOnym FastAPI app."""

    settings = settings or Settings.from_env()
    service = service or DatonymService(settings)
    llm_client = llm_client or LLMClient(settings)
    gateway = ChatGateway(service, llm_client)

    app = FastAPI(title="DatOnym", version="0.1.0")
    app.mount("/demo/assets", StaticFiles(directory=STATIC_DIR), name="demo-assets")

    @app.get("/demo", include_in_schema=False)
    async def demo() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/healthz", response_model=HealthResponse)
    async def healthz() -> HealthResponse:
        return HealthResponse(status="ok", service="DatOnym")

    @app.post("/v1/anonymize", response_model=AnonymizeResponse)
    async def anonymize(request: AnonymizeRequest) -> AnonymizeResponse:
        try:
            result = service.anonymize_text(request.text, language=request.language)
        except TokenCollisionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return AnonymizeResponse(
            text=result.text,
            entities=result.entities,
            token_count=len(list(result.mapping.entries())),
        )

    @app.post("/demo/anonymize", response_model=DemoAnonymizeResponse)
    async def demo_anonymize(request: DemoAnonymizeRequest) -> DemoAnonymizeResponse:
        try:
            result = service.anonymize_text(request.text, language=request.language)
        except TokenCollisionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        entries_by_token = {entry.token: entry for entry in result.mapping.entries()}
        ordered_tokens = []
        for entity in sorted(result.entities, key=lambda item: item.start):
            if entity.token in entries_by_token and entity.token not in ordered_tokens:
                ordered_tokens.append(entity.token)

        mapping = [
            DemoMappingEntry(
                entity_type=entries_by_token[token].entity_type,
                token=entries_by_token[token].token,
                original=entries_by_token[token].original,
            )
            for token in ordered_tokens
        ]
        return DemoAnonymizeResponse(
            text=result.text,
            restored_text=service.restore_text(result.text, result.mapping),
            entities=result.entities,
            mapping=mapping,
        )

    @app.post("/v1/chat/completions")
    async def chat_completions(request: ChatCompletionRequest):
        if request.stream:
            raise HTTPException(
                status_code=400,
                detail="DatOnym MVP does not support streaming responses.",
            )

        payload = request.model_dump(exclude_none=True)
        try:
            return await gateway.chat_completions(payload)
        except TokenCollisionError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except TypeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"LLM provider returned HTTP {exc.response.status_code}.",
            ) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail="LLM provider request failed.",
            ) from exc

    return app


app = create_app()
