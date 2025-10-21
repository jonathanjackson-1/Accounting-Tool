"""FastAPI application factory for the accounting agents backend."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router as api_router
from .config import get_settings


def create_app() -> FastAPI:
    """Application factory used by uvicorn."""
    settings = get_settings()
    app = FastAPI(
        title="Accounting Agents Backend",
        version="0.1.0",
        description="Staging backend skeleton providing upload and agent orchestration endpoints.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allow_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        """Basic health probe endpoint."""
        return {"status": "ok", "environment": settings.environment}

    return app


app = create_app()
