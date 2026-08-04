"""Deterministic budgets and fallbacks for malformed model output."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from agent.models import ResearchDecision, ResearchRequirements
from config import Config


@dataclass(frozen=True)
class RuntimeLimits:
    """Hard safety limits enforced independently of model decisions."""

    max_iterations: int = 5
    max_tool_calls: int = 6
    tool_timeout_seconds: float = 20.0
    max_elapsed_seconds: float = 120.0
    max_context_chars: int = 14_000
    max_evidence_chars: int = 4_000
    max_consecutive_no_new: int = 2

    @classmethod
    def from_config(cls) -> "RuntimeLimits":
        return cls(
            max_iterations=Config.MAX_ITERATIONS,
            max_tool_calls=Config.MAX_TOOL_CALLS,
            tool_timeout_seconds=Config.TOOL_TIMEOUT_SECONDS,
            max_elapsed_seconds=Config.MAX_ELAPSED_SECONDS,
            max_context_chars=Config.MAX_CONTEXT_CHARS,
            max_evidence_chars=Config.MAX_EVIDENCE_CHARS,
        )


class HeuristicFallbackPolicy:
    """Conservative fallback used only when structured model calls fail."""

    _ACADEMIC = {
        "algorithm", "academic", "arxiv", "machine learning", "method", "paper",
        "research", "scientific", "study", "technical", "transformer",
    }
    _RECENT = {
        "current", "latest", "new", "news", "price", "recent", "release", "today",
        "this month", "this year",
    }

    def analyze(self, question: str) -> ResearchRequirements:
        """Extract small, transparent requirements without pretending model insight."""
        requirements = [f"Answer the question: {question.strip()}"]
        lowered = question.lower()
        if any(term in lowered for term in ("compare", " versus ", " vs ", "difference")):
            requirements.append("Gather comparable evidence for every side of the comparison.")
        if any(term in lowered for term in self._RECENT):
            requirements.append("Verify time-sensitive claims with recent web evidence.")
        return ResearchRequirements(requirements=requirements, subquestions=[])

    def decide(self, payload: dict[str, Any]) -> ResearchDecision:
        """Select a sensible unused bundle/query or stop on basic sufficiency."""
        question = payload["question"]
        lowered = question.lower()
        names = list(payload["bundle_names"])
        attempts = {(row["bundle"], row["normalized_query"]) for row in payload["queries_attempted"]}
        evidence_count = int(payload["evidence_count"])
        used = {row["bundle"] for row in payload["queries_attempted"]}
        comparative = any(term in lowered for term in ("compare", " versus ", " vs ", "difference"))
        technical = any(term in lowered for term in self._ACADEMIC)
        simple = bool(re.match(r"^(?:what|who|where)\s+(?:is|was|are|were)\b", lowered))
        target = 2 if (comparative or technical) else 1
        if evidence_count >= target:
            return ResearchDecision(
                action="finish",
                action_summary="The available evidence meets the fallback sufficiency threshold.",
                unresolved_gaps=payload["unresolved_gaps"],
            )

        if any(term in lowered for term in self._RECENT):
            preference = ["web", "wikipedia", "academic"]
        elif technical:
            preference = ["academic", "web", "wikipedia"]
        elif simple:
            preference = ["wikipedia", "web", "academic"]
        else:
            preference = ["web", "wikipedia", "academic"]
        preference.extend(name for name in names if name not in preference)
        normalized_question = " ".join(question.split()).casefold()
        for name in preference:
            if name in names and name not in used and (name, normalized_question) not in attempts:
                return ResearchDecision(
                    action="search",
                    bundle=name,
                    query=question,
                    action_summary=f"Use {name} for the next unmet evidence requirement.",
                    unresolved_gaps=payload["unresolved_gaps"] or ["More supporting evidence is needed."],
                )
        return ResearchDecision(
            action="finish",
            action_summary="No useful untried fallback search remains.",
            unresolved_gaps=payload["unresolved_gaps"] or ["Evidence remains incomplete."],
        )
