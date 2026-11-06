"""TTS resource — Kokoro text-to-speech endpoint.

Provides an OpenAI-compatible endpoint for text-to-speech synthesis
using the Kokoro TTS model.

Routes:
  POST /v1/audio/speech  — synthesize speech from text
  GET  /v1/audio/voices  — list available voices
"""

import io

import numpy as np
import soundfile as sf
import torch
from fastapi import APIRouter, HTTPException, Response
from kokoro import KPipeline

from app.schemas.tts import TTSRequest

router = APIRouter(prefix="/v1/audio", tags=["Audio"])

# Supported voices (must match models.json config)
SUPPORTED_VOICES = [
    "af_heart",
    "af_bella",
    "af_nicole",
    "af_sarah",
    "af_sky",
    "am_adam",
    "am_michael",
    "bf_emma",
    "bf_isabella",
    "bm_george",
    "bm_lewis",
]

# Global pipeline instance (Lazy-loaded)
_PIPELINE = None


def get_pipeline():
    """Returns a singleton instance of the Kokoro pipeline."""
    global _PIPELINE
    if _PIPELINE is None:
        try:
            # Determine device: use CUDA if available, otherwise CPU
            device = "cuda" if torch.cuda.is_available() else "cpu"
            # Initialize the pipeline for American English ('a')
            _PIPELINE = KPipeline(lang_code="a", device=device)
        except Exception as e:
            # This might happen if espeak-ng is not installed or path is wrong
            raise HTTPException(
                status_code=503,
                detail=f"Failed to initialize TTS model. Ensure espeak-ng is installed. Error: {e!s}",
            )
    return _PIPELINE


@router.post(
    "/speech",
    summary="Create speech",
    description=(
        "Converts input text to speech audio using the Kokoro TTS model. "
        "Supports multiple voices and adjustable speed. "
        "Returns audio in the requested format (WAV or MP3). "
        "OpenAI-compatible: `POST /v1/audio/speech`."
    ),
    responses={
        200: {
            "description": "Audio stream of the synthesized speech",
            "content": {
                "audio/wav": {
                    "schema": {"type": "string", "format": "binary"},
                }
            },
        },
        400: {"description": "Invalid request parameters"},
        422: {"description": "Validation error"},
        503: {"description": "TTS model is not available or failed to load"},
    },
)
async def synthesize_speech(request: TTSRequest):
    """
    Generate speech audio from the provided text (OpenAI-compatible).

    - **model**: TTS model to use (e.g. `kokoro`)
    - **input**: The text to convert to speech (1–4096 characters)
    - **voice**: Voice ID to use (default: `af_heart`)
    - **speed**: Speed multiplier, 0.25–4.0 (default: 1.0)
    - **response_format**: Output audio format — currently only WAV is supported
    """

    # Validate voice
    if request.voice not in SUPPORTED_VOICES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Voice '{request.voice}' is not supported",
                "supported_voices": SUPPORTED_VOICES,
            },
        )

    # Get the pipeline (lazy-loaded singleton)
    pipeline = get_pipeline()

    try:
        # Generate speech segments (using OpenAI-spec field: `input`)
        generator = pipeline(request.input, voice=request.voice, speed=request.speed)

        audio_segments = []
        for _, _, audio in generator:
            audio_segments.append(audio)

        if not audio_segments:
            raise HTTPException(status_code=500, detail="No audio was generated.")

        # Concatenate audio segments
        full_audio = np.concatenate(audio_segments)

        # Write audio to buffer in WAV format
        buffer = io.BytesIO()
        sf.write(buffer, full_audio, 24000, format="WAV")
        buffer.seek(0)

        # Return the audio stream
        return Response(
            content=buffer.getvalue(),
            media_type="audio/wav",
            headers={
                "Content-Disposition": 'attachment; filename="speech.wav"',
                "X-Generated-Text-Length": str(len(request.input)),
                "X-Generated-Voice": request.voice,
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {e!s}")


@router.get(
    "/voices",
    summary="List available voices",
    description="Returns a list of all supported voice IDs for the Kokoro TTS model. Route: GET /v1/audio/voices.",
)
def list_voices():
    """Get all available TTS voices."""
    return {
        "voices": SUPPORTED_VOICES,
        "default": "af_heart",
        "count": len(SUPPORTED_VOICES),
    }
