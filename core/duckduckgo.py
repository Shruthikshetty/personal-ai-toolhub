"""
DuckDuckGo search provider implementation.

Performs web searches by querying DuckDuckGo HTML directly and parsing
results without external API keys. Pure Python, decoupled from web frameworks.
"""

import httpx
from bs4 import BeautifulSoup

from core.search import (
    BaseSearchEngine,
    SearchNetworkError,
    SearchParsingError,
    SearchResult,
    SearchServiceError,
)

DEFAULT_DUCKDUCKGO_URL = "https://html.duckduckgo.com/html/"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT_SECONDS = 10.0


class DuckDuckGoSearch(BaseSearchEngine):
    """DuckDuckGo web search provider using direct HTML scraping."""

    def __init__(
        self,
        url: str = DEFAULT_DUCKDUCKGO_URL,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.url = url
        self.user_agent = user_agent
        self.timeout = timeout

    async def search(
        self,
        query: str,
        max_results: int = 5,
        client: httpx.AsyncClient | None = None,
    ) -> list[SearchResult]:
        """
        Execute search query on DuckDuckGo HTML and extract results.

        Args:
            query: The search keywords or phrase.
            max_results: Maximum number of results to retrieve.
            client: Optional httpx.AsyncClient instance for connection pooling.

        Returns:
            A list of SearchResult objects.
        """
        data = {"q": query}
        headers = {"User-Agent": self.user_agent}

        try:
            if client is not None:
                res = await client.post(
                    self.url, data=data, headers=headers, timeout=self.timeout
                )
            else:
                async with httpx.AsyncClient() as session:
                    res = await session.post(
                        self.url, data=data, headers=headers, timeout=self.timeout
                    )
        except httpx.RequestError as e:
            raise SearchNetworkError(f"Search service unavailable: {e!s}") from e

        if res.status_code != 200:
            raise SearchServiceError(f"DuckDuckGo returned status {res.status_code}")

        try:
            soup = BeautifulSoup(res.text, "html.parser")
            results: list[SearchResult] = []

            for el in soup.find_all("div", class_="result"):
                title_el = el.find("a", class_="result__a")
                snippet_el = el.find(class_="result__snippet")

                if title_el and snippet_el:
                    title = title_el.get_text(strip=True)
                    url = title_el.get("href", "")
                    snippet = snippet_el.get_text(strip=True)

                    if title and url:
                        results.append(
                            SearchResult(
                                title=title,
                                url=url,
                                snippet=snippet,
                            )
                        )

                if len(results) >= max_results:
                    break

            return results
        except Exception as e:
            raise SearchParsingError(f"Failed to parse search results: {e!s}") from e


async def web_search_duck_duck_go(
    query: str,
    max_results: int = 5,
    client: httpx.AsyncClient | None = None,
) -> list[SearchResult]:
    """
    Convenience function to perform a DuckDuckGo search.

    Args:
        query: Search keywords or query.
        max_results: Maximum results to return.
        client: Optional httpx.AsyncClient instance.

    Returns:
        List of SearchResult objects.
    """
    engine = DuckDuckGoSearch()
    return await engine.search(query=query, max_results=max_results, client=client)
