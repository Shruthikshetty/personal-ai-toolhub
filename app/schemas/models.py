"""Pydantic schemas for the /api/models endpoints."""


from pydantic import BaseModel, Field


class ModelParameters(BaseModel):
    """Configuration parameters specific to a model."""

    voices: list[str] | None = Field(
        None, description="Available voices (for TTS models)"
    )
    default_voice: str | None = Field(None, description="Default voice to use")
    sample_rate: int | None = Field(None, description="Audio sample rate in Hz")
    max_text_length: int | None = Field(
        None, description="Maximum input text length"
    )


class ModelInfo(BaseModel):
    """Schema representing a single model entry."""

    id: str = Field(
        ..., description="Unique identifier for the model", examples=["kokoro-tts-v1"]
    )
    name: str = Field(
        ..., description="Human-readable model name", examples=["Kokoro TTS"]
    )
    type: str = Field(
        ..., description="Model type (tts, llm, stt, etc.)", examples=["tts"]
    )
    version: str = Field(..., description="Model version", examples=["1.0"])
    status: str = Field(
        default="available",
        description="Model availability status",
        examples=["available", "downloading", "unavailable"],
    )
    description: str | None = Field(
        None, description="Brief description of the model"
    )
    parameters: ModelParameters | None = Field(
        None, description="Model-specific configuration"
    )


class ModelCreate(BaseModel):
    """Schema for creating a new model entry."""

    id: str = Field(..., description="Unique identifier for the model")
    name: str = Field(..., description="Human-readable model name")
    type: str = Field(..., description="Model type (tts, llm, stt, etc.)")
    version: str = Field(default="1.0", description="Model version")
    status: str = Field(default="available", description="Model availability status")
    description: str | None = Field(
        None, description="Brief description of the model"
    )
    parameters: ModelParameters | None = Field(
        None, description="Model-specific configuration"
    )


class ModelListResponse(BaseModel):
    """Response schema for listing models."""

    data: list[ModelInfo] = Field(..., description="List of available models")
    count: int = Field(..., description="Total number of models")
