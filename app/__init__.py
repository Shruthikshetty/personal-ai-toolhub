"""
FastAPI application factory.

Creates and configures the FastAPI app instance with OpenAPI metadata
and registers all API routers.
"""

import logging
import time

from dotenv import load_dotenv

# Configure logging: keep normal operation quiet, only surface warnings/errors
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
for _n in ("httpx", "uvicorn", "asyncio", "fastapi", "urllib3", "watchfiles"):
    logging.getLogger(_n).setLevel(logging.WARNING)


def create_app():
    """Create and configure the FastAPI application."""
    # Load .env and all heavy imports only when the server is actually starting
    load_dotenv()

    from fastapi import FastAPI, Request

    from app.mcp.hello import mcp as hello_mcp
    from app.mcp.search import mcp as search_mcp
    from app.resources.images import router as images_router
    from app.resources.models import router as models_router
    from app.resources.search import router as search_router
    from app.resources.tts import router as tts_router

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
        """
        Only log requests/responses when an error occurs.

        Keeps normal operation quiet while preserving error details.
        """
        start_time = time.time()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                f"Unhandled exception while handling {request.method} {request.url.path}"
            )
            raise

        # Log only when status indicates error (4xx/5xx)
        if response.status_code >= 400:
            elapsed = time.time() - start_time
            try:
                body = await request.body()
                body_snip = body[:1000] if body else None
            except Exception:
                body_snip = None

            logger.error(
                "HTTP error %s %s %s (%.2fs)\nRequest body: %s",
                response.status_code,
                request.method,
                request.url.path,
                elapsed,
                repr(body_snip),
            )

        return response

    # Register routers
    app.include_router(models_router)
    app.include_router(tts_router)
    app.include_router(images_router)
    app.include_router(search_router)

    # Register all MCP servers for AI agents (Streamable HTTP & SSE)
    app.mount("/mcp/hello", hello_mcp.http_app(path="/", transport="http"))
    app.mount("/mcp/search", search_mcp.http_app(path="/", transport="http"))

    # Health check endpoint
    @app.get("/", tags=["Health"])
    def health_check():
        """Health check endpoint."""
        return {"status": "ok", "service": "custom-ai-api", "version": "0.1.0"}

    return app
