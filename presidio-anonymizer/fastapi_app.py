"""FastAPI REST API server for anonymizer."""

import json
import logging
import os
from logging.config import fileConfig
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from presidio_anonymizer import AnonymizerEngine, DeanonymizeEngine
from presidio_anonymizer.entities import InvalidParamError
from presidio_anonymizer.services.app_entities_convertor import AppEntitiesConvertor
from starlette.concurrency import run_in_threadpool

DEFAULT_PORT = "3000"

LOGGING_CONF_FILE = "logging.ini"

WELCOME_MESSAGE = r"""
 _______  _______  _______  _______ _________ ______  _________ _______
(  ____ )(  ____ )(  ____ \(  ____ \\__   __/(  __  \ \__   __/(  ___  )
| (    )|| (    )|| (    \/| (    \/   ) (   | (  \  )   ) (   | (   ) |
| (____)|| (____)|| (__    | (_____    | |   | |   ) |   | |   | |   | |
|  _____)|     __)|  __)   (_____  )   | |   | |   | |   | |   | |   | |
| (      | (\ (   | (            ) |   | |   | |   ) |   | |   | |   | |
| )      | ) \ \__| (____/\/\____) |___) (___| (__/  )___) (___| (___) |
|/       |/   \__/(_______/\_______)\_______/(______/ \_______/(_______)
"""


class Server:
    """FastAPI server for anonymizer."""

    def __init__(self) -> None:
        fileConfig(Path(Path(__file__).parent, LOGGING_CONF_FILE))
        self.logger = logging.getLogger("presidio-anonymizer")
        self.logger.setLevel(os.environ.get("LOG_LEVEL", self.logger.level))
        self.app = FastAPI(title="Presidio Anonymizer")
        self.logger.info("Starting anonymizer engine")
        self.anonymizer = AnonymizerEngine()
        self.deanonymize = DeanonymizeEngine()
        self.logger.info(WELCOME_MESSAGE)
        self._add_routes()
        self._add_error_handlers()

    def _add_routes(self) -> None:
        @self.app.get("/health", response_class=Response)
        def health() -> str:
            """Return basic health probe result."""
            return "Presidio Anonymizer service is up"

        @self.app.post("/anonymize")
        async def anonymize(request: Request) -> Response:
            content = await self._json_request_body(request)

            anonymizers_config = AppEntitiesConvertor.operators_config_from_json(
                content.get("anonymizers")
            )
            if AppEntitiesConvertor.check_custom_operator(anonymizers_config):
                raise HTTPException(
                    status_code=400, detail="Custom type anonymizer is not supported"
                )

            analyzer_results = AppEntitiesConvertor.analyzer_results_from_json(
                content.get("analyzer_results")
            )
            anonymizer_result = await run_in_threadpool(
                self.anonymizer.anonymize,
                text=content.get("text", ""),
                analyzer_results=analyzer_results,
                operators=anonymizers_config,
            )
            return Response(
                content=anonymizer_result.to_json(), media_type="application/json"
            )

        @self.app.post("/deanonymize")
        async def deanonymize(request: Request) -> Response:
            content = await self._json_request_body(request)

            deanonymize_entities = AppEntitiesConvertor.deanonymize_entities_from_json(
                content
            )
            deanonymize_config = AppEntitiesConvertor.operators_config_from_json(
                content.get("deanonymizers")
            )
            deanonymized_response = await run_in_threadpool(
                self.deanonymize.deanonymize,
                text=content.get("text", ""),
                entities=deanonymize_entities,
                operators=deanonymize_config,
            )
            return Response(
                content=deanonymized_response.to_json(),
                media_type="application/json",
            )

        @self.app.get("/anonymizers")
        def anonymizers() -> list[str]:
            """Return a list of supported anonymizers."""
            return self.anonymizer.get_anonymizers()

        @self.app.get("/deanonymizers")
        def deanonymizers() -> list[str]:
            """Return a list of supported deanonymizers."""
            return self.deanonymize.get_deanonymizers()

    async def _json_request_body(self, request: Request) -> dict[str, Any]:
        try:
            content = await request.json()
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid request json")

        if not content or not isinstance(content, dict):
            raise HTTPException(status_code=400, detail="Invalid request json")
        return content

    def _add_error_handlers(self) -> None:
        @self.app.exception_handler(InvalidParamError)
        def invalid_param(_: Request, err: InvalidParamError) -> JSONResponse:
            self.logger.warning(
                "Request failed with parameter validation error: %s", err.err_msg
            )
            return JSONResponse({"error": err.err_msg}, status_code=422)

        @self.app.exception_handler(HTTPException)
        def http_exception(_: Request, err: HTTPException) -> JSONResponse:
            return JSONResponse({"error": err.detail}, status_code=err.status_code)

        @self.app.exception_handler(Exception)
        def server_error(_: Request, err: Exception) -> JSONResponse:
            self.logger.exception("A fatal error occurred during execution")
            return JSONResponse({"error": "Internal server error"}, status_code=500)


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    server = Server()
    return server.app


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", DEFAULT_PORT))
    uvicorn.run(create_app(), host="0.0.0.0", port=port)
