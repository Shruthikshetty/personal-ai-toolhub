"""Entry point for the Custom AI API server."""

import uvicorn

from app import create_app

# Create the FastAPI app
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "run:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
    )
