from typing import Any, Dict, List, TypedDict


class ResearchFinding(TypedDict):
    source: str  # web, wikipedia, arxiv, etc.
    content: str
    url: str
    confidence: float  # 0-1 confidence score
    timestamp: str


class EvidenceRecord(TypedDict, total=False):
    """Serialized evidence shape used by the agentic runtime."""

    evidence_id: str
    source_type: str
    title: str
    url: str
    authors: List[str]
    published_at: str | None
    retrieved_at: str
    query: str
    content: str
    content_hash: str
    relevance_score: float | None
    metadata: Dict[str, Any]


class AgentState(TypedDict, total=False):
    mode: str
    question: str
    research_plan: List[Dict[str, str]]  # planner output: [{source, query}, ...]
    research_findings: List[ResearchFinding]  # findings with metadata
    analysis: str  # the LLM's synthesis of the findings
    report: str  # the final, formatted answer
    next_node: str  # trace of the next node (linear graph; informational)
    research_quality_score: float  # overall quality of research (0-1)
    sources_used: List[str]  # which sources contributed findings
    start_time: str  # when research started
    current_focus: str  # what aspect of the question is in focus
    research_requirements: List[str]
    evidence_ledger: List[EvidenceRecord]
    tool_call_history: List[Dict[str, Any]]
    queries_attempted: List[Dict[str, str]]
    unresolved_gaps: List[str]
    conflicts: List[Dict[str, Any]]
    iterations: int
    tool_calls: int
    approximate_context_tokens: int
    elapsed_time: float
    stop_reason: str
    final_report: str
    verification_result: Dict[str, Any]
    trace: List[Dict[str, Any]]
    evidence_coverage: Dict[str, List[str]]
