from typing import TypedDict, List, Annotated, Dict, Any
import operator
from datetime import datetime

class ResearchFinding(TypedDict):
    source: str  # web, wikipedia, arxiv, etc.
    content: str
    url: str
    confidence: float  # 0-1 confidence score
    timestamp: str

class AgentState(TypedDict):
    question: str
    research_findings: List[ResearchFinding]  # Enhanced findings with metadata
    analysis: str  # The LLM's synthesis of the findings
    report: str  # The final, formatted answer
    iterations: Annotated[int, operator.add]  # Tracks how many loops it's done
    next_node: str  # The next node to execute
    search_query: str  # Supervisor's reformulated query for the next search
    research_quality_score: float  # Overall quality of research (0-1)
    sources_used: List[str]  # Track which sources have been used
    max_iterations_reached: bool  # Safety flag
    start_time: str  # When research started
    current_focus: str  # What aspect of the question we're currently researching