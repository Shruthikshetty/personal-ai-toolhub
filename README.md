# Custom AI API

A local backend for running AI models, designed to be **OpenAI API-compatible**.

## Getting Started

### Prerequisites

- Python 3.10+
- [`espeak-ng`](https://github.com/espeak-ng/espeak-ng) installed and on your `PATH` (required by Kokoro for phonemization)
- Virtual environment (recommended)

### Installation

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS / Linux
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the server:
   ```bash
   python run.py
   ```

## Documentation & Access

| | URL |
|---|---|
| **Base URL** | http://localhost:8080 |
| **Swagger UI** | http://localhost:8080/docs |
| **ReDoc** | http://localhost:8080/redoc |
| **OpenAPI JSON** | http://localhost:8080/openapi.json |

## API Routes

All routes follow the [OpenAI API specification](https://platform.openai.com/docs/api-reference).

### Health

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | Health check |

### Models

| Method | Route | Description |
|---|---|---|
| `GET` | `/v1/models` | List all registered models |
| `GET` | `/v1/models/{model_id}` | Get a specific model by ID |
| `POST` | `/v1/models` | Register a new model |
| `DELETE` | `/v1/models/{model_id}` | Remove a model |

### Audio (TTS)

| Method | Route | Description |
|---|---|---|
| `POST` | `/v1/audio/speech` | Synthesize speech from text (Kokoro) |
| `GET` | `/v1/audio/voices` | List available voices |

#### Example — Create Speech

```bash
curl http://localhost:8080/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kokoro",
    "input": "Hello, world!",
    "voice": "af_heart",
    "speed": 1.0,
    "response_format": "wav"
  }' \
  --output speech.wav
```

Available voices: `af_heart`, `af_bella`, `af_nicole`, `af_sarah`, `af_sky`, `am_adam`, `am_michael`, `bf_emma`, `bf_isabella`, `bm_george`, `bm_lewis`

## Dependencies

| Package | Purpose |
|---|---|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `pydantic` | Request/response validation |
| `kokoro` | TTS model (Kokoro pipeline) |
| `soundfile` | Audio encoding (WAV output) |
| `numpy` | Audio buffer processing |
| `espeak-ng` *(system)* | Phonemization backend for Kokoro |
