"""TTS resource — Kokoro text-to-speech endpoint.

Provides an OpenAPI-documented endpoint for text-to-speech synthesis
using the Kokoro TTS model. Currently returns placeholder audio until
the Kokoro model is integrated.
"""

import io
import numpy as np
import soundfile as sf
from fastapi import APIRouter, HTTPException, Response
from kokoro import KPipeline

from app.schemas.tts import TTSRequest


router = APIRouter(prefix="/api/tts", tags=["Text-to-Speech"])

# Supported voices (must match models.json config)
SUPPORTED_VOICES = [
    "af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky",
    "am_adam", "am_michael",
    "bf_emma", "bf_isabella",
    "bm_george", "bm_lewis",
]

# Global pipeline instance (Lazy-loaded)
_PIPELINE = None


def get_pipeline():
    """Returns a singleton instance of the Kokoro pipeline."""
    global _PIPELINE
    if _PIPELINE is None:
        try:
            # Initialize the pipeline for American English ('a')
            _PIPELINE = KPipeline(lang_code='a')
        except Exception as e:
            # This might happen if espeak-ng is not installed or path is wrong
            raise HTTPException(
                status_code=503,
                detail=f"Failed to initialize TTS model. Ensure espeak-ng is installed. Error: {str(e)}"
            )
    return _PIPELINE


@router.post(
    "",
    summary="Synthesize speech from text",
    description=(
        "Converts input text to speech audio using the Kokoro TTS model. "
        "Supports multiple voices and adjustable speed. "
        "Returns audio in the requested format (WAV or MP3)."
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
    Generate speech audio from the provided text.

    - **text**: The text to convert to speech (1-5000 characters)
    - **voice**: Voice ID to use (default: af_heart)
    - **speed**: Speed multiplier, 0.25 to 4.0 (default: 1.0)
    - **format**: Output audio format — currently only WAV is supported in this implementation
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

    # Get the pipeline
    pipeline = get_pipeline()

    try:
        # Generate speech segments
        generator = pipeline(request.text, voice=request.voice, speed=request.speed)
        
        audio_segments = []
        for _, _, audio in generator:
            audio_segments.append(audio)

        if not audio_segments:
            raise HTTPException(status_code=500, detail="No audio was generated.")

        # Concatenate audio segments
        full_audio = np.concatenate(audio_segments)

        # Write audio to buffer in WAV format
        buffer = io.BytesIO()
        sf.write(buffer, full_audio, 24000, format='WAV')
        buffer.seek(0)

        # Return the audio stream
        return Response(
            content=buffer.getvalue(),
            media_type="audio/wav",
            headers={
                "Content-Disposition": f'attachment; filename="speech.wav"',
                "X-Generated-Text-Length": str(len(request.text)),
                "X-Generated-Voice": request.voice,
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")


@router.get(
    "/voices",
    summary="List available voices",
    description="Returns a list of all supported voice IDs for the Kokoro TTS model.",
)
def list_voices():
    """Get all available TTS voices."""
    return {
        "voices": SUPPORTED_VOICES,
        "default": "af_heart",
        "count": len(SUPPORTED_VOICES),
    }
