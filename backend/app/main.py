from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.api.v1.missions import router as missions_router
from app.api.v1.routes import router
from app.api.v1.sources import router as sources_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.version import SIMULATOR_VERSION

log = logging.getLogger("mission_architect")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title="Mission Architect API",
        version=SIMULATOR_VERSION,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def limit_and_log(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        length = request.headers.get("content-length")
        if length is not None and (
            not length.isdigit() or int(length) > settings.max_request_bytes
        ):
            return JSONResponse({"detail": "Requisição muito grande."}, status_code=413)
        started = time.perf_counter()
        response = await call_next(request)
        log.info(
            "request",
            extra={
                "ctx": {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "ms": round((time.perf_counter() - started) * 1000, 1),
                }
            },
        )
        return response

    @app.exception_handler(ValueError)
    async def value_error(_request: Request, exc: ValueError) -> JSONResponse:
        # Mensagens de ValueError do domínio são escritas para o usuário; não contêm segredos.
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.exception_handler(RuntimeError)
    async def runtime_error(_request: Request, exc: RuntimeError) -> JSONResponse:
        log.exception("runtime_error", exc_info=exc)
        return JSONResponse({"detail": "Falha interna do núcleo de simulação."}, status_code=500)

    app.include_router(router)
    app.include_router(missions_router)
    app.include_router(sources_router)
    return app


app = create_app()
