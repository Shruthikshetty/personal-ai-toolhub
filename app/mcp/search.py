from fastmcp import FastMCP

from core.search import search

# create a mcp instance
mcp = FastMCP("SearchService")


@mcp.tool()
async def web_search(
    query: str,
    max_results: int = 5,
):
    """performs web search and return the result in
    model readable  format
    """
    results = await search(
        query=query, max_results=max_results, fetch_content=True, provider="duckduckgo"
    )

    return results


# Allows running directly via stdio: python -m app.mcp.search
if __name__ == "__main__":
    mcp.run(transport="stdio")
