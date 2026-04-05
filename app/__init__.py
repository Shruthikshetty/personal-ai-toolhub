"""FastAPI application factory.

Creates and configures the FastAPI app instance with OpenAPI metadata
and registers all API routers.
"""

from fastapi import FastAPI

from app.resources.models import router as models_router
from app.resources.tts import router as tts_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Custom AI API",
        description=(
            "A local backend for running AI models with wrapper services.\n\n"
            "## Features\n"
            "- **Models Registry** — manage and query available local models\n"
            "- **Text-to-Speech** — Kokoro TTS synthesis with multiple voices\n\n"
            "More model types (LLM, STT, etc.) coming soon."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Register routers
    app.include_router(models_router)
    app.include_router(tts_router)

    @app.get("/", tags=["Health"])
    def health_check():
        """Health check endpoint."""
        return {"status": "ok", "service": "custom-ai-api", "version": "0.1.0"}

    return app
