"""FastAPI application factory.

Creates and configures the FastAPI app instance with OpenAPI metadata
and registers all API routers.
"""

import logging
from fastapi import FastAPI, Request
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
import time

from app.resources.models import router as models_router
from app.resources.tts import router as tts_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    # Add logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all HTTP requests and responses."""
        start_time = time.time()
        
        # Log request details
        logger.info(f"📥 {request.method} {request.url.path}")
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    logger.info(f"   Body: {body[:500]}")  # First 500 chars
            except Exception:
                pass
        
        # Process request
        response = await call_next(request)
        
        # Log response details
        elapsed = time.time() - start_time
        logger.info(f"📤 {response.status_code} {request.url.path} ({elapsed:.2f}s)")
        
        return response

    # Register routers
    app.include_router(models_router)
    app.include_router(tts_router)

    @app.get("/", tags=["Health"])
    def health_check():
        """Health check endpoint."""
        return {"status": "ok", "service": "custom-ai-api", "version": "0.1.0"}

    return app
