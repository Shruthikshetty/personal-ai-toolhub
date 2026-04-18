"""Images resource — OpenAI-compatible wrapper for ComfyUI.

Provides an OpenAI-compatible endpoint for image generation
which proxies requests to a ComfyUI generation route.

Routes:
  POST /v1/images/generations  — generate an image from text
"""

import os
import time
import json
import asyncio
import base64
import httpx
from pathlib import Path
from fastapi import APIRouter, HTTPException

from app.schemas.images import ImageGenerationRequest, ImageGenerationResponse, ImageGenerationData
from app.resources.models import _read_models

router = APIRouter(prefix="/v1/images", tags=["Images"])

# Configuration for ComfyUI
COMFYUI_SERVER_URL = os.getenv("COMFYUI_SERVER_URL", "http://127.0.0.1:8188")

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
        500: {"description": "Image generation failed"},
    },
)
async def create_image(request: ImageGenerationRequest):
    """
    Generate an image based on a text prompt (OpenAI-compatible) using ComfyUI.
    """
    async with httpx.AsyncClient() as client:
        try:
            # 1. Resolve requested model
            models = _read_models()
            model_info = next((m for m in models if m["id"] == request.model and m.get("type") == "image_gen"), None)
            
            if not model_info:
                raise HTTPException(status_code=400, detail=f"Image generation model '{request.model}' not found.")
                
            workflow_filename = model_info.get("parameters", {}).get("workflow_file")
            
            if not workflow_filename:
                raise HTTPException(status_code=500, detail=f"Model '{request.model}' is missing 'workflow_file' configuration.")
            
            # 2. Load the workflow
            workflow_path = Path(__file__).parent.parent / "data" / workflow_filename
            
            if not workflow_path.exists():
                raise HTTPException(status_code=500, detail=f"Workflow file '{workflow_filename}' not found for model '{request.model}'.")
                
            with open(workflow_path, "r", encoding="utf-8") as f:
                workflow = json.load(f)

            # 3. Inject parameters into the workflow
            # Z-Image-Turbo-LoRA.json has two parallel workflows for some reason.
            # Nodes 7 and 27 are the Positive Prompts.
            # Nodes 3 and 22 are EmptySD3LatentImage (size and batch)
            # Nodes 6 and 18 are KSampler (seed)
            for node_id in ["7", "27"]:
                if node_id in workflow and "inputs" in workflow[node_id] and "text" in workflow[node_id]["inputs"]:
                    workflow[node_id]["inputs"]["text"] = request.prompt
            
            # Fallback to model defaults if the user didn't supply custom overrides
            # (Pydantic defaults to 1024x1024 and n=1 if they are omitted from the request body)
            req_size = request.size
            model_params = model_info.get("parameters", {})
            
            if req_size == "1024x1024" and "default_size" in model_params:
                req_size = model_params["default_size"]
                
            req_n = request.n
            if req_n == 1 and "default_n" in model_params:
                req_n = model_params["default_n"]

            for node_id in ["3", "22"]:
                if node_id in workflow and "inputs" in workflow[node_id]:
                    try:
                        w, h = map(int, req_size.split("x"))
                        workflow[node_id]["inputs"]["width"] = w
                        workflow[node_id]["inputs"]["height"] = h
                        workflow[node_id]["inputs"]["batch_size"] = req_n
                    except ValueError:
                        pass
            
            # Use same seed for both KSamplers, or random
            seed = int(time.time() * 1000) % 1000000000000000
            for node_id in ["6", "18"]:
                if node_id in workflow and "inputs" in workflow[node_id]:
                    workflow[node_id]["inputs"]["seed"] = seed

            # 4. Submit workflow to ComfyUI
            prompt_payload = {"prompt": workflow}
            submit_res = await client.post(f"{COMFYUI_SERVER_URL}/prompt", json=prompt_payload, timeout=10.0)
            
            if submit_res.status_code != 200:
                raise HTTPException(status_code=submit_res.status_code, detail=f"ComfyUI submit error: {submit_res.text}")
                
            prompt_id = submit_res.json().get("prompt_id")
            if not prompt_id:
                raise HTTPException(status_code=500, detail="No prompt_id returned from ComfyUI.")

            # 5. Poll ComfyUI History for completion
            max_retries = 120 # 120 seconds timeout (generations can be slow)
            for _ in range(max_retries):
                hist_res = await client.get(f"{COMFYUI_SERVER_URL}/history/{prompt_id}", timeout=10.0)
                if hist_res.status_code == 200:
                    history = hist_res.json()
                    if prompt_id in history:
                        # Generation finished!
                        outputs = history[prompt_id].get("outputs", {})
                        
                        images_data = []
                        # 6. Extract image references from nodes (usually SaveImage)
                        for node_id, node_output in outputs.items():
                            if "images" in node_output:
                                for img in node_output["images"]:
                                    filename = img.get("filename")
                                    subfolder = img.get("subfolder", "")
                                    type_ = img.get("type", "output")
                                    
                                    # Construct URL to view the image
                                    img_url = f"{COMFYUI_SERVER_URL}/view?filename={filename}&subfolder={subfolder}&type={type_}"
                                    
                                    b64_encoded = None
                                    if getattr(request, "response_format", "url") == "b64_json":
                                        # Fetch the image and encode it
                                        try:
                                            img_res = await client.get(img_url, timeout=10.0)
                                            if img_res.status_code == 200:
                                                b64_encoded = base64.b64encode(img_res.content).decode("utf-8")
                                        except Exception as e:
                                            print(f"Failed to fetch image for b64 encoding: {e}")

                                    # OpenAI spec: if b64_json is requested, url should typically be omitted/optional, but pydantic schema handles both.
                                    images_data.append(ImageGenerationData(
                                        url=img_url if request.response_format == "url" else None,
                                        b64_json=b64_encoded
                                    ))
                                    
                        if not images_data:
                            raise HTTPException(status_code=500, detail="ComfyUI completed but no images were found in output.")

                        return ImageGenerationResponse(
                            created=int(time.time()),
                            data=images_data
                        )
                
                await asyncio.sleep(1.0)
            
            raise HTTPException(status_code=504, detail="ComfyUI timeout: Generation took too long.")

        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Failed to communicate with ComfyUI: {str(e)}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")
