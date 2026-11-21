"""Tavily-backed broad and recent web research bundle."""

from __future__ import annotations

from config import Config
from tool_bundles.base import BundleTool, EvaluationCase, ToolBundle
from tools import ResearchTools


def _web_query(query: str) -> str:
    return " ".join(query.replace("?", " ").split()[:24])


def build_web_bundle(tools: ResearchTools) -> ToolBundle:
    """Create the Tavily web research capability."""
    return ToolBundle(
        name="web",
        source_type="web",
        description="Broad web search backed by Tavily.",
        when_to_use=(
            "Recent events, companies, products, changing facts, or topics not "
            "adequately covered by specialized sources."
        ),
        when_not_to_use=(
            "Stable definitions alone or when primary academic papers are the "
            "main evidence requirement."
        ),
        tools=(BundleTool("tavily_search", "Search indexed web pages.", lambda q: tools.search("web", q)),),
        evaluation_cases=(
            EvaluationCase("What changed in a product release this month?", True),
            EvaluationCase("Define photosynthesis.", False),
        ),
        result_limit=Config.WEB_RESULT_LIMIT,
        timeout_seconds=Config.TOOL_TIMEOUT_SECONDS,
        query_transform=_web_query,
    )
