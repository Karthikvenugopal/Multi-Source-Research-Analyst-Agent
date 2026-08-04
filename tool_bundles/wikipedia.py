"""Wikipedia-backed stable background research bundle."""

from __future__ import annotations

import re

from config import Config
from tool_bundles.base import BundleTool, EvaluationCase, ToolBundle
from tools import ResearchTools


def _wikipedia_query(query: str) -> str:
    cleaned = re.sub(r"^(?:what|who|where)\s+(?:is|was|are|were)\s+", "", query, flags=re.I)
    return " ".join(cleaned.replace("?", " ").split()[:12])


def build_wikipedia_bundle(tools: ResearchTools) -> ToolBundle:
    """Create the Wikipedia background capability."""
    return ToolBundle(
        name="wikipedia",
        source_type="wikipedia",
        description="Encyclopedic background and definitions from Wikipedia.",
        when_to_use="Stable facts, definitions, historical context, and entity background.",
        when_not_to_use="Breaking news, current prices, or primary scientific evidence.",
        tools=(BundleTool("wikipedia_search", "Search Wikipedia summaries.", lambda q: tools.search("wikipedia", q)),),
        evaluation_cases=(
            EvaluationCase("What is the Haber process?", True),
            EvaluationCase("What happened in markets today?", False),
        ),
        result_limit=Config.WIKIPEDIA_RESULT_LIMIT,
        timeout_seconds=Config.TOOL_TIMEOUT_SECONDS,
        query_transform=_wikipedia_query,
    )
