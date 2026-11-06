"""
ComfyUI HTTP client — all network calls to ComfyUI in one place.

Handles prompt submission, history polling, and image fetching.
Raises plain Python exceptions (not HTTPException) so it stays
decoupled from FastAPI and usable from tests, CLI, or MCP tools.
"""

import asyncio
import base64
import logging
import os

import httpx

logger = logging.getLogger(__name__)

COMFYUI_SERVER_URL = os.getenv("COMFYUI_SERVER_URL", "http://127.0.0.1:8188")

# How long to wait for a generation before giving up (seconds)
GENERATION_TIMEOUT_SECONDS = 120


class ComfyUIError(Exception):
    """Raised when ComfyUI returns an unexpected response."""


class ComfyUITimeoutError(ComfyUIError):
    """Raised when a generation exceeds GENERATION_TIMEOUT_SECONDS."""


async def submit_prompt(client: httpx.AsyncClient, workflow_api: dict) -> str:
    """
    Submit a workflow prompt to ComfyUI.

    Args:
        client:       An open httpx.AsyncClient.
        workflow_api: Workflow in ComfyUI API format (dict keyed by node id).

    Returns:
        The prompt_id string assigned by ComfyUI.

    Raises:
        ComfyUIError: If ComfyUI rejects the prompt or returns no prompt_id.
    """
    res = await client.post(
        f"{COMFYUI_SERVER_URL}/prompt",
        json={"prompt": workflow_api},
        timeout=10.0,
    )

    if res.status_code != 200:
        detail = _extract_error(res)
        logger.error(f"ComfyUI submit error (status {res.status_code}): {detail}")
        raise ComfyUIError(
            f"ComfyUI rejected prompt (HTTP {res.status_code}): {detail}"
        )

    prompt_id = res.json().get("prompt_id")
    if not prompt_id:
        raise ComfyUIError("ComfyUI returned no prompt_id.")

    return prompt_id


async def poll_until_complete(
    client: httpx.AsyncClient,
    prompt_id: str,
    timeout: int = GENERATION_TIMEOUT_SECONDS,
) -> dict:
    """
    Poll ComfyUI history until the prompt finishes, then return its outputs dict.

    Args:
        client:    An open httpx.AsyncClient.
        prompt_id: The prompt_id returned by submit_prompt().
        timeout:   Max seconds to wait before raising ComfyUITimeoutError.

    Returns:
        The `outputs` dict from the completed history entry.

    Raises:
        ComfyUITimeoutError: If generation takes longer than `timeout` seconds.
        ComfyUIError:        If the history entry has an unexpected shape.
    """
    for _ in range(timeout):
        res = await client.get(
            f"{COMFYUI_SERVER_URL}/history/{prompt_id}",
            timeout=10.0,
        )
        if res.status_code == 200:
            history = res.json()
            if prompt_id in history:
                entry = history[prompt_id]
                if not isinstance(entry, dict):
                    raise ComfyUIError(f"Unexpected history entry type: {type(entry)}")
                return entry.get("outputs", {})

        await asyncio.sleep(1.0)

    raise ComfyUITimeoutError(
        f"Generation timed out after {timeout}s (prompt_id={prompt_id})"
    )


async def fetch_image_as_b64(client: httpx.AsyncClient, img_url: str) -> str | None:
    """
    Fetch an image from ComfyUI's /view endpoint and return it base64-encoded.

    Returns None if the fetch fails (logged as an error, not raised,
    so the caller can still return the URL form as a fallback).
    """
    try:
        res = await client.get(img_url, timeout=10.0)
        if res.status_code == 200:
            return base64.b64encode(res.content).decode("utf-8")
        logger.error(f"Failed to fetch image (HTTP {res.status_code}): {img_url}")
    except (httpx.HTTPError, ValueError) as e:
        logger.error(f"Failed to fetch or encode image: {e}")
    return None


def build_image_url(filename: str, subfolder: str, type_: str) -> str:
    """Build the ComfyUI /view URL for a generated image."""
    return f"{COMFYUI_SERVER_URL}/view?filename={filename}&subfolder={subfolder}&type={type_}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_error(res: httpx.Response) -> str:
    """Try to extract a readable error message from a ComfyUI error response."""
    try:
        import json

        return json.dumps(res.json(), indent=2)
    except (ValueError, KeyError):
        return res.text
