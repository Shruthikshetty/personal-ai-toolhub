"""Web Search resource — Search functionality for AI agents.

Provides an endpoint to perform web searches using DuckDuckGo.
Designed to be used as a 'tool' by AI models.
"""

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException

from app.schemas.search import SearchRequest, SearchResponse, SearchResult

router = APIRouter(prefix="/v1/tools", tags=["Tools"])


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
        url = "https://html.duckduckgo.com/html/"
        data = {"q": request.query}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        results = []
        async with httpx.AsyncClient() as client:
            res = await client.post(url, data=data, headers=headers, timeout=10.0)
            if res.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"Search service returned status {res.status_code}",
                )

            soup = BeautifulSoup(res.text, "html.parser")

            for el in soup.find_all("div", class_="result"):
                title_el = el.find("a", class_="result__a")
                snippet_el = el.find("a", class_="result__snippet")

                if title_el and snippet_el:
                    results.append(
                        SearchResult(
                            title=title_el.text.strip(),
                            url=title_el.get("href", ""),
                            snippet=snippet_el.text.strip(),
                        )
                    )

                if len(results) >= request.max_results:
                    break

        return SearchResponse(results=results, query=request.query)
    except httpx.RequestError as e:
        # Network-level failure — DuckDuckGo unreachable, DNS failure, timeout, etc.
        raise HTTPException(
            status_code=503,
            detail=f"Search service unavailable: {e!s}",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e!s}")


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
