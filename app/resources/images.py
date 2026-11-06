"""Images resource — OpenAI-compatible wrapper for ComfyUI.

Provides an OpenAI-compatible endpoint for image generation
which proxies requests to a local ComfyUI instance.

Routes:
  POST /v1/images/generations  — generate an image from text

All workflow manipulation lives in core/workflow.py.
All ComfyUI HTTP calls live in core/comfyui.py.
This file is only the FastAPI route layer.
"""

import logging
import time
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException

from app.resources.models import _read_models
from app.schemas.images import (
    ImageGenerationData,
    ImageGenerationRequest,
    ImageGenerationResponse,
)
from core.comfyui import (
    ComfyUIError,
    ComfyUITimeoutError,
    build_image_url,
    fetch_image_as_b64,
    poll_until_complete,
    submit_prompt,
)
from core.workflow import convert_to_api_format, inject_parameters, load_workflow

router = APIRouter(prefix="/v1/images", tags=["Images"])

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


@router.post(
    "/generations",
    response_model=ImageGenerationResponse,
    summary="Create image",
    description=(
        "Converts a text prompt to an image by forwarding the request to "
        "ComfyUI and polling for the result. OpenAI-compatible."
    ),
    responses={
        200: {"description": "Successfully generated image(s)"},
        400: {"description": "Invalid request parameters"},
        503: {"description": "ComfyUI is unreachable"},
        504: {"description": "Generation timed out"},
        500: {"description": "Image generation failed"},
    },
)
async def create_image(request: ImageGenerationRequest):
    """Generate an image based on a text prompt (OpenAI-compatible) using ComfyUI."""
    try:
        # 1. Resolve model from registry
        model_info = _resolve_model(request.model)
        model_params = model_info.get("parameters", {})

        # 2. Apply model-level defaults for size and batch
        size = request.size
        if size == "1024x1024" and "default_size" in model_params:
            size = model_params["default_size"]

        n = request.n
        if n == 1 and "default_n" in model_params:
            n = model_params["default_n"]

        # 3. Load and prepare the workflow
        workflow_path = _resolve_workflow_path(request.model, model_params)
        workflow_data = load_workflow(workflow_path)
        inject_parameters(workflow_data, prompt=request.prompt, size=size, n=n)
        workflow_api = convert_to_api_format(workflow_data)

        # 4. Submit and poll ComfyUI
        async with httpx.AsyncClient() as client:
            prompt_id = await submit_prompt(client, workflow_api)
            outputs = await poll_until_complete(client, prompt_id)

            # 5. Collect generated images
            images_data = await _collect_images(client, outputs, request)

        if not images_data:
            raise HTTPException(
                status_code=500,
                detail="ComfyUI completed but no images were found in output.",
            )

        return ImageGenerationResponse(created=int(time.time()), data=images_data)

    except httpx.RequestError as e:
        logger.exception("Failed to communicate with ComfyUI")
        raise HTTPException(
            status_code=503, detail=f"ComfyUI is unreachable: {e!s}"
        )
    except ComfyUITimeoutError as e:
        raise HTTPException(status_code=504, detail=str(e))
    except ComfyUIError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Image generation failed")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {e!s}")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _resolve_model(model_id: str) -> dict:
    """Look up the model in the registry; raise 400 if not found."""
    models = _read_models()
    model_info = next(
        (m for m in models if m["id"] == model_id and m.get("type") == "image_gen"),
        None,
    )
    if not model_info:
        raise HTTPException(
            status_code=400,
            detail=f"Image generation model '{model_id}' not found.",
        )
    return model_info


def _resolve_workflow_path(model_id: str, model_params: dict) -> Path:
    """Resolve and validate the workflow file path for a model."""
    workflow_filename = model_params.get("workflow_file")
    if not workflow_filename:
        raise HTTPException(
            status_code=500,
            detail=f"Model '{model_id}' is missing 'workflow_file' configuration.",
        )
    workflow_path = Path(__file__).parent.parent / "data" / workflow_filename
    if not workflow_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Workflow file '{workflow_filename}' not found for model '{model_id}'.",
        )
    return workflow_path


async def _collect_images(
    client: httpx.AsyncClient,
    outputs: dict,
    request: ImageGenerationRequest,
) -> list[ImageGenerationData]:
    """Extract image data from ComfyUI outputs and return a list of ImageGenerationData."""
    images_data: list[ImageGenerationData] = []
    want_b64 = getattr(request, "response_format", "url") == "b64_json"

    for node_output in outputs.values():
        for img in node_output.get("images", []):
            img_url = build_image_url(
                filename=img.get("filename"),
                subfolder=img.get("subfolder", ""),
                type_=img.get("type", "output"),
            )
            b64 = await fetch_image_as_b64(client, img_url) if want_b64 else None
            images_data.append(
                ImageGenerationData(
                    url=img_url if not want_b64 else None,
                    b64_json=b64,
                )
            )

    return images_data
