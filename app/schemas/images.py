from typing import Optional, List
from pydantic import BaseModel, Field


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., description="A text description of the desired image(s).")
    model: Optional[str] = Field("comfyui", description="The model to use for image generation.")
    n: Optional[int] = Field(1, description="The number of images to generate. Must be between 1 and 10.")
    size: Optional[str] = Field("1024x1024", description="The size of the generated images.")
    response_format: Optional[str] = Field(
        "url", description="The format in which the generated images are returned. Must be one of url or b64_json."
    )
    user: Optional[str] = Field(None, description="A unique identifier representing your end-user.")


class ImageGenerationData(BaseModel):
    url: Optional[str] = None
    b64_json: Optional[str] = None
    revised_prompt: Optional[str] = None


class ImageGenerationResponse(BaseModel):
    created: int
    data: List[ImageGenerationData]
