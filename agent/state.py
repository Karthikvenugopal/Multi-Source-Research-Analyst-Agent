"""Internal runtime state and public serialization."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from agent.models import ResearchRequirements
from evidence.ledger import EvidenceLedger
from evidence.models import EvidenceConflict


@dataclass
class RuntimeState:
    """Mutable state owned by one research session."""

    question: str
    requirements: ResearchRequirements = field(default_factory=ResearchRequirements)
    ledger: EvidenceLedger = field(default_factory=EvidenceLedger)
    tool_call_history: list[dict[str, Any]] = field(default_factory=list)
    queries_attempted: list[dict[str, str]] = field(default_factory=list)
    unresolved_gaps: list[str] = field(default_factory=list)
    conflicts: list[EvidenceConflict] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    tool_calls: int = 0
    approximate_context_tokens: int = 0
    start_time: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    elapsed_time: float = 0.0
    stop_reason: str = ""
    report: str = ""
    verification_result: dict[str, Any] = field(default_factory=dict)

    def to_result(self) -> dict[str, Any]:
        """Serialize the session with legacy-compatible convenience fields."""
        evidence = self.ledger.to_list()
        findings = [
            {
                "evidence_id": row["evidence_id"],
                "source": row["source_type"],
                "source_type": row["source_type"],
                "title": row["title"],
                "url": row["url"],
                "content": row["content"],
                "query": row["query"],
                "timestamp": row["retrieved_at"],
                "metadata": row["metadata"],
            }
            for row in evidence
        ]
        return {
            "mode": "agentic",
            "question": self.question,
            "research_requirements": self.requirements.requirements,
            "subquestions": self.requirements.subquestions,
            "evidence_ledger": evidence,
            "research_findings": findings,
            "tool_call_history": self.tool_call_history,
            "queries_attempted": self.queries_attempted,
            "unresolved_gaps": self.unresolved_gaps,
            "conflicts": [conflict.model_dump(mode="json") for conflict in self.conflicts],
            "iterations": self.iterations,
            "tool_calls": self.tool_calls,
            "approximate_context_tokens": self.approximate_context_tokens,
            "start_time": self.start_time,
            "elapsed_time": self.elapsed_time,
            "duration": self.elapsed_time,
            "stop_reason": self.stop_reason,
            "analysis": "",
            "final_report": self.report,
            "report": self.report,
            "verification_result": self.verification_result,
            "trace": self.trace,
            "evidence_coverage": self.ledger.coverage(),
            "sources_used": sorted({row["source_type"] for row in evidence}),
            "research_quality_score": 0.0,
        }
