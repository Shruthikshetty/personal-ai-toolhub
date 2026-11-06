"""Models resource — CRUD operations for the model registry.

Reads and writes model data from app/data/models.json.
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.schemas.models import ModelCreate, ModelInfo, ModelListResponse

router = APIRouter(prefix="/v1/models", tags=["Models"])

# Path to the models data file
DATA_FILE = Path(__file__).parent.parent / "data" / "models.json"


def _read_models() -> list[dict]:
    """Read all models from the JSON data file."""
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_models(models: list[dict]) -> None:
    """Write models list back to the JSON data file."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(models, f, indent=2, ensure_ascii=False)


@router.get(
    "",
    response_model=ModelListResponse,
    summary="List all models",
    description="Returns a list of all registered models with their configuration and status.",
)
def list_models():
    models = _read_models()
    return ModelListResponse(
        data=[ModelInfo(**m) for m in models],
        count=len(models),
    )


@router.get(
    "/{model_id}",
    response_model=ModelInfo,
    summary="Get a specific model",
    description="Returns details of a single model by its unique identifier.",
)
def get_model(model_id: str):
    models = _read_models()
    for model in models:
        if model["id"] == model_id:
            return ModelInfo(**model)
    raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")


@router.post(
    "",
    response_model=ModelInfo,
    status_code=201,
    summary="Register a new model",
    description="Adds a new model entry to the registry. The model ID must be unique.",
)
def create_model(model: ModelCreate):
    models = _read_models()

    # Check for duplicate ID
    if any(m["id"] == model.id for m in models):
        raise HTTPException(
            status_code=409,
            detail=f"Model with id '{model.id}' already exists",
        )

    new_model = model.model_dump()
    models.append(new_model)
    _write_models(models)

    return ModelInfo(**new_model)


@router.delete(
    "/{model_id}",
    summary="Remove a model",
    description="Removes a model from the registry by ID.",
)
def delete_model(model_id: str):
    models = _read_models()
    updated = [m for m in models if m["id"] != model_id]

    if len(updated) == len(models):
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    _write_models(updated)
    return {"message": f"Model '{model_id}' removed successfully"}
