"""Pydantic schemas for the /v1/images/generations endpoint (OpenAI-compatible)."""

from enum import Enum

from pydantic import BaseModel, Field


class ImageResponseFormat(str, Enum):
    """Supported output formats for generated images."""

    URL = "url"
    B64_JSON = "b64_json"


class ImageGenerationRequest(BaseModel):
    """Request schema for image generation (OpenAI-compatible)."""

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="A text description of the desired image(s).",
        examples=["A serene landscape with mountains and a lake at sunset"],
    )
    model: str = Field(
        default="comfyui",
        description="The model ID to use for image generation.",
        examples=["flux-dev", "z-image-turbo"],
    )
    n: int = Field(
        default=1,
        ge=1,
        le=10,
        description="The number of images to generate (must be between 1 and 10).",
        examples=[1],
    )
    size: str = Field(
        default="1024x1024",
        pattern=r"^\d+x\d+$",
        description="The size of the generated images in WIDTHxHEIGHT format.",
        examples=["1024x1024", "512x512", "768x1024"],
    )
    response_format: ImageResponseFormat = Field(
        default=ImageResponseFormat.URL,
        description="The format in which the generated images are returned.",
        examples=[ImageResponseFormat.URL],
    )
    user: str | None = Field(
        default=None,
        description="A unique identifier representing your end-user for monitoring.",
    )


class ImageGenerationData(BaseModel):
    """Data object containing a single generated image result."""

    url: str | None = Field(
        default=None,
        description="URL where the generated image can be viewed or downloaded.",
    )
    b64_json: str | None = Field(
        default=None,
        description="The base64-encoded string of the generated image if requested as b64_json.",
    )
    revised_prompt: str | None = Field(
        default=None,
        description="The prompt that was actually used to generate the image, if revised.",
    )


class ImageGenerationResponse(BaseModel):
    """Response schema for the image generation endpoint."""

    created: int = Field(
        ...,
        description="Unix timestamp (in seconds) of when the image generation completed.",
    )
    data: list[ImageGenerationData] = Field(
        ...,
        description="List of generated image objects.",
    )
