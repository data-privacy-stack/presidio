"""Pydantic models for DatOnym HTTP APIs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    """OpenAI-compatible chat message subset."""

    model_config = ConfigDict(extra="allow")

    role: str
    content: Any


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request subset."""

    model_config = ConfigDict(extra="allow")

    messages: list[ChatMessage]
    model: str | None = None
    stream: bool = False


class AnonymizeRequest(BaseModel):
    """Dry-run anonymization request."""

    text: str = Field(min_length=0)
    language: str | None = None


class EntityFinding(BaseModel):
    """Public metadata about an anonymized entity."""

    entity_type: str
    token: str
    start: int
    end: int
    score: float | None = None


class AnonymizeResponse(BaseModel):
    """Dry-run anonymization response without original values."""

    text: str
    entities: list[EntityFinding]
    token_count: int


class DemoAnonymizeRequest(BaseModel):
    """Local demo anonymization request."""

    text: str = Field(min_length=0)
    language: str | None = None


class DemoMappingEntry(BaseModel):
    """Request-local token mapping shown only in the demo UI."""

    entity_type: str
    token: str
    original: str


class DemoAnonymizeResponse(BaseModel):
    """Local demo response with visible mapping values."""

    text: str
    restored_text: str
    entities: list[EntityFinding]
    mapping: list[DemoMappingEntry]


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["ok"]
    service: Literal["DatOnym"]


JsonDict = dict[str, Any]
