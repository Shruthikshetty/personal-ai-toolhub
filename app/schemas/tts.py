"""Pydantic schemas for the /v1/audio/speech endpoint (OpenAI-compatible)."""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class AudioFormat(str, Enum):
    """Supported audio output formats."""
    WAV = "wav"
    MP3 = "mp3"


class TTSRequest(BaseModel):
    """Request schema for text-to-speech synthesis (OpenAI-compatible)."""
    model: str = Field(
        ...,
        description="The TTS model to use (e.g. 'kokoro')",
        examples=["kokoro"],
    )
    input: str = Field(
        ...,
        description="The text to synthesize into speech",
        min_length=1,
        max_length=4096,
        examples=["Hello, welcome to our text-to-speech service."],
    )
    voice: str = Field(
        default="af_heart",
        description="Voice ID to use for synthesis",
        examples=["af_heart", "af_bella", "am_adam"],
    )
    speed: float = Field(
        default=1.0,
        description="Speech speed multiplier (0.25–4.0)",
        ge=0.25,
        le=4.0,
    )
    response_format: AudioFormat = Field(
        default=AudioFormat.WAV,
        description="Output audio format",
    )


class TTSResponse(BaseModel):
    """Response metadata for TTS synthesis (returned in headers alongside audio stream)."""
    message: str = Field(..., description="Status message")
    voice: str = Field(..., description="Voice used for synthesis")
    speed: float = Field(..., description="Speed used for synthesis")
    format: str = Field(..., description="Audio format of the response")
    text_length: int = Field(..., description="Length of the input text")
