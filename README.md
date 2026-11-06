# Personal AI ToolHub

A modular personal AI toolkit and personal tools aggregator providing unified access to AI models, workflows, and utilities across **REST API**, **CLI**, and **Model Context Protocol (MCP)** interfaces.

---

## 1. Architecture: "One Core, Multiple Interfaces"

The project separates core business logic from consumer interfaces:

```
                      ┌──────────────────────────────────────────────┐
                      │              External AI Agents              │
                      │         (Antigravity, Cursor, Claude)        │
                      └──────────────┬───────────────────────────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           │ Stdio                   │ Network (SSE)           │ Terminal
           ▼                         ▼                         ▼
   ┌───────────────┐         ┌───────────────┐         ┌───────────────┐
   │ Stdio MCP     │         │   FastAPI     │         │  Typer CLI    │
   │ python -m ... │         │ /mcp/hello/sse│         │  toolhub ...  │
   └───────┬───────┘         └───────┬───────┘         └───────┬───────┘
           │                         │                         │
           └─────────────────────────┼─────────────────────────┘
                                     │ Calls internally
                                     ▼
                      ┌───────────────────────────────┐
                      │          Core Logic           │
                      │            (core/)            │
                      │  - Pure, framework-agnostic   │
                      │  - TTS, ComfyUI, Search, etc. │
                      └───────────────────────────────┘
```

- **`core/`**: Pure Python business logic with zero framework dependencies (no FastAPI, no Typer, no MCP).
- **`app/resources/`**: OpenAI-compatible REST API endpoints.
- **`app/cli.py`**: Command-line interface powered by Typer (`toolhub <command>`).
- **`app/mcp/`**: Model Context Protocol servers powered by FastMCP (stdio & SSE streaming).

---

## 2. Directory Layout

```text
custom-ai-api/
├── core/                         # 🧠 Core Services (Pure Python, framework-agnostic)
│   ├── __init__.py
│   ├── hello.py                  # Core reference implementation (say_hello)
│   ├── comfyui.py                # ComfyUI HTTP client (submit, poll, view)
│   └── workflow.py               # ComfyUI workflow loader & parameter injector
│
├── app/                          # 🌐 Web & API Application
│   ├── __init__.py               # FastAPI factory, router mounting & MCP SSE mounts
│   ├── cli.py                    # Typer CLI commands implementation
│   ├── mcp/                      # FastMCP server modules
│   │   ├── __init__.py
│   │   └── hello.py              # HelloService MCP tool
│   ├── resources/                # OpenAI-compatible API routes (/v1/audio, /v1/images, etc.)
│   │   └── __init__.py
│   ├── schemas/                  # Pydantic validation schemas
│   │   └── __init__.py
│   └── data/                     # ComfyUI workflows and model registry
│
├── plans/                        # 📐 Architecture & Roadmap specifications
│   ├── mcp_cli_skills_architecture.md
│   └── model_management_and_download.md
│
├── .env.example                  # Environment variable reference
├── .env                          # Local environment settings (git-ignored)
├── .gitignore
├── toolhub.bat                   # Direct Windows CLI launcher
├── setup.py                      # Package metadata and `toolhub` console script registration
├── requirements.txt              # Project dependencies
├── run.py                        # Entry point for the FastAPI server
├── start.bat                     # Windows startup script
└── start.sh                      # Linux production script
```

---

## 3. Getting Started

### Prerequisites

- Python 3.10+
- [`espeak-ng`](https://github.com/espeak-ng/espeak-ng) installed and on your `PATH` (required by Kokoro for phonemization)
- Virtual environment (recommended)

### Installation

1. **Create and activate a virtual environment:**

   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS / Linux
   source venv/bin/activate
   ```

2. **Install project and dependencies (editable mode):**

   ```bash
   pip install -e .
   ```

3. **Configure environment:**

   Copy `.env.example` to `.env` and adjust settings as needed:
   ```bash
   cp .env.example .env
   ```

4. **Run the server:**

   ```bash
   python run.py
   ```

---

## 4. Interfaces & Usage

### Interface 1: Command Line Interface (`toolhub`)

The CLI is built with **Typer**, providing automatic argument validation and help documentation.

- **Display help:**
  ```bash
  toolhub --help
  ```
- **Execute greeting:**
  ```bash
  toolhub hello Alice
  ```
- **Check version:**
  ```bash
  toolhub version
  ```

*(You can also invoke directly via `python -m app.cli <command>` or `.\toolhub.bat <command>` without activating the virtual environment).*

---

### Interface 2: Model Context Protocol (MCP)

Provides tools for AI agents (Cursor, Claude Desktop, Antigravity).

#### A. Interactive MCP Inspector (Schema & Testing UI)
To visually inspect schemas, argument types, and test MCP tools live in the browser:

```bash
fastmcp dev inspector app/mcp/hello.py:mcp
```

#### B. Direct Terminal Stdio Execution
You can test the MCP server directly via stdio in your terminal:

```bash
python -m app.mcp.hello
```

#### C. Desktop Agents Configuration (Claude / Cursor / Antigravity)
Add to your Claude Desktop / Cursor / Antigravity MCP configuration settings:

```json
{
  "mcpServers": {
    "toolhub-hello": {
      "command": "python",
      "args": ["-m", "app.mcp.hello"]
    }
  }
}
```

#### D. Network Streaming (SSE)
Mounted into the main FastAPI server at:
- **SSE Stream:** `http://localhost:8080/mcp/hello/sse`

---

### Interface 3: REST API (FastAPI)

All routes follow the [OpenAI API specification](https://platform.openai.com/docs/api-reference) where applicable.

| Documentation | URL |
| :--- | :--- |
| **Base URL** | `http://localhost:8080` |
| **Swagger UI** | `http://localhost:8080/docs` |
| **ReDoc** | `http://localhost:8080/redoc` |
| **OpenAPI JSON** | `http://localhost:8080/openapi.json` |

#### Health

| Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Health check endpoint |

#### Models Registry

| Method | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/v1/models` | List all registered local models |
| `GET` | `/v1/models/{model_id}` | Retrieve details for a specific model |
| `POST` | `/v1/models` | Register a new model |
| `DELETE` | `/v1/models/{model_id}` | Remove a model from registry |

#### Audio (Kokoro TTS)

| Method | Route | Description |
| :--- | :--- | :--- |
| `POST` | `/v1/audio/speech` | Synthesize speech from text (Kokoro model) |
| `GET` | `/v1/audio/voices` | List all available voices |

**Example — Create Speech:**

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

**Supported voices:** `af_heart`, `af_bella`, `af_nicole`, `af_sarah`, `af_sky`, `am_adam`, `am_michael`, `bf_emma`, `bf_isabella`, `bm_george`, `bm_lewis`

#### Images (ComfyUI Wrapper)

| Method | Route | Description |
| :--- | :--- | :--- |
| `POST` | `/v1/images/generations` | OpenAI-compatible text-to-image proxy to ComfyUI |

**Example — Generate Image:**

```bash
curl http://localhost:8080/v1/images/generations \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A futuristic city in cyberpunk neon style",
    "size": "1024x1024",
    "response_format": "url"
  }'
```

#### Web Search

| Method | Route | Description |
| :--- | :--- | :--- |
| `POST` | `/v1/search` | Web search powered by DuckDuckGo |

#### MCP Streaming Endpoints

| Protocol | Route | Description |
| :--- | :--- | :--- |
| `GET` | `/mcp/hello/sse` | FastMCP Server-Sent Events stream for AI agents |

---

## 5. Development & Formatting

Make sure your virtual environment is activated before running development tools:

- **Format code:**
  ```bash
  ruff format .
  ```
- **Lint and auto-fix:**
  ```bash
  ruff check --fix .
  ```

---

## 6. Key Dependencies

| Package | Purpose |
| :--- | :--- |
| `fastapi` | REST web framework |
| `uvicorn` | ASGI web server |
| `fastmcp` (4.x) | Model Context Protocol (MCP) server & inspector |
| `typer` | Modern CLI development framework |
| `pydantic` / `pydantic-settings` | Data validation and settings management |
| `python-dotenv` | Automatic `.env` environment file loader |
| `kokoro` | TTS synthesis pipeline |
| `soundfile` / `numpy` | Audio processing |
| `ruff` | Linter and formatter (development) |

---

## 7. Architecture Plans & Specs

Detailed design blueprints and implementation roadmaps are stored in the `plans/` directory:

- [MCP, CLI & Agent Skills Architecture](plans/mcp_cli_skills_architecture.md) — Comprehensive guide on the 4-layer design pattern, how core services bridge to FastMCP, Typer, REST, and Antigravity skills.
- [Model Management & Download Lifecycle](plans/model_management_and_download.md) — Architecture plan for registering, downloading, and tracking local AI models (Kokoro, ComfyUI checkpoints, GGUFs) with background job status.

