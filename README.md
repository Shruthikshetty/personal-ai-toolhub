# Custom AI API

A local backend for running AI models with wrapper services.

## Getting Started

### Prerequisites
- Python 3.8+
- Virtual environment (recommended)

### Installation
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   python run.py
   ```

## Documentation & Access
- **Base URL**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Requirements
- `requirements.txt` was created with direct dependencies for a clean installation.

## Important Notes
The TTS endpoint has the full API contract defined with a placeholder response — the TODO in `app/resources/tts.py` marks exactly where to wire in actual Kokoro inference when you're ready.
