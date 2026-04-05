"""TTS resource — Kokoro text-to-speech endpoint.

Provides an OpenAPI-documented endpoint for text-to-speech synthesis
using the Kokoro TTS model. Currently returns placeholder audio until
the Kokoro model is integrated.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.schemas.tts import TTSRequest, TTSResponse


router = APIRouter(prefix="/api/tts", tags=["Text-to-Speech"])

# Supported voices (must match models.json config)
SUPPORTED_VOICES = [
    "af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky",
    "am_adam", "am_michael",
    "bf_emma", "bf_isabella",
    "bm_george", "bm_lewis",
]


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
                },
                "audio/mpeg": {
                    "schema": {"type": "string", "format": "binary"},
                },
            },
        },
        400: {"description": "Invalid request parameters"},
        422: {"description": "Validation error"},
        503: {"description": "TTS model is not available"},
    },
)
async def synthesize_speech(request: TTSRequest):
    """
    Generate speech audio from the provided text.

    - **text**: The text to convert to speech (1-5000 characters)
    - **voice**: Voice ID to use (default: af_heart)
    - **speed**: Speed multiplier, 0.25 to 4.0 (default: 1.0)
    - **format**: Output audio format — wav or mp3 (default: wav)
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

    # --- TODO: Replace with actual Kokoro TTS inference ---
    # from kokoro import KPipeline
    # pipeline = KPipeline(lang_code='a')
    # generator = pipeline(request.text, voice=request.voice, speed=request.speed)
    # for i, (gs, ps, audio) in enumerate(generator):
    #     ... combine audio chunks ...
    # -------------------------------------------------------

    # Placeholder: return metadata until Kokoro is integrated
    # When integrated, this will return a StreamingResponse with audio bytes
    return TTSResponse(
        message="TTS endpoint ready — Kokoro model integration pending",
        voice=request.voice,
        speed=request.speed,
        format=request.format.value,
        text_length=len(request.text),
    )


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
