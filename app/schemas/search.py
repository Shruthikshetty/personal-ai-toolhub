from pydantic import BaseModel, Field
from typing import List, Optional

class SearchRequest(BaseModel):
    query: str = Field(..., description="The search query to perform.")
    max_results: int = Field(default=5, description="Maximum number of search results to return.")

class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str

class SearchResponse(BaseModel):
    results: List[SearchResult]
    query: str
