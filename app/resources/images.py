"""Images resource — OpenAI-compatible wrapper for ComfyUI.

Provides an OpenAI-compatible endpoint for image generation
which proxies requests to a ComfyUI generation route.

Routes:
  POST /v1/images/generations  — generate an image from text
"""

import asyncio
import base64
import json
import logging
import os
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

router = APIRouter(prefix="/v1/images", tags=["Images"])

# Module logger: only surface errors
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

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
            model_info = next(
                (
                    m
                    for m in models
                    if m["id"] == request.model and m.get("type") == "image_gen"
                ),
                None,
            )

            if not model_info:
                raise HTTPException(
                    status_code=400,
                    detail=f"Image generation model '{request.model}' not found.",
                )

            workflow_filename = model_info.get("parameters", {}).get("workflow_file")

            if not workflow_filename:
                raise HTTPException(
                    status_code=500,
                    detail=f"Model '{request.model}' is missing 'workflow_file' configuration.",
                )

            # 2. Load the workflow
            workflow_path = Path(__file__).parent.parent / "data" / workflow_filename

            if not workflow_path.exists():
                raise HTTPException(
                    status_code=500,
                    detail=f"Workflow file '{workflow_filename}' not found for model '{request.model}'.",
                )

            with open(workflow_path, "r", encoding="utf-8") as f:
                workflow_data = json.load(f)

            # 3. Prepare workflow for ComfyUI: keep original export format (nodes array)
            # Ensure each node has a `class_type` field (ComfyUI requires this)
            for node in workflow_data.get("nodes", []):
                if "type" in node and "class_type" not in node:
                    node["class_type"] = node["type"]

            # Inject parameters into the nodes in the original array structure
            # Node 7 is the CLIPTextEncode (positive prompt)
            # Node 3 is EmptySD3LatentImage (size and batch)
            # Node 6 is KSampler (seed)
            # Fallback to model defaults if the user didn't supply custom overrides
            req_size = request.size
            model_params = model_info.get("parameters", {})
            if req_size == "1024x1024" and "default_size" in model_params:
                req_size = model_params["default_size"]
            req_n = request.n
            if req_n == 1 and "default_n" in model_params:
                req_n = model_params["default_n"]

            seed = int(time.time() * 1000) % 1000000000000000

            for node in workflow_data.get("nodes", []):
                nid = node.get("id")
                if nid == 7:
                    if "widgets_values" in node and len(node["widgets_values"]) > 0:
                        node["widgets_values"][0] = request.prompt
                    elif (
                        "inputs" in node
                        and isinstance(node["inputs"], dict)
                        and "text" in node["inputs"]
                    ):
                        node["inputs"]["text"] = request.prompt
                elif nid == 3:
                    try:
                        w, h = map(int, req_size.split("x"))
                        if (
                            "widgets_values" in node
                            and len(node["widgets_values"]) >= 3
                        ):
                            node["widgets_values"][0] = w
                            node["widgets_values"][1] = h
                            node["widgets_values"][2] = req_n
                    except Exception as e:
                        logger.error(f"Failed to set size/batch for node 3: {e}")
                elif nid == 6:
                    if "widgets_values" in node and len(node["widgets_values"]) > 0:
                        node["widgets_values"][0] = seed
                        # seed injected; no logging on success

            # 4. Convert export format to ComfyUI API format (dict keyed by node id)
            # Build links map: (target_node_id, target_slot) -> (source_node_id, source_slot)
            links_map = {}
            for link in workflow_data.get("links", []):
                src_node, src_slot, tgt_node, tgt_slot = (
                    link[1],
                    link[2],
                    link[3],
                    link[4],
                )
                links_map[(tgt_node, tgt_slot)] = (src_node, src_slot)

            # Inject the runtime prompt into the CLIPTextEncode node that feeds the KSampler 'positive' input.
            try:
                positive_sources = set()
                for node in workflow_data.get("nodes", []):
                    if node.get("type") == "KSampler":
                        for slot_idx, input_spec in enumerate(
                            node.get("inputs", [])
                            if isinstance(node.get("inputs", []), list)
                            else []
                        ):
                            if input_spec.get("name") == "positive":
                                key = (node.get("id"), slot_idx)
                                if key in links_map:
                                    src_id, _ = links_map[key]
                                    positive_sources.add(src_id)

                if positive_sources:
                    for node in workflow_data.get("nodes", []):
                        if node.get("id") in positive_sources and (
                            node.get("type") == "CLIPTextEncode"
                            or node.get("class_type") == "CLIPTextEncode"
                        ):
                            if (
                                "widgets_values" in node
                                and len(node["widgets_values"]) > 0
                            ):
                                node["widgets_values"][0] = request.prompt
                            elif (
                                "inputs" in node
                                and isinstance(node["inputs"], dict)
                                and "text" in node["inputs"]
                            ):
                                node["inputs"]["text"] = request.prompt
            except Exception:
                # Don't fail generation for prompt injection; log only on errors
                logger.error("Failed to inject runtime prompt into CLIPTextEncode node")

            workflow_api = {}
            for node in workflow_data.get("nodes", []):
                nid = node.get("id")
                # Build inputs dict using links_map and input definitions
                inputs_dict = {}
                for slot_idx, input_spec in enumerate(
                    node.get("inputs", [])
                    if isinstance(node.get("inputs", []), list)
                    else []
                ):
                    name = input_spec.get("name", f"input_{slot_idx}")
                    if (nid, slot_idx) in links_map:
                        src_id, src_slot = links_map[(nid, slot_idx)]
                        inputs_dict[name] = [str(src_id), src_slot]
                # Build node structure expected by ComfyUI API
                node_struct = {
                    "class_type": node.get("class_type") or node.get("type"),
                    "inputs": inputs_dict,
                    "widgets_values": node.get("widgets_values", []),
                }
                # Populate common required inputs from widgets_values for known node types
                wv = node.get("widgets_values", [])
                ctype = node_struct["class_type"]
                try:
                    if ctype == "SaveImage":
                        if (
                            "filename_prefix" not in node_struct["inputs"]
                            and len(wv) > 0
                        ):
                            node_struct["inputs"]["filename_prefix"] = wv[0]
                    elif ctype == "VAELoader":
                        if "vae_name" not in node_struct["inputs"] and len(wv) > 0:
                            node_struct["inputs"]["vae_name"] = wv[0]
                    elif ctype == "EmptySD3LatentImage":
                        if len(wv) >= 3:
                            node_struct["inputs"].setdefault("width", wv[0])
                            node_struct["inputs"].setdefault("height", wv[1])
                            node_struct["inputs"].setdefault("batch_size", wv[2])
                    elif ctype == "CLIPLoader":
                        # widgets_values layout: [model_filename, clip_type?, type?]
                        if len(wv) > 0:
                            node_struct["inputs"].setdefault("clip_name", wv[0])
                        # Prefer the second widget as the 'type' if present (commonly holds the model family)
                        if len(wv) > 1 and isinstance(wv[1], str):
                            node_struct["inputs"].setdefault("type", wv[1])
                        elif len(wv) > 2 and isinstance(wv[2], str):
                            node_struct["inputs"].setdefault("type", wv[2])
                    elif ctype == "UNETLoader":
                        if len(wv) > 0:
                            node_struct["inputs"].setdefault("unet_name", wv[0])
                        # infer exact weight_dtype token from filename when possible
                        if (
                            "weight_dtype" not in node_struct["inputs"]
                            and len(wv) > 0
                            and isinstance(wv[0], str)
                        ):
                            fname = wv[0]
                            if "fp8_e4m3fn" in fname:
                                node_struct["inputs"]["weight_dtype"] = "fp8_e4m3fn"
                            elif "fp8_e5m2" in fname:
                                node_struct["inputs"]["weight_dtype"] = "fp8_e5m2"
                            elif "fp8_e4m3fn_fast" in fname:
                                node_struct["inputs"]["weight_dtype"] = (
                                    "fp8_e4m3fn_fast"
                                )
                            else:
                                node_struct["inputs"]["weight_dtype"] = "default"
                    elif ctype and ctype.startswith("Lora Loader Stack"):
                        # widgets_values pattern: [lora_01, strength_01, lora_02, strength_02, ...]
                        for i in range(0, min(len(wv), 8), 2):
                            idx = (i // 2) + 1
                            node_struct["inputs"].setdefault(f"lora_{idx:02d}", wv[i])
                            if i + 1 < len(wv):
                                node_struct["inputs"].setdefault(
                                    f"strength_{idx:02d}", wv[i + 1]
                                )
                    elif ctype == "CLIPTextEncode":
                        if "text" not in node_struct["inputs"] and len(wv) > 0:
                            node_struct["inputs"]["text"] = wv[0]

                    # Handle common vendor-specific loader variants (case-insensitive)
                    lc = (ctype or "").lower()
                    if "unet" in lc and "gguf" in lc:
                        # UnetLoaderGGUF -> provide unet_name
                        if len(wv) > 0:
                            node_struct["inputs"].setdefault("unet_name", wv[0])
                            # infer weight_dtype from filename when possible
                            if isinstance(wv[0], str):
                                fname = wv[0]
                                if "fp8_e4m3fn" in fname:
                                    node_struct["inputs"].setdefault(
                                        "weight_dtype", "fp8_e4m3fn"
                                    )
                                elif "fp8_e5m2" in fname:
                                    node_struct["inputs"].setdefault(
                                        "weight_dtype", "fp8_e5m2"
                                    )
                                else:
                                    node_struct["inputs"].setdefault(
                                        "weight_dtype", "default"
                                    )

                    if "dualcliploader" in lc or ("dualc" in lc and "clip" in lc):
                        # DualCLIPLoaderGGUF -> map clip names and type
                        if len(wv) > 0:
                            node_struct["inputs"].setdefault("clip_name1", wv[0])
                        if len(wv) > 1:
                            node_struct["inputs"].setdefault("clip_name2", wv[1])
                        if len(wv) > 2 and isinstance(wv[2], str):
                            node_struct["inputs"].setdefault("type", wv[2])

                    if "fluxguidance" in lc or "fluxguidance" == lc:
                        # FluxGuidance expects a 'guidance' input
                        if len(wv) > 0:
                            node_struct["inputs"].setdefault("guidance", wv[0])
                    elif ctype == "ModelSamplingAuraFlow":
                        if "shift" not in node_struct["inputs"] and len(wv) > 0:
                            node_struct["inputs"]["shift"] = wv[0]
                    elif ctype == "KSampler":
                        # widgets_values: [seed, randomize_flag, steps, cfg, scheduler_token, sampler_token, ...]
                        if len(wv) > 0:
                            node_struct["inputs"].setdefault("seed", wv[0])
                        if len(wv) > 2:
                            node_struct["inputs"].setdefault("steps", wv[2])
                        if len(wv) > 3:
                            node_struct["inputs"].setdefault("cfg", wv[3])
                        # Use widget order: put sampler_name from index 4 and scheduler from index 5 (swap if necessary)
                        if len(wv) > 4:
                            node_struct["inputs"].setdefault("sampler_name", wv[4])
                        if len(wv) > 5:
                            node_struct["inputs"].setdefault("scheduler", wv[5])
                        # Provide a safe default for denoise
                        node_struct["inputs"].setdefault("denoise", 1.0)
                except Exception as e:
                    logger.error(
                        f"Failed to map widgets to inputs for node {nid} ({ctype}): {e}"
                    )
                # Include outputs and properties if present
                if "outputs" in node:
                    node_struct["outputs"] = node.get("outputs")
                if "properties" in node:
                    node_struct["properties"] = node.get("properties")

                workflow_api[str(nid)] = node_struct

            prompt_payload = {"prompt": workflow_api}
            # Do not write debug files in production; only send payload to ComfyUI
            submit_res = await client.post(
                f"{COMFYUI_SERVER_URL}/prompt", json=prompt_payload, timeout=10.0
            )

            if submit_res.status_code != 200:
                error_detail = submit_res.text
                try:
                    error_json = submit_res.json()
                    error_detail = json.dumps(error_json, indent=2)
                except:
                    pass
                logger.error(
                    f"ComfyUI submit error (status {submit_res.status_code}): {error_detail}"
                )
                raise HTTPException(
                    status_code=submit_res.status_code,
                    detail=f"ComfyUI submit error: {error_detail}",
                )

            prompt_id = submit_res.json().get("prompt_id")
            if not prompt_id:
                raise HTTPException(
                    status_code=500, detail="No prompt_id returned from ComfyUI."
                )

            # Workflow submitted; no verbose logging

            # 5. Poll ComfyUI History for completion
            max_retries = 120  # 120 seconds timeout (generations can be slow)
            for attempt in range(max_retries):
                hist_res = await client.get(
                    f"{COMFYUI_SERVER_URL}/history/{prompt_id}", timeout=10.0
                )
                if hist_res.status_code == 200:
                    history = hist_res.json()
                    # Do not persist history payloads; only inspect outputs when present

                    if prompt_id in history:
                        # Generation finished
                        hist_entry = history[prompt_id]
                        if not isinstance(hist_entry, dict):
                            logger.error("Unexpected history entry type for prompt_id")
                            raise HTTPException(
                                status_code=500,
                                detail=f"Unexpected history entry type for prompt_id: {type(hist_entry)} (saved last_history_{prompt_id}.json)",
                            )

                        outputs = hist_entry.get("outputs", {})

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
                                    if (
                                        getattr(request, "response_format", "url")
                                        == "b64_json"
                                    ):
                                        # Fetch the image and encode it
                                        try:
                                            img_res = await client.get(
                                                img_url, timeout=10.0
                                            )
                                            if img_res.status_code == 200:
                                                b64_encoded = base64.b64encode(
                                                    img_res.content
                                                ).decode("utf-8")
                                        except Exception as e:
                                            logger.error(
                                                f"Failed to fetch image for b64 encoding: {e}"
                                            )

                                    images_data.append(
                                        ImageGenerationData(
                                            url=img_url
                                            if request.response_format == "url"
                                            else None,
                                            b64_json=b64_encoded,
                                        )
                                    )

                        if not images_data:
                            raise HTTPException(
                                status_code=500,
                                detail="ComfyUI completed but no images were found in output.",
                            )

                        return ImageGenerationResponse(
                            created=int(time.time()), data=images_data
                        )

                await asyncio.sleep(1.0)

            raise HTTPException(
                status_code=504, detail="ComfyUI timeout: Generation took too long."
            )

        except httpx.RequestError as e:
            logger.exception("Failed to communicate with ComfyUI")
            raise HTTPException(
                status_code=503, detail=f"Failed to communicate with ComfyUI: {e!s}"
            )
        except HTTPException:
            # Let FastAPI handle explicit HTTPExceptions
            raise
        except Exception as e:
            # Log full traceback so the root cause is visible in logs
            logger.exception("Image generation failed")
            raise HTTPException(
                status_code=500, detail=f"Image generation failed: {e!s}"
            )
