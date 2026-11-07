"""
Base search abstractions, data models, and exceptions for core search.

Defines the framework-agnostic search contract implemented by providers
such as DuckDuckGo.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


class SearchError(Exception):
    """Base exception for all search-related errors."""


class SearchServiceError(SearchError):
    """Raised when the upstream search provider returns an error response."""


class SearchNetworkError(SearchError):
    """Raised when network connectivity or request timeouts occur."""


class SearchParsingError(SearchError):
    """Raised when parsing search engine response content fails."""


@dataclass
class SearchResult:
    """Standardized search result item."""

    title: str
    url: str
    snippet: str
    content: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        """Convert result item to dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "content": self.content,
        }


class BaseSearchEngine(ABC):
    """
    Abstract base class for all search engines.

    Subclasses implement the asynchronous `search` method to query
    a specific search provider and return standardized `SearchResult` items.
    """

    @abstractmethod
    async def search(
        self,
        query: str,
        max_results: int = 5,
        fetch_content: bool = True,
    ) -> list[SearchResult]:
        """
        Execute search query asynchronously.

        Args:
            query: The search term or keywords.
            max_results: The maximum number of results to return.
            fetch_content: Whether to concurrently fetch readable webpage text.

        Returns:
            A list of SearchResult objects.

        Raises:
            SearchNetworkError: If the connection or request times out.
            SearchServiceError: If the search provider returns an error status.
            SearchParsingError: If results cannot be parsed.
            SearchError: For other general search failures.
        """
        pass


def get_search_engine(provider: str = "duckduckgo") -> BaseSearchEngine:
    """
    Factory function to retrieve a configured search engine instance.

    Args:
        provider: Provider identifier ('duckduckgo', etc.).

    Returns:
        An instance of BaseSearchEngine.
    """
    normalized = provider.strip().lower()
    if normalized in ("duckduckgo", "ddg"):
        from core.duckduckgo import DuckDuckGoSearch

        return DuckDuckGoSearch()

    raise ValueError(f"Unsupported search provider: {provider}")


async def search(
    query: str,
    max_results: int = 5,
    fetch_content: bool = True,
    provider: str = "duckduckgo",
) -> list[SearchResult]:
    """
    Execute a search with the specified provider.

    Args:
        query: The search query string.
        max_results: Maximum number of results to return.
        fetch_content: Whether to fetch readable page body content.
        provider: Search provider name (defaults to 'duckduckgo').

    Returns:
        List of SearchResult objects.
    """
    engine = get_search_engine(provider)
    return await engine.search(
        query, max_results=max_results, fetch_content=fetch_content
    )
