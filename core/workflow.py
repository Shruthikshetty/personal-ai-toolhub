"""
ComfyUI workflow utilities — pure data manipulation, no I/O.

Handles loading, parameter injection, and format conversion for
ComfyUI workflow JSON files exported from the ComfyUI UI.

No FastAPI, no HTTP — just workflow data in, workflow data out.
This keeps the logic testable and reusable independently of the API layer.
"""

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# ComfyUI workflow node IDs — these match the exported workflow JSON.
# If you re-export the workflow and nodes are renumbered, update here.
NODE_ID_POSITIVE_PROMPT = 7  # CLIPTextEncode (positive prompt)
NODE_ID_LATENT_IMAGE = 3     # EmptySD3LatentImage (width, height, batch)
NODE_ID_KSAMPLER = 6         # KSampler (seed)


def load_workflow(workflow_path: Path) -> dict:
    """Load a ComfyUI workflow JSON file from disk."""
    with open(workflow_path, encoding="utf-8") as f:
        return json.load(f)


def inject_parameters(
    workflow_data: dict,
    prompt: str,
    size: str,
    n: int,
) -> dict:
    """
    Inject generation parameters into the workflow node array.

    Mutates and returns the workflow dict with:
    - prompt injected into the positive CLIPTextEncode node
    - width/height/batch injected into the EmptySD3LatentImage node
    - a random seed injected into the KSampler node

    Args:
        workflow_data: Raw workflow dict (nodes array format from ComfyUI export).
        prompt:        Text prompt for image generation.
        size:          Image size string, e.g. "1024x1024".
        n:             Number of images to generate (batch size).

    Returns:
        The same workflow_data dict with parameters injected.
    """
    # Ensure each node has a class_type field (ComfyUI requires this)
    for node in workflow_data.get("nodes", []):
        if "type" in node and "class_type" not in node:
            node["class_type"] = node["type"]

    seed = int(time.time() * 1000) % 1_000_000_000_000_000

    for node in workflow_data.get("nodes", []):
        nid = node.get("id")

        if nid == NODE_ID_POSITIVE_PROMPT:
            if "widgets_values" in node and len(node["widgets_values"]) > 0:
                node["widgets_values"][0] = prompt
            elif (
                "inputs" in node
                and isinstance(node["inputs"], dict)
                and "text" in node["inputs"]
            ):
                node["inputs"]["text"] = prompt

        elif nid == NODE_ID_LATENT_IMAGE:
            try:
                w, h = map(int, size.split("x"))
                if "widgets_values" in node and len(node["widgets_values"]) >= 3:
                    node["widgets_values"][0] = w
                    node["widgets_values"][1] = h
                    node["widgets_values"][2] = n
            except (ValueError, IndexError, TypeError) as e:
                logger.error(f"Failed to set size/batch for node {NODE_ID_LATENT_IMAGE}: {e}")

        elif nid == NODE_ID_KSAMPLER and "widgets_values" in node and len(node["widgets_values"]) > 0:
            node["widgets_values"][0] = seed

    # Also inject prompt via graph traversal (handles re-exported workflows
    # where the positive CLIPTextEncode node may have a different ID)
    _inject_prompt_via_links(workflow_data, prompt)

    return workflow_data


def _inject_prompt_via_links(workflow_data: dict, prompt: str) -> None:
    """
    Fallback: inject prompt by tracing KSampler's 'positive' link to its
    source CLIPTextEncode node. Handles cases where the node IDs differ
    from the constants above (e.g. after re-export).
    """
    links_map = _build_links_map(workflow_data)
    try:
        positive_sources: set[int] = set()
        for node in workflow_data.get("nodes", []):
            if node.get("type") == "KSampler":
                inputs = node.get("inputs", [])
                if not isinstance(inputs, list):
                    continue
                for slot_idx, input_spec in enumerate(inputs):
                    if input_spec.get("name") == "positive":
                        key = (node.get("id"), slot_idx)
                        if key in links_map:
                            src_id, _ = links_map[key]
                            positive_sources.add(src_id)

        for node in workflow_data.get("nodes", []):
            if node.get("id") not in positive_sources:
                continue
            if node.get("type") not in ("CLIPTextEncode",) and node.get("class_type") not in ("CLIPTextEncode",):
                continue
            if "widgets_values" in node and len(node["widgets_values"]) > 0:
                node["widgets_values"][0] = prompt
            elif isinstance(node.get("inputs"), dict) and "text" in node["inputs"]:
                node["inputs"]["text"] = prompt

    except (KeyError, TypeError, IndexError):
        logger.error("Failed to inject prompt via link traversal")


def convert_to_api_format(workflow_data: dict) -> dict:
    """
    Convert the ComfyUI UI export format (nodes array) to the ComfyUI
    API prompt format (dict keyed by node id as string).

    The UI exports a `nodes` array; the API expects a flat dict where
    each key is the node id (as a string) and each value contains
    `class_type`, `inputs`, and optionally `outputs`/`properties`.
    """
    links_map = _build_links_map(workflow_data)
    workflow_api: dict[str, dict] = {}

    for node in workflow_data.get("nodes", []):
        nid = node.get("id")

        # Resolve wired inputs from the links map
        inputs_dict: dict = {}
        node_inputs = node.get("inputs", [])
        if isinstance(node_inputs, list):
            for slot_idx, input_spec in enumerate(node_inputs):
                name = input_spec.get("name", f"input_{slot_idx}")
                if (nid, slot_idx) in links_map:
                    src_id, src_slot = links_map[(nid, slot_idx)]
                    inputs_dict[name] = [str(src_id), src_slot]

        wv = node.get("widgets_values", [])
        ctype = node.get("class_type") or node.get("type")

        node_struct: dict = {
            "class_type": ctype,
            "inputs": inputs_dict,
            "widgets_values": wv,
        }

        # Map widgets_values → named inputs for each known node type
        try:
            _map_widgets_to_inputs(node_struct, ctype, wv)
        except (KeyError, IndexError, TypeError, ValueError) as e:
            logger.error(f"Failed to map widgets for node {nid} ({ctype}): {e}")

        if "outputs" in node:
            node_struct["outputs"] = node["outputs"]
        if "properties" in node:
            node_struct["properties"] = node["properties"]

        workflow_api[str(nid)] = node_struct

    return workflow_api


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_links_map(workflow_data: dict) -> dict[tuple, tuple]:
    """
    Build a lookup from (target_node_id, target_slot) → (source_node_id, source_slot)
    using the `links` array in the workflow export.
    """
    links_map: dict[tuple, tuple] = {}
    for link in workflow_data.get("links", []):
        # link format: [link_id, src_node, src_slot, tgt_node, tgt_slot, ...]
        src_node, src_slot, tgt_node, tgt_slot = link[1], link[2], link[3], link[4]
        links_map[(tgt_node, tgt_slot)] = (src_node, src_slot)
    return links_map


def _map_widgets_to_inputs(node_struct: dict, ctype: str | None, wv: list) -> None:
    """
    Populate the `inputs` dict of a node struct from its `widgets_values`
    for all known ComfyUI node types.
    """
    if not ctype:
        return

    lc = ctype.lower()

    if ctype == "SaveImage":
        if "filename_prefix" not in node_struct["inputs"] and wv:
            node_struct["inputs"]["filename_prefix"] = wv[0]

    elif ctype == "VAELoader":
        if "vae_name" not in node_struct["inputs"] and wv:
            node_struct["inputs"]["vae_name"] = wv[0]

    elif ctype == "EmptySD3LatentImage":
        if len(wv) >= 3:
            node_struct["inputs"].setdefault("width", wv[0])
            node_struct["inputs"].setdefault("height", wv[1])
            node_struct["inputs"].setdefault("batch_size", wv[2])

    elif ctype == "CLIPLoader":
        if wv:
            node_struct["inputs"].setdefault("clip_name", wv[0])
        if len(wv) > 1 and isinstance(wv[1], str):
            node_struct["inputs"].setdefault("type", wv[1])
        elif len(wv) > 2 and isinstance(wv[2], str):
            node_struct["inputs"].setdefault("type", wv[2])

    elif ctype == "UNETLoader":
        if wv:
            node_struct["inputs"].setdefault("unet_name", wv[0])
        if wv and isinstance(wv[0], str):
            node_struct["inputs"].setdefault("weight_dtype", _infer_dtype(wv[0]))

    elif ctype and ctype.startswith("Lora Loader Stack"):
        for i in range(0, min(len(wv), 8), 2):
            idx = (i // 2) + 1
            node_struct["inputs"].setdefault(f"lora_{idx:02d}", wv[i])
            if i + 1 < len(wv):
                node_struct["inputs"].setdefault(f"strength_{idx:02d}", wv[i + 1])

    elif ctype == "CLIPTextEncode":
        if "text" not in node_struct["inputs"] and wv:
            node_struct["inputs"]["text"] = wv[0]

    elif ctype == "KSampler":
        # widgets_values: [seed, randomize_flag, steps, cfg, sampler_name, scheduler, ...]
        if len(wv) > 0:
            node_struct["inputs"].setdefault("seed", wv[0])
        if len(wv) > 2:
            node_struct["inputs"].setdefault("steps", wv[2])
        if len(wv) > 3:
            node_struct["inputs"].setdefault("cfg", wv[3])
        if len(wv) > 4:
            node_struct["inputs"].setdefault("sampler_name", wv[4])
        if len(wv) > 5:
            node_struct["inputs"].setdefault("scheduler", wv[5])
        node_struct["inputs"].setdefault("denoise", 1.0)

    elif ctype == "ModelSamplingAuraFlow" and "shift" not in node_struct["inputs"] and wv:
        node_struct["inputs"]["shift"] = wv[0]

    # Vendor-specific GGUF variants (case-insensitive match)
    if "unet" in lc and "gguf" in lc and wv:
        node_struct["inputs"].setdefault("unet_name", wv[0])
        if isinstance(wv[0], str):
            node_struct["inputs"].setdefault("weight_dtype", _infer_dtype(wv[0]))

    if "dualcliploader" in lc or ("dualc" in lc and "clip" in lc):
        if len(wv) > 0:
            node_struct["inputs"].setdefault("clip_name1", wv[0])
        if len(wv) > 1:
            node_struct["inputs"].setdefault("clip_name2", wv[1])
        if len(wv) > 2 and isinstance(wv[2], str):
            node_struct["inputs"].setdefault("type", wv[2])

    if "fluxguidance" in lc and wv:
        node_struct["inputs"].setdefault("guidance", wv[0])


def _infer_dtype(filename: str) -> str:
    """Infer the weight_dtype token from a model filename."""
    if "fp8_e4m3fn_fast" in filename:
        return "fp8_e4m3fn_fast"
    if "fp8_e4m3fn" in filename:
        return "fp8_e4m3fn"
    if "fp8_e5m2" in filename:
        return "fp8_e5m2"
    return "default"

