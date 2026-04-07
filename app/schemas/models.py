"""Pydantic schemas for the /api/models endpoints."""

from pydantic import BaseModel, Field
from typing import Optional


class ModelParameters(BaseModel):
    """Configuration parameters specific to a model."""
    voices: Optional[list[str]] = Field(None, description="Available voices (for TTS models)")
    default_voice: Optional[str] = Field(None, description="Default voice to use")
    sample_rate: Optional[int] = Field(None, description="Audio sample rate in Hz")
    max_text_length: Optional[int] = Field(None, description="Maximum input text length")


class ModelInfo(BaseModel):
    """Schema representing a single model entry."""
    id: str = Field(..., description="Unique identifier for the model", examples=["kokoro-tts-v1"])
    name: str = Field(..., description="Human-readable model name", examples=["Kokoro TTS"])
    type: str = Field(..., description="Model type (tts, llm, stt, etc.)", examples=["tts"])
    version: str = Field(..., description="Model version", examples=["1.0"])
    status: str = Field(
        default="available",
        description="Model availability status",
        examples=["available", "downloading", "unavailable"],
    )
    description: Optional[str] = Field(None, description="Brief description of the model")
    parameters: Optional[ModelParameters] = Field(None, description="Model-specific configuration")


class ModelCreate(BaseModel):
    """Schema for creating a new model entry."""
    id: str = Field(..., description="Unique identifier for the model")
    name: str = Field(..., description="Human-readable model name")
    type: str = Field(..., description="Model type (tts, llm, stt, etc.)")
    version: str = Field(default="1.0", description="Model version")
    status: str = Field(default="available", description="Model availability status")
    description: Optional[str] = Field(None, description="Brief description of the model")
    parameters: Optional[ModelParameters] = Field(None, description="Model-specific configuration")


class ModelListResponse(BaseModel):
    """Response schema for listing models."""
    data: list[ModelInfo] = Field(..., description="List of available models")
    count: int = Field(..., description="Total number of models")
