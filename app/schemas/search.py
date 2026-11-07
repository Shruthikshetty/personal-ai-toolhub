from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., description="The search query to perform.")
    max_results: int = Field(
        default=5, description="Maximum number of search results to return."
    )
    fetch_content: bool = Field(
        default=True,
        description="Whether to fetch and extract readable article text from destination pages.",
    )


class SearchResult(BaseModel):
    title: str = Field(..., description="The title of the search result.")
    url: str = Field(..., description="The direct URL of the destination page.")
    snippet: str = Field(..., description="The brief preview snippet from search.")
    content: str | None = Field(
        default=None,
        description="Extracted readable text from the destination webpage, if fetched.",
    )


class SearchResponse(BaseModel):
    results: list[SearchResult]
    query: str
