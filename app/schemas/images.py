
from pydantic import BaseModel, Field


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., description="A text description of the desired image(s).")
    model: str | None = Field(
        "comfyui", description="The model to use for image generation."
    )
    n: int | None = Field(
        1, description="The number of images to generate. Must be between 1 and 10."
    )
    size: str | None = Field(
        "1024x1024", description="The size of the generated images."
    )
    response_format: str | None = Field(
        "url",
        description="The format in which the generated images are returned. Must be one of url or b64_json.",
    )
    user: str | None = Field(
        None, description="A unique identifier representing your end-user."
    )


class ImageGenerationData(BaseModel):
    url: str | None = None
    b64_json: str | None = None
    revised_prompt: str | None = None


class ImageGenerationResponse(BaseModel):
    created: int
    data: list[ImageGenerationData]
