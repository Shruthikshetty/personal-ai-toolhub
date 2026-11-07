"""Web Search resource — Search functionality for AI agents.

Provides an endpoint to perform web searches using DuckDuckGo.
Designed to be used as a 'tool' by AI models.

Delegates core search logic to core/duckduckgo.py and core/search.py.
"""

from fastapi import APIRouter, HTTPException

from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from core.duckduckgo import DuckDuckGoSearch
from core.search import (
    SearchError,
    SearchNetworkError,
    SearchServiceError,
)

router = APIRouter(prefix="/v1/tools", tags=["Tools"])
_search_engine = DuckDuckGoSearch()


@router.post(
    "/web_search",
    response_model=SearchResponse,
    summary="Perform a web search",
    description=(
        "Searches the web for the given query using DuckDuckGo directly and returns "
        "a list of relevant results including titles, URLs, and snippets."
    ),
)
async def web_search(request: SearchRequest):
    """
    Perform a web search by querying DuckDuckGo HTML directly.
    """
    try:
        results = await _search_engine.search(
            query=request.query,
            max_results=request.max_results,
        )
        return SearchResponse(
            results=[
                SearchResult(
                    title=r.title,
                    url=r.url,
                    snippet=r.snippet,
                )
                for r in results
            ],
            query=request.query,
        )
    except SearchNetworkError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Search service unavailable: {e!s}",
        )
    except SearchServiceError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search service error: {e!s}",
        )
    except SearchError as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e!s}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected search failure: {e!s}")


# This endpoint provides the JSON schema for the tool,
# which can be passed directly to OpenAI's tool calling API.
@router.get(
    "/web_search/schema",
    summary="Get tool schema",
    description="Returns the OpenAI-compatible tool definition for the web search tool.",
)
async def get_search_tool_schema():
    return {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for real-time information, news, and facts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Optional: maximum number of results to return (default is 5).",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    }
