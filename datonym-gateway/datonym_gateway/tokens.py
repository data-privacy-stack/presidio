"""Request-local DatOnym token mapping."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

TOKEN_PATTERN = re.compile(r"#DATONYM_([A-Z0-9_]+)_([0-9]{4})#")


class TokenCollisionError(ValueError):
    """Raised when input already contains a DatOnym-looking token."""


class UnknownTokenError(ValueError):
    """Raised when a strict restore sees a token outside the request mapping."""


@dataclass(frozen=True)
class TokenEntry:
    """One reversible request-local token mapping."""

    entity_type: str
    original: str
    token: str


def normalize_entity_type(entity_type: str) -> str:
    """Normalize a Presidio entity type for token rendering."""

    normalized = re.sub(r"[^A-Z0-9]+", "_", entity_type.upper()).strip("_")
    if not normalized:
        raise ValueError("entity_type must contain at least one alphanumeric char")
    return normalized


class DatonymMapping:
    """Holds original values only for one request."""

    def __init__(self) -> None:
        self._by_value: dict[tuple[str, str], TokenEntry] = {}
        self._by_token: dict[str, TokenEntry] = {}
        self._counters: dict[str, int] = {}

    def assert_no_token_collision(self, text: str) -> None:
        """Reject inputs that already contain DatOnym token syntax."""

        match = TOKEN_PATTERN.search(text)
        if match:
            raise TokenCollisionError("Input already contains a DatOnym token.")

    def get_or_create(self, entity_type: str, original: str) -> str:
        """Return a stable token for an entity value within this request."""

        normalized_entity = normalize_entity_type(entity_type)
        key = (normalized_entity, original)
        if key in self._by_value:
            return self._by_value[key].token

        next_index = self._counters.get(normalized_entity, 0) + 1
        self._counters[normalized_entity] = next_index
        token = f"#DATONYM_{normalized_entity}_{next_index:04d}#"
        entry = TokenEntry(normalized_entity, original, token)
        self._by_value[key] = entry
        self._by_token[token] = entry
        return token

    def restore_text(self, text: str, *, strict: bool = False) -> str:
        """Replace known tokens with originals."""

        def replace(match: re.Match[str]) -> str:
            token = match.group(0)
            entry = self._by_token.get(token)
            if entry:
                return entry.original
            if strict:
                raise UnknownTokenError(f"Unknown DatOnym token: {token}")
            return token

        return TOKEN_PATTERN.sub(replace, text)

    def entries(self) -> Iterable[TokenEntry]:
        """Return mapping entries without exposing mutability."""

        return tuple(self._by_token.values())
