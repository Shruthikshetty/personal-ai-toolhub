"""
DuckDuckGo search provider implementation.

Performs web searches by querying DuckDuckGo HTML directly and parsing
results without external API keys. Optionally fetches and extracts clean
readable text from the result pages for richer AI context.
"""

import asyncio
import urllib.parse

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
DEFAULT_PAGE_FETCH_TIMEOUT_SECONDS = 4.0
DEFAULT_MAX_CONTENT_CHARS = 1200


def _clean_url(raw_url: str) -> str:
    """Extract direct target URL from DuckDuckGo redirect link."""
    if "uddg=" in raw_url:
        parsed = urllib.parse.urlparse(raw_url)
        qs = urllib.parse.parse_qs(parsed.query)
        if "uddg" in qs and qs["uddg"]:
            return qs["uddg"][0]
    if raw_url.startswith("//"):
        return f"https:{raw_url}"
    return raw_url


async def _fetch_page_content(
    client: httpx.AsyncClient,
    url: str,
    timeout: float = DEFAULT_PAGE_FETCH_TIMEOUT_SECONDS,
    max_chars: int = DEFAULT_MAX_CONTENT_CHARS,
) -> str | None:
    """
    Fetch and extract readable text from a destination webpage.

    Returns None if fetching or parsing fails, ensuring resilience.
    """
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        resp = await client.get(
            url, headers=headers, timeout=timeout, follow_redirects=True
        )
        if resp.status_code != 200:
            return None

        content_type = resp.headers.get("content-type", "").lower()
        if "text/html" not in content_type and "text/plain" not in content_type:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Strip clutter tags
        for tag in soup(
            [
                "script",
                "style",
                "nav",
                "header",
                "footer",
                "aside",
                "svg",
                "noscript",
                "form",
            ]
        ):
            tag.decompose()

        # Extract content from substantive paragraphs and headings
        blocks: list[str] = []
        for el in soup.find_all(["p", "article", "h1", "h2", "h3", "li"]):
            text = el.get_text(separator=" ", strip=True)
            if len(text) > 30:
                blocks.append(text)

        if not blocks:
            body = soup.find("body")
            if body:
                text = body.get_text(separator=" ", strip=True)
                return " ".join(text.split())[:max_chars] if text else None
            return None

        joined = " ".join(blocks)
        cleaned = " ".join(joined.split())
        return cleaned[:max_chars] if cleaned else None
    except Exception:
        # Graceful fallback: never fail the search if a single website is down/blocked
        return None


class DuckDuckGoSearch(BaseSearchEngine):
    """DuckDuckGo web search provider with optional page-content extraction."""

    def __init__(
        self,
        url: str = DEFAULT_DUCKDUCKGO_URL,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        page_fetch_timeout: float = DEFAULT_PAGE_FETCH_TIMEOUT_SECONDS,
        max_content_chars: int = DEFAULT_MAX_CONTENT_CHARS,
    ):
        self.url = url
        self.user_agent = user_agent
        self.timeout = timeout
        self.page_fetch_timeout = page_fetch_timeout
        self.max_content_chars = max_content_chars

    async def search(
        self,
        query: str,
        max_results: int = 5,
        fetch_content: bool = True,
        client: httpx.AsyncClient | None = None,
    ) -> list[SearchResult]:
        """
        Execute search query on DuckDuckGo HTML and extract results.

        Args:
            query: The search keywords or phrase.
            max_results: Maximum number of results to retrieve.
            fetch_content: Whether to fetch readable body text from target pages.
            client: Optional httpx.AsyncClient instance for connection pooling.

        Returns:
            A list of SearchResult objects with snippets and rich content.
        """
        data = {"q": query}
        headers = {"User-Agent": self.user_agent}

        try:
            if client is not None:
                res = await client.post(
                    self.url, data=data, headers=headers, timeout=self.timeout
                )
                if res.status_code != 200:
                    raise SearchServiceError(
                        f"DuckDuckGo returned status {res.status_code}"
                    )
                results = self._parse_html(res.text, max_results)
                if fetch_content and results:
                    await self._enrich_with_page_content(client, results)
                return results

            async with httpx.AsyncClient() as session:
                res = await session.post(
                    self.url, data=data, headers=headers, timeout=self.timeout
                )
                if res.status_code != 200:
                    raise SearchServiceError(
                        f"DuckDuckGo returned status {res.status_code}"
                    )
                results = self._parse_html(res.text, max_results)
                if fetch_content and results:
                    await self._enrich_with_page_content(session, results)
                return results

        except httpx.RequestError as e:
            raise SearchNetworkError(f"Search service unavailable: {e!s}") from e

    def _parse_html(self, html: str, max_results: int) -> list[SearchResult]:
        """Parse raw DuckDuckGo HTML into SearchResult objects."""
        try:
            soup = BeautifulSoup(html, "html.parser")
            results: list[SearchResult] = []

            for el in soup.find_all("div", class_="result"):
                title_el = el.find("a", class_="result__a")
                snippet_el = el.find(class_="result__snippet")

                if title_el and snippet_el:
                    title = title_el.get_text(separator=" ", strip=True)
                    raw_url = title_el.get("href", "")
                    url = _clean_url(raw_url)
                    # Use separator=" " to avoid squishing joined words
                    snippet = snippet_el.get_text(separator=" ", strip=True)

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

    async def _enrich_with_page_content(
        self,
        client: httpx.AsyncClient,
        results: list[SearchResult],
    ) -> None:
        """Concurrently fetch and attach page text to results."""
        tasks = [
            _fetch_page_content(
                client=client,
                url=r.url,
                timeout=self.page_fetch_timeout,
                max_chars=self.max_content_chars,
            )
            for r in results
        ]
        contents = await asyncio.gather(*tasks, return_exceptions=True)

        for r, content in zip(results, contents, strict=False):
            if isinstance(content, str) and content:
                r.content = content


async def web_search_duck_duck_go(
    query: str,
    max_results: int = 5,
    fetch_content: bool = True,
    client: httpx.AsyncClient | None = None,
) -> list[SearchResult]:
    """
    Convenience function to perform a DuckDuckGo search.

    Args:
        query: Search keywords or query.
        max_results: Maximum results to return.
        fetch_content: Whether to fetch readable page content.
        client: Optional httpx.AsyncClient instance.

    Returns:
        List of SearchResult objects.
    """
    engine = DuckDuckGoSearch()
    return await engine.search(
        query=query,
        max_results=max_results,
        fetch_content=fetch_content,
        client=client,
    )
