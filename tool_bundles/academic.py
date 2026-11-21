"""ArXiv-backed technical and scientific research bundle."""

from __future__ import annotations

import re

from config import Config
from tool_bundles.base import BundleTool, EvaluationCase, ToolBundle
from tools import ResearchTools

_STOPWORDS = {
    "a", "an", "and", "are", "can", "compare", "does", "explain", "for", "how",
    "in", "is", "it", "of", "on", "the", "their", "to", "what", "which", "why",
    "with", "would",
}


def tailor_academic_query(query: str) -> str:
    """Convert a long natural-language question into concise technical terms."""
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9+.-]*", query)
    technical = [token for token in tokens if token.lower() not in _STOPWORDS]
    return " ".join(technical[:12]) or " ".join(tokens[:12])


def build_academic_bundle(tools: ResearchTools) -> ToolBundle:
    """Create the ArXiv academic research capability."""
    def search(query: str):
        rows = tools.search("arxiv", query)
        for row in rows:
            row = dict(row)
            row["metadata"] = {**row.get("metadata", {}), "provider": "arxiv"}
            yield row

    return ToolBundle(
        name="academic",
        source_type="academic",
        description="Primary and preprint research discovery through ArXiv.",
        when_to_use="Research papers, technical methods, scientific or machine-learning topics.",
        when_not_to_use="Basic entity facts, general history, or breaking non-academic news.",
        tools=(BundleTool("arxiv_search", "Search paper metadata and abstracts.", lambda q: list(search(q))),),
        evaluation_cases=(
            EvaluationCase("How does transformer self-attention work?", True),
            EvaluationCase("Who founded a company last week?", False),
        ),
        result_limit=Config.ARXIV_RESULT_LIMIT,
        timeout_seconds=Config.TOOL_TIMEOUT_SECONDS,
        query_transform=tailor_academic_query,
    )
