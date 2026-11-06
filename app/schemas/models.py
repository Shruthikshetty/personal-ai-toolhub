"""Pydantic schemas for the /v1/models endpoints."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TTSModelParameters(BaseModel):
    """Configuration parameters specific to Text-to-Speech (TTS) models."""

    model_config = ConfigDict(extra="allow")

    voices: list[str] | None = Field(
        None, description="Available voices supported by the TTS model"
    )
    default_voice: str | None = Field(
        None, description="Default voice ID to use for synthesis"
    )
    sample_rate: int | None = Field(
        None, description="Audio output sample rate in Hz (e.g. 24000)"
    )
    max_text_length: int | None = Field(
        None, description="Maximum character length of input text per request"
    )


class ImageGenModelParameters(BaseModel):
    """Configuration parameters specific to Image Generation models (e.g. ComfyUI workflows)."""

    model_config = ConfigDict(extra="allow")

    default_n: int | None = Field(
        1, description="Default number of images to generate (batch size)"
    )
    default_size: str | None = Field(
        "1024x1024", description="Default image dimensions in WIDTHxHEIGHT format"
    )
    workflow_file: str | None = Field(
        None, description="Filename of the ComfyUI workflow JSON stored in app/data/"
    )


# Model parameters can be TTS-specific, ImageGen-specific, or generic key-value pairs
ModelParameters = TTSModelParameters | ImageGenModelParameters | dict[str, Any]


class ModelInfo(BaseModel):
    """Schema representing a single registered model entry."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(
        ...,
        description="Unique identifier for the model",
        examples=["kokoro-tts-v1", "Flux-Dev-image"],
    )
    name: str = Field(
        ...,
        description="Human-readable model name",
        examples=["Kokoro TTS", "Flux Dev Image"],
    )
    type: str = Field(
        ...,
        description="Model modality/type (tts, image_gen, llm, stt, etc.)",
        examples=["tts", "image_gen"],
    )
    version: str = Field(
        default="1.0",
        description="Model version string",
        examples=["1.0"],
    )
    status: str = Field(
        default="available",
        description="Model availability status",
        examples=["available", "downloading", "unavailable"],
    )
    description: str | None = Field(
        None,
        description="Brief description of the model and its capabilities",
    )
    parameters: ModelParameters | None = Field(
        None,
        description="Model-specific configuration parameters",
    )


class ModelCreate(BaseModel):
    """Schema for registering a new model entry."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Unique identifier for the model")
    name: str = Field(..., description="Human-readable model name")
    type: str = Field(..., description="Model type (tts, image_gen, llm, stt, etc.)")
    version: str = Field(default="1.0", description="Model version")
    status: str = Field(default="available", description="Model availability status")
    description: str | None = Field(None, description="Brief description of the model")
    parameters: ModelParameters | None = Field(
        None, description="Model-specific configuration"
    )


class ModelListResponse(BaseModel):
    """Response schema for listing models."""

    data: list[ModelInfo] = Field(..., description="List of available models")
    count: int = Field(..., description="Total number of models")
