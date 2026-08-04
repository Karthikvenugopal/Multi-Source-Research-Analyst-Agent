"""Shared source clients and normalization for legacy and agentic modes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities import ArxivAPIWrapper, WikipediaAPIWrapper


class ToolSearchError(RuntimeError):
    """Raised when a source client cannot complete a search."""


class ResearchTools:
    """Own external clients and return provider-neutral search result dictionaries.

    The ``search`` method is the strict interface used by agentic tool bundles: it
    raises :class:`ToolSearchError` and never disguises an error as evidence. The
    three source-specific methods retain the v1 error/result shape for the legacy
    graph and its historical comparisons.
    """

    _LEGACY_CONFIDENCE = {"web": 0.8, "wikipedia": 0.9, "arxiv": 0.85}

    def __init__(
        self,
        web_limit: int = 5,
        wikipedia_limit: int = 3,
        arxiv_limit: int = 3,
    ) -> None:
        self.result_limits = {
            "web": max(1, web_limit),
            "wikipedia": max(1, wikipedia_limit),
            "arxiv": max(1, arxiv_limit),
        }
        self.tavily_tool = TavilySearchResults(max_results=self.result_limits["web"])
        self.wikipedia_api = WikipediaAPIWrapper(
            top_k_results=self.result_limits["wikipedia"]
        )
        self.arxiv_api = ArxivAPIWrapper(top_k_results=self.result_limits["arxiv"])

    def search(self, source: str, query: str) -> List[Dict[str, Any]]:
        """Search one source and return normalized evidence candidates.

        Results contain deterministic metadata only. Relevance or confidence is
        deliberately not inferred from the source type.
        """
        normalized_query = " ".join(query.split()).strip()
        if not normalized_query:
            raise ValueError("search query must not be empty")

        handlers = {
            "web": self._search_web,
            "wikipedia": self._search_wikipedia,
            "arxiv": self._search_arxiv,
        }
        handler = handlers.get(source)
        if handler is None:
            raise ValueError(f"unknown research source: {source}")
        try:
            return handler(normalized_query)[: self.result_limits[source]]
        except Exception as exc:
            if isinstance(exc, (ToolSearchError, ValueError)):
                raise
            raise ToolSearchError(f"{source} search failed: {exc}") from exc

    def _search_web(self, query: str) -> List[Dict[str, Any]]:
        raw = self.tavily_tool.invoke(query)
        rows = raw if isinstance(raw, list) else [{"content": str(raw)}]
        return [
            self._normalized(
                "web",
                title=str(row.get("title") or "Web search result"),
                url=str(row.get("url") or ""),
                content=str(row.get("content") or row.get("raw_content") or ""),
                published_at=row.get("published_date"),
                metadata={
                    key: value
                    for key, value in row.items()
                    if key not in {"title", "url", "content", "raw_content"}
                },
            )
            for row in rows
            if isinstance(row, Mapping)
            and str(row.get("content") or row.get("raw_content") or "").strip()
        ]

    def _search_wikipedia(self, query: str) -> List[Dict[str, Any]]:
        content = self.wikipedia_api.run(query)
        if not content:
            return []
        return [
            self._normalized(
                "wikipedia",
                title=f"Wikipedia: {query}",
                url=f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}",
                content=str(content),
            )
        ]

    def _search_arxiv(self, query: str) -> List[Dict[str, Any]]:
        content = self.arxiv_api.run(query)
        if not content:
            return []
        return [
            self._normalized(
                "arxiv",
                title=f"ArXiv: {query}",
                url=f"https://arxiv.org/search/?query={query.replace(' ', '+')}",
                content=str(content),
            )
        ]

    @staticmethod
    def _normalized(
        source_type: str,
        *,
        title: str,
        url: str,
        content: str,
        authors: List[str] | None = None,
        published_at: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return {
            "source_type": source_type,
            "title": title,
            "url": url,
            "authors": authors or [],
            "published_at": published_at,
            "content": content,
            "metadata": metadata or {},
        }

    # Legacy compatibility -------------------------------------------------

    def web_search(self, query: str) -> List[Dict[str, Any]]:
        """Run a web search using the historical v1 result contract."""
        return self._legacy_search("web", query)

    def wikipedia_search(self, query: str) -> List[Dict[str, Any]]:
        """Run a Wikipedia search using the historical v1 result contract."""
        return self._legacy_search("wikipedia", query)

    def arxiv_search(self, query: str) -> List[Dict[str, Any]]:
        """Run an ArXiv search using the historical v1 result contract."""
        return self._legacy_search("arxiv", query)

    def _legacy_search(self, source: str, query: str) -> List[Dict[str, Any]]:
        retrieved_at = datetime.now(timezone.utc).isoformat()
        try:
            return [
                {
                    "source": source,
                    "content": row["content"],
                    "url": row.get("url", ""),
                    "title": row.get("title", "Untitled"),
                    "confidence": self._LEGACY_CONFIDENCE[source],
                    "timestamp": retrieved_at,
                }
                for row in self.search(source, query)
            ] or [
                {
                    "source": source,
                    "content": f"No {source.title()} results found for: {query}",
                    "url": "",
                    "title": "No Results",
                    "confidence": 0.0,
                    "timestamp": retrieved_at,
                }
            ]
        except Exception as exc:
            return [{
                "source": source,
                "content": f"Error in {source} search: {exc}",
                "url": "",
                "title": "Search Error",
                "confidence": 0.0,
                "timestamp": retrieved_at,
            }]

    def calculate_research_quality(self, findings: List[Dict[str, Any]]) -> float:
        """Retain the original v1 heuristic for baseline compatibility only."""
        if not findings:
            return 0.0
        avg_confidence = sum(f.get("confidence", 0.0) for f in findings) / len(findings)
        sources = {f.get("source", "unknown") for f in findings}
        diversity_bonus = min(0.2, len(sources) * 0.05)
        quality_penalty = sum(0.1 for f in findings if f.get("confidence", 0.0) < 0.3)
        return min(1.0, max(0.0, avg_confidence + diversity_bonus - quality_penalty))
