"""Runtime settings for DatOnym."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    """Configuration loaded from environment variables."""

    llm_base_url: str
    llm_api_key: str | None
    llm_model_default: str | None
    analyzer_config: Path
    language: str
    score_threshold: float
    request_timeout_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        default_config = (
            _repo_root()
            / "presidio-analyzer"
            / "presidio_analyzer"
            / "conf"
            / "datonym_de_analyzer.yaml"
        )
        analyzer_config = Path(
            os.getenv("DATONYM_ANALYZER_CONFIG", str(default_config))
        )
        return cls(
            llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com"),
            llm_api_key=os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"),
            llm_model_default=os.getenv("LLM_MODEL_DEFAULT"),
            analyzer_config=analyzer_config,
            language=os.getenv("DATONYM_LANGUAGE", "de"),
            score_threshold=float(os.getenv("DATONYM_SCORE_THRESHOLD", "0.35")),
            request_timeout_seconds=float(
                os.getenv("DATONYM_REQUEST_TIMEOUT_SECONDS", "60")
            ),
        )
