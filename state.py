from typing import TypedDict, List, Dict


class ResearchFinding(TypedDict):
    source: str  # web, wikipedia, arxiv, etc.
    content: str
    url: str
    confidence: float  # 0-1 confidence score
    timestamp: str


class AgentState(TypedDict, total=False):
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
